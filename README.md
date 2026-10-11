# RACC artifact

Anonymous replay records for the paper "Ranking Is Not Retention". The package checks the numbers in Table 1, Table 2, Table 3, Figure 1, and Figure 3. It does not rerun the condenser.

## Layout

| Directory | Contents |
| --- | --- |
| `splits/` | Development, training, and held-out manifests, the message-level trajectory list, and the SWE-smith slice. |
| `edge_ledger/` | Strict deferred-use edges. |
| `replay_logs/` | One compression log per stream, policy, and budget, plus the sealed message-level ranking export. |
| `protocols/` | Frozen protocol and seal files, with paths anonymized and hashes recomputed. |
| `scripts/` | Aggregation scripts and `reproduce_tables.py`. |
| `models/` | TF-IDF checkpoint and the Qwen3-0.6B LoRA adapter. |
| `outputs/` | Comparison table produced by `reproduce_tables.py`. |

`DISCREPANCIES.md` records any recomputed value that disagrees with the printed paper cell, and the cells this package cannot recompute. `OMITTED_LARGE_FILES.md` lists large research-tree files that were not copied. `ANONYMIZATION_CHECK.txt` records the anonymization scan.

## Data

The streams are public SWE-rebench trajectories and the public task instances those trajectories were built on, including the SWE-bench-extra and SWE-smith slices named in the paper. This package redistributes neither trajectory text nor repository contents. It redistributes instance identifiers, repository names, and the derived replay records. Obtain the upstream releases from their publishers and follow the licenses shipped with those releases.

## Environment

Python 3.11 or newer, standard library only, for `scripts/reproduce_tables.py`. numpy, pandas, and scikit-learn are enough to load `models/tfidf_checkpoint.joblib`. They are not required to recompute the tables. No network connection is required.

```bash
python3 scripts/reproduce_tables.py
```

Run that command from this directory. The script prints each paper value, the recomputed value, and `MATCH`, `MISMATCH`, or `UNAVAILABLE`.

## Left out

Trajectory text, repository checkouts, held-out decision views, group text, score dumps, and the base weights of Qwen3-0.6B are not included. The base model is the public id `Qwen/Qwen3-0.6B`. Files of 20 MB or more that remain in the research tree are listed in `OMITTED_LARGE_FILES.md`. Logs that exist only on the research host, including the appendix capacity sweep, are listed in `SERVER_LOGS_NOT_COPIED.md`. Compact fields from those logs that the main tables use are already in `replay_logs/`.

The protocol and seal files under `protocols/` had machine paths replaced by `/data/` and their own hashes recomputed; see `protocols/README.md`.

Counts written by the builder: native train streams 25, native dev streams 13, held-out streams 299, message-level train trajectories 17728, message-level dev trajectories 3500, SWE-smith unique pairs 156.
