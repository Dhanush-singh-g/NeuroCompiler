"""Program-grouped configuration prediction with training-only abstention."""
import math

import numpy as np
from sklearn.linear_model import Ridge

from src.benchmarks.compact import MENU

CHOICES = list(MENU)[1:]


def program_weights(rows):
    counts = {p: sum(r["program"] == p for r in rows) for p in {r["program"] for r in rows}}
    return np.asarray([1 / counts[r["program"]] for r in rows])


def features(values):
    x = np.asarray(values, dtype=float)
    if x.shape[-1] != 58 or not np.isfinite(x).all() or (x < 0).any():
        raise ValueError("Expected 58 finite nonnegative static features")
    return np.log1p(x)


class Regressor:
    def __init__(self, mode="ridge"):
        if mode not in ("ridge", "constant"):
            raise ValueError("Unknown model")
        self.mode = mode

    def fit(self, rows):
        if not rows:
            raise ValueError("Empty training set")
        self.programs = sorted({r["program"] for r in rows})
        x = features([r["features"] for r in rows])
        weights = program_weights(rows)
        self.center = np.average(x, axis=0, weights=weights)
        self.scale = np.sqrt(np.average((x - self.center) ** 2, axis=0, weights=weights))
        self.scale[self.scale < 1e-8] = 1.
        self.models = {}
        for choice in CHOICES:
            y = np.clip([r["outcomes"][choice]["log_speedup"] for r in rows], np.log(.5), np.log(2))
            if self.mode == "constant":
                # Equal weight to original programs, including their multiple inputs.
                self.models[choice] = float(np.median([
                    np.mean([v for r, v in zip(rows, y) if r["program"] == p]) for p in self.programs]))
            else:
                self.models[choice] = Ridge(alpha=10).fit((x - self.center) / self.scale,
                                                         y, sample_weight=weights)
        return self

    def scores(self, values):
        x = (features(values).reshape(1, -1) - self.center) / self.scale
        return {c: float(m) if self.mode == "constant" else float(m.predict(x)[0])
                for c, m in self.models.items()}


class Selector:
    def __init__(self, mode="O3", guarded=True):
        self.mode = mode
        self.guarded = guarded

    def fit(self, rows):
        self.programs = sorted({r["program"] for r in rows})
        self.margin = {c: 0. for c in CHOICES}
        self.calibration = []
        if self.mode == "O3":
            return self
        if len(self.programs) < 4:
            raise ValueError("At least four original programs are required")
        if self.guarded:
            errors = {c: [] for c in CHOICES}
            for held in self.programs:
                fit_rows = [r for r in rows if r["program"] != held]
                regressor = Regressor(self.mode).fit(fit_rows)
                held_rows = [r for r in rows if r["program"] == held]
                self.calibration.append({"held": held, "fit": regressor.programs})
                for c in CHOICES:
                    errors[c].append(float(np.mean([
                        regressor.scores(r["features"])[c] - r["outcomes"][c]["log_speedup"]
                        for r in held_rows])))
            self.margin = {c: max(0., float(np.quantile(v, .8))) for c, v in errors.items()}
        self.regressor = Regressor(self.mode).fit(rows)
        return self

    def choose(self, values):
        features(values)  # Validate input even for the explicit O3 policy.
        if self.mode == "O3":
            return {"configuration": "O3", "scores": {}, "margins": {}, "policy": "O3"}
        scores = self.regressor.scores(values)
        adjusted = {c: s - self.margin[c] for c, s in scores.items()}
        best = max(CHOICES, key=lambda c: adjusted[c])
        choice = best if adjusted[best] > math.log1p(.03) else "O3"
        return {"configuration": choice, "scores": scores, "margins": self.margin,
                "policy": ("guarded_" if self.guarded else "raw_") + self.mode}


def grouped_score(records):
    groups = sorted({r["program"] for r in records})
    if not groups:
        return {"programs": 0, "geomean": None, "interval": None, "worst_program": None}
    values = np.asarray([np.mean([r["log_speedup"] for r in records if r["program"] == p]) for p in groups])
    rng = np.random.default_rng(20261010)
    boot = np.mean(values[rng.integers(len(groups), size=(2000, len(groups)))], axis=1)
    return {"programs": len(groups), "geomean": float(np.exp(np.mean(values))),
            "interval": np.exp(np.quantile(boot, [.025, .975])).tolist(),
            "worst_program": float(np.exp(np.min(values))),
            "interval_scope": "program resampling of timing point estimates; conditional on prior menu selection"}


def cross_validate(rows):
    results = {}
    groups = sorted({r["program"] for r in rows})
    if len(groups) < 5:
        return results
    for mode, guarded in [("ridge", False), ("constant", False), ("ridge", True), ("constant", True)]:
        key = ("guarded_" if guarded else "raw_") + mode
        records, folds = [], []
        for held in groups:
            fit_rows = [r for r in rows if r["program"] != held]
            model = Selector(mode, guarded).fit(fit_rows)
            folds.append({"held": held, "fit": model.programs, "calibration": model.calibration})
            for row in (r for r in rows if r["program"] == held):
                decision = model.choose(row["features"])
                choice = decision["configuration"]
                records.append({"program": held, "case": row["case"], "decision": decision,
                                "log_speedup": row["outcomes"][choice]["log_speedup"]})
        results[key] = {"score": grouped_score(records), "records": records, "folds": folds,
                        "changes": sum(r["decision"]["configuration"] != "O3" for r in records)}
    return results


def select_policy(cv):
    """Only predeclared guarded policies may replace the O3 comparator."""
    eligible = [name for name, value in cv.items() if name.startswith("guarded_")
                and value["score"]["geomean"] > 1.01 and value["score"]["interval"][0] > 1.
                and value["score"]["worst_program"] >= 1 / 1.03]
    return max(eligible, key=lambda name: cv[name]["score"]["geomean"]) if eligible else "O3"
