"""Portable inference for the frozen experimental Ridge model; no pickle loads."""
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from src.benchmarks.compact import MENU
from src.features.transform import FEATURE_NAMES, candidate_vector, parse_ir, summaries, METRICS

ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = ROOT / 'presentation/model.json'


def load_model():
    model = json.loads(MODEL_PATH.read_text())
    if (model['schema'] != 1 or model['toolchain_major'] != 10
            or model['menu'] != MENU or model['feature_names'] != FEATURE_NAMES
            or model['deployment_qualified'] is not False or model['approved_policy'] != 'O3'):
        raise ValueError('Presentation model contract mismatch')
    n = len(FEATURE_NAMES)
    for key in ('center', 'scale', 'coefficients'):
        a = np.asarray(model[key], dtype=float)
        if a.shape != (n,) or not np.isfinite(a).all():
            raise ValueError('Invalid model parameters')
    if min(model['scale']) <= 0 or not math.isfinite(model['intercept']):
        raise ValueError('Invalid model scale/intercept')
    return model


def predict(irs, sizes, aliases, input_bytes, iterations):
    model = load_model()
    parsed = {choice: parse_ir(text) for choice, text in irs.items()}
    base = parsed['O3']
    scores, explanations, vectors = {'O3': 0.}, {}, {}
    for choice in list(MENU)[1:]:
        vector = candidate_vector(base, parsed[choice], choice, input_bytes, iterations,
                                  (sizes[choice] - sizes['O3']) / sizes['O3'])
        vectors[choice] = vector
        standardized = (np.asarray(vector) - model['center']) / model['scale']
        contributions = standardized * model['coefficients']
        raw = float(model['intercept'] + contributions.sum())
        scores[choice] = raw if aliases[choice] != 'O3' else 0.
        indices = sorted(range(len(vector)), key=lambda i: abs(contributions[i]), reverse=True)[:6]
        explanations[choice] = {
            'intercept': model['intercept'], 'raw_score': raw,
            'top_contributions': [{'feature': FEATURE_NAMES[i], 'contribution': float(contributions[i]),
                                   'value': vector[i]} for i in indices],
            'outside_training_scale_fields': int(np.sum(np.abs(standardized) > 6)),
            'scope': 'Linear model attribution; not a causal explanation of runtime.',
        }
    # Preserve the original selector's menu ordering and tie behavior exactly.
    best = max(list(MENU)[1:], key=lambda choice: scores[choice])
    choice = best if scores[best] - model['margin'] > math.log1p(model['floor']) else 'O3'
    metrics = {}
    for name, functions in parsed.items():
        totals, indirect = summaries(functions)
        metrics[name] = {**dict(zip(METRICS, map(int, totals[0]))),
                         'functions': len(functions), 'indirect_reachability': bool(indirect)}
    return {
        'choice': choice, 'approved_choice': 'O3', 'policy': model['policy'],
        'deployment_qualified': False, 'scores': scores, 'explanations': explanations,
        'aliases': aliases, 'feature_count': len(FEATURE_NAMES), 'vectors': vectors,
        'metrics': metrics, 'model_sha256': hashlib.sha256(MODEL_PATH.read_bytes()).hexdigest(),
        'model_source_sha256': model['source_model_sha256'],
        'reason': ('No distinct alternative exceeds the experimental decision threshold.'
                   if choice == 'O3' else 'Highest experimental predicted score above its decision threshold.'),
        'scope': 'Static prediction made before native execution; no live timing informs this decision.',
    }
