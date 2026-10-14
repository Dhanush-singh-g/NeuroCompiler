"""Distinct executable targets, original-program weighting and complete CV."""
import math

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor

from src.benchmarks.broad import MENU


def training_rows(programs,lower):
    rows=[]
    for p in programs:
        for c in list(MENU)[1:]:
            if p['aliases'][c]!=c or c not in p['outcomes']:continue
            s=p['outcomes'][c]
            rows.append({'program':p['program'],'case':p['case'],'choice':c,'vector':p['features'][c],
                         'target':math.log(s['interval'][0]) if lower else s['log_speedup']})
    return rows


class NativeSelector:
    def __init__(self,alpha=10.,lower=True,floor=.03,kind="ridge",depth=3):
        self.alpha,self.lower,self.floor=alpha,lower,floor
        self.kind,self.depth=kind,depth

    def fit(self,programs):
        rows=training_rows(programs,self.lower)
        if not rows:raise ValueError('No independent qualified candidate targets')
        x=np.asarray([r['vector'] for r in rows]);y=np.clip([r['target'] for r in rows],math.log(.25),math.log(4.))
        self.mean=x.mean(axis=0);self.scale=x.std(axis=0);self.scale[self.scale<1e-8]=1.
        weights=np.where(y<0,2.,1.)
        for program in {r['program'] for r in rows}:
            positions=[i for i,r in enumerate(rows) if r['program']==program]
            weights[positions]/=weights[positions].sum()
        if self.kind=='ridge':model=Ridge(alpha=self.alpha)
        elif self.kind=='forest':model=RandomForestRegressor(n_estimators=128,max_depth=self.depth,min_samples_leaf=4,random_state=20261102,n_jobs=1)
        else:raise ValueError('Unknown model family')
        self.model=model.fit((x-self.mean)/self.scale,y,sample_weight=weights)
        self.programs=sorted({r['program'] for r in rows});self.cases=sorted({r['case'] for r in rows})
        self.row_count=len(rows);self.program_weight_totals={p:float(sum(weights[i] for i,r in enumerate(rows) if r['program']==p)) for p in self.programs}
        return self

    def choose(self,m):
        canonical=[c for c in list(MENU)[1:] if m['aliases'][c]==c]
        scores={'O3':0.}
        if canonical:
            x=np.asarray([m['features'][c] for c in canonical])
            scores.update(zip(canonical,map(float,self.model.predict((x-self.mean)/self.scale))))
        scores={c:scores[m['aliases'][c]] for c in list(MENU)[1:]}
        best=max(scores,key=scores.get)
        return {'choice':best if scores[best]>math.log1p(self.floor) else 'O3','scores':scores}


def program_score(records):
    if not records:return None
    names=sorted({r['program'] for r in records})
    values=np.asarray([np.mean([r['log_speedup'] for r in records if r['program']==p]) for p in names])
    boot=values[np.random.default_rng(20261031).integers(len(values),size=(4000,len(values)))].mean(axis=1)
    return {'original_programs':len(names),'workloads':len(records),'geometric_speedup':float(np.exp(values.mean())),
            'program_bootstrap_interval':np.exp(np.quantile(boot,[.025,.975])).tolist(),
            'worst_original_program':float(np.exp(values.min())),
            'changed_workloads':sum(r['choice']!='O3' for r in records),
            'confirmed_workloads':sum(r['confirmed_gain'] for r in records),
            'utility':float(values.mean()+2*np.minimum(values,0).mean()),
            'scope':'program resampling only; omits timing uncertainty; input variants are not programs'}


def program_cv(labels,manifests,alpha,lower,floor,kind="ridge",depth=3):
    names=sorted({p['program'] for p in labels});rows=training_rows(labels,lower)
    effective=sorted({r['program'] for r in rows})
    if len(effective)<5:return {'eligible':False,'reason':'fewer than five original programs with distinct qualified targets',
                               'folds':[],'records':[],'score':None,'effective_training_programs':effective}
    folds=[];records=[];unscorable=[]
    for held in names:
        train=[p for p in labels if p['program']!=held];test=[p for p in labels if p['program']==held]
        selector=NativeSelector(alpha,lower,floor,kind,depth).fit(train)
        folds.append({'held_program':held,'train_programs':selector.programs,'train_cases':selector.cases,'test_cases':[p['case'] for p in test]})
        for p in test:
            d=selector.choose(manifests[p['case']]);c=d['choice']
            if c not in p['outcomes']:
                unscorable.append({'case':p['case'],'program':held,**d});continue
            s=p['outcomes'][c];records.append({'case':p['case'],'program':held,**d,'log_speedup':s['log_speedup'],'confirmed_gain':s['confirmed_gain']})
    return {'eligible':not unscorable,'folds':folds,'records':records,'unscorable':unscorable,
            'qualified_prediction_coverage':len(records)/len(labels),'score':program_score(records) if not unscorable else None}
