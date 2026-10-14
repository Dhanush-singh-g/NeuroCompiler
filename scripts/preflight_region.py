"""Training-only build/oracle preflight; all clocks excluded from fit labels."""
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.benchmarks.region import *


def main():
    output=ROOT/'results/region_preflight.json'
    if output.exists():raise ValueError('Existing preflight; refusing overwrite')
    if (ROOT/'results/region_declaration.json').exists():raise ValueError('Preflight must precede declaration')
    worker=compile_worker();report={'scope':'training-only preflight; all clocks excluded from learning',
                                   'complete':False,'manifests':{}}
    for program in PROGRAMS:
        m=compile_program(program,worker)
        for case in CASES:
            if case.startswith(program+'_'):
                report['manifests'][case]=prepare_case(case,m);save(output,report)
                print('Preflight',case,'four independent oracle comparisons pass',flush=True)
    report['complete']=True;save(output,report)


if __name__=='__main__':main()
