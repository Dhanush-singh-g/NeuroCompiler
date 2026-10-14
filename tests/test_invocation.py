import copy
import json
import math
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.benchmarks.invocation import BASIS,PRIME,MASK,ROOT,TOOLS,MENU,PROTOCOL,tool,validate_cell,xxh64,json_tokens,summarize
from src.supervised.invocation import NativeSelector,program_cv,training_rows


class OracleTests(unittest.TestCase):
    def test_official_seeded_and_long_input_xxh64_vectors(self):
        data=json.loads((Path(__file__).parent/'fixtures/xxh64_vectors.json').read_text())
        state=2654435761;buffer=bytearray()
        for _ in range(max(v['size'] for v in data['vectors'])):
            buffer.append(state>>56);state=state*11400714785074694797&MASK
        for v in data['vectors']:
            with self.subTest(size=v['size'],seed=v['seed']):
                self.assertEqual(xxh64(bytes(buffer[:v['size']]),v['seed']),int(v['expected_hex'],16))

    def test_published_xxh64_vectors(self):
        for value,expected in [(b'',0xef46db3751d8e999),(b'a',0xd24ec4f1a98c6e5b),(b'abc',0x44bc2cf5ad770999)]:
            self.assertEqual(xxh64(value),expected)

    def test_nested_json_token_boundaries_and_escaped_delimiters(self):
        self.assertEqual(json_tokens(b'{"x":[1,"}"]}'),[[1,0,13],[3,2,3],[2,5,12],[4,6,7],[3,9,10]])


class NativeOrderingTests(unittest.TestCase):
    def test_worker_switches_each_invocation_and_checks_separate_placement(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp);worker=base/'worker'
            tool([TOOLS/'clang','-O2','-rdynamic',ROOT/'src/benchmarks/invocation_worker.c','-ldl','-lm','-o',worker])
            so=[]
            for side in ['A','B']:
                source=base/(side+'.c');library=base/(side+'.so')
                source.write_text('#include <stdio.h>\n#include <stdint.h>\nextern void polybench_timer_start(void),polybench_timer_stop(void),nc_emit_u64(uint64_t);\n'
                    'int nc_benchmark_main(int argc,char **argv){if(argc!=3)return 2;FILE *f=fopen(argv[1],"a");if(!f)return 2;'
                    f'fputc(\'{side}\',f);fclose(f);polybench_timer_start();volatile int x=0;for(int i=0;i<1000;i++)x+=i;'
                    'polybench_timer_stop();nc_emit_u64(7);return 0;}')
                tool([TOOLS/'clang','-O2','-fPIC','-shared',source,'-o',library]);so.append(str(library))
            trace=base/'trace';row=json.loads(subprocess.run([str(worker),*so,'3','2','1',str(trace)],capture_output=True,check=True).stdout)
            expected='A'+'AB'*2
            for p in range(2):
                for i in range(3):expected+='AB' if (p+i)%2==0 else 'BA'
            self.assertEqual(trace.read_text(),expected)
            m={'expected':{'checksum':f'{(BASIS^7)*PRIME&MASK:016x}','values':1}}
            validate_cell(row,m,2,3,True,placement=True)
            bad=copy.deepcopy(row);bad['samples'][0]['left_first_invocations']+=1
            with self.assertRaisesRegex(ValueError,'ordering'):validate_cell(bad,m,2,3,True)
            bad=copy.deepcopy(row);bad['right_entry_address']=bad['left_entry_address']
            with self.assertRaisesRegex(ValueError,'placement'):validate_cell(bad,m,2,3,True,placement=True)


def labels_fixture():
    labels=[];manifests={}
    for p in range(5):
        for i in range(2 if p else 1):
            case=f'p{p}_{i}';aliases={c:('O3' if c in ['O3','Os'] else c) for c in MENU}
            features={c:[float(p),float(j),float(i)] for j,c in enumerate(list(MENU)[1:])}
            loss={'speedup':.9,'log_speedup':math.log(.9),'interval':[.89,.91],'confirmed_gain':False}
            outcomes={c:dict(loss) for c in MENU};outcomes['O3']={'speedup':1.,'log_speedup':0.,'interval':[1.,1.],'confirmed_gain':False}
            outcomes['Os']=outcomes['O3']
            labels.append({'case':case,'program':f'p{p}','features':features,'outcomes':outcomes,'aliases':aliases})
            manifests[case]={'features':features,'aliases':aliases}
    return labels,manifests


class LearningTests(unittest.TestCase):
    def test_positive_effect_with_failed_candidate_control_is_not_admitted(self):
        m={'program':'p','features':{},'aliases':{c:('O2' if c=='O2' else 'O3') for c in MENU}}
        rows=[]
        for block in range(PROTOCOL['blocks']):
            for role,right in [('qualification',.04),('candidate_control',.08),('effect',.03)]:
                rows.append({'case':'p','role':role,'choice':'O3' if role=='qualification' else 'O2',
                    'samples':[{'left':{'cpu_seconds':.04,'wall_seconds':.04},
                                'right':{'cpu_seconds':right,'wall_seconds':right*2}} for _ in range(PROTOCOL['pairs'])]})
        labels,d=summarize({'manifests':{'p':m},'records':rows})
        self.assertEqual(len(labels),1)
        self.assertNotIn('O2',labels[0]['outcomes'])
        candidate=d['p']['measurements']['O2']['cpu']['effect']
        self.assertGreater(candidate['speedup'],1.03)
        self.assertFalse(candidate['qualified']);self.assertFalse(candidate['confirmed_gain'])

    def test_aliases_do_not_inflate_independent_target_count(self):
        labels,_=labels_fixture();rows=training_rows(labels,False)
        self.assertEqual(len(rows),3*len(labels))
        self.assertNotIn('Os',{r['choice'] for r in rows})

    def test_weight_is_equal_per_original_program_with_unequal_input_coverage(self):
        labels,_=labels_fixture();model=NativeSelector().fit(labels)
        self.assertEqual(len(model.programs),5)
        for weight in model.program_weight_totals.values():self.assertAlmostEqual(weight,1.)

    def test_cv_holds_all_input_variants_of_original_program_out(self):
        labels,manifests=labels_fixture();result=program_cv(labels,manifests,10,True,.03)
        self.assertTrue(result['eligible'])
        for fold in result['folds']:
            self.assertNotIn(fold['held_program'],fold['train_programs'])
            self.assertTrue(all(not case.startswith(fold['held_program']+'_') for case in fold['train_cases']))

    def test_missing_selected_target_invalidates_cv(self):
        labels,manifests=labels_fixture();labels[0]['outcomes'].pop('O2')
        with patch.object(NativeSelector,'choose',return_value={'choice':'O2','scores':{}}):
            result=program_cv(labels,manifests,10,True,.03)
        self.assertFalse(result['eligible']);self.assertIsNone(result['score'])
        self.assertEqual(len(result['unscorable']),1)


if __name__=='__main__':unittest.main()
