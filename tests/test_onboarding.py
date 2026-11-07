"""Verify the data and service behind the independent onboarding checks."""
import json
from pathlib import Path
import sys
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import urlopen

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from onboarding_fixtures import Service, ThreadingHTTPServer

class FixtureServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),Service)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.base=f'http://127.0.0.1:{cls.server.server_port}'
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join()
    def fetch(self,path):
        with urlopen(self.base+path,timeout=5) as response:return json.load(response)
    def test_pagination_reaches_all_records(self):
        page=self.fetch('/normal/tickets?page=1');rows=page['tickets']
        while page['next']:
            with urlopen(page['next'],timeout=5) as response:page=json.load(response)
            rows+=page['tickets']
        self.assertEqual([x['ticket_id'] for x in rows],[101,102,103,104])
    def test_empty_and_holdout_are_distinct(self):
        self.assertEqual(self.fetch('/empty/tickets')['tickets'],[])
        self.assertEqual(self.fetch('/holdout/tickets')['tickets'][0]['ticket_id'],907)
    def test_error_fixtures_return_real_http_errors(self):
        for variant,status in [('error',503),('rate-limit',429)]:
            with self.assertRaises(HTTPError) as caught:self.fetch(f'/{variant}/tickets')
            self.assertEqual(caught.exception.code,status)
            caught.exception.close()
    def test_large_fixture_crosses_batch_boundary(self):
        page=self.fetch('/large/tickets');rows=page['tickets']
        while page['next']:
            with urlopen(page['next'],timeout=5) as response:page=json.load(response)
            rows+=page['tickets']
        self.assertEqual(len(rows),10001)
        self.assertEqual(sum(x['ticket_id'] for x in rows),50015001)
    def test_loop_fixture_repeats_its_own_url(self):
        self.assertEqual(self.fetch('/loop/tickets?page=1')['next'],self.base+'/loop/tickets?page=1')

if __name__=='__main__':unittest.main()
