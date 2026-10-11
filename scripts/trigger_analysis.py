#!/usr/bin/env python3
"""Per-trigger and per-edge analyses of the development replay (standard library only).

Feeds Section 6.3 and Appendix D/E: the sufficient condition for a wipe,
trigger reasons, edges that cross a compression, remaining distance at the
deleting compression, and origin-merged re-read charges.
"""
from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path


def jsonl(path: Path):
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    model = args.root / "experiments/racc_deliverables_20260915/model_v2"
    data = model / "data/formal_dataset_v7"
    replay = model / "replay_v18_combined"

    groups = defaultdict(list)
    for g in jsonl(data / "groups.jsonl"):
        groups[g["stream_id"]].append(g)
    decision_index = {}
    for row in jsonl(data / "online_inputs.jsonl"):
        decision_index[(row["stream_id"], row["decision_action_event_id"])] = row["decision_group_index"]
    views = {}
    pinned = {}
    for v in jsonl(replay / "decision_views.jsonl"):
        views[(v["budget"], v["arm"], v["stream_id"], v["decision_action_event_id"])] = v
        key = (v["budget"], v["arm"], v["stream_id"])
        if key not in pinned and len(v["live_event_ids"]) == 2:
            pinned[key] = v["history_tokens"]
    triggers = list(jsonl(replay / "triggers.jsonl"))

    print("== trigger reasons", Counter((t["arm"], t["budget"], tuple(t["reasons"])) for t in triggers))

    # Sufficient condition: capacity below the smallest live source group.
    for arm in ("Default-Recency", "Age-only", "RACC-TFIDF", "Oracle-Future"):
        for budget in (28672, 57344):
            rows = [t for t in triggers if t["arm"] == arm and t["budget"] == budget]
            wipes = explained = cond_true = 0
            for t in rows:
                view = views[(budget, arm, t["stream_id"], t["decision_action_event_id"])]
                after = set(view["live_original_event_ids"])
                forgotten = set(t["forgotten_event_ids"])
                live_before = forgotten | after
                live_groups = [g for g in groups[t["stream_id"]] if set(g["event_ids"]) <= live_before]
                if not live_groups:
                    continue
                capacity = t["target_tokens"] - pinned[(budget, arm, t["stream_id"])]
                smallest = min(g["source_tokens"] for g in live_groups)
                wipe = all(set(g["event_ids"]) <= forgotten for g in live_groups)
                cond = capacity < smallest
                wipes += wipe
                cond_true += cond
                explained += wipe and cond
            print(f"== {arm:16s} {budget}: triggers {len(rows)} wipes {wipes} "
                  f"C<min group {cond_true} wipes explained by it {explained}")

    # Edges: compressions between origin and consumer, remaining distance at deletion.
    edges = list(jsonl(data / "strict_edges.jsonl"))
    for budget in (28672, 57344):
        for arm in ("Default-Recency", "RACC-TFIDF", "Oracle-Future"):
            crossing = 0
            remaining = []
            for e in edges:
                if e["distance_action_groups"] < 2:
                    continue
                sid = e["stream_id"]
                origin_ids = set(e["origin_event_ids"])
                crossed = False
                for t in triggers:
                    if t["arm"] != arm or t["budget"] != budget or t["stream_id"] != sid:
                        continue
                    d = decision_index.get((sid, t["decision_action_event_id"]))
                    if d is None or not (e["origin_group_index"] < d <= e["consume_group_index"]):
                        continue
                    crossed = True
                    if origin_ids & set(t["forgotten_event_ids"]):
                        remaining.append((e["repo"], e["origin_group_index"], e["consume_group_index"] - d))
                crossing += crossed
            print(f"== {arm:16s} {budget}: delayed edges crossing a compression {crossing}/26; "
                  f"origin deleted with remaining distance {sorted(set(remaining))}")

    # Origin-merged re-read charge for Default-Recency at 28,672.
    per_edge = list(jsonl(model / "m1a_v12/per_edge.jsonl"))
    for arm in ("Default-Recency", "RACC-TFIDF"):
        lost = [r for r in per_edge if r["arm"] == arm and r["budget"] == 28672 and not r["retained"]]
        by_repo_edge = defaultdict(float)
        by_repo_origin = defaultdict(dict)
        for r in lost:
            by_repo_edge[r["repo"]] += r["reacquisition_tokens"]
            by_repo_origin[r["repo"]][(r["stream_id"], r["origin_group_index"])] = r["reacquisition_tokens"]
        repos = {r["repo"] for r in per_edge}
        edge_total = sum(by_repo_edge.values())
        origin_total = sum(sum(v.values()) for v in by_repo_origin.values())
        print(f"== {arm} 28672 lost edges {len(lost)} unique origins "
              f"{sum(len(v) for v in by_repo_origin.values())} charge per-edge {edge_total:.0f} merged {origin_total:.0f}")

    # Where the copied span sits inside its origin group text (TF-IDF reads 8,000 chars).
    text = {(g["stream_id"], g["group_index"]): g.get("text") or "" for gl in groups.values() for g in gl}
    beyond = [e for e in edges if (pos := text.get((e["stream_id"], e["origin_group_index"]), "").find(e["atom"])) >= 8000]
    missing = [e for e in edges if e["atom"] not in text.get((e["stream_id"], e["origin_group_index"]), "")]
    print(f"== spans beyond 8,000 chars: {len(beyond)}/{len(edges)}; not found verbatim in group text: {len(missing)}")

    # Leave-one-repository-out for RACC minus Default at 28,672.
    rep = defaultdict(dict)
    for r in jsonl(model / "m1a_v12/per_repository.jsonl"):
        if r["DUF"] is not None:
            rep[(r["budget"], r["repo"])][r["arm"]] = r["DUF"]
    for budget in (28672, 57344):
        diffs = {repo: v["RACC-TFIDF"] - v["Default-Recency"] for (b, repo), v in rep.items() if b == budget}
        print(f"== {budget} paired repo differences RACC-Default {diffs}")
        for drop in diffs:
            rest = [d for r, d in diffs.items() if r != drop]
            print(f"   without {drop}: mean {statistics.mean(rest) * 100:+.2f}pp")


if __name__ == "__main__":
    main()
