#!/usr/bin/env python3
"""Recompute every number reported in the paper from the sealed evidence files.

Standard library only. Run from anywhere:

    python3 collect_numbers.py --root /path/to/agentic_teachmaster_research

The script only reads files. Each printed block names the table, figure or
sentence it feeds.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path

ARMS = ["Default-Recency", "Age-only", "RACC-TFIDF", "Oracle-Future"]
BUDGETS = ["28672", "57344"]
TAU = 0.6632113018429802


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def jsonl(path: Path):
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def quantile(values, p):
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(p * len(ordered)))]


def r2_ranking(root: Path) -> None:
    exports = root / "experiments/reacq_aware_compressor_r2/paper_exports"
    print("== Table 1 / Figure 1a: message-level ranking (R2 dev split)")
    with (exports / "data_summary.csv").open() as f:
        for row in csv.DictReader(f):
            print("  data", row["split"], row["horizon"], "rows", row["rows"], "repos", row["repositories"],
                  "decisions", row["decisions"], "positives", row["positive"], "prevalence",
                  round(float(row["prevalence"]), 4))
    with (exports / "ranking.csv").open() as f:
        for row in csv.DictReader(f):
            if row["method"] in {"age_only", "static", "qwen_ensemble", "prevalence"} or row["horizon"] == "horizon_macro":
                print("  rank", row["method"], row["horizon"], row["metric"], round(float(row["value"]), 3))
    with (exports / "repository_bootstrap.csv").open() as f:
        for row in csv.DictReader(f):
            print("  boot", row["metric"], round(float(row["estimate"]), 3),
                  [round(float(row["ci95_low"]), 3), round(float(row["ci95_high"]), 3)],
                  "repos", row["effective_repositories"])


def dev_replay(root: Path) -> None:
    model = root / "experiments/racc_deliverables_20260915/model_v2"
    result = load(model / "m1a_v12/result.json")
    print("== Table 2: native development slice (m1a_v12)")
    print("  edges", result["edge_count"], "delayed", result["delayed_edge_count"],
          "immediate", result["immediate_edge_count"])
    for budget in BUDGETS:
        base = result["metrics"][budget]["Default-Recency"]["mean_history_tokens"]
        for arm in ARMS:
            m = result["metrics"][budget][arm]
            rm, em = m["repository_macro"], m["edge_micro"]
            print(f"  {budget} {arm:16s} DUF {rm['DUF']:.3f} {[round(x, 3) for x in rm['DUF_95ci']]}"
                  f" edge {em['DUF'] * m['n_delayed_edges']:.0f}/{m['n_delayed_edges']}"
                  f" IR_I {rm['IR_I']:.2f} PTR {rm['PTR']:.3f} reacq {rm['reacquisition_tokens']:.1f}"
                  f" tokens {m['mean_history_tokens']:.0f} ({(m['mean_history_tokens'] / base - 1) * 100:+.2f}%)")
    rows = list(jsonl(model / "m1a_v12/per_edge.jsonl"))
    print("  summary salvage (atom verbatim in a live summary):",
          sum(bool(r["summary_survived"]) for r in rows), "/", len(rows))
    grouped = defaultdict(dict)
    for r in rows:
        grouped[(r["budget"], r["strict_edge_id"])][r["arm"]] = r
    print("== Appendix C: delayed edges on which arms differ")
    for (budget, edge_id), arms in sorted(grouped.items()):
        outcomes = {a: (int(arms[a]["retained"]), int(bool(arms[a]["ptr"]))) for a in ARMS}
        if len(set(outcomes.values())) > 1:
            any_row = next(iter(arms.values()))
            print(f"  {budget} {any_row['repo']:32s} {any_row['split']:5s} origin {any_row['origin_group_index']:>3}"
                  f" d={any_row['distance_action_groups']:>2} (retained, ptr) {outcomes}")
    audit = load(model / "f1_audit/result.json")
    print("  split-macro DUF", {k: round(v["DUF"], 3) for k, v in audit["dev_split_macro_DUF"].items()})


def variants(root: Path) -> None:
    model = root / "experiments/racc_deliverables_20260915/model_v2"
    print("== Table 3: packing and scorer variants vs Age-only (development slice)")
    sources = {
        "m1a_v4": ["Age-only", "Oracle-Future"],
        "m1a_v8": ["RACC-TFIDF"],
        "m1a_v13": ["RACC-TFIDF-noprotect"],
        "m1a_v10": None, "m1a_v11": None, "m1a_v9": None,
        "m1a_v5": None, "m1a_v6": None, "m1a_v7": None,
    }
    age = load(model / "m1a_v4/result.json")["metrics"]
    for name in sources:
        path = model / name / "result.json"
        if not path.exists():
            print("  missing", name)
            continue
        metrics = load(path)["metrics"]
        for budget in BUDGETS:
            for arm, m in metrics[budget].items():
                if arm in {"Age-only", "Oracle-Future"} and name != "m1a_v4":
                    continue
                a = age[budget]["Age-only"]
                print(f"  {name:8s} {budget} {arm:22s} DUF {m['repository_macro']['DUF']:.4f}"
                      f" ({(m['repository_macro']['DUF'] - a['repository_macro']['DUF']) * 100:+.3f}pp)"
                      f" tokens {(m['mean_history_tokens'] / a['mean_history_tokens'] - 1) * 100:+.2f}%"
                      f" IR_I {m['repository_macro']['IR_I']}")


def capacity(root: Path) -> None:
    model = root / "experiments/racc_deliverables_20260915/model_v2"
    print("== Figure 3a / Section 6.3: pinned prefix and retention capacity")
    first = {}
    for row in jsonl(model / "replay_v18/decision_views.jsonl"):
        if row["budget"] == 28672 and row["stream_id"] not in first:
            first[row["stream_id"]] = (row["history_tokens"], len(row["live_event_ids"]))
    dev = [t for t, n in first.values() if n == 2]
    print("  dev pinned prefix: streams", len(dev), "median", statistics.median(dev), "range", min(dev), max(dev))
    first = {}
    pattern = re.compile(r'"arm": "Default-Recency"')
    views = model / "replay_final_v24/merged/decision_views.jsonl"
    if views.exists():
        with views.open(encoding="utf-8") as stream:
            for line in stream:
                if '"budget": 28672' not in line or not pattern.search(line):
                    continue
                row = json.loads(line)
                if row["stream_id"] not in first:
                    first[row["stream_id"]] = (row["history_tokens"], len(row["live_event_ids"]))
        sealed = [t for t, n in first.values() if n == 2]
        print("  sealed pinned prefix: streams", len(sealed), "median", statistics.median(sealed),
              "range", min(sealed), max(sealed))
    triggers = list(jsonl(model / "replay_v18/triggers.jsonl"))
    for budget in (28672, 57344):
        rows = [t for t in triggers if t["budget"] == budget]
        print(f"  dev Default {budget}: triggers {len(rows)} streams {len({t['stream_id'] for t in rows})}"
              f" retained-before-summary median {statistics.median(t['retained_tokens_before_summary'] for t in rows)}"
              f" summary median {statistics.median(t['summary_tokens_in_resulting_history'] for t in rows)}")
    audit = load(model / "f1_audit/result.json")
    for split, table in audit["all_deleted_triggers"].items():
        for key, value in sorted(table.items()):
            print(f"  wipe {split:5s} {key:24s} {value['all_live_source_deleted']}/{value['triggers']}"
                  f" = {value['all_live_source_deleted'] / value['triggers']:.3f}")


def scorer(root: Path) -> None:
    model = root / "experiments/racc_deliverables_20260915/model_v2"
    print("== Figure 3b / Section 6.4: TF-IDF risk distribution and threshold")
    split = {}
    for row in jsonl(model / "data/formal_dataset_v7/online_inputs.jsonl"):
        split[(row["stream_id"], row["decision_action_event_id"], row["candidate_group_id"])] = row["split"]
    values = defaultdict(list)
    for row in jsonl(model / "m1b/tfidf_scores.jsonl"):
        values[split[(row["stream_id"], row["decision_action_event_id"], row["candidate_group_id"])]].append(row["risk"])
    for name, v in values.items():
        print(f"  {name}: rows {len(v)} median {quantile(v, .5):.4f} p90 {quantile(v, .9):.4f}"
              f" p99 {quantile(v, .99):.4f} max {max(v):.4f} >=tau {sum(x >= TAU for x in v)}")
    audit = load(model / "f1_audit/result.json")
    final = audit["score_distributions"]["final"]
    print("  sealed:", {k: final[k] for k in ("rows", "median", "p90", "p99", "max", "rows_ge_tau")})
    print("  tau train values", [round(x, 4) for x in audit["tau"]["train_values"]])
    print("  event-level AUC", json.dumps(audit["dev_event_level_auc"], indent=None))
    print("  top TF-IDF coefficients (now)", [w for w, _ in audit["tfidf_top_coefficients"]["now"]])


def sealed(root: Path) -> None:
    model = root / "experiments/racc_deliverables_20260915/model_v2"
    print("== Table 4: sealed SWE-smith slice")
    result = load(model / "m1a_final_v24/result.json")
    print("  edges", result["edge_count"], "delayed", result["delayed_edge_count"], "immediate",
          result["immediate_edge_count"])
    for budget in BUDGETS:
        base = result["metrics"][budget]["Default-Recency"]["mean_history_tokens"]
        for arm in ARMS:
            m = result["metrics"][budget][arm]
            print(f"  {budget} {arm:16s} DUF {m['edge_micro']['DUF']:.0f} IR_I {m['edge_micro']['IR_I']:.2f}"
                  f" PTR {m['edge_micro']['PTR']:.2f} tokens {m['mean_history_tokens']:.0f}"
                  f" ({(m['mean_history_tokens'] / base - 1) * 100:+.2f}%)")
    audit = load(model / "f1_audit/result.json")
    print("  funnel", audit["strict_edge_funnel"]["final"])
    print("  dev tools", audit["strict_edge_funnel"]["dev"]["tools"])
    print("  delayed edge", [e for e in audit["final_edges"] if e["distance_action_groups"] >= 2])
    report = load(model / "replay_final_v24/merged/replay_report.json")
    print("  replay runs", report["stream_arm_budget_runs"], "triggers", report["trigger_count"])


def rv1(root: Path) -> None:
    model = root / "experiments/racc_deliverables_20260915/model_v2"
    print("== Table 3: development controls (rv1_capacity e1-e4), delta vs Age-only of the same batch/target")
    batches = {
        "e1": "rv1_capacity/e1/eval/result.json",
        "e2": "rv1_capacity/e2/eval/result.json",
        "e3": "rv1_capacity/e3/eval/result.json",
        "e4_half": "rv1_capacity/e4_msgqwen/dev_half/eval/result.json",
        "e4_prefix": "rv1_capacity/e4_msgqwen/dev_prefix/eval/result.json",
    }
    e1, e2 = load(model / batches["e1"])["metrics"], load(model / batches["e2"])["metrics"]
    for name, rel in batches.items():
        metrics = load(model / rel)["metrics"]
        for budget, arms in metrics.items():
            for arm, m in arms.items():
                if "prefix" in arm:
                    ref = e1[budget]["Age-only-prefix"]
                elif name == "e1":
                    ref = e1[budget]["Age-only"]
                else:
                    ref = e2[budget]["Age-only"]
                rm = m["repository_macro"]
                print(f"  {name:9s} {budget} {arm:24s} DUF {rm['DUF']:.4f} "
                      f"({(rm['DUF'] - ref['repository_macro']['DUF']) * 100:+.1f}pp) "
                      f"kept {m['edge_micro']['DUF'] * m['n_delayed_edges']:.0f}/{m['n_delayed_edges']} "
                      f"tokens {(m['mean_history_tokens'] / ref['mean_history_tokens'] - 1) * 100:+.2f}% IR_I {rm['IR_I']}")
    print("== Table 2 / Appendix: held-out set (rv1_heldout/report_delayed/report.json)")
    report = load(model / "rv1_heldout/report_delayed/report.json")
    print("  funnel", report["funnel"])
    for budget, arms in report["metrics"].items():
        base = arms["Default-Recency"]["mean_history_tokens"]
        for arm, m in arms.items():
            rm, em = m["repository_macro"], m["edge_micro"]
            print(f"  {budget} {arm:22s} DUF {rm['DUF']:.3f} {[round(x, 3) for x in rm['DUF_95ci']]} "
                  f"edge {em['DUF']:.3f} IR_I {rm['IR_I']:.3f} tokens {(m['mean_history_tokens'] / base - 1) * 100:+.2f}%")
    for d in report["paired_differences"]:
        print(f"  paired {d['budget']} {d['arm']:22s} - {d['baseline']:16s} {d['mean_difference'] * 100:+.1f}pp "
              f"{[round(x * 100, 1) for x in d['repository_cluster_bootstrap_95ci']]}")
    for w in report["wipe"]["by_arm_budget"]:
        print(f"  wipe {w['budget']} {w['arm']:22s} {w['wipe_triggers']}/{w['triggers']}")
    print("  capacity, crossing edges and deleted-origin sizes: run heldout_capacity_analysis.py on the server")


def rv1_ext(root: Path) -> None:
    model = root / "experiments/racc_deliverables_20260915/model_v2/rv1_heldout_ext"
    print("== Tables 2-3 post-hoc held-out rows (rv1_heldout_ext): see RESULT.md tables")
    for part in ("A_capacity", "B_noise", "C_quota"):
        text = (model / part / "RESULT.md").read_text(encoding="utf-8")
        for line in text.splitlines():
            if line.startswith("| ") and ("28672" in line or "57344" in line):
                cells = [c.strip() for c in line.strip("|").split("|")]
                print(f"  {part:10s}", " | ".join(cells[:7]))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    r2_ranking(args.root)
    dev_replay(args.root)
    variants(args.root)
    capacity(args.root)
    scorer(args.root)
    sealed(args.root)
    rv1(args.root)
    rv1_ext(args.root)


if __name__ == "__main__":
    main()
