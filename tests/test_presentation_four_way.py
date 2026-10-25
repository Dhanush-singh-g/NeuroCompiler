"""Head-to-head ranking contracts; synthetic fixtures are not native evidence."""
import itertools
import unittest
from src.presentation.worker import pair_summary
from src.presentation.four_way import four_way_summary


def fixture(times, aliases=None, wall_times=None):
    options={'O1':'O1','O2':'O2','O3':'O3','NeuroCompiler':'NC'}
    aliases=aliases or {name:name for name in options.values()}
    names=list(dict.fromkeys(aliases.values()))
    def cell(a,b,control=False):
        samples=[{'block':i//4,'candidate_first':bool(i%2),
                  'baseline':{'cpu':times[a],'wall':(wall_times or times)[a]*1.1},
                  'candidate':{'cpu':times[b],'wall':(wall_times or times)[b]*1.1}} for i in range(12)]
        return pair_summary(samples,control=control,family_size=20)
    controls={name:cell(name,name,True) for name in names}
    pairs=[{'left':a,'right':b,'cell':cell(a,b)} for a,b in itertools.combinations(names,2)]
    return options,aliases,controls,pairs


class FourWayTests(unittest.TestCase):
    def test_nc_can_win_when_both_clocks_and_all_competitors_agree(self):
        data=fixture({'O1':.08,'O2':.06,'O3':.05,'NC':.04})
        rank=four_way_summary(*data)
        self.assertEqual(rank['status'],'reliable_winner')
        self.assertEqual(rank['winner_options'],['NeuroCompiler'])
        self.assertEqual(rank['head_to_head_cells'],6)

    def test_o1_can_win_without_changing_model_prediction(self):
        rank=four_way_summary(*fixture({'O1':.04,'O2':.06,'O3':.05,'NC':.08}))
        self.assertEqual(rank['winner_options'],['O1'])

    def test_close_observed_times_are_not_a_reliable_winner(self):
        rank=four_way_summary(*fixture({'O1':.05,'O2':.0501,'O3':.0502,'NC':.0503}))
        self.assertEqual(rank['status'],'no_clear_winner')
        self.assertEqual(rank['winner_options'],[])
        self.assertEqual(rank['clocks']['cpu']['fastest_observed_options'],['O1'])

    def test_failed_self_control_blocks_a_preference(self):
        options,aliases,controls,pairs=fixture({'O1':.08,'O2':.06,'O3':.05,'NC':.04})
        controls['O1']['qualified']=False
        rank=four_way_summary(options,aliases,controls,pairs)
        self.assertEqual(rank['status'],'inconclusive')
        self.assertEqual(rank['winner_options'],[])

    def test_shared_winner_is_explicit_and_all_identical_is_not_a_gain(self):
        aliases={'O1':'O1','O2':'O2','O3':'O3','NC':'O3'}
        rank=four_way_summary(*fixture({'O1':.08,'O2':.06,'O3':.04},aliases))
        self.assertEqual(rank['winner_options'],['O3','NeuroCompiler'])
        self.assertEqual(rank['clocks']['cpu']['options']['O3']['runtime_ms'],rank['clocks']['cpu']['options']['NeuroCompiler']['runtime_ms'])
        aliases={name:'O3' for name in ('O1','O2','O3','NC')}
        rank=four_way_summary(*fixture({'O3':.04},aliases))
        self.assertEqual(rank['status'],'identical')
        self.assertEqual(rank['winner_options'],[])

    def test_missing_head_to_head_cannot_be_a_winner(self):
        options,aliases,controls,pairs=fixture({'O1':.08,'O2':.06,'O3':.05,'NC':.04})
        rank=four_way_summary(options,aliases,controls,pairs[:-1])
        self.assertEqual(rank['status'],'inconclusive')
        self.assertFalse(rank['complete_pair_coverage'])

    def test_cpu_wall_tradeoff_does_not_create_a_global_winner(self):
        rank=four_way_summary(*fixture({'O1':.04,'O2':.05,'O3':.06,'NC':.07},
                                      wall_times={'O1':.07,'O2':.06,'O3':.05,'NC':.04}))
        self.assertEqual(rank['status'],'no_clear_winner')
        self.assertEqual(rank['clocks']['cpu']['fastest_observed_options'],['O1'])
        self.assertEqual(rank['clocks']['wall']['fastest_observed_options'],['NeuroCompiler'])
