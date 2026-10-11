# Edge ledger

`edges.jsonl` lists every strict deferred-use edge used by the paper. Span text is omitted.

| Field | Meaning |
| --- | --- |
| `strict_edge_id` | Edge identifier. |
| `origin_group_index` | Action-group index of the origin. |
| `consume_group_index` | Action-group index of the consumer. |
| `distance_action_groups` | Distance `d`, in action groups. |
| `delayed` | True when `d >= 2`. |
| `repo` | Repository. |
| `split` | Split label recorded in the source file. |
| `stream_id` | Trajectory stream. |
| `trajectory_id` | Trajectory identifier. |
| `source_slice` | `native-development`, `held-out`, or `swe-smith`. |

Counts in this file: held-out 238 strict / 215 delayed; native 31 strict / 26 delayed; SWE-smith 5 strict / 1 delayed.
