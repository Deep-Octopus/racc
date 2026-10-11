#!/usr/bin/env python3
"""Recompute the paper's Table 1, Table 2, Table 3, Figure 1 and Figure 3.

Reads replay_logs/, edge_ledger/ and the message-level ranking export shipped
under replay_logs/message_ranking/. Does not modify those files and does not
rerun a condenser. A value the packaged logs do not determine is reported as
unavailable and is not filled in from the paper.
"""
from __future__ import annotations

import csv
import hashlib
import json
import random
import statistics
from collections import defaultdict
from pathlib import Path

ART = Path(__file__).resolve().parents[1]
BOOTSTRAPS = 2000
BOOTSTRAP_SEED = 20260914
CHECKS: list[dict] = []


def jsonl(path: Path):
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def bootstrap_ci(values: list[float], seed_key: str) -> tuple[float, float]:
    rng = random.Random(BOOTSTRAP_SEED ^ int(hashlib.sha256(seed_key.encode()).hexdigest()[:16], 16))
    n = len(values)
    means = sorted(sum(values[rng.randrange(n)] for _ in range(n)) / n for _ in range(BOOTSTRAPS))
    return means[50], means[1949]


def record(item: str, paper, recomputed, matched: bool | None, note: str = "") -> None:
    status = "UNAVAILABLE" if matched is None else ("MATCH" if matched else "MISMATCH")
    CHECKS.append({
        "item": item,
        "paper": paper,
        "recomputed": recomputed,
        "status": status,
        "note": note,
    })
    paper_text = "unavailable" if paper is None else paper
    got_text = "unavailable" if recomputed is None else recomputed
    print(f"{status}\t{item}\tpaper={paper_text}\trecomputed={got_text}")


def check_duf(item: str, paper: float, value: float | None, note: str = "") -> None:
    if value is None:
        record(item, f"{paper:.3f}", None, None, note)
        return
    got = round(value, 3)
    record(item, f"{paper:.3f}", f"{got:.3f}", got == round(paper, 3), note)


def check_points(item: str, paper: float, value: float | None, note: str = "") -> None:
    if value is None:
        record(item, f"{paper:.1f}", None, None, note)
        return
    got = round(value, 1)
    record(item, f"{paper:.1f}", f"{got:.1f}", got == round(paper, 1), note)


def check_ci(item: str, paper: tuple[float, float], lo: float | None, hi: float | None, note: str = "") -> None:
    paper_text = f"[{paper[0]:.1f}, {paper[1]:.1f}]"
    if lo is None or hi is None:
        record(item, paper_text, None, None, note)
        return
    got = (round(lo, 1), round(hi, 1))
    record(item, paper_text, f"[{got[0]:.1f}, {got[1]:.1f}]", got == (round(paper[0], 1), round(paper[1], 1)), note)


def check_int(item: str, paper: int, value: int | None, note: str = "") -> None:
    if value is None:
        record(item, str(paper), None, None, note)
        return
    record(item, str(paper), str(value), int(value) == int(paper), note)


def check_text(item: str, paper: str, value: str | None, note: str = "") -> None:
    if value is None:
        record(item, paper, None, None, note)
        return
    record(item, paper, value, value == paper, note)


def macro(repo_duf: dict[str, float]) -> float | None:
    if not repo_duf:
        return None
    return statistics.mean(repo_duf.values())


def paired(arm: dict[str, float], baseline: dict[str, float], budget: int, arm_name: str, baseline_name: str):
    repos = sorted(set(arm) & set(baseline))
    if not repos:
        return None, None, None
    diffs = [arm[repo] - baseline[repo] for repo in repos]
    mean = statistics.mean(diffs) * 100
    lo, hi = bootstrap_ci(diffs, f"heldout:{budget}:{arm_name}-minus-{baseline_name}")
    return mean, lo * 100, hi * 100


def repo_duf_from_edges(edges: list[dict]) -> dict[str, float]:
    grouped: dict[str, list[float]] = defaultdict(list)
    for edge in edges:
        if not edge.get("delayed") or edge.get("kept") is None:
            continue
        grouped[edge["repo"]].append(1.0 if edge["kept"] else 0.0)
    if not grouped:
        return {}
    return {repo: statistics.mean(values) for repo, values in grouped.items()}


def half_up(value: float) -> int:
    if value >= 0:
        return int(value + 0.5)
    return int(value - 0.5)


def load_edges_by_run() -> dict[tuple, list[dict]]:
    found: dict[tuple, list[dict]] = defaultdict(list)
    for path in sorted((ART / "replay_logs").glob("*.jsonl")):
        if path.name.endswith("_repository.jsonl") or path.name.endswith("_history.jsonl"):
            continue
        for run in jsonl(path):
            key = (path.stem, run["arm"], int(run["budget"]))
            found[key].extend(run.get("edges") or [])
    return found


def load_repo_table() -> dict[tuple, dict[str, float]]:
    path = ART / "replay_logs" / "heldout_phase1_repository.jsonl"
    found: dict[tuple, dict[str, float]] = defaultdict(dict)
    if not path.exists():
        return found
    for row in jsonl(path):
        if row.get("DUF") is None:
            continue
        found[(row["arm"], int(row["budget"]))][row["repo"]] = float(row["DUF"])
    return found


def compression_stats() -> dict:
    stats = {
        "capacity": defaultdict(list),
        "wipe": defaultdict(lambda: [0, 0]),
        "pinned": defaultdict(dict),
        "prefix_over_target": defaultdict(lambda: [0, 0]),
        "max_capacity": {},
    }
    for path in sorted((ART / "replay_logs").glob("*.jsonl")):
        if path.name.endswith("_repository.jsonl") or path.name.endswith("_history.jsonl") or path.parent.name != "replay_logs":
            continue
        if path.name.startswith("message_"):
            continue
        for run in jsonl(path):
            study = path.stem
            arm = run["arm"]
            budget = int(run["budget"])
            pinned = run.get("stream_pinned_prefix_tokens")
            if pinned is not None:
                stats["pinned"][(study, arm, budget)][run["stream_id"]] = int(pinned)
            for compression in run.get("compressions") or []:
                key = (study, arm, budget)
                if compression.get("capacity_tokens") is not None:
                    stats["capacity"][key].append(int(compression["capacity_tokens"]))
                if compression.get("prefix_tokens") is not None and compression.get("target_tokens") is not None:
                    over, total = stats["prefix_over_target"][key]
                    stats["prefix_over_target"][key] = [
                        over + int(int(compression["prefix_tokens"]) > int(compression["target_tokens"])),
                        total + 1,
                    ]
                if compression.get("wipe") is not None:
                    wipes, total = stats["wipe"][key]
                    stats["wipe"][key] = [wipes + int(bool(compression["wipe"])), total + 1]
    for key, values in stats["capacity"].items():
        if values:
            stats["max_capacity"][key] = max(values)
    return stats


def ranking_value(rows: list[dict], method: str, metric: str) -> float | None:
    for row in rows:
        if row["method"] == method and row["horizon"] == "horizon_macro" and row["metric"] == metric:
            return float(row["value"])
    return None


def check_rank(rows: list[dict], method: str, metric: str, paper: float) -> None:
    value = ranking_value(rows, method, metric)
    label = f"Table 1 / Figure 1a {method} {metric}"
    if value is None:
        record(label, f"{paper:.3f}", None, None, "no horizon_macro row in the sealed ranking export")
        return
    got = round(value, 3)
    record(label, f"{paper:.3f}", f"{got:.3f}", got == round(paper, 3))


def duf_for(edges_by_run, repo_table, study: str, arm: str, budget: int) -> tuple[dict[str, float], str]:
    edges = edges_by_run.get((study, arm, budget), [])
    from_edges = repo_duf_from_edges(edges)
    if from_edges:
        return from_edges, "per-edge kept at consume"
    from_repo = repo_table.get((arm, budget), {})
    if from_repo:
        return from_repo, "repository rows; edge-level kept flag is absent from the synced per-edge files"
    return {}, "absent"


def main() -> None:
    ranking_path = ART / "replay_logs" / "message_ranking" / "ranking.csv"
    summary_path = ART / "replay_logs" / "message_ranking" / "data_summary.csv"
    ranking_rows = list(csv.DictReader(ranking_path.open(encoding="utf-8")))
    summary_rows = list(csv.DictReader(summary_path.open(encoding="utf-8")))
    dev_summary = next(row for row in summary_rows if row["split"] == "dev")
    check_int("Table 1 decision points", 4427, int(dev_summary["decisions"]))
    check_int("Table 1 repositories", 293, int(dev_summary["repositories"]))
    for method, paper in (
        ("prevalence", 0.003),
        ("age_only", 0.010),
        ("static", 0.020),
        ("qwen_ensemble", 0.046),
    ):
        check_rank(ranking_rows, method, "AUPRC", paper)
    record(
        "Table 1 Random R@1%",
        ".205",
        None,
        None,
        "The paper calls this expected recall k/n. The sealed export has no such row. "
        "Its prevalence horizon_macro Recall@1% is a different quantity and is not substituted.",
    )
    record(
        "Table 1 Random R@5%",
        ".225",
        None,
        None,
        "The paper calls this expected recall k/n. The sealed export has no such row. "
        "Its prevalence horizon_macro Recall@5% is a different quantity and is not substituted.",
    )
    for method, metric, paper in (
        ("age_only", "Recall@1%", 0.336),
        ("age_only", "Recall@5%", 0.401),
        ("age_only", "NDCG@1%", 0.339),
        ("age_only", "NDCG@5%", 0.379),
        ("static", "Recall@1%", 0.446),
        ("static", "Recall@5%", 0.536),
        ("static", "NDCG@1%", 0.453),
        ("static", "NDCG@5%", 0.505),
        ("qwen_ensemble", "Recall@1%", 0.616),
        ("qwen_ensemble", "Recall@5%", 0.723),
        ("qwen_ensemble", "NDCG@1%", 0.628),
        ("qwen_ensemble", "NDCG@5%", 0.690),
        ("qwen_seed_20260915", "Recall@5%", 0.732),
        ("qwen_seed_20260916", "Recall@5%", 0.697),
        ("qwen_seed_20260917", "Recall@5%", 0.678),
    ):
        check_rank(ranking_rows, method, metric, paper)

    edges_by_run = load_edges_by_run()
    repo_table = load_repo_table()
    ledger_delayed = []
    ledger_counts = defaultdict(lambda: [0, 0, set()])
    for edge in jsonl(ART / "edge_ledger" / "edges.jsonl"):
        slot = ledger_counts[edge["source_slice"]]
        slot[0] += 1
        if edge["delayed"]:
            slot[1] += 1
            slot[2].add(edge["repo"])
            if edge["source_slice"] == "held-out":
                ledger_delayed.append(edge)
    held = ledger_counts["held-out"]
    native = ledger_counts["native-development"]
    smith = ledger_counts["swe-smith"]
    check_int("Held-out strict edges", 238, held[0])
    check_int("Table 2 delayed edges", 215, held[1])
    check_int("Table 2 delayed repositories", 110, len(held[2]))
    check_int("Native development strict edges", 31, native[0])
    check_int("Native development delayed edges", 26, native[1])
    check_int("SWE-smith strict edges", 5, smith[0])
    check_int("SWE-smith delayed edges", 1, smith[1])

    phase = "heldout_phase1"
    table2 = {
        28672: {
            "Age-only": (0.595, None, None),
            "Default-Recency": (0.573, -2.2, (-5.2, 0.3)),
            "RACC-TFIDF": (0.578, -1.7, (-4.1, -0.1)),
            "Oracle-Future": (1.000, 40.5, (32.1, 49.0)),
            "Age-quota": (0.701, 10.6, (6.2, 15.6)),
            "TFIDF-quota": (0.684, 8.9, (2.0, 16.0)),
            "Oracle-quota": (0.951, 35.6, (27.3, 43.4)),
        },
        57344: {
            "Age-only": (0.978, None, None),
            "Default-Recency": (0.973, -0.5, (-1.4, 0.0)),
            "RACC-TFIDF": (0.911, -6.7, (-11.4, -2.8)),
            "Oracle-Future": (1.000, 2.2, (0.0, 5.3)),
            "Age-quota": (0.978, 0.0, None),
            "TFIDF-quota": (0.925, -5.3, (-9.7, -1.2)),
            "Oracle-quota": (1.000, 2.2, (0.0, 5.2)),
        },
    }
    study_of = {
        "Age-only": phase,
        "Default-Recency": phase,
        "RACC-TFIDF": phase,
        "Oracle-Future": phase,
        "Age-quota": phase,
        "TFIDF-quota": phase,
        "Oracle-quota": "heldout_quota",
        "Oracle-rank": "heldout_prefix",
        "Age-only-prefix": "heldout_prefix",
        "TFIDF-rank-prefix": "heldout_prefix",
        "Oracle-rank-prefix": "heldout_prefix",
        "Oracle-Future-prefix": "heldout_prefix",
        "Random-quota-20261001": phase,
        "Random-quota-20261002": "heldout_quota",
        "Random-quota-20261003": "heldout_quota",
    }
    duf_cache = {}
    for budget, arms in table2.items():
        for arm, (paper_duf, paper_delta, paper_ci) in arms.items():
            values, grain = duf_for(edges_by_run, repo_table, study_of[arm], arm, budget)
            duf_cache[(arm, budget)] = values
            value = macro(values)
            check_duf(f"Table 2 {arm} B={budget} DUF", paper_duf, value, grain)
            if paper_delta is None:
                continue
            age = duf_cache.get(("Age-only", budget))
            if age is None:
                age, _ = duf_for(edges_by_run, repo_table, phase, "Age-only", budget)
            delta, lo, hi = paired(values, age, budget, arm, "Age-only")
            check_points(f"Table 2 {arm} B={budget} delta", paper_delta, delta, grain)
            if paper_ci is not None:
                check_ci(f"Table 2 {arm} B={budget} CI", paper_ci, lo, hi, grain)
    for budget, paper_duf, paper_delta, paper_range in (
        (28672, 0.584, -1.1, 7.2),
        (57344, 0.909, -6.9, 1.2),
    ):
        seeds = []
        for arm in ("Random-quota-20261001", "Random-quota-20261002", "Random-quota-20261003"):
            values, grain = duf_for(edges_by_run, repo_table, study_of[arm], arm, budget)
            seeds.append(macro(values))
        if any(value is None for value in seeds):
            check_duf(f"Table 2 Random-quota B={budget} DUF", paper_duf, None, "a seed is missing")
            check_points(f"Table 2 Random-quota B={budget} delta", paper_delta, None)
            check_points(f"Table 2 Random-quota B={budget} range", paper_range, None)
        else:
            check_duf(
                f"Table 2 Random-quota B={budget} DUF",
                paper_duf,
                statistics.mean(seeds),
                "mean of repository-macro DUF across seeds 20261001, 20261002, 20261003",
            )
            age = macro(duf_cache[("Age-only", budget)])
            check_points(
                f"Table 2 Random-quota B={budget} delta",
                paper_delta,
                (statistics.mean(seeds) - age) * 100,
            )
            check_points(
                f"Table 2 Random-quota B={budget} range",
                paper_range,
                (max(seeds) - min(seeds)) * 100,
            )

    oracle_rank, grain = duf_for(edges_by_run, repo_table, "heldout_prefix", "Oracle-rank", 28672)
    check_duf("Table 2 Oracle rank B=28672 DUF", 0.596, macro(oracle_rank), grain)
    delta, lo, hi = paired(oracle_rank, duf_cache[("Age-only", 28672)], 28672, "Oracle-rank", "Age-only")
    check_points("Table 2 Oracle rank B=28672 delta", 0.1, delta, grain)
    check_ci("Table 2 Oracle rank B=28672 CI", (-1.9, 2.6), lo, hi, grain)
    if macro(duf_cache[("Oracle-quota", 28672)]) is not None and macro(duf_cache[("Age-quota", 28672)]) is not None:
        gap = (macro(duf_cache[("Oracle-quota", 28672)]) - macro(duf_cache[("Age-quota", 28672)])) * 100
    else:
        gap = None
    check_points("Table 2 quota gap Oracle-quota minus Age-quota B=28672", 25.0, gap)

    age_prefix, grain = duf_for(edges_by_run, repo_table, "heldout_prefix", "Age-only-prefix", 28672)
    tfidf_prefix, _ = duf_for(edges_by_run, repo_table, "heldout_prefix", "TFIDF-rank-prefix", 28672)
    oracle_prefix, _ = duf_for(edges_by_run, repo_table, "heldout_prefix", "Oracle-rank-prefix", 28672)
    future_prefix, _ = duf_for(edges_by_run, repo_table, "heldout_prefix", "Oracle-Future-prefix", 28672)
    check_duf("Table 3 Age-only prefix-excluded DUF", 0.694, macro(age_prefix), grain)
    for label, arm_name, values, paper_delta, paper_ci in (
        ("TF-IDF rank", "TFIDF-rank-prefix", tfidf_prefix, -6.9, (-15.0, 1.1)),
        ("Oracle rank", "Oracle-rank-prefix", oracle_prefix, 14.4, (6.9, 22.3)),
        ("Oracle-Future", "Oracle-Future-prefix", future_prefix, 30.6, (22.8, 39.2)),
    ):
        delta, lo, hi = paired(values, age_prefix, 28672, arm_name, "Age-only-prefix")
        check_points(f"Table 3 {label} prefix-excluded delta", paper_delta, delta)
        check_ci(f"Table 3 {label} prefix-excluded CI", paper_ci, lo, hi)
    standard_tfidf = duf_cache[("RACC-TFIDF", 28672)]
    standard_oracle = oracle_rank
    standard_future = duf_cache[("Oracle-Future", 28672)]
    standard_age = duf_cache[("Age-only", 28672)]
    for label, values, paper_delta, paper_ci, arm_name in (
        ("TF-IDF rank", standard_tfidf, -1.7, (-4.1, -0.1), "RACC-TFIDF"),
        ("Oracle rank", standard_oracle, 0.1, (-1.9, 2.6), "Oracle-rank"),
        ("Oracle-Future", standard_future, 40.5, (32.1, 49.0), "Oracle-Future"),
    ):
        delta, lo, hi = paired(values, standard_age, 28672, arm_name, "Age-only")
        check_points(f"Table 3 {label} standard delta", paper_delta, delta)
        check_ci(f"Table 3 {label} standard CI", paper_ci, lo, hi)

    stats = compression_stats()
    age_caps = stats["capacity"].get((phase, "Age-only", 28672), [])
    default_caps = stats["capacity"].get((phase, "Default-Recency", 28672), [])
    check_points(
        "Table 3 median capacity standard target",
        -407,
        statistics.median(age_caps) if age_caps else None,
        "median of target_tokens - prefix_tokens on Age-only triggers",
    )
    if default_caps:
        record(
            "Prose median capacity Default-Recency B=28672",
            "-407",
            f"{statistics.median(default_caps):.1f}",
            round(statistics.median(default_caps), 1) == -407,
            "same definition on Default-Recency triggers",
        )
    neg = sum(value < 0 for value in default_caps)
    check_int("Prose negative capacity count Default-Recency B=28672", 194, neg if default_caps else None)
    check_int("Prose Default-Recency compressions B=28672", 271, len(default_caps))
    check_int(
        "Prose maximum capacity Default-Recency B=28672",
        439,
        stats["max_capacity"].get((phase, "Default-Recency", 28672)),
    )
    over, total = stats["prefix_over_target"].get((phase, "Default-Recency", 28672), [0, 0])
    if total:
        record(
            "Figure 3 prefix overfills held-out B=28672",
            "72%",
            f"{round(100 * over / total)}%",
            round(100 * over / total) == 72,
            f"{over} of {total}",
        )
    wipes, total = stats["wipe"].get((phase, "Default-Recency", 28672), [0, 0])
    if total:
        record(
            "Prose Default-Recency wipes B=28672",
            "262 of 271",
            f"{wipes} of {total}",
            (wipes, total) == (262, 271),
        )
        record(
            "Figure 3 held-out wipe share B=28672",
            "96.7%",
            f"{100 * wipes / total:.1f}%",
            round(100 * wipes / total, 1) == 96.7,
        )
    wipes, total = stats["wipe"].get((phase, "Age-only", 28672), [0, 0])
    if total:
        record(
            "Table 3 Age-only wipe rate standard",
            "97.0%",
            f"{100 * wipes / total:.1f}%",
            round(100 * wipes / total, 1) == 97.0,
            f"{wipes} of {total}",
        )
    wipes, total = stats["wipe"].get((phase, "Default-Recency", 57344), [0, 0])
    if total:
        record(
            "Figure 3 held-out wipe share B=57344",
            "0%",
            f"{100 * wipes / total:.1f}%",
            wipes == 0,
            f"{wipes} of {total}",
        )
    prefix_caps = stats["capacity"].get(("heldout_prefix", "Age-only-prefix", 28672), [])
    if prefix_caps:
        med = statistics.median(prefix_caps)
        record(
            "Table 3 median capacity prefix-excluded",
            "about 7k",
            str(round(med)),
            round(med / 1000) == 7,
            "median of target_tokens - prefix_tokens",
        )
    else:
        record("Table 3 median capacity prefix-excluded", "about 7k", None, None)
    wipes, total = stats["wipe"].get(("heldout_prefix", "Age-only-prefix", 28672), [0, 0])
    if total == 0:
        record(
            "Table 3 Age-only wipe rate prefix-excluded",
            "4.9%",
            None,
            None,
            "Held-out group sizes are not in the local sync, so the wipe bit for prefix-excluded triggers was not stored.",
        )
    else:
        record(
            "Table 3 Age-only wipe rate prefix-excluded",
            "4.9%",
            f"{100 * wipes / total:.1f}%",
            round(100 * wipes / total, 1) == 4.9,
            f"{wipes} of {total}",
        )

    for budget, paper in ((28672, 13849), (57344, 13849)):
        pinned = list(stats["pinned"].get(("development", "Default-Recency", budget), {}).values())
        if not pinned:
            record(f"Figure 3 development median prefix B={budget}", str(paper), None, None)
            continue
        med = statistics.median(pinned)
        got = half_up(med)
        record(
            f"Figure 3 development median prefix B={budget}",
            str(paper),
            str(got),
            got == paper,
            f"exact median {med} over {len(pinned)} streams; the figure prints the half-up integer",
        )
        if budget == 57344:
            room = 28672 - got
            record("Figure 3 development capacity bar B=57344", "14823", str(room), room == 14823)
        else:
            room = 14336 - got
            record("Figure 3 development capacity bar B=28672", "487", str(room), room == 487)
    for budget, paper in ((28672, "90.6%"), (57344, "0%")):
        wipes, total = stats["wipe"].get(("development", "Default-Recency", budget), [0, 0])
        if not total:
            record(f"Figure 3 development wipe share B={budget}", paper, None, None)
        else:
            text = "0%" if wipes == 0 else f"{100 * wipes / total:.1f}%"
            record(f"Figure 3 development wipe share B={budget}", paper, text, text == paper, f"{wipes} of {total}")
    for budget, target, bar_paper in ((28672, 14336, "0"), (57344, 28672, "14080")):
        pinned = list(stats["pinned"].get((phase, "Default-Recency", budget), {}).values())
        label = f"Figure 3 held-out median prefix B={budget}"
        if not pinned:
            record(label, "14592", None, None, "no stream-level pinned prefix")
            record(f"Figure 3 held-out capacity bar B={budget}", bar_paper, None, None)
            continue
        med = statistics.median(pinned)
        got = half_up(med)
        record(
            label,
            "14592",
            str(got),
            got == 14592,
            f"exact median {med} over {len(pinned)} streams; the figure prints the half-up integer",
        )
        room = max(0, target - got)
        record(
            f"Figure 3 held-out capacity bar B={budget}",
            bar_paper,
            str(room),
            str(room) == bar_paper,
            f"max(0, {target} - {got})",
        )
    forced = deleted = larger = seen = 0
    mechanism_complete = True
    for run in jsonl(ART / "replay_logs" / "heldout_phase1.jsonl"):
        if run["arm"] != "Default-Recency" or int(run["budget"]) != 28672:
            continue
        for compression in run.get("compressions") or []:
            seen += 1
            outside = compression.get("outside_source_tokens")
            origins = compression.get("deleted_origins")
            if outside is None or origins is None or compression.get("capacity_tokens") is None:
                mechanism_complete = False
                continue
            capacity = int(compression["capacity_tokens"])
            if compression.get("wipe") and outside and all(int(token) > capacity for token in outside):
                forced += 1
            for origin in origins:
                deleted += 1
                larger += int(int(origin["source_tokens"]) > capacity)
    if not mechanism_complete or seen == 0:
        record("Prose forced wipes", "213", None, None, "group sizes were not stored on every Default-Recency trigger")
        record("Prose deleted origins larger than capacity", "67 of 69", None, None)
    else:
        record("Prose forced wipes", "213", str(forced), forced == 213, f"{forced} of {seen} compressions")
        text = f"{larger} of {deleted}"
        record("Prose deleted origins larger than capacity", "67 of 69", text, text == "67 of 69")
    history_path = ART / "replay_logs" / "heldout_view_history.jsonl"
    totals = defaultdict(lambda: [0, 0])
    if history_path.exists():
        for row in jsonl(history_path):
            if row["study"] != "heldout_phase1" or int(row["budget"]) != 28672:
                continue
            if row["arm"] not in ("Default-Recency", "Oracle-Future"):
                continue
            slot = totals[row["arm"]]
            slot[0] += int(row["history_tokens"])
            slot[1] += 1
    if totals["Default-Recency"][1] and totals["Oracle-Future"][1]:
        ratio = (totals["Oracle-Future"][0] / totals["Oracle-Future"][1]) / (totals["Default-Recency"][0] / totals["Default-Recency"][1]) - 1
        got = round(ratio * 100, 1)
        record(
            "Figure 1b history-token increase",
            "1.7%",
            f"{got:.1f}%",
            got == 1.7,
            "mean history tokens over every phase-1 decision view at budget 28672",
        )
    else:
        record(
            "Figure 1b history-token increase",
            "1.7%",
            None,
            None,
            "per-view history tokens were not packaged",
        )
    default_duf = macro(duf_cache[("Default-Recency", 28672)])
    future_duf = macro(duf_cache[("Oracle-Future", 28672)])
    if default_duf is None:
        record("Figure 1b production keeps", "57%", None, None)
    else:
        text = f"{round(default_duf * 100)}%"
        record("Figure 1b production keeps", "57%", text, text == "57%")
    if future_duf is None:
        record("Figure 1b hindsight keeps", "100%", None, None)
    else:
        text = f"{round(future_duf * 100)}%"
        record("Figure 1b hindsight keeps", "100%", text, text == "100%")

    out = ART / "outputs"
    out.mkdir(exist_ok=True)
    with (out / "comparison.tsv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["item", "paper", "recomputed", "status", "note"])
        writer.writeheader()
        writer.writerows(CHECKS)
    mismatches = [row for row in CHECKS if row["status"] == "MISMATCH"]
    unavailable = [row for row in CHECKS if row["status"] == "UNAVAILABLE"]
    matched = [row for row in CHECKS if row["status"] == "MATCH"]
    lines = [
        "# Discrepancies",
        "",
        "Paper values are the printed cells in Table 1 (`tab:ranking`), Table 2 (`tab:heldout`), "
        "Table 3 (`tab:capacity`), Figure 1 and Figure 3. Recomputed values come from "
        "`replay_logs/`, `edge_ledger/` and the sealed message-level ranking export. "
        "No paper number was edited.",
        "",
        f"Matched: {len(matched)}. Mismatched: {len(mismatches)}. Not recomputed: {len(unavailable)}.",
        "",
        "## Mismatches",
        "",
    ]
    if not mismatches:
        lines.append("No recomputed value disagrees with the paper at the printed precision.")
    else:
        lines.append("| Item | Paper | Recomputed |")
        lines.append("| --- | --- | --- |")
        for row in mismatches:
            lines.append(f"| {row['item']} | {row['paper']} | {row['recomputed']} |")
    lines.extend(["", "## Not recomputed", ""])
    if not unavailable:
        lines.append("Every compared item was recomputed from the packaged files.")
    else:
        lines.append("| Item | Paper | Why |")
        lines.append("| --- | --- | --- |")
        for row in unavailable:
            why = row["note"].replace("|", "/")
            lines.append(f"| {row['item']} | {row['paper']} | {why} |")
    lines.append("")
    (ART / "DISCREPANCIES.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"\nmatched={len(matched)} mismatched={len(mismatches)} unavailable={len(unavailable)}")


if __name__ == "__main__":
    main()
