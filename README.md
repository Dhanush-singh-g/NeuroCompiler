# Complete NeuroCompiler research workspace

This branch contains the complete generated data/models/results snapshot in 58 ordered archive parts (32 MiB maximum each), plus checksums and a per-file manifest. It is optional for dashboard viewing. Source code, model bundles and the recorded frontend are on main.

To view the dashboard, clone only main and follow START_HERE.md:
https://github.com/Dhanush-singh-g/NeuroCompiler/blob/main/START_HERE.md

To restore research files, clone this branch into a separate sibling folder and use the checksum-checking join and restore scripts from the main checkout. Full instructions are in START_HERE.md. The archive contains 6,529 files, 2,995,330,244 extracted bytes; the reconstructed gzip is 1,937,023,187 bytes. Every archive member was verified against its checksum before publication. No native artifacts or models are executed by restoration.

Original experiment ZIP snapshots, failed measurements, raw records, datasets, upstream archives/licenses and model bundles are retained. Git metadata, virtual environments and Python caches are omitted. Internal upstream file symlinks are materialized and their targets recorded.

These are frozen experimental results, not a demonstrated learned gain over -O3. The BLAKE2 result is training-only headroom.
