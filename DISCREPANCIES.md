# Discrepancies

Paper values are the printed cells in Table 1 (`tab:ranking`), Table 2 (`tab:heldout`), Table 3 (`tab:capacity`), Figure 1 and Figure 3. Recomputed values come from `replay_logs/`, `edge_ledger/` and the sealed message-level ranking export. No paper number was edited.

Matched: 115. Mismatched: 0. Not recomputed: 2.

## Mismatches

No recomputed value disagrees with the paper at the printed precision.

## Not recomputed

| Item | Paper | Why |
| --- | --- | --- |
| Table 1 Random R@1% | .205 | The paper calls this expected recall k/n. The sealed export has no such row. Its prevalence horizon_macro Recall@1% is a different quantity and is not substituted. |
| Table 1 Random R@5% | .225 | The paper calls this expected recall k/n. The sealed export has no such row. Its prevalence horizon_macro Recall@5% is a different quantity and is not substituted. |
