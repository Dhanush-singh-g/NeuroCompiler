"""Portable inference and real LLVM rollouts for the experimental proxy models."""
import hashlib
import json
from pathlib import Path
import numpy as np

from src.rl.offline import TransitionLearner
from src.rl.llvm_environment import LLVMEnvironment,ACTIONS,FEATURE_NAMES

ROOT=Path(__file__).resolve().parents[2]
MODEL_PATH=ROOT/'presentation/sequential_model.json'


def load_agent(model_path=None):
    contents=Path(model_path or MODEL_PATH).read_bytes();data=json.loads(contents)
    if data['objective']!='instruction_count' or data['actions']!=ACTIONS or data['feature_names']!=FEATURE_NAMES:
        raise ValueError('Sequential model schema/action/objective mismatch.')
    agent=TransitionLearner(list(ACTIONS),'instruction_count',gamma=data['gamma'])
    agent.center=np.asarray(data['center']);agent.scale=np.asarray(data['scale'])
    if agent.center.shape!=(len(FEATURE_NAMES),) or agent.scale.shape!=agent.center.shape or np.any(agent.scale<=0):
        raise ValueError('Invalid sequential normalization.')
    agent.immediate={a:np.asarray(w) for a,w in data['immediate'].items()}
    agent.q={a:np.asarray(w) for a,w in data['q'].items()}
    agent.supported=list(agent.q)
    if set(agent.supported)!=set(ACTIONS) or set(agent.immediate)!=set(ACTIONS):
        raise ValueError('Incomplete learned action coverage.')
    for value in [agent.center,agent.scale,*agent.q.values(),*agent.immediate.values()]:
        if not np.isfinite(value).all():raise ValueError('Nonfinite learned parameters.')
    if any(w.shape!=(len(FEATURE_NAMES)+1,) for w in [*agent.q.values(),*agent.immediate.values()]):
        raise ValueError('Invalid sequential weight shape.')
    return agent,data,hashlib.sha256(contents).hexdigest()


def select_checkpoint(checkpoints, baseline=None):
    """Static count guard. Prefer O3 on ties; never claim this rule is learned."""
    if not checkpoints:raise ValueError('A rollout requires at least one checkpoint.')
    if any(c['instructions']<0 for c in checkpoints):raise ValueError('Invalid instruction count.')
    best=min(checkpoints,key=lambda c:c['instructions'])
    if baseline is not None and baseline['instructions']<=best['instructions']:
        return {**baseline,'applied':'O3','actions':[]}
    return {**best,'applied':'learned_checkpoint'}


def rollout(llvm_bin, initial, directory, mode, tool_hashes, baseline=None, model_path=None):
    if mode not in ('sl','rl','hybrid'):raise ValueError('Unknown sequential mode.')
    agent,model,digest=load_agent(model_path)
    if model['toolchain_sha256']!=tool_hashes:raise ValueError('Sequential model toolchain mismatch.')
    env=LLVMEnvironment(llvm_bin,directory,horizon=model['horizon']);state=env.reset(initial)
    beginning=state['instructions'];trace=[]
    checkpoints=[{'instructions':beginning,'path':env.current,'actions':[],'step':0}]
    while not state['done']:
        decision=agent.choose(state['features'],mode,top_k=3,available=state['available_actions'])
        transition=env.step(decision['action']);after=transition['after']
        trace.append({'action':decision['action'],'before_instructions':state['instructions'],
                      'after_instructions':after['instructions'],'q_score':decision['q_scores'][decision['action']],
                      'immediate_prediction':decision['immediate_scores'][decision['action']],
                      'allowed_candidates':decision['candidates'],'compile_elapsed_seconds':transition['compile_elapsed_seconds']})
        state=after
        checkpoints.append({'instructions':state['instructions'],'path':env.current,
                            'actions':[t['action'] for t in trace if t['action']!='STOP'],'step':len(trace)})
    selected=select_checkpoint(checkpoints,baseline)
    selection={k:v for k,v in selected.items() if k!='path'}
    selection.update(rule='Minimum static instruction count over policy checkpoints and O3; O3 wins ties.',
                     learned_rule=False,runtime_protection=False)
    return {'mode':mode,'objective':'instruction_count','trace':trace,'initial_instructions':beginning,
            'final_instructions':selected['instructions'],'policy_final_instructions':state['instructions'],
            'best_policy_instructions':min(c['instructions'] for c in checkpoints),
            'selected_actions':selected['actions'],'selection':selection,
            'checkpoints':[{k:v for k,v in c.items() if k!='path'} for c in checkpoints],
            'model_sha256':digest,
            'training_rows':model['training_rows'],'training_programs':len(model['training_programs']),
            'dataset_sha256':model['dataset_sha256'],'deployment_qualified':False,
            'scope':'Trained count-proxy rollout plus explicit static checkpoint/O3 guard. Not runtime-trained; real-world generalization unproven.'},selected['path']
