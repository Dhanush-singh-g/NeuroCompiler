"""Training-only correctness preflight; no preflight timing enters fitting."""
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.benchmarks.broad import BASE, ROOT, CASES, MENU, BASIS, PRIME, MASK, input_bytes, oracle, run_cell, save, sha


def main():
    path=ROOT/'results/broad_preflight.json'
    if path.exists():raise ValueError('Existing preflight')
    inputs=BASE/'preflight_inputs';inputs.mkdir(exist_ok=False)
    report={'scope':'training correctness only; all clock observations excluded from formal labels',
            'records':[],'complete':False,'correct_workloads':0}
    for case in CASES:
        program=case.split('_')[0];m=json.loads((BASE/'programs'/program/'manifest.json').read_text())
        data=inputs/(case+'.dat');data.write_bytes(input_bytes(case));value=oracle(case)
        m.update({'id':case,'input':str(data),'input_sha256':sha(data),'repetitions':1,
                  'expected':{'checksum':f'{(BASIS^value)*PRIME&MASK:016x}','values':1}})
        for choice in MENU:
            report['records'].append(run_cell(m,'reference_O0',choice,0,'preflight',pairs=1,repetitions=1))
            save(path,report)
        report['correct_workloads']+=1;save(path,report);print('Preflight correct',case,flush=True)
    report['complete']=True;save(path,report)


if __name__=='__main__':main()
