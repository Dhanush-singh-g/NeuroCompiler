"""Detect stale, leaked, or arithmetically misleading count evidence."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path
import numpy as np
from src.rl.evidence import audit,digest
from src.rl.live_evidence import audit_live,ROOT
from src.rl.validation import describe_support,family_interval


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory();self.addCleanup(self.temporary.cleanup)
        self.root=Path(self.temporary.name)
        for path in (ROOT/'presentation').glob('*.json'):
            shutil.copyfile(path,self.root/path.name)

    def load(self,name):return json.loads((self.root/name).read_text())
    def save(self,name,value):
        (self.root/name).write_text(json.dumps(value,indent=2)+'\n')

    def rebind(self,name):
        manifest=self.load('credibility_manifest.json');manifest['artifacts'][name]=digest(self.root/name)
        self.save('credibility_manifest.json',manifest)

    def test_complete_evidence_is_consistent(self):
        result=audit_live(self.root)
        self.assertEqual(result['validation']['families'],24)
        self.assertEqual(result['additional_candidate_output_checks'],720)
        self.assertTrue(result['coefficient_refit_checked'])
        interval=result['intervals']['hybrid_vs_fixed_equal_guard']['interval95']
        self.assertLess(interval[0],1);self.assertGreater(interval[1],1)

    def test_changed_training_dataset_is_rejected(self):
        with (self.root/'sequential_training.json').open('a') as output:output.write(' ')
        with self.assertRaisesRegex(ValueError,'Changed frozen artifact'):audit(self.root)

    def test_falsified_summary_is_rejected_even_if_report_hash_is_updated(self):
        original=self.load('sequential_evaluation.json');original['summary']['hybrid_guarded']['fewer']=9
        self.save('sequential_evaluation.json',original)
        published=self.load('generalization_results.json');published['summary']=original['summary']
        published['evaluation_report_sha256']=digest(self.root/'sequential_evaluation.json')
        self.save('generalization_results.json',published)
        with self.assertRaisesRegex(ValueError,'Incorrect aggregate'):audit(self.root)

    def test_cross_validation_family_leak_is_rejected(self):
        value=self.load('model_validation.json')
        value['folds'][0]['validation_families'].append(value['folds'][0]['training_families'][0])
        self.save('model_validation.json',value);self.rebind('model_validation.json')
        with self.assertRaisesRegex(ValueError,'family leakage'):audit_live(self.root)

    def test_falsified_training_range_is_rejected(self):
        value=self.load('training_support.json');value['maximum'][0]+=10
        self.save('training_support.json',value);self.rebind('training_support.json')
        with self.assertRaisesRegex(ValueError,'bounds do not match'):audit_live(self.root)

    def test_unequal_checkpoint_guard_claim_is_rejected(self):
        value=self.load('checkpoint_baseline_audit.json');value['results'][0]['counts']['fixed_checkpoint_guarded']+=1
        self.save('checkpoint_baseline_audit.json',value);self.rebind('checkpoint_baseline_audit.json')
        with self.assertRaisesRegex(ValueError,'all checkpoints'):audit_live(self.root)


class DiagnosticMathTests(unittest.TestCase):
    def test_feature_range_is_advisory_and_not_confidence(self):
        profile={'minimum':[0,1],'maximum':[2,3],'feature_names':['x','y'],'scope':'unit fixture'}
        within=describe_support([1,2],profile);outside=describe_support([1,4],profile)
        self.assertEqual(within['status'],'within_training_ranges')
        self.assertEqual(outside['outside_fields'][0]['feature'],'y')
        self.assertFalse(outside['confidence_calibrated']);self.assertFalse(outside['selection_changed'])
        with self.assertRaises(ValueError):describe_support([float('nan'),2],profile)

    def test_bootstrap_treats_variants_as_correlated(self):
        rows=[{'family':'a','counts':{'O3':100,'candidate':50}},
              {'family':'b','counts':{'O3':100,'candidate':200}}]
        single=family_interval(rows,'O3','candidate',draws=1000)
        replicated=family_interval(rows+rows,'O3','candidate',draws=1000)
        self.assertEqual(single,replicated)
        self.assertEqual(single['families'],2)
        self.assertAlmostEqual(single['ratio'],1)


class LiveRangeDiagnosticTests(unittest.TestCase):
    def test_real_unfamiliar_module_is_flagged_without_changing_policy(self):
        from src.presentation.server import toolchain
        from src.presentation.worker import analyze,execute
        try:config=toolchain()
        except ValueError as error:raise unittest.SkipTest(str(error))
        source='#include <stdio.h>\n'+''.join(f'unsigned f{i}(unsigned x){{return x+{i}u;}}\n' for i in range(50))
        source+='int main(int argc,char**argv){printf("%u\\n",f49((unsigned)argc));return 0;}\n'
        with tempfile.TemporaryDirectory() as scratch:
            root=Path(scratch)
            request={**config,'source':source,'arguments':[],'stdin':'','iterations':0,'policy_mode':'hybrid'}
            result=analyze(root,request);seq=result['decision']['sequential']
            self.assertEqual(seq['input_support']['status'],'outside_training_ranges')
            self.assertGreaterEqual(seq['input_support']['outside_steps'],1)
            self.assertFalse(seq['input_support']['selection_changed'])
            self.assertFalse(seq['input_support']['confidence_calibrated'])
            self.assertEqual(execute(root/'reference',request,root)['stdout_preview'],'50\n')
            self.assertEqual(execute(root/'LearnedPolicy/program',request,root)['stdout_preview'],'50\n')
