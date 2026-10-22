"""Portable inference for the frozen experimental Ridge model; no pickle loads."""
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from src.benchmarks.compact import MENU
from src.features.transform import FEATURE_NAMES, candidate_vector, parse_ir, summaries, METRICS
from src.presentation.summary import decision_diagnostics

ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = ROOT / 'presentation/model.json'


def load_model():
    contents = MODEL_PATH.read_bytes()
    model = json.loads(contents)
    model['_artifact_sha256'] = hashlib.sha256(contents).hexdigest()
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
    if any(not math.isfinite(model[k]) or model[k] < 0 for k in ('margin', 'floor')):
        raise ValueError('Invalid model decision threshold')
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
        if not math.isfinite(raw) or not np.isfinite(contributions).all():
            raise ValueError('Model score is not finite; input is outside the supported numerical range.')
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
    diagnostics = decision_diagnostics(scores, aliases, choice)
    notes = []
    if choice != 'O3' and scores[choice] < math.log1p(.03):
        notes.append('The predicted effect is below 3%, the demo\'s gain threshold. This is a small model estimate, not a confident improvement.')
    if choice != 'O3' and explanations[choice]['outside_training_scale_fields']:
        notes.append('Some input features exceed the training feature scale. The model is extrapolating; prediction reliability is unvalidated.')
    diagnostics['recommendation_notes'] = notes
    metrics = {}
    for name, functions in parsed.items():
        totals, indirect = summaries(functions)
        metrics[name] = {**dict(zip(METRICS, map(int, totals[0]))),
                         'functions': len(functions), 'indirect_reachability': bool(indirect)}
    return {
        'choice': choice, 'approved_choice': 'O3', 'policy': model['policy'],
        'deployment_qualified': False, 'scores': scores, 'explanations': explanations,
        'aliases': aliases, 'feature_count': len(FEATURE_NAMES), 'vectors': vectors,
        'metrics': metrics, 'model_sha256': model['_artifact_sha256'],
        'model_source_sha256': model['source_model_sha256'],
        'diagnostics': diagnostics, 'reason': diagnostics['explanation'],
        'scope': 'Static prediction made before native execution; no live timing informs this decision.',
    }
