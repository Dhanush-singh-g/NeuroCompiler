"""Export a verified registered workload with O3 as the default."""
import argparse
import json
import shutil
import sys
from pathlib import Path

import joblib

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import study_persistent as study
from src.benchmarks.compact import save, sha


def main():
    p = argparse.ArgumentParser(); p.add_argument('--case', required=True)
    p.add_argument('--split', choices=['train', 'development'], default='development')
    p.add_argument('--output', required=True, type=Path); p.add_argument('--experimental', action='store_true'); args = p.parse_args()
    raw = json.loads(study.path(args.split).read_text()); study.verify(raw)
    if not raw['complete']:
        raise ValueError('Incomplete study')
    selection = json.loads(study.path('selection').read_text()); model = study.ROOT / f'models/sl_{study.NAME}_bundle.joblib'
    if sha(model) != selection['model_sha256'] or sha(study.path('train')) != selection['training_sha256']:
        raise ValueError('Frozen selection changed')
    bundle = joblib.load(model); m = raw['manifests'][args.case]; decision = {'choice': 'O3', 'scores': {}}
    if args.experimental:
        if not bundle['cv_certified'] or bundle['experimental'] is None:
            raise ValueError('No CV-qualified experimental model')
        decision = bundle['experimental'].choose(m)
    out = args.output.resolve(); out.mkdir(parents=True, exist_ok=False)
    artifact = m['artifacts'][decision['choice']]
    for source, name in [(artifact['bc'], 'program.bc'), (artifact['so'], 'candidate.so'),
                         (m['worker'], 'isolated_library_worker.out'), (m['input'], 'input.dat')]:
        shutil.copy2(source, out / name)
    save(out / 'manifest.json', {'case': args.case, 'program': m['program'], 'decision': decision,
         'default': 'O3', 'experimental': args.experimental, 'cv_certified': bundle['cv_certified'], 'static_only': True,
         'expected': m['expected'], 'model_sha256': sha(model), 'training_sha256': sha(study.path('train')),
         'selection_sha256': sha(study.path('selection')), 'declaration_sha256': sha(study.DECLARATION),
         'files_sha256': {name: sha(out / name) for name in ['program.bc', 'candidate.so', 'isolated_library_worker.out', 'input.dat']},
         'scope': 'registered warm native library API and frozen input on compatible Intel CPU; no fresh final-test certification'})
    print('Exported', args.case, decision['choice'])


if __name__ == '__main__': main()
