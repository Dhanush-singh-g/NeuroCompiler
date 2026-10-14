"""Independent SL for LLVM19 kernel latency, with whole-family validation."""
import math

import numpy as np
from sklearn.linear_model import Ridge

from src.benchmarks.polybench import MENU


def examples(programs, lower=False, choices=None):
    rows = []
    for p in programs:
        for choice in list(MENU)[1:] if choices is None else choices:
            if choice not in p['outcomes']:
                continue
            s = p["outcomes"][choice]
            rows.append({"program": p["case"], "family": p["family"], "choice": choice,
                         "vector": p["features"][choice],
                         "target": math.log(s["interval"][0]) if lower else s["log_speedup"]})
    return rows


class Selector:
    def __init__(self, alpha=10., lower=True, floor=.03, choices=None):
        self.alpha, self.lower, self.floor = alpha, lower, floor
        self.choices = list(MENU)[1:] if choices is None else list(choices)

    def fit(self, programs):
        if not programs:
            raise ValueError("No timing-qualified training programs")
        rows = examples(programs, self.lower, getattr(self,'choices',list(MENU)[1:]))
        x = np.asarray([r["vector"] for r in rows])
        self.mean = x.mean(axis=0)
        self.scale = x.std(axis=0)
        self.scale[self.scale < 1e-8] = 1
        y = np.clip([r["target"] for r in rows], np.log(.25), np.log(4.))
        # Every program contributes the same total weight; losses weigh twice.
        weights = np.where(np.asarray(y) < 0, 2., 1.)
        for ident in {r["program"] for r in rows}:
            indices = [i for i,r in enumerate(rows) if r["program"] == ident]
            weights[indices] /= weights[indices].sum()
        self.model = Ridge(alpha=self.alpha).fit((x-self.mean)/self.scale, y, sample_weight=weights)
        self.programs = sorted(p["case"] for p in programs)
        self.families = sorted({p["family"] for p in programs})
        return self

    def choose(self, manifest):
        choices = getattr(self,'choices',list(MENU)[1:])
        x = np.asarray([manifest["features"][c] for c in choices])
        predicted = self.model.predict((x-self.mean)/self.scale)
        scores = {c: (0. if manifest["aliases"][c] == "O3" else float(v))
                  for c,v in zip(choices,predicted)}
        best = max(scores, key=scores.get)
        return {"choice": best if scores[best] > math.log1p(self.floor) else "O3", "scores": scores}


def score(records):
    if not records:
        return None
    logs = np.asarray([r["log_speedup"] for r in records])
    rng = np.random.default_rng(20261022)
    boot = np.mean(logs[rng.integers(len(logs), size=(4000, len(logs)))], axis=1)
    return {"geometric_speedup": float(np.exp(logs.mean())),
            "program_bootstrap_interval": np.exp(np.quantile(boot,[.025,.975])).tolist(),
            "worst_program": float(np.exp(logs.min())),
            "changes": sum(r["choice"] != "O3" for r in records),
            "confirmed_programs": sum(r["confirmed_gain"] for r in records),
            "utility": float(logs.mean()+2*np.minimum(logs,0).mean())}


def family_cv(programs, manifests, alpha, lower, floor, choices=None):
    folds, records, unscorable = [], [], []
    families = sorted({p["family"] for p in programs})
    if len(families) < 2 or len(programs) < 5:
        return {"eligible": False, "folds": [], "records": [], "score": None}
    for held in families:
        train = [p for p in programs if p["family"] != held]
        test = [p for p in programs if p["family"] == held]
        selector = Selector(alpha, lower, floor, choices).fit(train)
        folds.append({"held_family": held, "train_programs": selector.programs,
                      "train_families": selector.families, "test_programs": [p["case"] for p in test]})
        for p in test:
            d = selector.choose(manifests[p["case"]])
            if d['choice'] not in p['outcomes']:
                unscorable.append({'program':p['case'],'family':held,**d,
                                   'reason':'predicted candidate lacks qualified timing'})
                continue
            s = p["outcomes"][d["choice"]]
            records.append({"program": p["case"], "family": held, **d,
                            "log_speedup": s["log_speedup"], "confirmed_gain": s["confirmed_gain"]})
    # Missing selected outcomes cannot be dropped to improve the CV score.
    return {"eligible": not unscorable, "folds": folds, "records": records,
            "unscorable":unscorable,"score":score(records) if not unscorable else None,
            "qualified_prediction_coverage":len(records)/len(programs)}
