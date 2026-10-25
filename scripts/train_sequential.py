"""Generate real LLVM transitions and train experimental instruction-count policies."""
import argparse
import hashlib
import json
import math
import sys
import tempfile
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from src.presentation.server import toolchain
from src.presentation.worker import command,save
from src.benchmarks.kernels import PRELUDE,KERNELS,SUFFIX
from src.rl.llvm_environment import LLVMEnvironment,ACTIONS,FEATURE_NAMES
from src.rl.offline import TransitionLearner

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--episodes',type=int,default=2)
    args=p.parse_args()
    if args.output.exists():p.error('Use a fresh output directory; no overwrite.')
    args.output.mkdir(parents=True)
    config=toolchain();tools=Path(config['llvm_bin']);rng=np.random.default_rng(20261025)
    declaration={'objective':'instruction_count','reward':'log((before+1)/(after+1)) - 0.001 per non-STOP action; STOP reward 0',
                 'horizon':4,'actions':ACTIONS,'feature_names':FEATURE_NAMES,'seed':20261025,
                 'toolchain':config['toolchain_sha256'],'training_programs':list(KERNELS),
                 'scope':'Eight already-opened synthetic programs, no new real-program holdout evaluation; structural LLVM verification only during collection.'}
    declaration['learning']={'gamma':.9,'iterations':20,'ridge':1.,'hybrid_top_k':3}
    declaration['source_sha256']={name:hashlib.sha256((PRELUDE+body+SUFFIX).encode()).hexdigest() for name,body in KERNELS.items()}
    declaration['implementation_sha256']={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in
        ('scripts/train_sequential.py','src/rl/llvm_environment.py','src/rl/offline.py','src/features/transform.py')}
    declaration['frontend']=['-O1','-Xclang','-disable-llvm-passes','-emit-llvm']
    declaration['gcc_version']=command(['gcc','--version'],ROOT).splitlines()[0]
    context=hashlib.sha256(json.dumps(declaration,sort_keys=True).encode()).hexdigest()
    save(args.output/'declaration.json',declaration)
    rows=[]
    includes=command(['gcc','-print-file-name=include'],ROOT).strip()
    for name,body in KERNELS.items():
        directory=args.output/name;directory.mkdir()
        source=directory/'source.c';source.write_text(PRELUDE+body+SUFFIX)
        initial=directory/'initial.bc'
        command([tools/'clang','-O1','-Xclang','-disable-llvm-passes','-isystem',includes,
                 '-emit-llvm','-c',source,'-o',initial],ROOT)
        for episode in range(args.episodes):
            env=LLVMEnvironment(tools,directory/f'episode{episode}',horizon=4);state=env.reset(initial)
            for step in range(4):
                options=[]
                for action in ACTIONS:
                    probe=LLVMEnvironment(tools,directory/f'probe{episode}_{step}_{action}',horizon=4)
                    probe.reset(env.current);probe.history=list(env.history)
                    transition=probe.step(action);after=transition['after']
                    reward=0. if action=='STOP' else math.log((state['instructions']+1)/(after['instructions']+1))-.001
                    row={'program':name,'split':'train','objective':'instruction_count','context_id':context,
                         'state':state['features'],'action':action,'next_state':after['features'],
                         'reward':reward,'done':after['done'],'next_actions':after['available_actions'],
                         'transform_verified':True,'native_semantic_validation':False,
                         'before_instructions':state['instructions'],'after_instructions':after['instructions'],
                         'before_sha256':state['bitcode_sha256'],'after_sha256':after['bitcode_sha256'],
                         'compile_elapsed_seconds':transition['compile_elapsed_seconds']}
                    rows.append(row);options.append(action)
                # Explore a seeded sequence, not a reward-selected training winner.
                action=str(rng.choice([a for a in options if a!='STOP']))
                state=env.step(action)['after']
                if state['done']:break
        print(name,len(rows),'transitions',flush=True)
    save(args.output/'transitions.json',{'declaration':declaration,'rows':rows})
    agent=TransitionLearner(list(ACTIONS),'instruction_count',ridge=1.,iterations=20).fit(rows)
    model={'schema':1,'algorithm':'offline fitted Q iteration + immediate-reward ridge SL',
           'objective':'instruction_count','deployment_qualified':False,'actions':ACTIONS,
           'feature_names':FEATURE_NAMES,'horizon':4,'gamma':agent.gamma,'context_id':context,
           'center':agent.center.tolist(),'scale':agent.scale.tolist(),
           'immediate':{a:w.tolist() for a,w in agent.immediate.items()},
           'q':{a:w.tolist() for a,w in agent.q.items()},'training_rows':len(rows),
           'training_programs':agent.programs,'bellman_residuals':agent.bellman_residuals,
           'dataset_sha256':hashlib.sha256((args.output/'transitions.json').read_bytes()).hexdigest(),
           'toolchain_sha256':config['toolchain_sha256'],
           'limitations':['Proxy objective, not a runtime-trained policy.','Small synthetic training corpus; no validated real-program generalization.',
                          'Offline action support is global, not state-local.','SL pruning can discard useful preparation actions.',
                          'Training transitions use LLVM structural verification; native output checks happen in the app before timing.']}
    save(args.output/'model.json',model)
    print('Saved actual transition dataset and trained SL/RL coefficients:',args.output,flush=True)


if __name__=='__main__':main()
