"""Session counts are descriptive; no repeated-input inflation or false wins."""
import hashlib
import unittest

from src.presentation.scorecard import session_scorecard


def result(kind='analysis', source='custom C source', args=None, model='model1',
           choice='O3', outcome='unchanged', qualified=False, blocked=False):
    return {'kind':kind, 'source_sha256':hashlib.sha256(source.encode()).hexdigest(),
            'input':{'source':source, 'arguments':args or [], 'stdin':'', 'iterations':0},
            'decision':{'choice':choice, 'aliases':{'O3':'O3','different':'different'}, 'model_sha256':model},
            'measurement':{'status':'blocked' if blocked else 'completed',
                           'summary':{'clocks':{c:{'status':outcome,'qualified':qualified} for c in ('cpu','wall')}}}}


class ScorecardTests(unittest.TestCase):
    def test_empty_session_is_zero(self):
        card=session_scorecard([],[])
        self.assertEqual(card['totals']['inputs'],0)
        self.assertEqual(card['totals']['tested'],0)
        self.assertEqual(card['source_files'],0)

    def test_repeat_input_counts_once_and_last_comparison_wins(self):
        records=[result(choice='different'),
                 result('comparison',choice='different',outcome='faster',qualified=True),
                 result(choice='different'),
                 result('comparison',choice='different',outcome='slower',qualified=True)]
        total=session_scorecard(records,[])['totals']
        self.assertEqual(total['inputs'],1)
        self.assertEqual(total['tested'],1)
        self.assertEqual(total['wins'],0)
        self.assertEqual(total['losses'],1)
        self.assertEqual(total['changed_choice'],1)

    def test_provenance_and_arguments_are_kept_separate(self):
        examples=[{'id':'sieve','source':'training'},{'id':'mix','source':'demo'}]
        records=[result(source='training'),result(source='demo'),result(args=['10']),result(args=['20'])]
        card=session_scorecard(records,examples)
        self.assertEqual(card['groups']['training_example']['inputs'],1)
        self.assertEqual(card['groups']['bundled_demo']['inputs'],1)
        self.assertEqual(card['groups']['custom']['inputs'],2)
        self.assertEqual(card['source_files'],3)

    def test_failed_quality_cannot_be_a_win_and_identity_is_separate(self):
        records=[result(choice='different'),result('comparison',choice='different',outcome='faster'),
                 result(source='unchanged'),result('comparison',source='unchanged')]
        total=session_scorecard(records,[])['totals']
        self.assertEqual(total['wins'],0)
        self.assertEqual(total['inconclusive'],1)
        self.assertEqual(total['unchanged'],1)
        self.assertEqual(total['unqualified_timings'],2)

    def test_model_versions_and_correctness_blocks(self):
        records=[result(),result('comparison',blocked=True),result(model='model2')]
        total=session_scorecard(records,[])['totals']
        self.assertEqual(total['inputs'],2)
        self.assertEqual(total['tested'],1)
        self.assertEqual(total['blocked'],1)

    def test_one_clock_cannot_create_a_win(self):
        measured=result('comparison',choice='different',outcome='faster',qualified=True)
        measured['measurement']['summary']['clocks']['wall']['qualified']=False
        total=session_scorecard([result(choice='different'),measured],[])['totals']
        self.assertEqual(total['wins'],0)
        self.assertEqual(total['inconclusive'],1)

    def test_shared_four_way_winner_is_not_an_individual_nc_win(self):
        measured=result('comparison',qualified=True)
        measured['measurement']['four_way']={'status':'reliable_winner',
            'winner_options':['O3','NeuroCompiler'],'controls_passed':True,'complete_pair_coverage':True}
        total=session_scorecard([result(),measured],[])['totals']
        self.assertEqual(total['best_shared'],1)
        self.assertEqual(total['best_NeuroCompiler'],0)
        self.assertEqual(total['wins'],0)
        measured['measurement']['four_way']['controls_passed']=False
        total=session_scorecard([result(),measured],[])['totals']
        self.assertEqual(total['best_shared'],0)
        self.assertEqual(total['four_way_inconclusive'],1)
