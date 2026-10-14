"""Restrict recommendations to the declared measured menu, group by program."""
import math

import numpy as np

from src.supervised.region import NativeSelector, program_score, training_rows
from src.benchmarks.expanded import ACTIVE, MENU


class Selector(NativeSelector):
    def choose(self, manifest):
        canonical = [c for c in ACTIVE[1:] if manifest['aliases'][c] == c]
        scores = {'O3': 0.}
        if canonical:
            x = np.asarray([manifest['features'][c] for c in canonical])
            scores.update(zip(canonical, map(float, self.model.predict((x-self.mean)/self.scale))))
        scores.update({c: scores[manifest['aliases'][c]] for c in ACTIVE[1:]})
        best = max(scores, key=scores.get)
        return {'choice': best if scores[best] > math.log1p(self.floor) else 'O3', 'scores': scores}


def cv(labels, manifests, *parameters):
    names = sorted({p['program'] for p in labels}); rows = training_rows(labels, parameters[1])
    effective = sorted({r['program'] for r in rows})
    if len(effective) < 5:
        return {'eligible': False, 'reason': 'fewer than five original programs with qualified targets',
                'folds': [], 'records': [], 'score': None, 'effective_training_programs': effective}
    folds = []; records = []; unscorable = []
    for held in names:
        train = [p for p in labels if p['program'] != held]; test = [p for p in labels if p['program'] == held]
        selector = Selector(*parameters).fit(train)
        folds.append({'held_program': held, 'train_programs': selector.programs, 'train_cases': selector.cases,
                      'test_cases': [p['case'] for p in test]})
        for p in test:
            decision = selector.choose(manifests[p['case']]); choice = decision['choice']
            if choice not in p['outcomes']:
                unscorable.append({'case': p['case'], 'program': held, **decision}); continue
            s = p['outcomes'][choice]
            records.append({'case': p['case'], 'program': held, **decision, 'log_speedup': s['log_speedup'], 'confirmed_gain': s['confirmed_gain']})
    return {'eligible': not unscorable, 'folds': folds, 'records': records, 'unscorable': unscorable,
            'qualified_prediction_coverage': len(records)/len(labels), 'score': program_score(records) if not unscorable else None}
