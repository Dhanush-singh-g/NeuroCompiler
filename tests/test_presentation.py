"""Live-app contracts and native integration; no frozen research experiments."""
import hashlib
import json
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

from src.benchmarks.compact import MENU
from src.presentation.model import load_model, predict
from src.presentation.server import Application, Handler, markdown_report, toolchain, validate_input
from src.presentation.worker import pair_summary
from src.presentation.summary import comparison_summary, decision_diagnostics


class InputTests(unittest.TestCase):
    def test_no_shell_expansion_and_real_stdin(self):
        data = validate_input({'source':'int main(void){return 0;}', 'arguments':'"a b" $(touch) ;', 'stdin':'21 34\n'})
        self.assertEqual(data['arguments'], ['a b', '$(touch)', ';'])
        self.assertEqual(data['stdin'], '21 34\n')

    def test_input_boundaries(self):
        for value in [[], {}, {'source':True}, {'source':'x'*49153}, {'source':'x\x00'},
                      {'source':'x','arguments':'"'}, {'source':'x','stdin':[]},
                      {'source':'x','iterations':True}, {'source':'x','iterations':-1},
                      {'source':'x','arguments':'x '*17}]:
            with self.subTest(value=str(value)[:80]), self.assertRaises(ValueError):
                validate_input(value)

    def test_model_contract(self):
        m = load_model()
        self.assertEqual(len(m['coefficients']), 156)
        self.assertEqual(m['approved_policy'], 'O3')
        self.assertFalse(m['deployment_qualified'])
        self.assertEqual(m['real_training_programs'], 7)
        self.assertEqual(m['synthetic_training_programs'], 6)

    def test_invalid_model_thresholds_are_rejected(self):
        from unittest.mock import patch
        model=load_model()
        with tempfile.TemporaryDirectory() as scratch:
            path=Path(scratch)/'model.json'
            for key,value in [('floor',-1),('margin',float('nan'))]:
                changed=dict(model);changed[key]=value
                path.write_text(json.dumps(changed))
                with patch('src.presentation.model.MODEL_PATH',path), self.assertRaises(ValueError):
                    load_model()


class MeasurementTests(unittest.TestCase):
    def samples(self, ratio=1., short=False, order=False):
        out = []
        for i in range(12):
            duration = .001 if short else .05
            actual = ratio * (1.1 if order and i % 2 else 1.)
            out.append({'block':i//4,'candidate_first':bool(i%2),
                        'baseline':{'cpu':duration,'wall':duration*1.1},
                        'candidate':{'cpu':duration/actual,'wall':duration*1.1/actual}})
        return out

    def test_identical_control_and_real_effect(self):
        self.assertTrue(pair_summary(self.samples(), control=True)['qualified'])
        effect = pair_summary(self.samples(2.))
        self.assertTrue(effect['qualified'])
        self.assertAlmostEqual(effect['clocks']['cpu']['speedup'], 2.)
        self.assertAlmostEqual(effect['clocks']['cpu']['median_seconds'], .025)

    def test_short_noisy_or_biased_controls_fail(self):
        self.assertFalse(pair_summary(self.samples(short=True), control=True)['qualified'])
        self.assertFalse(pair_summary(self.samples(1.1), control=True)['qualified'])
        self.assertFalse(pair_summary(self.samples(order=True))['qualified'])

    def test_identical_code_does_not_become_fake_regression(self):
        control=pair_summary(self.samples(.9), control=True)
        control['verdict']='inconclusive'
        decision={'choice':'O3','aliases':{'O3':'O3'}}
        s=comparison_summary(decision,{'O3':control})['clocks']['cpu']
        self.assertEqual(s['status'],'unchanged')
        self.assertEqual(s['time_change_percent'],0.)
        self.assertFalse(s['qualified'])
        self.assertIsNone(s['gap_to_best_percent'])
        self.assertTrue(s['failure_reasons'])

    def test_time_percentage_and_gap_have_correct_denominator(self):
        control=pair_summary(self.samples(),control=True);control['verdict']='same_binary'
        slow=pair_summary(self.samples(.8));slow['verdict']='slower_in_demo'
        fast=pair_summary(self.samples(1.25));fast['verdict']='faster_in_demo'
        cells={'O3':control,'slow':slow,'fast':fast}
        decision={'choice':'slow','aliases':{c:c for c in cells}}
        s=comparison_summary(decision,cells)['clocks']['cpu']
        self.assertEqual(s['status'],'slower')
        self.assertAlmostEqual(s['time_change_percent'],25.)
        self.assertAlmostEqual(s['gap_to_best_percent'],56.25)
        decision['choice']='fast'
        s=comparison_summary(decision,cells)['clocks']['cpu']
        self.assertEqual(s['status'],'faster')
        self.assertAlmostEqual(s['time_change_percent'],-20.)
        self.assertAlmostEqual(s['gap_to_best_percent'],0.)
        varying=self.samples(.8)
        varying[0]['baseline']['cpu'] *= 8
        irregular=pair_summary(varying);irregular['verdict']='inconclusive'
        decision['choice']='irregular';decision['aliases']['irregular']='irregular'
        measured=comparison_summary(decision,{'O3':control,'irregular':irregular})['clocks']['cpu']
        self.assertAlmostEqual(measured['baseline_ms']/measured['neurocompiler_ms'],measured['speedup'])

    def test_different_binary_and_identical_menu_are_distinguished(self):
        s={'O3':0.,'candidate':-.1}
        self.assertEqual(decision_diagnostics(s,{'O3':'O3','candidate':'O3'},'O3')['code'],'identical_menu')
        d=decision_diagnostics(s,{'O3':'O3','candidate':'candidate'},'O3')
        self.assertEqual(d['code'],'baseline_preferred')
        self.assertEqual(d['distinct_executables'],2)


class LiveIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.config = toolchain()
        except ValueError as error:
            raise unittest.SkipTest(str(error))
        cls.temp = tempfile.TemporaryDirectory()
        cls.app = Application(cls.config, cls.temp.name)
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.server.app = cls.app
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.app.close(); cls.server.shutdown(); cls.server.server_close(); cls.thread.join()
        cls.temp.cleanup()

    def request(self, path, body=None, headers=None, raw=False):
        data = None if body is None else json.dumps(body).encode()
        h = {} if body is None else {'Content-Type':'application/json','X-NeuroCompiler-Token':self.app.token}
        h.update(headers or {})
        with urllib.request.urlopen(urllib.request.Request(self.base+path, data=data, headers=h), timeout=10) as response:
            return response.read() if raw else json.load(response)

    def wait(self, job):
        deadline = time.monotonic()+40
        while job['status']=='running' and time.monotonic()<deadline:
            time.sleep(.05)
            job = self.request('/api/jobs/'+job['id'])
        self.assertNotEqual(job['status'], 'running')
        return job

    def analyze(self, source, **extra):
        job = self.wait(self.request('/api/jobs', {'operation':'analyze','source':source, **extra}))
        self.assertEqual(job['status'], 'completed', job)
        return job

    def test_01_health_assets_and_request_protection(self):
        self.assertEqual(self.request('/api/health')['status'], 'ready')
        self.assertIn(b'Your program.', self.request('/', raw=True))
        self.assertIn(b'id="study-status"', self.request('/research/', raw=True))
        for path in ['/presentation/model.json', '/.git/config', '/api/jobs/1234', '/../README.md']:
            with self.assertRaises(urllib.error.HTTPError) as raised:
                self.request(path)
            self.assertEqual(raised.exception.code, 404)
        for headers in [{'Host':'attacker.example'}, {'Origin':'https://attacker.example'}, {'X-NeuroCompiler-Token':'wrong'}]:
            with self.assertRaises(urllib.error.HTTPError) as raised:
                self.request('/api/jobs', {'source':'int main(void){return 0;}'}, headers)
            self.assertEqual(raised.exception.code, 403)

    def test_02_native_input_prediction_reports_and_ir(self):
        source = '#include <stdio.h>\nint main(void){int a,b;if(scanf("%d%d",&a,&b)!=2)return 1;printf("%d\\n",a+b);return 0;}\n'
        analysis = self.analyze(source, stdin='21 34\n')
        result = analysis['result']
        self.assertFalse(result['native_execution'])
        self.assertIsNone(result['measurement'])
        self.assertEqual(result['decision']['feature_count'],156)
        self.assertEqual(set(result['decision']['scores']),set(MENU))
        ir = self.request(f"/api/jobs/{analysis['id']}/ir/O3", raw=True)
        self.assertIn(b'define',ir)
        selected = self.request(f"/api/jobs/{analysis['id']}/selected.bc", raw=True)
        self.assertEqual(hashlib.sha256(selected).hexdigest(),result['artifacts'][result['decision']['choice']]['bitcode_sha256'])
        approved = self.request(f"/api/jobs/{analysis['id']}/approved.bc", raw=True)
        self.assertEqual(hashlib.sha256(approved).hexdigest(),result['artifacts']['O3']['bitcode_sha256'])
        before = result['decision']
        with self.assertRaises(urllib.error.HTTPError) as raised:
            self.request('/api/jobs', {'operation':'compare','analysis_id':analysis['id']})
        self.assertEqual(raised.exception.code,400)
        compared = self.wait(self.request('/api/jobs',{'operation':'compare','analysis_id':analysis['id'],'trusted_code':True}))
        self.assertEqual(compared['status'],'completed',compared)
        result = compared['result']
        self.assertEqual(before,result['decision'])
        self.assertTrue(result['correctness']['passed'])
        self.assertEqual(result['correctness']['checks']['O0 reference']['stdout_preview'],'55\n')
        self.assertLess(result['prediction_frozen_at'],result['measurement_started_at'])
        self.assertFalse(result['measurement']['self_control_passed']) # Too short, not a fabricated gain.
        self.assertEqual(result['measurement']['protocol'],'live-native-process-v2')
        self.assertEqual(result['measurement']['summary']['clocks']['cpu']['time_change_percent'],0.)
        self.assertTrue(all(c['verdict']=='inconclusive' for c in result['measurement']['cells'].values()))
        export = self.request(f"/api/jobs/{compared['id']}/report.json")
        self.assertEqual(export['source_sha256'],hashlib.sha256(source.encode()).hexdigest())
        report = self.request(f"/api/jobs/{compared['id']}/report.md",raw=True).decode()
        self.assertIn('experimental model failed research deployment gates',report)
        self.assertIn('Inconclusive'.lower(),report)
        self.assertNotIn('generalizable improvement achieved',report)

    def test_03_compiler_error_is_visible(self):
        job = self.wait(self.request('/api/jobs',{'source':'int main( { syntax error'}))
        self.assertEqual(job['status'],'failed')
        self.assertIn('error:',job['message'])
        self.assertNotIn('result',job)

    def test_04_output_mismatch_blocks_timing(self):
        source = '#include <stdio.h>\nint main(void){\n#ifdef __OPTIMIZE__\nputs("optimized");\n#else\nputs("reference");\n#endif\nreturn 0;}\n'
        analysis = self.analyze(source)
        job = self.wait(self.request('/api/jobs',{'operation':'compare','analysis_id':analysis['id'],'trusted_code':True}))
        self.assertEqual(job['status'],'completed')
        self.assertFalse(job['result']['correctness']['passed'])
        self.assertEqual(job['result']['measurement']['status'],'blocked')
        self.assertNotIn('cells',job['result']['measurement'])

    def test_05_mutated_binary_is_rejected(self):
        analysis = self.analyze('int main(void){return 0;}')
        (self.app.runs/analysis['id']/'O3/program').write_bytes(b'changed')
        job = self.wait(self.request('/api/jobs',{'operation':'compare','analysis_id':analysis['id'],'trusted_code':True}))
        self.assertEqual(job['status'],'failed')
        self.assertIn('artifact changed',job['message'])

    def test_06_serialization_cancellation_and_no_source_execution(self):
        marker = Path(self.temp.name)/'should-not-exist'
        source = f'#include <stdio.h>\nint main(void){{FILE*f=fopen("{marker}","w");if(f)fclose(f);for(;;){{}}return 0;}}'
        analysis = self.analyze(source)
        self.assertFalse(marker.exists())
        job = self.request('/api/jobs',{'operation':'compare','analysis_id':analysis['id'],'trusted_code':True})
        with self.assertRaises(urllib.error.HTTPError) as raised:
            self.request('/api/jobs',{'source':'int main(void){return 0;}'})
        self.assertEqual(raised.exception.code,409)
        cancelled = self.request('/api/jobs/'+job['id']+'/cancel',{})
        self.assertEqual(cancelled['status'],'cancelled')
        self.assertIsNotNone(self.app.jobs[job['id']]['process'].poll())

    def test_07_infinite_loop_is_bounded(self):
        analysis = self.analyze('int main(void){volatile unsigned i=0;for(;;)i++;return 0;}')
        job = self.wait(self.request('/api/jobs',{'operation':'compare','analysis_id':analysis['id'],'trusted_code':True}))
        self.assertEqual(job['status'],'failed')
        self.assertIn('2 second limit',job['message'])

    def test_08_native_clocks_and_timing_helper_integrity(self):
        from unittest.mock import patch
        from src.presentation.worker import execute, compare, JobError
        analysis=self.analyze('#include <time.h>\nint main(void){struct timespec t={0,20000000};nanosleep(&t,0);return 0;}')
        root=self.app.runs/analysis['id']
        request=json.loads((root/'request.json').read_text())
        observed=execute(root/'O3/program',request,root)
        self.assertGreaterEqual(observed['wall'],.019)
        self.assertLess(observed['cpu'],observed['wall'])
        self.assertIsInstance(observed['cpu_id'],int)
        changed_model=root/'changed-model.json';changed_model.write_text('{}')
        with patch('src.presentation.worker.MODEL_PATH',changed_model), self.assertRaisesRegex(JobError,'Model changed'):
            compare(root,{'analysis_root':str(root)})
        (root/'native-runner').write_bytes(b'changed')
        job=self.wait(self.request('/api/jobs',{'operation':'compare','analysis_id':analysis['id'],'trusted_code':True}))
        self.assertEqual(job['status'],'failed')
        self.assertIn('Timing helper changed',job['message'])


if __name__ == '__main__':
    unittest.main()
