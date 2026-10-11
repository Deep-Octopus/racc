# Replay logs

One JSONL record per stream, policy, and budget. Summary text and model generations are omitted. `summary_survived` is the sealed boolean from the per-edge file. No development summary preserved a reused span in that field, and the trigger records do not contain the span text.

| File | Runs |
| --- | --- |
| `heldout_phase1.jsonl` | Age-only, Default-Recency, RACC-TFIDF, Oracle-Future, Age-quota, TFIDF-quota, Random-quota-20261001. |
| `heldout_phase1_repository.jsonl` | Sealed per-repository DUF for those seven policies. Age-quota, TFIDF-quota, and Random-quota-20261001 have no per-edge kept flag in the synced files, so their DUF is recomputed from this sidecar. |
| `heldout_prefix.jsonl` | Prefix-excluded policies and Oracle-rank at budget 28672. |
| `heldout_quota.jsonl` | Oracle-quota and Random-quota seeds 20261002 and 20261003. |
| `heldout_noise.jsonl` | Repetition policies from the same held-out study. Table 2 does not use them. |
| `development.jsonl` | Native development replay. |
| `swe_smith.jsonl` | SWE-smith replay. Kept flags are null: the later message-model replay is a different run and is not attached here. |
| `heldout_view_history.jsonl` | One history-token count per held-out decision view, for the phase-1 and prefix-excluded replays. |
| `message_ranking/` | Sealed message-level ranking export for Table 1 and Figure 1a. |

Compression fields:

| Field | Meaning |
| --- | --- |
| `decision_action_event_id`, `cascade_index` | Trigger point. |
| `forgotten_event_ids` | Forgotten set `F_t`. |
| `prefix_tokens` | Pinned prefix size `|P|`. |
| `target_tokens` | Compression target. |
| `capacity_tokens` | `C_{B,t} = target_tokens - prefix_tokens`. |
| `wipe` | True when the compression forgets every live source group outside the prefix. |
| `outside_source_tokens` | Source-token size of each live non-prefix group at that trigger. Present for the phase-1 and prefix-excluded held-out replays. |
| `deleted_origins` | Delayed origins whose events are fully forgotten at that trigger while the consumer is still ahead. Each entry has `origin_group_index` and `source_tokens`. |
| `retained_tokens_before_summary` | History tokens retained before the summary is inserted. |
| `stream_pinned_prefix_tokens` | History size of the first decision view in that stream with two live events. |

On a held-out trigger, `prefix_tokens` is the value recorded for that compression, and `capacity_tokens` is `target_tokens - prefix_tokens`. `stream_pinned_prefix_tokens` is the separate stream-level prefix drawn in Figure 3. On the development replay the trigger file has no per-compression prefix, so both prefix fields are that stream-level history size. SWE-smith decision views were left out because of their size, so SWE-smith `prefix_tokens`, `capacity_tokens`, and `wipe` are null.

Held-out `wipe`, `outside_source_tokens`, and `deleted_origins` use the group membership rule in `rv1_heldout_ext/code/analyze_ext.py`: the first two non-condensation events are the prefix, and a trigger with no live source group outside that prefix is not a wipe. Development `wipe` uses the same membership rule as `scripts/trigger_analysis.py`. Quota runs have no group-level wipe record, so their `wipe` values are null.

`kept` on an edge is whether that edge was retained at the consumer. Null means the synced per-edge file does not record it.
