"""VGI worker exposing JPEG photo metadata as the SQL table function photos.main.files(folder).

Read-only: files are opened with O_RDONLY | O_NOFOLLOW and never written. Only regular
*.jpg / *.jpeg files directly inside ``folder`` are read (no recursion, symlinks skipped).
Diagnostics go to stderr; stdout carries the Arrow protocol.
"""

from __future__ import annotations

import json
import logging
import os
import stat
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, Any, ClassVar

import pyarrow as pa
from PIL import Image, UnidentifiedImageError

from vgi import Arg, Worker
from vgi.catalog import Catalog, Schema
from vgi.table_function import (
    OutputCollector,
    ProcessParams,
    TableFunctionGenerator,
    bind_fixed_schema,
    init_single_worker,
)

log = logging.getLogger("photo_worker")

JPEG_EXTENSIONS = (".jpg", ".jpeg")
BATCH_SIZE = 256

# EXIF tag ids
TAG_MODEL = 0x0110
TAG_DATETIME = 0x0132
TAG_EXIF_IFD = 0x8769
TAG_GPS_IFD = 0x8825
TAG_DATETIME_ORIGINAL = 0x9003
TAG_DATETIME_DIGITIZED = 0x9004
GPS_LAT_REF, GPS_LAT, GPS_LON_REF, GPS_LON = 1, 2, 3, 4

OUTPUT_SCHEMA = pa.schema(
    [
        pa.field("path", pa.string(), nullable=False),
        pa.field("size_bytes", pa.int64(), nullable=False),
        pa.field("camera_model", pa.string()),
        pa.field("taken_at", pa.timestamp("us")),
        pa.field("latitude", pa.float64()),
        pa.field("longitude", pa.float64()),
    ]
)


class CorruptPhoto(Exception):
    """The file has a JPEG extension but cannot be decoded."""


# ---------------------------------------------------------------- EXIF parsing


def _clean_str(value: Any) -> str | None:
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")
    if not isinstance(value, str):
        return None
    value = value.replace("\x00", "").strip()
    return value or None


def _parse_datetime(value: Any) -> datetime | None:
    text = _clean_str(value)
    if text is None:
        return None
    for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y:%m:%d %H:%M:%S.%f"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None  # e.g. "0000:00:00 00:00:00" placeholder


def _gps_coordinate(dms: Any, ref: Any, positive: str, negative: str) -> float | None:
    try:
        degrees, minutes, seconds = (float(x) for x in dms)
    except (TypeError, ValueError, ZeroDivisionError):
        return None
    value = degrees + minutes / 60.0 + seconds / 3600.0
    ref_text = (_clean_str(ref) or "").upper()
    if ref_text == negative:
        value = -value
    elif ref_text not in ("", positive):
        return None
    if value != value:  # NaN from 0/0 rationals
        return None
    return value


def read_metadata(path: str) -> dict[str, Any]:
    """Return one output row for ``path``. Raises CorruptPhoto for undecodable files."""
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(fd, "rb") as fh:
        size = os.fstat(fh.fileno()).st_size
        try:
            with Image.open(fh, formats=["JPEG"]) as img:
                exif = img.getexif()
                # Decode at reduced scale to detect truncated/corrupt data cheaply.
                img.draft("RGB", (64, 64))
                img.load()
        except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as exc:
            raise CorruptPhoto(str(exc)) from exc

    exif_ifd = exif.get_ifd(TAG_EXIF_IFD) if exif else {}
    gps_ifd = exif.get_ifd(TAG_GPS_IFD) if exif else {}

    taken_at = None
    for raw in (
        exif_ifd.get(TAG_DATETIME_ORIGINAL),
        exif_ifd.get(TAG_DATETIME_DIGITIZED),
        exif.get(TAG_DATETIME) if exif else None,
    ):
        taken_at = _parse_datetime(raw)
        if taken_at is not None:
            break

    lat = lon = None
    if GPS_LAT in gps_ifd and GPS_LON in gps_ifd:
        lat = _gps_coordinate(gps_ifd[GPS_LAT], gps_ifd.get(GPS_LAT_REF), "N", "S")
        lon = _gps_coordinate(gps_ifd[GPS_LON], gps_ifd.get(GPS_LON_REF), "E", "W")
        if lat is None or lon is None or not (-90 <= lat <= 90 and -180 <= lon <= 180):
            lat = lon = None

    return {
        "path": path,
        "size_bytes": size,
        "camera_model": _clean_str(exif.get(TAG_MODEL)) if exif else None,
        "taken_at": taken_at,
        "latitude": lat,
        "longitude": lon,
    }


def list_jpegs(folder: str) -> list[str]:
    """Sorted absolute paths of regular, non-symlink JPEG files directly in ``folder``."""
    folder = os.path.abspath(folder)
    names = []
    with os.scandir(folder) as it:
        for entry in it:
            if not entry.name.lower().endswith(JPEG_EXTENSIONS):
                continue
            if entry.is_symlink() or not entry.is_file(follow_symlinks=False):
                continue
            names.append(os.path.join(folder, entry.name))
    return sorted(names)


def rows_for(paths: list[str]) -> list[dict[str, Any]]:
    rows = []
    for path in paths:
        try:
            rows.append(read_metadata(path))
        except CorruptPhoto as exc:
            print(f"photo_worker: skipping corrupt file {path}: {exc}", file=sys.stderr, flush=True)
        except OSError as exc:  # vanished, permission denied, became a symlink
            print(f"photo_worker: skipping unreadable file {path}: {exc}", file=sys.stderr, flush=True)
    return rows


# ---------------------------------------------------------------- VGI function


@dataclass(slots=True, frozen=True, kw_only=True)
class FilesArgs:
    """Arguments for ``files``."""

    folder: Annotated[str | None, Arg(0, doc="Folder containing .jpg/.jpeg files (not recursive)")]


@dataclass
class FilesState:
    """Remaining file paths to process; encoded as JSON between ticks."""

    paths: list[str]
    index: int = 0

    def serialize_to_bytes(self) -> bytes:
        return json.dumps({"p": self.paths, "i": self.index}).encode()

    @classmethod
    def deserialize_from_bytes(cls, data: bytes) -> FilesState:
        obj = json.loads(data)
        return cls(paths=obj["p"], index=obj["i"])


@init_single_worker
@bind_fixed_schema
class Files(TableFunctionGenerator[FilesArgs, FilesState]):
    """List JPEG photos in a folder with camera model, capture time and GPS position.

    One row per decodable .jpg/.jpeg directly inside the folder. Photos without EXIF
    get NULL metadata; corrupt files are skipped with a diagnostic on stderr.
    A NULL folder returns no rows.
    """

    FIXED_SCHEMA: ClassVar[pa.Schema] = OUTPUT_SCHEMA

    class Meta:
        name = "files"
        description = (
            "JPEG photo metadata (path, size_bytes, camera_model, taken_at, latitude, longitude) "
            "for files directly inside a folder. NULL folder returns no rows."
        )

    @classmethod
    def initial_state(cls, params: ProcessParams[FilesArgs]) -> FilesState:
        folder = params.args.folder
        if folder is None:
            return FilesState(paths=[])
        if not os.path.isdir(folder):
            raise ValueError(f"files(): folder does not exist or is not a directory: {folder}")
        return FilesState(paths=list_jpegs(folder))

    @classmethod
    def process(cls, params: ProcessParams[FilesArgs], state: FilesState, out: OutputCollector) -> None:
        if state.index >= len(state.paths):
            out.finish()
            return
        chunk = state.paths[state.index : state.index + BATCH_SIZE]
        state.index += len(chunk)
        rows = rows_for(chunk)
        out.emit(pa.RecordBatch.from_pylist(rows, schema=params.output_schema))


class PhotosWorker(Worker):
    """Worker exposing the ``photos`` catalog."""

    catalog = Catalog(name="photos", schemas=[Schema(path=["main"], functions=[Files])])


if __name__ == "__main__":
    logging.basicConfig(stream=sys.stderr, level=logging.WARNING)
    PhotosWorker().run()
