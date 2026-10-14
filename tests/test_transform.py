import math
import unittest
from unittest.mock import patch

import numpy as np

from src.features.transform import FEATURE_NAMES,METRICS,candidate_vector,parse_ir,summaries
from src.supervised.transform import CHOICES,TransformSelector,cross_validate,select_policies
from src.benchmarks.compact import PROTOCOL,effect

IR='''define i32 @main(i32 %n) {
entry:
  br label %loop
loop:
  %i = phi i32 [ 0, %entry ], [ %j, %loop ]
  %j = add i32 %i, 1
  %test = icmp ult i32 %j, %n
  br i1 %test, label %loop, label %exit
exit:
  %x = call i32 @leaf(i32 %j)
  ret i32 %x
}
define i32 @leaf(i32 %x) {
entry:
  %y = shl i32 %x, 1
  ret i32 %y
}
define i32 @unused() {
entry:
  ret i32 1
}
'''


def learning_rows(n=5):
    rows=[]
    for i in range(n):
        static={'aliases':{c:c for c in ['O3',*CHOICES]},'features':{}}
        for j,c in enumerate(CHOICES):
            values=[0.]*len(FEATURE_NAMES);values[0]=i+1;values[-3+j]=1.
            static['features'][c]=values
        for j,c in enumerate(CHOICES):
            rows.append({'case':f'case{i}','program':f'program{i}','choice':c,
                'target':math.log(1.04 if j==0 else .99),'confirmed_gain':j==0,
                'vector':static['features'][c],'static':static})
    return rows


class FeatureTests(unittest.TestCase):
    def test_function_and_cfg_metrics(self):
        parsed=parse_ir(IR);m=parsed['main']['counts']
        self.assertEqual(m['blocks'],3)
        self.assertEqual(m['edges'],3)
        self.assertEqual(m['cyclic_blocks'],1)
        self.assertEqual(m['cyclic_regions'],1)
        self.assertEqual(m['cyclic_instructions'],4)
        self.assertEqual(m['instructions'],7)
        self.assertEqual(m['phi'],1)
        self.assertEqual(m['call'],1)

    def test_reachability_is_not_module_size(self):
        values,indirect=summaries(parse_ir(IR))
        idx=METRICS.index('instructions')
        self.assertEqual(values[0][idx],10)
        self.assertEqual(values[2][idx],9)
        self.assertFalse(indirect)

    def test_zero_transform_has_zero_delta(self):
        f=parse_ir(IR);v=candidate_vector(f,f,CHOICES[0],0,10)
        n=3*len(METRICS)
        self.assertTrue(np.all(np.asarray(v[n:2*n+len(METRICS)])==0))
        self.assertEqual(len(v),len(FEATURE_NAMES))

    def test_changed_function_features(self):
        base=parse_ir(IR);candidate=parse_ir(IR.replace('%y = shl i32 %x, 1','%y = mul i32 %x, 2'))
        v=candidate_vector(base,candidate,CHOICES[0],0,0)
        self.assertGreater(v[FEATURE_NAMES.index('absolute_function_delta_shift')],0)
        self.assertGreater(v[FEATURE_NAMES.index('changed_function_fraction')],0)

    def test_indirect_call_uncertainty_is_explicit(self):
        text=IR.replace('@leaf(i32 %j)','%callee(i32 %j)')
        values,indirect=summaries(parse_ir(text))
        self.assertTrue(indirect)
        self.assertEqual(parse_ir(text)['main']['counts']['indirect_call'],1)

    def test_unknown_cfg_target_rejected(self):
        with self.assertRaisesRegex(ValueError,'CFG'):
            parse_ir(IR.replace('label %exit','label %missing'))


class LearningTests(unittest.TestCase):
    def test_precision_protocol_does_not_change_existing_default(self):
        def records(pairs):
            return [{'left_seconds':[.102]*pairs,'right_seconds':[.1]*pairs} for _ in range(4)]
        old=effect(records(10))
        # A 2% bias passes the old 3% control and fails the new 1% control.
        self.assertTrue(old['control_pass'])
        precision={**PROTOCOL,'pairs':40,'control_tolerance':.01,'seed':20261013}
        self.assertFalse(effect(records(40),precision)['control_pass'])
        self.assertEqual(effect(records(10)),old)
    def test_nested_program_isolation(self):
        # Ridge modes exercise all real fold/scaling/calibration logic quickly.
        with patch('src.supervised.transform.MODES',['ridge1']):
            cv=cross_validate(learning_rows(),floors=(0.,.03))
        for result in cv.values():
            for f in result['folds']:
                self.assertNotIn(f['held'],f['fit'])
                for inner in f['calibration']:
                    self.assertNotIn(inner['held'],inner['fit'])
                    self.assertNotIn(f['held'],inner['fit'])
                    self.assertTrue(set(inner['fit']).issubset(f['fit']))

    def test_candidate_alias_always_abstains(self):
        rows=learning_rows();m=TransformSelector('ridge1',False,0.).fit(rows)
        static=rows[0]['static']
        for c in CHOICES:static['aliases'][c]='O3'
        self.assertEqual(m.choose(static)['configuration'],'O3')

    def test_policy_threshold_and_gain_confirmation_are_separate(self):
        rows=learning_rows()
        for r in rows:r['target']=math.log(1.02) if r['choice']==CHOICES[0] else math.log(.99)
        m=TransformSelector('ridge1',False,.03).fit(rows)
        self.assertEqual(m.choose(rows[0]['static'])['configuration'],'O3')
        m.floor=0.
        self.assertEqual(m.choose(rows[0]['static'])['configuration'],CHOICES[0])

    def test_gate_requires_two_confirmed_programs(self):
        cv={'raw_ridge1':{'score':{'geomean':1.04,'interval':[1.01,1.1],'worst_program':.99},'confirmed_programs':1}}
        self.assertEqual(select_policies(cv)[0],'O3')
        cv['raw_ridge1']['confirmed_programs']=2
        self.assertEqual(select_policies(cv)[0],'raw_ridge1')

    def test_invalid_vectors_rejected_even_for_o3(self):
        rows=learning_rows();s=rows[0]['static'];m=TransformSelector().fit([])
        s['features'][CHOICES[0]]=[float('nan')]*len(FEATURE_NAMES)
        with self.assertRaises(ValueError):m.choose(s)


if __name__=='__main__':unittest.main()
