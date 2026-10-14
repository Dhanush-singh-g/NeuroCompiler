import copy
import math
import unittest

from src.features.timed_region import analyze, vector, FEATURE_NAMES
from src.features.transform import METRICS
from src.benchmarks.region import clock_effect, PROTOCOL, validate_cell


IR = '''
define i32 @nc_benchmark_main() {
entry:
 call void @prepare()
 call void @polybench_timer_start()
 br label %loop
after:
 call void @verify()
 ret i32 0
loop:
 %i = phi i32 [ 0, %entry ], [ %j, %loop ]
 call void @library()
 %j = add i32 %i, 1
 %c = icmp slt i32 %j, 4
 br i1 %c, label %loop, label %stop
stop:
 call void @polybench_timer_stop()
 br label %after
}
define void @prepare() {
entry:
 %x = add i32 1, 2
 ret void
}
define void @verify() {
entry:
 %x = mul i32 3, 4
 ret void
}
define void @library() {
entry:
 %x = lshr i32 100, 1
 ret void
}
'''


class TimedFeaturesTests(unittest.TestCase):
    def test_cfg_order_and_untimed_helpers(self):
        result=analyze(IR)
        self.assertEqual(result['reachable_functions'], ['library'])
        self.assertEqual(result['entry'][METRICS.index('instructions')], 6)
        self.assertEqual(result['closure'][METRICS.index('instructions')], 8)
        self.assertEqual(result['entry'][METRICS.index('cyclic_blocks')], 1)
        self.assertEqual(result['ambiguous_instructions'], 0)

    def test_untimed_changes_do_not_change_vector(self):
        changed=IR.replace('%x = mul i32 3, 4', '%x = fdiv double 3.0, 4.0')
        self.assertEqual(vector(analyze(IR), analyze(changed)), vector(analyze(IR), analyze(IR)))
        self.assertEqual(len(vector(analyze(IR), analyze(IR))), len(FEATURE_NAMES))

    def test_inlined_work_and_indirect_uncertainty(self):
        result=analyze(IR.replace('call void @library()', '%k = mul i32 2, 9\n call void %callback()'))
        self.assertEqual(result['reachable_functions'], [])
        self.assertTrue(result['indirect_lower_bound'])
        self.assertEqual(result['entry'][METRICS.index('integer')], 2)

    def test_missing_boundary_rejects(self):
        with self.assertRaisesRegex(ValueError,'Missing timer'):
            analyze(IR.replace('call void @polybench_timer_stop()', ''))

    def test_mixed_phase_join_is_reported(self):
        ir='''define i32 @nc_benchmark_main(i1 %c) {
entry:
 br i1 %c, label %timed, label %join
timed:
 call void @polybench_timer_start()
 %x = add i32 1, 2
 br label %join
join:
 call void @maybe_timed()
 call void @polybench_timer_stop()
 ret i32 0
}'''
        result=analyze(ir)
        self.assertEqual(result['ambiguous_instructions'], 1)
        self.assertNotIn('maybe_timed', result['direct_callees'])


def rows(values):
    return [{'block':i,'samples':[{'left_first':(p%2==0)==bool(i%2),
            'left':{'cpu_seconds':math.exp(value),'wall_seconds':math.exp(value)},
            'right':{'cpu_seconds':1.,'wall_seconds':1.}} for p,value in enumerate(block)]}
            for i,block in enumerate(values)]


class MeasurementTests(unittest.TestCase):
    def test_opposite_starts_cannot_cancel_block_bias(self):
        values=[[.025 if p%2==0 else -.025 for p in range(PROTOCOL['pairs'])] for _ in range(PROTOCOL['blocks'])]
        result=clock_effect(rows(values),'cpu')
        self.assertFalse(result['order_pass'])
        self.assertFalse(result['control_pass'])
        self.assertTrue(all(v>.049 for v in result['block_order_log_differences']))

    def test_balanced_real_effect_passes_order_but_not_null_control(self):
        result=clock_effect(rows([[math.log(1.12)]*PROTOCOL['pairs']]*PROTOCOL['blocks']), 'cpu')
        self.assertTrue(result['order_pass']);self.assertFalse(result['control_pass'])
        self.assertAlmostEqual(result['speedup'],1.12)

    def test_process_order_metadata_and_oracle_checked(self):
        value={'cpu_seconds':.04,'wall_seconds':.04,'checksum':'abcd','values':1,
               'mode':'one_implementation','repetitions':3}
        row={'granularity':'isolated_process','pairs':1,'repetitions':3,'first':True,
             'samples':[{'pair':0,'left_first':True,'left':value,'right':value.copy()}]}
        manifest={'expected':{'checksum':'abcd','values':1}}
        validate_cell(row,manifest,1,3,True)
        altered=copy.deepcopy(row);altered['samples'][0]['left_first']=False
        with self.assertRaises(ValueError):validate_cell(altered,manifest,1,3,True)
        altered=copy.deepcopy(row);altered['samples'][0]['right']['checksum']='bad'
        with self.assertRaises(ValueError):validate_cell(altered,manifest,1,3,True)


if __name__=='__main__':unittest.main()
