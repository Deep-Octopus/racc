# Scripts

`reproduce_tables.py` is the check that runs on this package. From the package root:

```bash
python3 scripts/reproduce_tables.py
```

It reads `replay_logs/` and `edge_ledger/`, writes `outputs/comparison.tsv`, and rewrites `DISCREPANCIES.md`. Python 3.11 or newer, standard library only. It does not need a network connection and it does not rerun a condenser.

`collect_numbers.py`, `trigger_analysis.py`, and `heldout_capacity_analysis.py` are the aggregation scripts from the paper repository. They read the research tree through `--root` (or a positional evidence directory). They import only the Python standard library. This package does not include group text, held-out decision views, or the raw trajectory rows those scripts open, so they are the definition of the aggregation rather than a second runner against the package.
