import copy
import math
import unittest
from unittest.mock import patch

from src.benchmarks.paired import MENU,PROTOCOL,clock_effect,summarize,verify
from src.supervised.polybench import Selector,examples,family_cv
from src.supervised.partial import partial_labels


def fixture():
    item={'id':'p','split':'train','family':'f'}
    m={**item,'eligible':True,'repetitions':1,'expected':{'checksum':'a','values':2},
       'artifacts':{c:{'so_sha256':'same'} for c in [*MENU,'O3_copy']},
       'aliases':{c:'O3' for c in MENU},'features':{c:[0.,1.] for c in list(MENU)[1:]}}
    records=[]
    for block in range(PROTOCOL['blocks']):
        samples=[{'pair':p,'left_first':p%2==0,
            'left':{'cpu_seconds':.04,'wall_seconds':.05,'checksum':'a','values':2},
            'right':{'cpu_seconds':.04,'wall_seconds':.1,'checksum':'a','values':2}}
            for p in range(PROTOCOL['pairs'])]
        records.append({'case':'p','left':'O3','right':'O3_copy','choice':'O3','role':'qualification',
            'block':block,'pairs':PROTOCOL['pairs'],'repetitions':1,'first':True,'samples':samples,
            'process_elapsed_seconds':4.,'scheduler_delta':{'steal':10}})
    return {'protocol':PROTOCOL,'inventory':[item],'split':'train','complete':True,
            'manifests':{'p':m},'records':records,'failures':{}}


class NativeClockTests(unittest.TestCase):
    def test_cpu_qualification_does_not_imply_wall_qualification(self):
        r=fixture();labels,d=summarize(r)
        self.assertEqual(len(labels),1)
        self.assertTrue(d['p']['cpu_menu_qualified'])
        self.assertFalse(d['p']['wall_menu_qualified'])

    def test_scheduler_steal_does_not_remove_samples(self):
        r=fixture();q=clock_effect(r['records'],'cpu')
        self.assertEqual(q['speedup'],1.)
        self.assertEqual(len(r['records'][0]['samples']),PROTOCOL['pairs'])
        self.assertEqual(r['records'][0]['scheduler_delta']['steal'],10)

    def test_changed_logical_pair_order_rejected(self):
        r=fixture();r['records'][0]['samples'][0]['left_first']=False
        with patch('src.benchmarks.paired.inventory',return_value=r['inventory']):
            with self.assertRaisesRegex(ValueError,'ordering'):verify(r,artifacts=False)

    def test_truncated_raw_pairs_rejected(self):
        r=fixture();r['records'][0]['samples'].pop()
        with patch('src.benchmarks.paired.inventory',return_value=r['inventory']):
            with self.assertRaisesRegex(ValueError,'trial count'):verify(r,artifacts=False)

    def test_nonfinite_clock_rejected(self):
        r=fixture();r['records'][0]['samples'][0]['left']['cpu_seconds']=float('nan')
        with patch('src.benchmarks.paired.inventory',return_value=r['inventory']):
            with self.assertRaisesRegex(ValueError,'clock duration'):verify(r,artifacts=False)

    def test_output_mismatch_rejected(self):
        r=fixture();r['records'][0]['samples'][0]['left']['checksum']='bad'
        with patch('src.benchmarks.paired.inventory',return_value=r['inventory']):
            with self.assertRaisesRegex(ValueError,'output'):verify(r,artifacts=False)

    def test_fabricated_reported_gain_rejected(self):
        r=fixture();r['labels'],r['diagnostics']=summarize(r)
        r['diagnostics']['p']['outcomes']['O3']['speedup']=2.
        with patch('src.benchmarks.paired.inventory',return_value=r['inventory']):
            with self.assertRaisesRegex(ValueError,'Reported (labels|effects) changed'):verify(r,artifacts=False)

    def test_nonidentical_baseline_copy_rejected(self):
        r=fixture();r['manifests']['p']['artifacts']['O3_copy']['so_sha256']='different'
        with patch('src.benchmarks.paired.inventory',return_value=r['inventory']):
            with self.assertRaisesRegex(ValueError,'placement'):verify(r,artifacts=False)


class DynamicMenuTests(unittest.TestCase):
    def test_family_cv_uses_all_seven_new_candidates(self):
        choices=list(MENU)[1:];programs=[];manifests={}
        for family in ['a','b','c']:
            for i in range(2):
                name=family+str(i)
                f={c:[float(i),float(j)] for j,c in enumerate(choices)}
                s={c:{'log_speedup':math.log(.9),'interval':[.89,.91],'confirmed_gain':False} for c in choices}
                s['O3']={'log_speedup':0.,'interval':[1.,1.],'confirmed_gain':False}
                programs.append({'case':name,'family':family,'features':f,'outcomes':s})
                manifests[name]={'features':f,'aliases':{c:c for c in MENU}}
        result=family_cv(programs,manifests,10,True,.03,choices)
        self.assertTrue(result['eligible'])
        for row in result['records']:
            self.assertEqual(set(row['scores']),set(choices))
            self.assertEqual(row['choice'],'O3')
        for fold in result['folds']:self.assertNotIn(fold['held_family'],fold['train_families'])


class PartialQualificationTests(unittest.TestCase):
    def test_missing_targets_are_absent_and_qualified_losses_remain(self):
        p={'case':'p','family':'f','features':{'O2':[1.],'O3_no_vector':[2.]},
           'outcomes':{'O2':{'interval':[.8,.95],'log_speedup':math.log(.9)}}}
        rows=examples([p],choices=['O2','O3_no_vector'])
        self.assertEqual([r['choice'] for r in rows],['O2'])
        self.assertLess(rows[0]['target'],0.)

    def test_missing_selected_cv_outcome_invalidates_selection(self):
        programs=[];manifests={}
        for i in range(6):
            name=str(i);features={'O2':[float(i)],'O3_no_vector':[float(i+1)]}
            outcomes={'O3':{'interval':[1.,1.],'log_speedup':0.,'confirmed_gain':False},
                      'O2':{'interval':[.8,.95],'log_speedup':math.log(.9),'confirmed_gain':False}}
            programs.append({'case':name,'family':str(i//2),'features':features,'outcomes':outcomes})
            manifests[name]={'features':features,'aliases':{'O2':'O2','O3_no_vector':'O3_no_vector'}}
        with patch.object(Selector,'choose',return_value={'choice':'O3_no_vector','scores':{}}):
            result=family_cv(programs,manifests,10,True,.03,['O2','O3_no_vector'])
        self.assertFalse(result['eligible'])
        self.assertIsNone(result['score'])
        self.assertEqual(len(result['unscorable']),6)
        self.assertEqual(result['qualified_prediction_coverage'],0.)

    def test_partial_admission_keeps_qualified_loss_and_rejects_noisy_win(self):
        raw=fixture();m=raw['manifests']['p']
        m['aliases']['O2']='O2';m['aliases']['O3_no_vector']='O3_no_vector'
        baseline={'speedup':1.,'log_speedup':0.,'interval':[1.,1.]}
        loss={'speedup':.9,'log_speedup':math.log(.9),'interval':[.8,.95],
              'candidate_control':{'control_pass':True}}
        noisy={'speedup':2.,'log_speedup':math.log(2.),'interval':[1.8,2.2],
               'candidate_control':{'control_pass':False}}
        diagnostics={'p':{'cpu_control':{'control_pass':True},'cpu_menu_qualified':False,
                          'outcomes':{'O3':baseline,'O2':loss,'O3_no_vector':noisy}}}
        with patch('src.supervised.partial.verify',return_value=([],diagnostics)):
            rows=partial_labels(raw)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['outcomes']['O2']['speedup'],.9)
        self.assertNotIn('O3_no_vector',rows[0]['outcomes'])
        self.assertIn('O3_no_vector',rows[0]['unqualified_choices'])


if __name__=='__main__':unittest.main()
