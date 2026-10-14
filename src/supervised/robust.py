"""Uncertainty-aware candidate learning, scored on held-out real programs."""
import math

import numpy as np
from sklearn.linear_model import Ridge

from src.supervised.compact import grouped_score
from src.supervised.transform import CHOICES, TransformSelector, vectors

VARIANTS = ['point', 'lower', 'lower_risk']


def is_real(program):
    return program.startswith(('benchmark://', 'real://'))


def uncertainty_rows(raw,static,case_prefix=''):
    from src.supervised.transform import join_labels
    if not raw['labels']:return []
    rows=join_labels(raw,static)
    labels={r['case']:r for r in raw['labels']}
    for r in rows:
        outcome=labels[r['case']]['outcomes'][r['choice']]
        r['lower_target']=math.log(outcome['interval'][0]) if 'interval' in outcome else r['target']
        if not np.isfinite(r['lower_target']) or r['lower_target']>r['target']+1e-12:
            raise ValueError('Invalid candidate uncertainty bound')
        r['case']=case_prefix+r['case']
    return rows


class RiskRegressor:
    def __init__(self,variant='lower_risk',alpha=10.):
        if variant not in VARIANTS or alpha<=0:raise ValueError('Unknown risk regressor')
        self.variant,self.alpha=variant,alpha

    def fit(self,rows):
        self.programs=sorted({r['program'] for r in rows})
        if not rows:raise ValueError('Empty training data')
        x=vectors(rows)
        y=np.asarray([r['target'] if self.variant=='point' else r['lower_target'] for r in rows])
        if not np.isfinite(y).all():raise ValueError('Invalid runtime target')
        self.training_targets=y.tolist()
        factors=np.asarray([2. if self.variant=='lower_risk' and r['target']<0 else 1. for r in rows])
        totals={p:float(sum(w for r,w in zip(rows,factors) if r['program']==p)) for p in self.programs}
        weights=np.asarray([w/totals[r['program']] for r,w in zip(rows,factors)])
        self.training_weights=weights.tolist()
        self.center=np.average(x,axis=0,weights=weights)
        self.scale=np.sqrt(np.average((x-self.center)**2,axis=0,weights=weights));self.scale[self.scale<1e-8]=1.
        self.model=Ridge(alpha=self.alpha).fit((x-self.center)/self.scale,np.clip(y,np.log(.5),np.log(2)),sample_weight=weights)
        return self

    def predict(self,rows):
        return np.asarray(self.model.predict((vectors(rows)-self.center)/self.scale))


class RobustSelector(TransformSelector):
    def __init__(self,variant='lower_risk',alpha=10.,floor=.01):
        super().__init__('ridge'+str(alpha),False,floor)
        self.variant,self.alpha=variant,alpha

    def fit(self,rows):
        self.programs=sorted({r['program'] for r in rows});self.margin=0.;self.calibration=[]
        if len(self.programs)<4:raise ValueError('At least four training programs required')
        self.regressor=RiskRegressor(self.variant,self.alpha).fit(rows)
        return self


def real_cross_validate(rows):
    """Original real programs are the held-out units; synthetic inputs never score."""
    programs=sorted({r['program'] for r in rows if is_real(r['program'])})
    if len(programs)<5:raise ValueError('Insufficient real program coverage')
    results={}
    for domain in ['real_only','with_kernels']:
        available=[r for r in rows if domain=='with_kernels' or is_real(r['program'])]
        for variant in VARIANTS:
            for alpha in [1.,10.]:
                replay={0.:[],.01:[]};folds=[]
                for held in programs:
                    fit=[r for r in available if r['program']!=held];test=[r for r in available if r['program']==held]
                    model=RobustSelector(variant,alpha).fit(fit);folds.append({'held':held,'fit':model.programs})
                    for case in sorted({r['case'] for r in test}):
                        candidates=[r for r in test if r['case']==case]
                        for floor in replay:
                            model.floor=floor;decision=model.choose(candidates[0]['static'])
                            chosen=next((r for r in candidates if r['choice']==decision['configuration']),None)
                            replay[floor].append({'case':case,'program':held,'decision':decision,
                                'log_speedup':chosen['target'] if chosen else 0.,
                                'lower_log_speedup':chosen['lower_target'] if chosen else 0.,
                                'confirmed_gain':chosen['confirmed_gain'] if chosen else False})
                for floor,records in replay.items():
                    key=f'{domain}_{variant}_ridge{alpha:g}_floor{floor:g}'
                    groups=[float(np.mean([r['log_speedup'] for r in records if r['program']==p])) for p in programs]
                    utility=float(np.mean(groups)-2*np.mean(np.maximum(-np.asarray(groups),0)))
                    results[key]={'domain':domain,'variant':variant,'alpha':alpha,'floor':floor,
                        'score':grouped_score(records),'utility_log':utility,'records':records,'folds':folds,
                        'changes':sum(r['decision']['configuration']!='O3' for r in records),
                        'worst_input':math.exp(min(r['log_speedup'] for r in records)),
                        'confirmed_programs':len({r['program'] for r in records if r['confirmed_gain']})}
    return results


def select_robust(cv):
    eligible=[k for k,v in cv.items() if v['score']['geomean']>1.01 and v['score']['interval'][0]>1
        and v['score']['worst_program']>=1/1.03 and v['worst_input']>=1/1.01 and v['confirmed_programs']>=2]
    selected=max(eligible,key=lambda k:cv[k]['utility_log']) if eligible else 'O3'
    positive=[k for k,v in cv.items() if v['utility_log']>0]
    experimental=max(positive,key=lambda k:cv[k]['utility_log']) if positive else 'O3'
    return selected,experimental
