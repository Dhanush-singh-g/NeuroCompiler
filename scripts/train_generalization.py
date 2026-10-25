"""Collect native-checked training transitions; freeze a family split and model.

No test source is compiled or scored here. Instruction count is the sole reward.
Use a fresh output directory. The older eight-program experiment stays preserved.
"""
import argparse
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.rl.corpus import records,manifest
from src.rl.llvm_environment import LLVMEnvironment,ACTIONS,FEATURE_NAMES
from src.rl.offline import TransitionLearner
from src.presentation.server import toolchain
from src.presentation.worker import command,save

ROOT=Path(__file__).resolve().parents[1]
INPUTS=['1','3']


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def native_output(path,arg):
    result=subprocess.run([str(Path(path).resolve()),arg],capture_output=True,timeout=3,
                          env={'PATH':'/usr/bin:/bin','LANG':'C','LC_ALL':'C'})
    if result.returncode or len(result.stdout)>65536:raise ValueError('Native correctness invocation failed.')
    return result.stdout


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();output=args.output.resolve()
    if output.exists():p.error('Use a fresh output directory; no overwrites.')
    output.mkdir(parents=True)
    config=toolchain();tools=Path(config['llvm_bin']);split=manifest()
    save(output/'split.json',split)
    declaration={'schema':2,'objective':'instruction_count','horizon':4,'episodes':3,'seed':20261026,
      'reward':'log((before+1)/(after+1)) - 0.001 per non-STOP action; STOP reward 0',
      'actions':ACTIONS,'feature_names':FEATURE_NAMES,'toolchain':config['toolchain_sha256'],
      'split_sha256':sha(output/'split.json'),'correctness_inputs':INPUTS,
      'native_oracles':'GCC -O0 and Clang -O0 must agree; every probed transform matches both fixed inputs.',
      'exploration':['seeded uniform non-STOP walk','greedy immediate-reward walk','fixed mem2reg/instcombine/simplifycfg/gvn walk'],
      'learning':{'gamma':.9,'iterations':20,'ridge':1.,'hybrid_top_k':3},
      'evaluation_plan':{'scope':'12 authored synthetic programs, six unseen algorithm families; two variants are not independent families.',
        'modes':['sl','rl','hybrid'],'baselines':['O3','Oz','fixed','random'],
        'fixed':['mem2reg','instcombine','simplifycfg','gvn'],'random_seed':20261027,
        'guard':'Minimum instruction count among raw policy checkpoints and O3; prefer O3 on a tie.',
        'runtime':'Not evaluated by this count study. App runtime comparison is separate.',
        'no_selection':'One frozen model; no test-based tuning or model selection.'},
      'implementation_sha256':{name:sha(ROOT/name) for name in ('scripts/train_generalization.py','scripts/evaluate_generalization.py',
        'src/rl/corpus.py','src/rl/offline.py','src/rl/llvm_environment.py','src/hybrid/sequential.py')},
      'gcc_version':command(['gcc','--version'],ROOT).splitlines()[0],
      'frontend':['-O1','-Xclang','-disable-llvm-passes','-emit-llvm'],
      'scope':'Synthetic count-proxy expansion; old research reservations and runtime labels are untouched.'}
    save(output/'declaration.json',declaration);context=sha(output/'declaration.json')
    rng=np.random.default_rng(declaration['seed']);rows=[]
    include=command(['gcc','-print-file-name=include'],ROOT).strip()
    for record in records():
        if record['split']!='train':continue
        directory=output/record['id'];directory.mkdir();source=directory/'source.c';source.write_text(record['source'])
        command(['gcc','-O0',source,'-lm','-o',directory/'gcc-reference'],ROOT)
        command([tools/'clang','-O0','-isystem',include,source,'-lm','-o',directory/'clang-reference'],ROOT)
        expected={arg:native_output(directory/'gcc-reference',arg) for arg in INPUTS}
        if any(native_output(directory/'clang-reference',arg)!=expected[arg] for arg in INPUTS):
            raise ValueError('Cross-compiler reference mismatch: '+record['id'])
        initial=directory/'initial.bc'
        command([tools/'clang','-O1','-Xclang','-disable-llvm-passes','-isystem',include,'-emit-llvm','-c',source,'-o',initial],ROOT)
        verified={}
        def check(path):
            digest=sha(path)
            if digest not in verified:
                exe=directory/'check-program'
                command([tools/'clang',path,'-O3','-Xclang','-disable-llvm-passes','-lm','-o',exe],ROOT)
                if any(native_output(exe,arg)!=expected[arg] for arg in INPUTS):
                    raise ValueError('Transition output mismatch: '+record['id'])
                verified[digest]=True
        check(initial)
        for episode in range(declaration['episodes']):
            env=LLVMEnvironment(tools,directory/f'episode{episode}');state=env.reset(initial)
            for step in range(4):
                rewards={}
                for action in ACTIONS:
                    probe=LLVMEnvironment(tools,directory/f'probe{episode}_{step}_{action}')
                    probe.reset(env.current);probe.history=list(env.history)
                    transition=probe.step(action);after=transition['after'];check(probe.current)
                    reward=0. if action=='STOP' else math.log((state['instructions']+1)/(after['instructions']+1))-.001
                    rows.append({'program':record['id'],'family':record['family'],'split':'train',
                        'objective':'instruction_count','context_id':context,'state':state['features'],
                        'action':action,'next_state':after['features'],'reward':reward,'done':after['done'],
                        'next_actions':after['available_actions'],'transform_verified':True,'native_semantic_validation':True,
                        'correctness_inputs':INPUTS,'source_sha256':record['source_sha256'],
                        'before_instructions':state['instructions'],'after_instructions':after['instructions'],
                        'before_sha256':state['bitcode_sha256'],'after_sha256':after['bitcode_sha256'],
                        'compile_elapsed_seconds':transition['compile_elapsed_seconds']})
                    rewards[action]=reward
                action=(str(rng.choice([a for a in ACTIONS if a!='STOP'])) if episode==0 else
                        max(ACTIONS,key=lambda a:rewards[a]) if episode==1 else
                        declaration['evaluation_plan']['fixed'][step])
                state=env.step(action)['after']
                if state['done']:break
        print(record['id'],len(rows),'native-checked transitions',flush=True)
    save(output/'transitions.json',{'declaration':declaration,'rows':rows})
    agent=TransitionLearner(list(ACTIONS),'instruction_count').fit(rows)
    model={'schema':2,'algorithm':'offline fitted Q iteration + immediate-reward ridge SL',
        'objective':'instruction_count','deployment_qualified':False,'actions':ACTIONS,'feature_names':FEATURE_NAMES,
        'horizon':4,'gamma':agent.gamma,'context_id':context,'center':agent.center.tolist(),'scale':agent.scale.tolist(),
        'immediate':{a:w.tolist() for a,w in agent.immediate.items()},'q':{a:w.tolist() for a,w in agent.q.items()},
        'training_rows':len(rows),'training_programs':agent.programs,
        'training_families':sorted({r['family'] for r in rows}),'bellman_residuals':agent.bellman_residuals,
        'dataset_sha256':sha(output/'transitions.json'),'split_sha256':sha(output/'split.json'),
        'declaration_sha256':sha(output/'declaration.json'),'toolchain_sha256':config['toolchain_sha256'],
        'limitations':['Instruction-count reward, not runtime-trained.','Authored synthetic corpus; real-world generalization unproven.',
          'Action support is global, not state-local.','SL pruning can discard useful preparation actions.',
          'Every training transform passed two fixed native input checks; this is not semantic equivalence proof.',
          'O3/checkpoint guard is deterministic static selection, not a learned improvement.']}
    save(output/'model.json',model)
    save(output/'frozen.json',{'model_sha256':sha(output/'model.json'),'dataset_sha256':sha(output/'transitions.json'),
        'declaration_sha256':sha(output/'declaration.json'),'split_sha256':sha(output/'split.json')})
    print('Frozen model and split; no test program was compiled.',flush=True)

if __name__=='__main__':main()
