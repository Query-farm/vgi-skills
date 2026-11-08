import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


verify = module("verify_worker", ROOT / "skills/vgi-worker/scripts/verify_worker.py")
pack = module("package_worker", ROOT / "skills/vgi-package/scripts/package_worker.py")


class VerifierTests(unittest.TestCase):
    def manifest(self, root, **overrides):
        spec = {"schema_version": 1, "catalog": "demo", "worker": ["python", "worker with space.py"],
                "checks": [{"sql": "SELECT 42", "rows": [[42]]}]}
        spec.update(overrides)
        (root / "vgi-worker.json").write_text(json.dumps(spec))

    def test_manifest_requires_expected_results(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.manifest(root, checks=[{"sql": "SELECT 42"}])
            with self.assertRaisesRegex(ValueError, "expected rows"):
                verify.read_manifest(root)

    def test_rejects_catalog_injection(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.manifest(root, catalog="demo'; DROP TABLE x; --")
            with self.assertRaisesRegex(ValueError, "SQL identifier"):
                verify.read_manifest(root)

    def test_argv_keeps_spaces(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.manifest(root)
            self.assertEqual(verify.read_manifest(root)["worker"][1], "worker with space.py")
            self.assertEqual(verify.sql_string("a'b"), "'a''b'")

    def test_invalid_manifest_is_machine_readable_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.manifest(root, worker="python worker.py")
            result = subprocess.run([sys.executable, str(ROOT / "skills/vgi-test/scripts/verify_worker.py"), "--project", folder], text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            report = json.loads(result.stdout)
            self.assertEqual(report["status"], "failed")
            self.assertIn("argv", report["error"])

    def test_wrong_expected_rows_fail_real_engine(self):
        try:
            import duckdb
        except ImportError:
            self.skipTest("Run with uv run --with duckdb==2.0.0 for real engine checks")
        fixture = ROOT / "examples/python-double"
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.manifest(root, worker=["uv", "run", str(fixture / "worker.py")], checks=[{"sql": "SELECT demo.main.double(21)", "rows": [[999]]}])
            result = subprocess.run([sys.executable, str(ROOT / "skills/vgi-worker/scripts/verify_worker.py"), "--project", folder], text=True, capture_output=True, timeout=120)
            report = json.loads(result.stdout)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(report["checks"][0]["rows"], [[42]])
            self.assertEqual(report["checks"][0]["status"], "failed")

    def test_timeout_returns_failure(self):
        try:
            import duckdb
        except ImportError:
            self.skipTest("Run with duckdb for real process timeout check")
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "stuck.py").write_text("import time\ntime.sleep(60)\n")
            self.manifest(root, worker=[sys.executable, "stuck.py"])
            result = subprocess.run([sys.executable, str(ROOT / "skills/vgi-worker/scripts/verify_worker.py"), "--project", folder, "--timeout", "1"], text=True, capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 1)
            self.assertIn("timed out", json.loads(result.stdout)["error"])


class AttachOptionTests(unittest.TestCase):
    def manifest(self, root, **overrides):
        VerifierTests.manifest(self, root, **overrides)

    def test_literals_and_env_render_with_env_redacted(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.manifest(root, attach_options={"api_url": "http://x/'y", "retries": 3, "strict": True, "token": {"env": "T"}})
            spec = verify.read_manifest(root)
            options, secrets = verify.attach_options(spec, {"T": "xoxb-secret"})
            self.assertEqual(secrets, ["xoxb-secret"])
            real = verify.attach_sql("demo", "w", options)
            shown = verify.attach_sql("demo", "w", options, display=True)
            self.assertIn("api_url 'http://x/''y'", real)
            self.assertIn("retries 3", real)
            self.assertIn("strict true", real)
            self.assertIn("token 'xoxb-secret'", real)
            self.assertIn("token <redacted>", shown)
            self.assertNotIn("xoxb-secret", shown)

    def test_missing_env_names_the_variable(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.manifest(root, attach_options={"token": {"env": "NOT_SET_ANYWHERE"}})
            with self.assertRaisesRegex(ValueError, "NOT_SET_ANYWHERE"):
                verify.attach_options(verify.read_manifest(root), {})

    def test_rejects_bad_option_names_and_values(self):
        for options, message in [
            ({"bad name": "x"}, "SQL identifier"),
            ({"location": "x"}, "set by the verifier"),
            ({"token": {"env": "A", "extra": 1}}, "literal or"),
            ({"token": None}, "must not be null"),
            ({"token": ["x"]}, "must be a string"),
            (["token"], "must be an object"),
        ]:
            with self.subTest(options=options), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                self.manifest(root, attach_options=options)
                with self.assertRaisesRegex(ValueError, message):
                    verify.read_manifest(root)

    def test_scrub_removes_secrets_everywhere(self):
        report = {"error": "bad token xoxb-1", "checks": [{"rows": [["xoxb-1"]]}], "n": 1}
        self.assertEqual(verify.scrub(report, ["xoxb-1"]),
                         {"error": "bad token <redacted>", "checks": [{"rows": [["<redacted>"]]}], "n": 1})

    def test_missing_env_is_machine_readable_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.manifest(root, attach_options={"token": {"env": "VGI_VERIFIER_TEST_UNSET"}})
            result = subprocess.run([sys.executable, str(ROOT / "skills/vgi-worker/scripts/verify_worker.py"), "--project", folder], text=True, capture_output=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn("VGI_VERIFIER_TEST_UNSET", json.loads(result.stdout)["error"])

    def test_options_reach_the_engine_and_never_leak(self):
        try:
            import duckdb
        except ImportError:
            self.skipTest("Run with uv run --with duckdb==2.0.0 for real engine checks")
        # The fixture declares no attach options, so the extension must reject the
        # option by name: proof it reached ATTACH. The value must not appear anywhere.
        fixture = ROOT / "examples/python-double"
        secret = "s3cr3t-value-that-must-not-leak"
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.manifest(root, worker=["uv", "run", str(fixture / "worker.py")],
                          attach_options={"token": {"env": "VGI_VERIFIER_TEST_TOKEN"}},
                          checks=[{"sql": "SELECT demo.main.double(21)", "rows": [[42]]}])
            env = {**__import__("os").environ, "VGI_VERIFIER_TEST_TOKEN": secret}
            result = subprocess.run([sys.executable, str(ROOT / "skills/vgi-worker/scripts/verify_worker.py"), "--project", folder],
                                    text=True, capture_output=True, timeout=120, env=env)
            self.assertNotIn(secret, result.stdout + result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(result.returncode, 1, report)
            self.assertIn("token", report["error"])


class PackagingTests(unittest.TestCase):
    def test_reproducible_archive_and_permissions(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "worker.sh").write_text("#!/bin/sh\nexit 0\n")
            (root / "worker.sh").chmod(0o755)
            first = pack.package(root, ["worker.sh"], root / "one", "demo", "0.1.0")
            second = pack.package(root, ["worker.sh"], root / "two", "demo", "0.1.0")
            self.assertEqual(first["sha256"], second["sha256"])
            with zipfile.ZipFile(root / "one" / first["artifact"]) as bundle:
                self.assertEqual(bundle.namelist(), ["worker.sh"])
                self.assertEqual(bundle.getinfo("worker.sh").external_attr >> 16, 0o755)

    def test_refuses_paths_and_credentials(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / ".env").write_text("TOKEN=test")
            for include in [["../outside"], [str(root / ".env")], [".env"]]:
                with self.assertRaises(ValueError):
                    pack.package(root, include, root / "dist", "demo", "0.1.0")

    def test_refuses_symlink_and_missing_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "real.py").write_text("pass")
            (root / "link.py").symlink_to(root / "real.py")
            for include in [["link.py"], ["absent.py"]]:
                with self.assertRaises(ValueError):
                    pack.package(root, include, root / "dist", "demo", "0.1.0")


if __name__ == "__main__":
    unittest.main()
