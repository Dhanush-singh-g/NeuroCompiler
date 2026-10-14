"""Evidence presentation regressions; no native timing or model fitting."""
import copy
import json
import tempfile
import threading
import unittest
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

from scripts.build_dashboard import STUDY, build_data, correctness_status, export, normalized_stat
from scripts.serve_dashboard import Handler


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def put(self, name, data):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data))

    def stat(self):
        return {'speedup': 1., 'interval': [.995, 1.005], 'blocks': [1., 1., 1.],
                'order_log_difference': 0., 'block_order_log_differences': [0., 0., 0.],
                'control_pass': True}

    def test_absent_evidence_never_becomes_zero_gain_or_success(self):
        data = build_data(self.root)
        self.assertIsNone(data['corpus']['correctness_cells'])
        self.assertEqual(data['measurement']['status'], 'unavailable')
        self.assertIsNone(data['measurement']['pairs'])
        self.assertIsNone(data['model']['default'])
        self.assertIsNone(data['headroom'])
        self.assertTrue(data['warnings'])

    def test_invalid_json_is_unavailable_and_identified(self):
        path = self.root / STUDY / 'preflight.json'
        path.parent.mkdir(parents=True)
        path.write_text('{')
        data = build_data(self.root)
        self.assertEqual(next(s['status'] for s in data['sources'] if s['path'].endswith('preflight.json')), 'invalid')
        self.assertIsNone(data['corpus']['training_inputs'])

    def test_frozen_preflight_mismatch_cannot_display_correctness_success(self):
        self.put(STUDY + '/frozen.json', {'preflight_sha256': '0'*64, 'training_cases': ['test']})
        self.put(STUDY + '/preflight.json', {'complete': True, 'manifests': {'test': {'program': 'fake'}}})
        data = build_data(self.root)
        self.assertEqual(data['corpus']['status'], 'unavailable')
        self.assertFalse(data['programs'])
        self.assertTrue(any('differs from frozen' in w for w in data['warnings']))

    def test_control_gate_includes_order_bias_even_inside_ratio_bounds(self):
        raw = self.stat()
        raw['block_order_log_differences'][1] = .2
        raw['control_pass'] = False
        stat = normalized_stat(raw, .03)
        self.assertFalse(stat['passed'])
        self.assertEqual(stat['reasons'], ['Starting-order bias'])

    def test_false_control_decision_and_nonfinite_values_are_rejected(self):
        raw = self.stat()
        raw['control_pass'] = False
        with self.assertRaises(ValueError): normalized_stat(raw, .03)
        raw = self.stat()
        raw['interval'][0] = float('nan')
        with self.assertRaises(ValueError): normalized_stat(raw, .03)

    def test_development_stays_unrun_and_does_not_inflate_training(self):
        self.put(STUDY + '/frozen.json', {'training_cases': [], 'development_cases': ['jsonh_flat', 'jsonh_nested']})
        self.put(STUDY + '/preflight.json', {'complete': True, 'manifests': {}})
        data = build_data(self.root)
        self.assertEqual(data['corpus']['training_programs'], 0)
        self.assertEqual(data['corpus']['development_programs'], 1)
        self.assertEqual(len(data['programs']), 1)
        self.assertTrue(all(s == 'unrun' for i in data['programs'][0]['inputs'] for s in i['settings'].values()))

    def test_correctness_requires_complete_pairs_and_both_oracles(self):
        good = {'expected': {'checksum': 'abc', 'values': 1}, 'correctness': {'O3': {'samples': [
            {'left': {'checksum': 'abc', 'values': 1}, 'right': {'checksum': 'abc', 'values': 1}} for _ in range(2)]}}}
        self.assertEqual(correctness_status(good, 'O3'), 'passed')
        bad = copy.deepcopy(good)
        bad['correctness']['O3']['samples'][1]['right']['checksum'] = 'wrong'
        self.assertEqual(correctness_status(bad, 'O3'), 'failed')
        good['correctness']['O3']['samples'].pop()
        self.assertEqual(correctness_status(good, 'O3'), 'unavailable')

    def test_only_one_qualified_probe_clock_does_not_create_gain(self):
        self.put('results/persistent_probe.json', {'complete': True, 'summary': {'statistics': {
            'cpu': {'qualified': True, 'confirmed_gain': True},
            'wall': {'qualified': False, 'confirmed_gain': False}}}})
        self.assertIsNone(build_data(self.root)['headroom'])

    def test_export_escapes_script_payload_and_removes_stale_reports(self):
        self.put('results/expanded_source_pins.json', {'jsonh': {'repository': '</script><script>alert(1)</script>'}})
        self.put(STUDY + '/frozen.json', {'development_cases': ['jsonh_flat']})
        output = self.root / 'site'
        (output / 'reports').mkdir(parents=True)
        (output / 'reports' / 'FINAL_ASSESSMENT.md').write_text('stale')
        export(self.root, output)
        self.assertNotIn('</script>', (output / 'results.js').read_text())
        self.assertFalse((output / 'reports' / 'FINAL_ASSESSMENT.md').exists())
        self.assertEqual(json.loads((output / 'data.json').read_text())['programs'][0]['pin']['repository'], '</script><script>alert(1)</script>')


class ServerTests(unittest.TestCase):
    def test_asset_allowlist_blocks_evidence_and_path_traversal(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'index.html').write_text('<h1>Dashboard</h1>')
            (root / 'secret.txt').write_text('private')
            handler = partial(Handler, directory=str(root))
            server = ThreadingHTTPServer(('127.0.0.1', 0), handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                address = f'http://127.0.0.1:{server.server_port}'
                with urlopen(address + '/') as response:
                    self.assertEqual(response.read(), b'<h1>Dashboard</h1>')
                    self.assertEqual(response.headers['X-Content-Type-Options'], 'nosniff')
                for path in ('/secret.txt', '/%2e%2e/secret.txt', '/.git/config', '/results/expanded_native_20261012/gate.json'):
                    with self.assertRaises(HTTPError) as caught: urlopen(address + path)
                    self.assertEqual(caught.exception.code, 404)
            finally:
                server.shutdown()
                server.server_close()
                thread.join()


if __name__ == '__main__':
    unittest.main()
