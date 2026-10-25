"""Reproduce diagnostic validation without changing the frozen model or tests."""
import argparse
import hashlib
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.rl.evidence import audit,digest
from src.rl.validation import family_validation,range_profile
from src.presentation.worker import save
ROOT=Path(__file__).resolve().parents[1]

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    if args.output.exists():p.error('Use a fresh output directory; no overwrites.')
    audit(ROOT/'presentation')
    args.output.mkdir(parents=True)
    model=json.loads((ROOT/'presentation/sequential_model.json').read_text())
    rows=json.loads((ROOT/'presentation/sequential_training.json').read_text())['rows']
    declaration={'model_sha256':digest(ROOT/'presentation/sequential_model.json'),
        'dataset_sha256':model['dataset_sha256'],'folds':4,'seed':20261028,
        'hyperparameter_selection':False,'scope':'Training-only diagnostic. Frozen test programs are not used.',
        'implementation_sha256':{name:digest(ROOT/name) for name in ('scripts/validate_count_model.py','src/rl/validation.py')}}
    save(args.output/'declaration.json',declaration)
    validation=family_validation(rows,list(model['actions']))
    save(args.output/'validation.json',{'declaration':declaration,**validation})
    save(args.output/'support.json',range_profile(rows,model,declaration['model_sha256']))
    print(json.dumps(validation['family_balanced'],indent=2),flush=True)
