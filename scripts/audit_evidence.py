"""Audit the committed count evidence; optionally reproduce frozen coefficients."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.rl.evidence import audit

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]/'presentation')
    p.add_argument('--refit',action='store_true')
    args=p.parse_args()
    print(json.dumps(audit(args.root,args.refit),indent=2))
