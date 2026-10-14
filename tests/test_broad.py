import copy
import math
import unittest
from unittest.mock import patch

import numpy as np

from src.benchmarks.broad import MENU, semantic_json
from src.supervised.broad import NativeSelector, program_cv, training_rows


def fixture():
    labels=[];manifests={}
    for p in range(6):
        for i in range(1 if p==0 else 2):
            case=f'p{p}_{i}';aliases={c:('O3' if c in ['O3','Os'] else c) for c in MENU}
            features={c:[float(p),float(j),float(i)] for j,c in enumerate(list(MENU)[1:])}
            loss={'speedup':.9,'log_speedup':math.log(.9),'interval':[.89,.91],'confirmed_gain':False}
            outcomes={c:dict(loss) for c in MENU}
            outcomes['O3']={'speedup':1.,'log_speedup':0.,'interval':[1.,1.],'confirmed_gain':False}
            outcomes['Os']=outcomes['O3']
            labels.append({'case':case,'program':f'p{p}','features':features,'aliases':aliases,'outcomes':outcomes})
            manifests[case]={'features':features,'aliases':aliases}
    return labels,manifests


class BroadLearningTests(unittest.TestCase):
    def test_forest_preserves_equal_program_weight_despite_input_imbalance(self):
        labels,_=fixture();model=NativeSelector(kind='forest').fit(labels)
        self.assertEqual(len(model.programs),6)
        for total in model.program_weight_totals.values():self.assertAlmostEqual(total,1.)
        self.assertEqual(model.row_count,5*len(labels))
        self.assertNotIn('Os',{r['choice'] for r in training_rows(labels,False)})

    def test_forest_cv_holds_all_inputs_of_a_program_out(self):
        labels,manifests=fixture();cv=program_cv(labels,manifests,10,True,.03,'forest',3)
        self.assertTrue(cv['eligible'])
        for fold in cv['folds']:
            self.assertNotIn(fold['held_program'],fold['train_programs'])
            self.assertTrue(all(not c.startswith(fold['held_program']+'_') for c in fold['train_cases']))

    def test_missing_forest_selected_outcome_withholds_score(self):
        labels,manifests=fixture();labels[0]['outcomes'].pop('O3_large_inline')
        with patch.object(NativeSelector,'choose',return_value={'choice':'O3_large_inline','scores':{}}):
            cv=program_cv(labels,manifests,10,False,.01,'forest',6)
        self.assertFalse(cv['eligible']);self.assertIsNone(cv['score'])
        self.assertEqual(len(cv['unscorable']),1)

    def test_forest_prediction_is_deterministic_and_preserves_O3_aliases(self):
        labels,manifests=fixture();a=NativeSelector(kind='forest').fit(labels);b=NativeSelector(kind='forest').fit(labels)
        case=next(iter(manifests.values()));pa,pb=a.choose(case),b.choose(case)
        self.assertEqual(pa,pb);self.assertEqual(pa['choice'],'O3');self.assertEqual(pa['scores']['Os'],0.)
        self.assertTrue(np.isfinite(list(pa['scores'].values())).all())

    def test_unknown_model_family_is_rejected(self):
        labels,_=fixture()
        with self.assertRaisesRegex(ValueError,'Unknown model'):NativeSelector(kind='other').fit(labels)

    def test_json_oracle_distinguishes_types_keys_and_order(self):
        examples=[None,False,0,'0',[0],{'a':0},{'b':0},[1,2],[2,1]]
        self.assertEqual(len({semantic_json(v) for v in examples}),len(examples))
        self.assertEqual(semantic_json({'a':[True,None,17]}),semantic_json(copy.deepcopy({'a':[True,None,17]})))


if __name__=='__main__':unittest.main()
