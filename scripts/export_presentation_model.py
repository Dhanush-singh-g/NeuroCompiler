"""Export the repository's trusted, frozen Ridge model to portable JSON.

Maintainer operation: needs the original sklearn environment and restored
selection report. The live app never unpickles a model or retrains on its inputs.
"""
import hashlib
import json
from pathlib import Path

import joblib

from src.features.transform import FEATURE_NAMES
from src.benchmarks.compact import MENU

ROOT = Path(__file__).resolve().parents[1]


def main():
    model_path = ROOT / 'models/sl_transform_policy_bundle.joblib'
    report_path = ROOT / 'results/transform_policy_selection.json'
    bundle = joblib.load(model_path)
    assert bundle['menu'] == MENU and bundle['feature_names'] == FEATURE_NAMES
    policy = bundle['experimental']
    selector = bundle['models'][policy]
    regressor = selector.regressor
    report = json.loads(report_path.read_text())
    data = {
        'schema': 1, 'name': 'NeuroCompiler / experimental transformation selector',
        'toolchain_major': 10, 'policy': policy, 'approved_policy': bundle['selected'],
        'deployment_qualified': False, 'feature_names': FEATURE_NAMES, 'menu': MENU,
        'center': regressor.center.tolist(), 'scale': regressor.scale.tolist(),
        'coefficients': regressor.model.coef_.tolist(),
        'intercept': float(regressor.model.intercept_),
        'margin': float(selector.margin), 'floor': float(getattr(selector, 'floor', .03)),
        'training_programs': selector.programs, 'training_rows': report['rows'],
        'real_training_programs': report['real_programs'],
        'synthetic_training_programs': report['synthetic_programs'],
        'historical_cv': report['cross_validation'][policy]['score'],
        'provenance': bundle['provenance'],
        'source_model': model_path.relative_to(ROOT).as_posix(),
        'source_model_sha256': hashlib.sha256(model_path.read_bytes()).hexdigest(),
        'selection_report_sha256': hashlib.sha256(report_path.read_bytes()).hexdigest(),
        'limitations': [
            'Earlier LLVM10 model; separate from the latest LLVM19 library study.',
            'Experimental model failed deployment gates. Approved policy remains O3.',
            'Training: seven real and six synthetic programs; 39 candidate targets.',
            'CV is conditional on prior menu selection and development-informed feature design.',
            'Scores are predicted log speedups, not calibrated probabilities or confidence.',
            'Live inputs are demonstrations, never untouched research holdouts or training labels.',
        ],
    }
    output = ROOT / 'presentation/model.json'
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')
    print(output)


if __name__ == '__main__':
    main()
