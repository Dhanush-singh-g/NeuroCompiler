import copy
import math
import unittest
from unittest.mock import patch

from src.benchmarks.polybench import MENU, PROTOCOL, INPUT_FIXES, inventory, outcomes, verify
from src.features.transform import parse_ir, summaries
from src.supervised.polybench import family_cv, Selector


class CorpusTests(unittest.TestCase):
    def test_official_inventory_has_fixed_family_splits(self):
        items = inventory()
        self.assertEqual(len(items), 30)
        self.assertEqual(sum(i['split']=='train' for i in items),22)
        self.assertEqual(sum(i['split']=='development' for i in items),6)
        self.assertEqual(sum(i['split']=='reserved_test' for i in items),2)
        self.assertEqual({i['family'] for i in items if i['split']=='train'},
                         {'datamining','linear-algebra/kernels','linear-algebra/solvers'})

    def test_input_adapters_do_not_touch_kernel(self):
        from src.benchmarks.polybench import CORPUS
        for item in inventory():
            fix = INPUT_FIXES.get(item['id'])
            if not fix:
                continue
            source = (CORPUS/item['path']).read_text()
            prefix, kernel = source.split('/* DCE code.',1)
            self.assertEqual(prefix.count(fix[0]),1)
            self.assertNotIn(fix[0],kernel)
            self.assertEqual(source.replace(*fix).split('/* DCE code.',1)[1],kernel)

    def test_renamed_entrypoint_reaches_kernel(self):
        ir = '''define i32 @nc_benchmark_main() {
entry:
  call void @kernel()
  ret i32 0
}
define void @kernel() {
entry:
  ret void
}
'''
        parsed=parse_ir(ir)
        old,_=summaries(parsed)
        actual,_=summaries(parsed,entrypoint='nc_benchmark_main')
        self.assertEqual(old[2][0],0)
        self.assertEqual(actual[2][0],3)

    def test_reserved_build_rejected_before_filesystem_work(self):
        from src.benchmarks.polybench import build
        with self.assertRaisesRegex(ValueError,'Reserved'):
            build({'split':'reserved_test'},'/tmp/unused_reserved_polybench')


def synthetic_report():
    trial = {'kernel_seconds':.02,'process_elapsed_seconds':.03,
             'checksum':'a','values':1,'repetitions':1,
             'scheduler_delta':{'user':1,'system':0,'idle':0,'steal':2}}
    manifest = {'id':'p','split':'train','artifacts':{},'expected':{'checksum':'a','values':1},
                'features':{},'family':'f','repetitions':1,'aliases':{c:'O3' for c in MENU}}
    records=[]
    for block in range(PROTOCOL['blocks']):
        records.append({'case':'p','choice':'O3','block':block,'role':'qualification',
             'first':True,'left':'O3','right':'O3',
             'left_seconds':[.02]*PROTOCOL['pairs'],'right_seconds':[.02]*PROTOCOL['pairs'],
             'left_trials':[copy.deepcopy(trial) for _ in range(PROTOCOL['pairs'])],
             'right_trials':[copy.deepcopy(trial) for _ in range(PROTOCOL['pairs'])]})
    return {'protocol':PROTOCOL,'inventory':[],'split':'train','complete':False,
            'manifests':{'p':manifest},'records':records,'failures':{}}


class MeasurementTests(unittest.TestCase):
    def test_identical_control_names_still_alternate_logical_order(self):
        from src.benchmarks.polybench import cell
        m=synthetic_report()['manifests']['p']
        m['artifacts']={'O3':{'elf':'unused'}}
        trials=[{'kernel_seconds':float(i+1),'checksum':'a','values':1}
                for i in range(2*PROTOCOL['pairs'])]
        with patch('src.benchmarks.polybench.trial',side_effect=trials):
            c=cell(m,'O3',0,'qualification')
        for i in range(PROTOCOL['pairs']):
            left_first=(i%2==0)==c['first']
            expected=2*i+(1 if left_first else 2)
            self.assertEqual(c['left_seconds'][i],expected)

    def test_scheduler_delays_are_not_subtracted_or_discarded(self):
        r=synthetic_report()
        labels,_=outcomes(r)
        self.assertEqual(len(labels),1)
        self.assertEqual(labels[0]['outcomes']['O3']['speedup'],1.)
        self.assertEqual(len(r['records'][0]['left_trials']),PROTOCOL['pairs'])
        self.assertEqual(r['records'][0]['left_trials'][0]['scheduler_delta']['steal'],2)

    def test_failed_unchanged_control_prevents_labels(self):
        r=synthetic_report()
        r['records'][0]['right_seconds']=[.04]*PROTOCOL['pairs']
        labels,diagnostics=outcomes(r)
        self.assertFalse(labels)
        self.assertFalse(diagnostics['p']['accepted'])

    def test_incomplete_menu_cannot_enter_training(self):
        r=synthetic_report()
        r['manifests']['p']['aliases']['O2']='O2'
        labels,_=outcomes(r)
        self.assertFalse(labels)


class FamilyLearningTests(unittest.TestCase):
    def test_no_family_members_in_their_training_fold(self):
        programs=[];manifests={}
        for f in ['a','b','c']:
            for i in range(2):
                name=f+str(i)
                features={c:[float(i),float(j)] for j,c in enumerate(list(MENU)[1:])}
                stats={c:{'log_speedup':math.log(.98 if j else 1.04),
                          'interval':[.97,1.05],'confirmed_gain':False}
                       for j,c in enumerate(MENU)}
                programs.append({'case':name,'family':f,'features':features,'outcomes':stats})
                manifests[name]={'features':features,'aliases':{c:c for c in MENU}}
        cv=family_cv(programs,manifests,10,True,.03)
        self.assertTrue(cv['eligible'])
        for fold in cv['folds']:
            self.assertNotIn(fold['held_family'],fold['train_families'])
            self.assertFalse(set(fold['train_programs']) & set(fold['test_programs']))

    def test_insufficient_families_blocks_cross_validation(self):
        self.assertFalse(family_cv([],{},1,True,.03)['eligible'])

    def test_no_qualified_data_blocks_model_fit(self):
        with self.assertRaisesRegex(ValueError,'No timing-qualified'):
            Selector().fit([])


if __name__=='__main__':
    unittest.main()
