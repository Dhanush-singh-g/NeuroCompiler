import copy
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from src.benchmarks.polybench import ROOT,TOOLS,tool
from src.benchmarks.persistent import validate


class PersistentNativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir='/tmp');cls.base=Path(cls.temp.name)
        source=cls.base/'fixture.c';source.write_text('''#include <stdint.h>
extern void polybench_timer_start(void),polybench_timer_stop(void),nc_emit_u64(uint64_t);
int nc_benchmark_main(int argc,char **argv){(void)argc;(void)argv;volatile uint64_t sum=0;
polybench_timer_start();for(unsigned i=0;i<200000;i++)sum+=i;polybench_timer_stop();nc_emit_u64(sum);return 0;}
''')
        cls.library=cls.base/'fixture.so';cls.worker=cls.base/'worker'
        tool([TOOLS/'clang','-O2','-shared','-fPIC',source,'-o',cls.library])
        tool([TOOLS/'clang','-O2','-rdynamic',ROOT/'src/benchmarks/persistent_library_worker.c','-ldl','-lm','-o',cls.worker])
        oracle=((1469598103934665603^(199999*200000//2))*1099511628211)&((1<<64)-1)
        cls.manifest={'expected':{'checksum':f'{oracle:016x}','values':1}}

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def collect(self,method,reps=4,first=True):
        result=subprocess.run([str(self.worker),str(self.library),str(self.library),'/unused',str(reps),'2',str(int(first)),'2',method],
                              capture_output=True,check=True,timeout=10)
        row=json.loads(result.stdout);validate(row,self.manifest,2,reps,first,method);return row

    def test_micro_uses_separate_children_and_balances_every_even_batch(self):
        row=self.collect('micro')
        self.assertNotEqual(row['left_pid'],row['right_pid'])
        for s in row['samples']:
            self.assertEqual(s['left_first_invocations'],2);self.assertEqual(len(s['clock_trace']),4)

    def test_odd_micro_counts_and_reverse_order(self):
        row=self.collect('micro',3,False)
        self.assertEqual([s['left_first_invocations'] for s in row['samples']],[1,2])

    def test_batch_uses_one_rpc_per_side(self):
        row=self.collect('batch')
        self.assertEqual([s['left_first_invocations'] for s in row['samples']],[4,0])
        self.assertTrue(all(len(s['clock_trace'])==1 for s in row['samples']))

    def test_missing_trace_or_changed_aggregate_rejects(self):
        row=self.collect('micro');bad=copy.deepcopy(row);bad['samples'][0]['clock_trace'].pop()
        with self.assertRaises(ValueError):validate(bad,self.manifest,2,4,True,'micro')
        bad=copy.deepcopy(row);bad['samples'][0]['left']['cpu_seconds']*=2
        with self.assertRaises(ValueError):validate(bad,self.manifest,2,4,True,'micro')

    def test_corrupted_oracle_or_process_identity_rejects(self):
        row=self.collect('batch');bad=copy.deepcopy(row);bad['samples'][0]['right']['checksum']='bad'
        with self.assertRaises(ValueError):validate(bad,self.manifest,2,4,True,'batch')
        bad=copy.deepcopy(row);bad['right_pid']=bad['left_pid']
        with self.assertRaises(ValueError):validate(bad,self.manifest,2,4,True,'batch')

    def test_invalid_mode_fails_before_launch(self):
        result=subprocess.run([str(self.worker),'/absent','/absent','/unused','4','2','1','2','invalid'],capture_output=True,timeout=10)
        self.assertEqual(result.returncode,2)


if __name__=='__main__':unittest.main()
