# Server logs seen and not copied

The local research tree does not hold every replay log. The files below were present on the research host when this package was assembled. They were not copied. Compact fields that Table 1, Table 2, Table 3, Figure 1, and Figure 3 use were reduced into `replay_logs/` before the raw logs were left behind. Nothing on the host was modified or deleted by that reduction.

These logs are newer than the September 2026 local sync. The held-out phase-1 views and the prefix, quota, and noise views are dated 2026-10-02. The three capacity-sweep views are dated 2026-10-05. The sweep is the newest replay material on the host. It feeds the ten-cell appendix table. `scripts/reproduce_tables.py` does not recompute that appendix. The two sweep cells that repeat the main capacity comparison are already checked from the prefix-excluded study.

| Bytes | Log | What this package kept |
| --- | --- | --- |
| 561644145 | Held-out phase-1 decision views | Pinned-prefix length of the first two-event view, and history tokens of every view |
| 55968696 | Held-out group records | Per-trigger group sizes used for wipe, forced wipe, and deleted-origin size |
| 813671520 | Held-out online inputs | Nothing. Trajectory text was not required |
| 283527775 | Prefix-excluded decision views | Trigger membership for the prefix-excluded target |
| 250381314 | Quota-arm decision views | Nothing further. Quota retention uses the synced per-edge and per-repository records |
| 240449003 | Noise-arm decision views | Nothing further. Same source as the quota row |
| 372893800 | Capacity sweep, tighter room | Nothing. Appendix only |
| 459282523 | Capacity sweep, larger room | Nothing. Appendix only |
| 280556869 | Capacity sweep, middle budget | Nothing. Appendix only |

Copied whole, these nine files are about 3.3 GB. The built package stays under 500 MB without them.
