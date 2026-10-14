import math
import unittest
from unittest.mock import patch

import numpy as np

from src.benchmarks.real import CASES,input_bytes
from src.supervised.robust import RiskRegressor,RobustSelector,real_cross_validate,select_robust,uncertainty_rows
from tests.test_transform import learning_rows
from scripts.evaluate_robust import timing_score
from src.benchmarks.compact import MENU,PROTOCOL,summarize
from src.supervised.frozen import predictions_equal


def rows():
    r=learning_rows(5)
    for x in r:
        x['program']='real://'+x['program'];x['lower_target']=x['target']-.01
    return r


class RobustTests(unittest.TestCase):
    def test_prediction_roundoff_does_not_change_frozen_choice(self):
        a={'configuration':'O3','scores':{'candidate':.013618390665402207},'margin':0.}
        b={'configuration':'O3','scores':{'candidate':.013618390665402214},'margin':0.}
        self.assertTrue(predictions_equal(a,b))

    def test_frozen_choice_and_score_changes_are_rejected(self):
        a={'configuration':'O3','scores':{'candidate':.01}}
        self.assertFalse(predictions_equal(a,{'configuration':'candidate','scores':{'candidate':.01}}))
        self.assertFalse(predictions_equal(a,{'configuration':'O3','scores':{'candidate':.010001}}))

    def test_nonfinite_prediction_or_structure_changes_rejected(self):
        self.assertFalse(predictions_equal({'score':float('nan')},{'score':float('nan')}))
        self.assertFalse(predictions_equal({'score':1.},{'score':1.,'extra':0}))
        self.assertFalse(predictions_equal(True,1))

    def test_multiple_inputs_share_one_held_program(self):
        import copy
        r=rows();second=copy.deepcopy(r[:3])
        for x in second:x['case']='second_input'
        with patch('src.supervised.robust.VARIANTS',['point']):cv=real_cross_validate(r+second)
        for v in cv.values():
            self.assertEqual(len(v['records']),6)
            self.assertEqual(v['score']['programs'],5)
            for fold in v['folds']:self.assertNotIn(fold['held'],fold['fit'])

    def test_studies_namespace_inputs_without_changing_original_program(self):
        r=rows();static=r[0]['static'];static['program']=r[0]['program']
        raw={'labels':[{'case':'input','program':static['program'],
            'outcomes':{c:{'log_speedup':0.,'confirmed_gain':False} for c in MENU}}]}
        joined=uncertainty_rows(raw,{'input':static},case_prefix='long:')
        self.assertEqual({x['case'] for x in joined},{'long:input'})
        self.assertEqual({x['program'] for x in joined},{static['program']})
        self.assertEqual(raw['labels'][0]['case'],'input')

    def test_timing_uncertainty_is_present_with_one_program(self):
        effects=[{'case':'a','choice':'candidate','role':'effect',
            'left_seconds':[.09,.11]*20,'right_seconds':[.1]*40} for _ in range(4)]
        outcomes=[{'case':'a','program':'real://one','choice':'candidate','log_speedup':0.}]
        score=timing_score(outcomes,effects)
        self.assertEqual(score['point_only_interval'],[1.,1.])
        self.assertLess(score['interval'][0],1.)
        self.assertGreater(score['interval'][1],1.)
        self.assertTrue(score['timing_uncertainty_included'])

    def test_empty_timing_score_does_not_claim_gain(self):
        s=timing_score([],[])
        self.assertIsNone(s['geomean']);self.assertIsNone(s['interval'])

    def test_new_pair_budget_preserves_old_summarizer_default(self):
        m={'program':'real://one','features':[0,1],'aliases':{c:'O3' for c in MENU}}
        def report(pairs):return {'manifests':{'one':m},'profiles':{'one':{'eligible':True}},
            'records':[{'case':'one','role':'qualification','left_seconds':[.1]*pairs,'right_seconds':[.1]*pairs} for _ in range(4)]}
        old=summarize(report(10))
        self.assertEqual(summarize(report(20),{**PROTOCOL,'pairs':20}),old)
        self.assertEqual(summarize(report(10)),old)

    def test_fully_rejected_training_source_supplies_no_rows(self):
        self.assertEqual(uncertainty_rows({'labels':[]},{}),[])

    def test_uncertainty_target_and_negative_loss_weight(self):
        r=rows();m=RiskRegressor('lower_risk',1).fit(r)
        self.assertEqual(m.training_targets,[x['lower_target'] for x in r])
        for p in m.programs:
            weights=[w for x,w in zip(r,m.training_weights) if x['program']==p]
            self.assertAlmostEqual(sum(weights),1.)
            self.assertAlmostEqual(weights[1],2*weights[0])

    def test_point_ablation_uses_original_targets(self):
        r=rows();m=RiskRegressor('point',1).fit(r)
        self.assertEqual(m.training_targets,[x['target'] for x in r])

    def test_entire_original_program_is_held_out_and_kernels_never_score(self):
        r=rows();kernel=rows()[:3]
        for x in kernel:x['program']='kernel://auxiliary';x['case']='aux'
        with patch('src.supervised.robust.VARIANTS',['lower_risk']):cv=real_cross_validate(r+kernel)
        for key,v in cv.items():
            self.assertEqual(v['score']['programs'],5)
            self.assertFalse(any(x['program'].startswith('kernel:') for x in v['records']))
            for fold in v['folds']:
                self.assertNotIn(fold['held'],fold['fit'])
                self.assertEqual('kernel://auxiliary' in fold['fit'],key.startswith('with_kernels'))

    def test_risk_gate_rejects_harmful_input_even_when_group_average_passes(self):
        spec={'score':{'geomean':1.04,'interval':[1.01,1.1],'worst_program':1.01},
              'worst_input':.98,'confirmed_programs':2,'utility_log':.02}
        self.assertEqual(select_robust({'candidate':spec})[0],'O3')
        spec['worst_input']=.995
        self.assertEqual(select_robust({'candidate':spec})[0],'candidate')

    def test_nonpositive_utility_falls_back_to_o3(self):
        spec={'score':{'geomean':1.,'interval':[.99,1.01],'worst_program':.99},
              'worst_input':.99,'confirmed_programs':0,'utility_log':-.001}
        self.assertEqual(select_robust({'candidate':spec}),('O3','O3'))

    def test_real_inputs_are_deterministic_and_distinct(self):
        values=[input_bytes(c) for c in CASES]
        self.assertEqual(len(set(values)),len(CASES))
        for c,v in zip(CASES,values):self.assertEqual(input_bytes(c),v)
        with self.assertRaises(ValueError):input_bytes('susan_reserved')

    def test_exact_o3_aliases_are_rejected_by_risk_selector(self):
        r=rows();m=RobustSelector('point',1,0.).fit(r);s=r[0]['static']
        for c in s['aliases']:s['aliases'][c]='O3'
        self.assertEqual(m.choose(s)['configuration'],'O3')

    def test_nonfinite_uncertainty_target_rejected(self):
        r=rows();r[0]['lower_target']=float('nan')
        with self.assertRaises(ValueError):RiskRegressor().fit(r)


if __name__=='__main__':unittest.main()
