# Splits

Manifests only. Repository contents and trajectory text are not in this package.

| File | What it lists |
| --- | --- |
| `training_native.jsonl` | Native streams whose recorded split is `train` (25 streams). |
| `development_native.jsonl` | Native streams whose recorded split is `dev` (13 streams). `in_development_replay` marks the streams in the fixed-trace development replay. |
| `heldout.jsonl` | Held-out streams (299 streams). The recorded split label is `test`. |
| `message_level/trajectories.jsonl` | Message-level ranking trajectories (17728 train, 3500 dev). These public rows have a repository and a trajectory id. They do not carry a SWE-bench instance id. |
| `message_level/*.csv` | Sealed ranking export used by Table 1 and Figure 1a. The same files are under `replay_logs/message_ranking/`. |
| `swe_smith/repos.txt`, `swe_smith/instance_ids.txt` | The two SWE-smith lists, copied in their original line order. The lists are not row-aligned. |
| `swe_smith/pairs.jsonl` | 156 pairs whose repository slug and instance slug match uniquely. |
| `swe_smith/unpaired.txt` | Lines that did not form a unique pair. |

Fields: `repo`, `instance_id` when the source has one, `split`, and `stream_id` / `trajectory_id` when the source has them.
