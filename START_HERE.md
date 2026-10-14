# Start the NeuroCompiler dashboard

The dashboard is a local application for exploring recorded compiler research
results. It runs on Windows, macOS or Linux with **Python 3.10 or newer**. You
do not need LLVM, CompilerGym, Node.js, a virtual environment, or pip packages
to view it. It does not compile code or launch timing experiments.

## 1. Install Python and download the project

Install Python from https://www.python.org/downloads/. On Windows, enable
**Add Python to PATH** if the installer offers it. Open PowerShell or Command
Prompt and check:

```powershell
python --version
```

If Windows does not recognize `python`, try `py -3 --version`. On macOS/Linux,
use `python3 --version`. Confirm that the version is 3.10 or newer.

With Git installed, download the project:

```bash
git clone https://github.com/Dhanush-singh-g/NeuroCompiler.git
cd NeuroCompiler
```

Alternatively, open the GitHub repository, select **Code → Download ZIP**,
extract it, and open a terminal inside the extracted `NeuroCompiler-main`
folder. That folder should contain README.md, dashboard/ and scripts/.

## 2. Start the application

From the project folder, run:

```powershell
python scripts/serve_dashboard.py --port 8000
```

On Windows, if needed, use:

```powershell
py -3 scripts/serve_dashboard.py --port 8000
```

On macOS/Linux, use:

```bash
python3 scripts/serve_dashboard.py --port 8000
```

Wait for `Dashboard listening on 127.0.0.1:8000`. Keep this terminal open.

## 3. Open it in your browser

On **the same computer**, type this into the browser's address bar:

```text
http://127.0.0.1:8000
```

You should see **Optimization, with evidence.** The recorded dashboard includes:

- **Overview:** corpus coverage, baseline stability, study stages and the
  explicitly training-only BLAKE2 result.
- **Benchmarks:** search programs/inputs, choose a compiler setting and inspect
  recorded correctness. Two untouched development programs remain reserved.
- **Measurement quality:** CPU/wall controls for five logical CPUs. Select a
  matrix cell to inspect intervals, blocks and failure reasons.
- **Evidence and sources:** use the information button to see source hashes
  and download reports. The down-arrow button exports the dashboard JSON.

Close the application with **Ctrl+C** in the server terminal. Start it again
with the same command whenever you want to view it.

## Common problems

| Message or symptom | What to do |
| --- | --- |
| `python` is not recognized | Use `py -3` on Windows, or install Python and reopen the terminal. |
| `can't open file ...serve_dashboard.py` | Change to the extracted/cloned project folder first. |
| `Address already in use` / port error | Run with `--port 8001`, then enter `http://127.0.0.1:8001` in the browser. |
| Browser cannot connect | Confirm the server terminal is still running and that the address uses the same port. |
| Directly opening index.html does not work | Use the Python server; managed browsers can block local file URLs. |
| Evidence is unavailable after rebuilding data | Restore the release's raw records, or use `git restore dashboard/data.json dashboard/results.js` to recover the committed snapshot, then reload. |

**Do not run `build_dashboard.py` as part of ordinary startup.** A complete
recorded snapshot is already included in the repository.

## Optional: restore the full research workspace

Code, tests, reports, model bundles and the frontend are in Git. Large datasets,
native binaries, raw timing records, logs and original experimental snapshots
are preserved in the **project-snapshot-2026-10-14** GitHub release:

https://github.com/Dhanush-singh-g/NeuroCompiler/releases/tag/project-snapshot-2026-10-14

These large downloads are unnecessary for viewing the dashboard. For research,
download `neurocompiler-research-workspace-20261014.tar.gz` and its accompanying
manifest and SHA256 file. The archive retains the generated data/, models/ and
results/ trees, including the original nested snapshots; it omits virtual
environments and Python caches.
Internal upstream documentation symlinks are materialized as regular files,
with their original targets retained in the manifest for portability.

Restore it into this checkout with:

```bash
python scripts/restore_research_workspace.py path/to/neurocompiler-research-workspace-20261014.tar.gz --manifest path/to/research-workspace-manifest.json --sha256-file path/to/research-workspace.sha256
```

The helper verifies the archive hash, paths and per-file checksums. It refuses
to overwrite different existing files, and skips files that are already
identical. It never unpickles models or executes native artifacts. Allow disk
space for the downloaded archive plus approximately 3 GB of extracted files.
Only after restoration can you regenerate the displayed snapshot with:

```bash
python scripts/build_dashboard.py
```

To run compiler experiments, follow the separately documented Linux/LLVM19
portable runner and the frozen admission protocol in EXPANDED_SL.md. Existing
Intel-native artifacts are not portable executables for other CPU architectures.
The complete compiler environment is a separate setup from dashboard viewing.

The current study remains inconclusive about learned improvement over `-O3`.
Viewing or publishing the frontend does not change that result.
