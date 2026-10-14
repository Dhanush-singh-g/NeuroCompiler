"""Pooled SL over candidate-specific static transformations, grouped by program."""
import math

import numpy as np
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.linear_model import Ridge

from src.benchmarks.compact import MENU
from src.features.transform import FEATURE_NAMES
from src.supervised.compact import grouped_score

CHOICES=list(MENU)[1:]
MODES=["ridge1","ridge10","trees"]


def vectors(rows):
    x=np.asarray([r["vector"] for r in rows],dtype=float)
    if x.shape!=(len(rows),len(FEATURE_NAMES)) or not np.isfinite(x).all():
        raise ValueError("Invalid static transformation vector")
    return x


class CandidateRegressor:
    def __init__(self,mode):self.mode=mode

    def fit(self,rows):
        self.programs=sorted({r["program"] for r in rows})
        if not self.programs:raise ValueError("No training programs")
        x=vectors(rows)
        y=np.clip([r["target"] for r in rows],np.log(.5),np.log(2))
        counts={p:sum(r["program"]==p for r in rows) for p in self.programs}
        weights=np.asarray([1/counts[r["program"]] for r in rows])
        self.center=np.average(x,axis=0,weights=weights)
        self.scale=np.sqrt(np.average((x-self.center)**2,axis=0,weights=weights))
        self.scale[self.scale<1e-8]=1.
        if self.mode.startswith("ridge"):
            self.model=Ridge(alpha=float(self.mode[5:]))
        elif self.mode=="trees":
            self.model=ExtraTreesRegressor(n_estimators=96,max_depth=4,min_samples_leaf=3,
                max_features=.7,random_state=20261011,n_jobs=1)
        else:raise ValueError("Unknown regressor")
        self.model.fit((x-self.center)/self.scale,y,sample_weight=weights)
        return self

    def predict(self,rows):
        return np.asarray(self.model.predict((vectors(rows)-self.center)/self.scale))


class TransformSelector:
    def __init__(self,mode="O3",guarded=False,floor=.03):
        self.mode,self.guarded,self.floor=mode,guarded,floor

    def fit(self,rows):
        self.programs=sorted({r["program"] for r in rows})
        self.margin=0.;self.calibration=[]
        if self.mode=="O3":return self
        if len(self.programs)<4:raise ValueError("At least four training programs")
        if self.guarded:
            errors=[]
            for held in self.programs:
                fit=[r for r in rows if r["program"]!=held]
                test=[r for r in rows if r["program"]==held]
                m=CandidateRegressor(self.mode).fit(fit)
                errors.append(float(np.max(m.predict(test)-np.asarray([r["target"] for r in test]))))
                self.calibration.append({"held":held,"fit":m.programs})
            self.margin=max(0.,float(np.quantile(errors,.8)))
        self.regressor=CandidateRegressor(self.mode).fit(rows)
        return self

    def choose(self,static):
        rows=[{"vector":static["features"][c]} for c in CHOICES]
        vectors(rows)
        if self.mode=="O3":return {"configuration":"O3","scores":{},"margin":0.}
        values=self.regressor.predict(rows)
        scores={c:float(v) if static["aliases"][c]!="O3" else 0. for c,v in zip(CHOICES,values)}
        best=max(CHOICES,key=lambda c:scores[c])
        choice=best if scores[best]-self.margin>math.log1p(getattr(self,"floor",.03)) else "O3"
        return {"configuration":choice,"scores":scores,"margin":self.margin}


def join_labels(raw,static):
    rows=[]
    for label in raw["labels"]:
        s=static[label["case"]]
        if s["program"]!=label["program"]:raise ValueError("Feature program mismatch")
        for choice in CHOICES:
            rows.append({"case":label["case"],"program":label["program"],"choice":choice,
                "vector":s["features"][choice],"target":label["outcomes"][choice]["log_speedup"],
                "confirmed_gain":label["outcomes"][choice]["confirmed_gain"],"static":s})
    vectors(rows)
    return rows


def cross_validate(rows,floors=(.03,)):
    programs=sorted({r["program"] for r in rows});results={}
    if len(programs)<5:return results
    for mode in MODES:
        for guarded in (False,True):
            key=("guarded_" if guarded else "raw_")+mode
            records={floor:[] for floor in floors};folds=[]
            for held in programs:
                fit=[r for r in rows if r["program"]!=held]
                test=[r for r in rows if r["program"]==held]
                model=TransformSelector(mode,guarded).fit(fit)
                folds.append({"held":held,"fit":model.programs,"calibration":model.calibration})
                for case in sorted({r["case"] for r in test}):
                    candidates=[r for r in test if r["case"]==case]
                    for floor in floors:
                        model.floor=floor
                        decision=model.choose(candidates[0]["static"])
                        choice=decision["configuration"]
                        chosen=next((r for r in candidates if r["choice"]==choice),None)
                        records[floor].append({"program":held,"case":case,"decision":decision,
                            "log_speedup":chosen["target"] if chosen else 0.,
                            "confirmed_gain":chosen["confirmed_gain"] if chosen else False})
            for floor,replay in records.items():
                name=key if len(floors)==1 else f"{key}_floor{floor:g}"
                results[name]={"score":grouped_score(replay),"records":replay,"folds":folds,
                    "mode":mode,"guarded":guarded,"floor":floor,
                    "changes":sum(r["decision"]["configuration"]!="O3" for r in replay),
                    "confirmed_programs":len({r["program"] for r in replay if r["confirmed_gain"]})}
    return results


def select_policies(cv):
    # This new experiment permits raw or guarded predictors only when the same
    # held-program performance gates pass, with gains on >=2 original programs.
    eligible=[k for k,v in cv.items() if v["score"]["geomean"]>1.01
        and v["score"]["interval"][0]>1 and v["score"]["worst_program"]>=1/1.03
        and v["confirmed_programs"]>=2]
    selected=max(eligible,key=lambda k:cv[k]["score"]["geomean"]) if eligible else "O3"
    exploratory=max(cv,key=lambda k:cv[k]["score"]["geomean"]) if cv else "O3"
    return selected,exploratory
