"""Advisory input-range reporting around the unchanged frozen policy."""
import hashlib
import json
from pathlib import Path
from src.rl.validation import describe_support
from src.rl.llvm_environment import LLVMEnvironment
from src.hybrid.sequential import ROOT


def attach_support(sequence,llvm_bin,episode,directory,horizon=4):
    contents=(ROOT/'presentation/training_support.json').read_bytes()
    manifest=json.loads((ROOT/'presentation/credibility_manifest.json').read_text())
    if hashlib.sha256(contents).hexdigest()!=manifest['artifacts']['training_support.json']:
        raise ValueError('Training-range profile changed after its diagnostic declaration.')
    profile=json.loads(contents)
    if profile['model_sha256']!=sequence['model_sha256'] or profile['dataset_sha256']!=sequence['dataset_sha256']:
        raise ValueError('Training-range profile does not match the frozen model/data. Update all presentation artifacts together.')
    observations=[];history=[]
    for index,step in enumerate(sequence['trace']):
        # Reuse the original environment's feature extractor in fresh read-only
        # diagnostic copies, without changing the frozen inference implementation.
        observer=LLVMEnvironment(llvm_bin,Path(directory)/f'step{index}',horizon=horizon)
        observer.reset(Path(episode)/f'state{index}.bc');observer.history=list(history)
        diagnostic=describe_support(observer.observe()['features'],profile)
        step['input_support']=diagnostic;observations.append(diagnostic)
        history.append(step['action'])
    sequence['input_support']={'status':'outside_training_ranges' if any(r['outside_fields'] for r in observations) else 'within_training_ranges',
        'outside_steps':sum(bool(r['outside_fields']) for r in observations),'evaluated_steps':len(observations),
        'profile_sha256':hashlib.sha256((ROOT/'presentation/training_support.json').read_bytes()).hexdigest(),
        'confidence_calibrated':False,'selection_changed':False,'scope':profile['scope']}
