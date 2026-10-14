# NeuroCompiler results dashboard

A responsive, static dashboard of recorded experiment evidence. It offers a
study overview, searchable program/input explorer, compiler-setting correctness
records, CPU/wall control matrix, source hashes, report downloads and JSON export.
It does not compile user code, run native benchmarks or make model predictions.

From the repository root, use Python 3.10 or newer:

```bash
python scripts/serve_dashboard.py --port 8000
```

View the server on your own machine in a browser at port 8000. Stop it with
Ctrl+C. The server binds to loopback by default and serves only the dashboard
assets and three copied reports; it does not expose the repository or raw
benchmark files. No pip/npm installation, CompilerGym, LLVM, network access
or credentials are needed to view the dashboard.

The evidence snapshot is committed with the frontend. Do not run the build
command as an installation step on a fresh clone: raw research records are
distributed separately as release assets. See ../START_HERE.md for complete
startup and optional workspace-restoration instructions.

The HTML, CSS, JavaScript and bundled evidence are also a static site. Deploy
only the dashboard directory, keeping the assets and reports together. The
dashboard zip can be extracted on Windows, macOS or Linux and served with
`python -m http.server 8000 --directory dashboard` from its extracted parent.
Avoid serving the repository root with a generic file server. Publication to
an external host has not been performed.

The bundled `results.js` avoids browser data-fetch dependencies. Direct local
file opening is intended to work in ordinary browsers, but was not verified:
the managed Chromium policy here rejects file URLs. The HTTP workflow was
verified in Chromium at desktop and mobile viewport sizes, with no external
requests or browser JavaScript errors.

## Data and interpretation

`build_dashboard.py` reads these fixed, existing studies:

- Expanded 12 October corpus: 21 training implementations, 42 correctness
  inputs, 168 recorded checks, and two unexecuted development implementations.
- Expanded admission: 90 cells / 2,160 matched pairs across five logical CPUs.
  No target passed all six controls on both clocks. The chart displays
  identical-O3 stability ratios, not compiler speedups.
- Previous persistent-study selection: O3 default, no qualified learned
  selector. Its 11 qualified targets are not pooled into the expanded study.
- Previous BLAKE2 probe: approximately 12.1% less API CPU time on one
  preselected training input. It is excluded from fitting and does not
  establish learned generalization or whole-application improvement.

Exported missing or invalid evidence is shown as unavailable, never as zero
gain, a passing control or a fabricated example. Preflight and source pins
are checked against their frozen declaration hashes. Correctness displays
require both recorded pairs to match the independent expected output.
Recorded control decisions are checked against their recorded order, interval
and block summaries. This is a presentation check, not a replacement for the
full scientific audit or a recomputation of bootstrap statistics from traces.
Source hashes identify exact export inputs. Use the original study auditors
for full native artifact and experiment verification.

The export is a dated snapshot, not a live feed. After restoring the generated
workspace from the release, rebuild it intentionally with
`python scripts/build_dashboard.py` if evidence changes. The build command changes only dashboard exports/report
copies and leaves all experiment sources, declarations and raw results alone.
No new expanded model or performance score is displayed. Large-inline is shown
for correctness only; the expanded recommendation menu excludes it.

## Validation

```bash
python -m unittest tests.test_dashboard
```

Ten tests cover missing/invalid evidence, frozen-hash mismatches, order-bias
failures, false control decisions, nonfinite ratios, development separation,
incomplete/incorrect oracle comparisons, two-clock probe qualification,
script escaping/stale reports and the server's asset/path restrictions.

With optional Playwright and Chromium installed, start the server and run:

```bash
python scripts/check_dashboard_browser.py
```

That check covers navigation, search, compiler settings, empty results,
reserved development, both clocks, failure reasons, provenance, keyboard
dialog dismissal, real JSON downloads, mobile layout and missing snapshots.
Its current results and screenshots are under `results/dashboard_*`.

Earlier experimental snapshots remain unchanged; they do not include the
dashboard. No GitHub commit/push or public deployment was performed.
