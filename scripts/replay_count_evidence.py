"""Replay opened synthetic cases with the exact committed model/data bindings.

This is replication of old cases, never a fresh unseen-program experiment.
It does not collect new training data or replace deployed weights.
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.rl.live_evidence import audit_live
from src.presentation.worker import save
ROOT=Path(__file__).resolve().parents[1]

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();output=args.output.resolve()
    if output.exists():p.error('Use a fresh replay directory; no overwrites.')
    evidence=audit_live();output.mkdir(parents=True)
    names={'sequential_model.json':'model.json','sequential_training.json':'transitions.json',
           'generalization_frozen.json':'frozen.json','generalization_split.json':'split.json',
           'generalization_declaration.json':'declaration.json'}
    for original,target in names.items():shutil.copyfile(ROOT/'presentation'/original,output/target)
    save(output/'REPLAY.json',{'model_sha256':evidence['integrity']['model_sha256'],
        'scope':'Replication of already-opened authored cases. Not a fresh unseen-program result. No model retuning.'})
    subprocess.run([sys.executable,ROOT/'scripts/evaluate_generalization.py','--run',output],cwd=ROOT,check=True)
    # The parent frozen metadata is copied byte-for-byte, retaining the current
    # committed coefficients and data even though replayed BC paths may differ.
    if json.loads((output/'frozen.json').read_text())!=json.loads((ROOT/'presentation/generalization_frozen.json').read_text()):
        raise ValueError('Replay context changed.')
    subprocess.run([sys.executable,ROOT/'scripts/audit_checkpoint_baselines.py','--artifacts',output/'evaluation',
                    '--output',output/'checkpoint_audit'],cwd=ROOT,check=True)
    print('Replayed opened cases with the committed model; no deployed files changed.')
