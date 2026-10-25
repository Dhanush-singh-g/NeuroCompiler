"""One-shot evaluation of a frozen count model on predeclared unseen families.

Reports all programs, raw policy and guarded policy, fixed/random/Oz controls.
Refuses to repeat an evaluation or accept a changed dataset/declaration/model.
Does not train, tune, select models, or measure native runtime.
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.rl.corpus import records,manifest
from src.rl.llvm_environment import LLVMEnvironment,ACTIONS
from src.hybrid.sequential import rollout
from src.presentation.server import toolchain
from src.presentation.worker import command,save
from train_generalization import sha,native_output,INPUTS

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True)
    args=p.parse_args();run=args.run.resolve()
    frozen=json.loads((run/'frozen.json').read_text())
    for field,name in [('model_sha256','model.json'),('dataset_sha256','transitions.json'),
                       ('declaration_sha256','declaration.json'),('split_sha256','split.json')]:
        if sha(run/name)!=frozen[field]:raise ValueError('Frozen artifact changed: '+name)
    split=json.loads((run/'split.json').read_text());declaration=json.loads((run/'declaration.json').read_text())
    if split!=manifest():raise ValueError('Corpus/split changed after freeze.')
    for name,digest in declaration['implementation_sha256'].items():
        if sha(ROOT/name)!=digest:raise ValueError('Declared implementation changed: '+name)
    train=json.loads((run/'transitions.json').read_text())['rows']
    test_families={r['family'] for r in split['programs'] if r['split']=='test'}
    if test_families & {r['family'] for r in train}:raise ValueError('Family leakage.')
    if any(r['split']!='train' for r in train):raise ValueError('Training split contamination.')
    # Creation is exclusive. A failed run is retained and cannot be silently restarted.
    evaluation=run/'evaluation';evaluation.mkdir(exist_ok=False)
    save(evaluation/'started.json',{'frozen':frozen,'plan':declaration['evaluation_plan']})
    config=toolchain();tools=Path(config['llvm_bin'])
    if declaration['toolchain']!=config['toolchain_sha256']:raise ValueError('Compiler context changed.')
    include=command(['gcc','-print-file-name=include'],ROOT).strip()
    rng=np.random.default_rng(declaration['evaluation_plan']['random_seed']);results=[]
    for record in records():
        if record['split']!='test':continue
        directory=evaluation/record['id'];directory.mkdir();source=directory/'source.c';source.write_text(record['source'])
        command(['gcc','-O0',source,'-lm','-o',directory/'gcc-reference'],ROOT)
        command([tools/'clang','-O0','-isystem',include,source,'-lm','-o',directory/'clang-reference'],ROOT)
        expected={arg:native_output(directory/'gcc-reference',arg) for arg in INPUTS}
        if any(native_output(directory/'clang-reference',arg)!=expected[arg] for arg in INPUTS):
            raise ValueError('Heldout reference mismatch: '+record['id'])
        initial=directory/'initial.bc'
        command([tools/'clang','-O1','-Xclang','-disable-llvm-passes','-isystem',include,'-emit-llvm','-c',source,'-o',initial],ROOT)
        counts={};checks={};traces={}
        def inspect(label,path):
            env=LLVMEnvironment(tools,directory/('inspect_'+label));state=env.reset(path)
            exe=directory/('program_'+label)
            command([tools/'clang',path,'-O3','-Xclang','-disable-llvm-passes','-lm','-o',exe],ROOT)
            correct=all(native_output(exe,arg)==expected[arg] for arg in INPUTS)
            counts[label]=state['instructions'];checks[label]=correct
            if not correct:raise ValueError('Heldout output mismatch: '+record['id']+' '+label)
        for label in ('O3','Oz'):
            bc=directory/(label+'.bc');command([tools/'opt','-'+label,initial,'-o',bc],ROOT);inspect(label,bc)
        for label in ('fixed','random'):
            env=LLVMEnvironment(tools,directory/label);env.reset(initial)
            actions=(declaration['evaluation_plan']['fixed'] if label=='fixed' else
                     [str(rng.choice([a for a in ACTIONS if a!='STOP'])) for _ in range(4)])
            for action in actions:env.step(action)
            traces[label]=actions;inspect(label,env.current)
        for mode in ('sl','rl','hybrid'):
            sequence,guarded=rollout(tools,initial,directory/mode,mode,config['toolchain_sha256'],
                baseline={'instructions':counts['O3'],'path':directory/'O3.bc','step':0},model_path=run/'model.json')
            # Validate and score the terminal policy independently of the deterministic guard.
            non_stop=[t for t in sequence['trace'] if t['action']!='STOP']
            raw=directory/mode/('state'+str(len(non_stop))+'.bc')
            inspect(mode+'_raw',raw);inspect(mode+'_guarded',guarded)
            traces[mode]=sequence
        row={'id':record['id'],'family':record['family'],'source_sha256':record['source_sha256'],
             'split':'test','counts':counts,'native_checks':checks,'inputs':INPUTS,'traces':traces}
        results.append(row);save(evaluation/(record['id']+'.json'),row)
        print(record['id'],counts,flush=True)
    labels=list(results[0]['counts']);summary={}
    for label in labels:
        ratios=[r['counts']['O3']/r['counts'][label] for r in results]
        by_family={family:[r for r in results if r['family']==family] for family in test_families}
        family_ratios=[math.exp(sum(math.log(r['counts']['O3']/r['counts'][label]) for r in group)/len(group)) for group in by_family.values()]
        summary[label]={'fewer':sum(r['counts'][label]<r['counts']['O3'] for r in results),
            'equal':sum(r['counts'][label]==r['counts']['O3'] for r in results),
            'more':sum(r['counts'][label]>r['counts']['O3'] for r in results),
            'geomean_O3_over_candidate':math.exp(sum(map(math.log,ratios))/len(ratios)),
            'family_balanced_geomean_O3_over_candidate':math.exp(sum(map(math.log,family_ratios))/len(family_ratios))}
    report={'schema':1,'objective':'instruction_count','runtime_evaluated':False,'frozen':frozen,
            'programs':len(results),'independent_families':len(test_families),'results':results,'summary':summary,
            'all_output_checks_passed':all(all(r['native_checks'].values()) for r in results),
            'scope':'Single frozen evaluation on authored synthetic unseen families. Variants are correlated. No real-world or runtime generalization claim. Guard gains are not evidence of an RL advantage over fixed/random/Oz.'}
    save(evaluation/'report.json',report)
    print(json.dumps(summary,indent=2),flush=True)

if __name__=='__main__':main()
