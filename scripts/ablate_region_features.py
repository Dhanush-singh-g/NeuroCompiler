"""Declared diagnostic: whole-entry versus timed-region features, same labels.

This report cannot alter the primary model menu, frozen selection or holdouts.
All comparisons reuse the current study's qualified timings, never older ones.
"""
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.benchmarks.region import ROOT,NAME,MENU,TOOLS,tool,verify,check_declaration,input_features,save,sha
from src.features.transform import parse_ir,candidate_vector
from src.supervised.region import program_cv


def main():
    output=ROOT/'results/region_feature_ablation.json'
    if output.exists():raise ValueError('Existing ablation')
    declaration=check_declaration();source=ROOT/f'results/{NAME}_train.json'
    raw=json.loads(source.read_text());labels,_=verify(raw)
    if not raw['complete']:raise ValueError('Incomplete training')
    manifests=copy.deepcopy(raw['manifests']);whole_labels=copy.deepcopy(labels);cache={}
    for case,m in manifests.items():
        program=m['program']
        if program not in cache:
            ir={c:parse_ir(tool([TOOLS/'llvm-dis',m['artifacts'][c]['bc'],'-o','-']).decode()) for c in MENU}
            size=Path(m['artifacts']['O3']['so']).stat().st_size
            cache[program]={c:candidate_vector(ir['O3'],ir[c],c,0,1,
                (Path(m['artifacts'][c]['so']).stat().st_size-size)/size,entrypoint='nc_benchmark_main')[:-3]
                +[float(c==other) for other in list(MENU)[1:]] for c in list(MENU)[1:]}
        m['features']={c:v+input_features(Path(m['input']).read_bytes()) for c,v in cache[program].items()}
    for label in whole_labels:label['features']=manifests[label['case']]['features']
    studies={}
    for name,points,features in [('timed',labels,raw['manifests']),('whole_entry',whole_labels,manifests)]:
        experiments=[]
        for parameters in declaration['parameters']:
            experiments.append({'parameters':parameters,**program_cv(points,features,*parameters)})
        studies[name]={'feature_count':len(next(iter(features.values()))['features']['O2']),
                       'experiments':experiments,'selection_changed':False}
    save(output,{'training_sha256':sha(source),'declaration_sha256':sha(ROOT/'results/region_declaration.json'),
                 'scope':'identical current qualified targets and folds; diagnostic only; no old labels or holdout outcomes',
                 'studies':studies})
    print(json.dumps({name:{'features':s['feature_count'],'fully_scorable':sum(e['eligible'] for e in s['experiments']),
        'passes_primary_gates':sum(e['eligible'] and e['score']['utility']>0 and e['score']['worst_original_program']>=.97
                                  and e['score']['confirmed_workloads']>=1 for e in s['experiments'])}
                     for name,s in studies.items()},indent=2))


if __name__=='__main__':main()
