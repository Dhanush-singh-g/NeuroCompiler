"""Freeze splits, menu, parameters, sources and provenance before formal timings."""
import datetime
import shutil
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.benchmarks.region import *


def main():
    output=ROOT/'results/region_declaration.json'
    if output.exists():raise ValueError('Existing declaration')
    preflight=json.loads((ROOT/'results/region_preflight.json').read_text())
    if not preflight['complete'] or set(preflight['manifests'])!=set(CASES):raise ValueError('Incomplete preflight')
    parameters=[(a,l,f,'ridge',3) for a in [1.,10.] for l in [False,True] for f in [.01,.03]]
    parameters += [(10.,l,f,'forest',d) for d in [3,6] for l in [False,True] for f in [.01,.03]]
    sources=['src/benchmarks/region.py','src/features/timed_region.py','src/supervised/region.py',
             'src/benchmarks/broad.py','src/benchmarks/invocation.py','src/benchmarks/compact.py',
             'src/benchmarks/real.py','src/benchmarks/polybench.py','src/features/transform.py',
             'src/supervised/frozen.py','src/benchmarks/invocation_worker.c','src/benchmarks/isolated_library_worker.c',
             'scripts/collect_region.py','scripts/train_region.py','scripts/evaluate_region.py','scripts/optimize_region.py',
             'scripts/preflight_region.py','scripts/declare_region.py','scripts/ablate_region_features.py']
    hashes={name:sha(ROOT/name) for name in sources}
    for name in sources:
        dest=BASE/'declared_sources'/name;dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(ROOT/name,dest)
    save(output,{'declared_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
                 'protocol':PROTOCOL,'source_pins':pins(),'source_sha256':hashes,
                 'parameters':parameters,'training_cases':CASES,'development_cases':DEVELOPMENT,
                 'preflight_sha256':sha(ROOT/'results/region_preflight.json'),
                 'prior_artifact_sha256':sha(ROOT/'results/broad_iteration.zip'),
                 'development_rule':'no development build or execution before freezing model; measure predicted setting only plus O3 controls',
                 'prior_development_reuse':'Parson/picohttpparser are now training; their old outcomes are opened but not pooled',
                 'feature_ablation':'same 16 variants and current qualified labels; timed versus whole-entry features; diagnostic only, no selection feedback',
                 'research_basis':'Retained CompilerGym and benchmark-methodology papers motivate whole-program holdouts, repeated paired controls and reporting bias; no claimed ML speedup from those papers'})
    check_declaration();print('Frozen',len(PROGRAMS),'training implementations and',len(DEVELOPMENT),'fresh development workloads')


if __name__=='__main__':main()
