"""Read the graded rows of the registered run and apply the decision rule (design file 判断标准.md).

    python -B -m ccversions analyze --graded <graded.jsonl> [--graded ...] --out <folder> [--interim]

Input: the graded.jsonl files that `grade` wrote for the passes of the run and for their resend plans.
Nothing here calls a model or reads a raw record; every number comes from the graded rows, and all the
arithmetic of the rule itself is in judge.py (which the simulations call too).

What it does, in the order of the design file:

  section 1   a resent ask replaces the ask it was sent for. Per version and pass: asked, scored, correct,
              errors and voids by reason, and a flag where errors plus voids pass 5 per cent
  section 2   which cells count: one item in one pass counts once every version of the main group has a
              record for it. With --interim (after two passes): whether the third pass opens
  section 3   the scan over every run of consecutive versions on accuracy, twice (errors and voids left
              out; errors and voids counted as wrong), with the three conditions and a bootstrap range
  section 5   secondary numbers, reported and never used for a verdict: before and after 2.1.303, output
              tokens, answer length, share of asks that tried tools, time per ask, accuracy over the
              blocks in the order they ran, accuracy and thinking split by "tried a tool or not", and the
              versions whose first request had the same size on every item (same prompt, as far as its
              size can tell), compared with each other and scanned as groups
  section 5-2 the same scan on log thinking tokens
  section 6   every small group against its reference, item by item, with a bootstrap range
  section 7   the numbers of the figure: per version accuracy and thinking with their ranges, and the
              band the versions fall into by luck alone when they are all the same

Outputs: report.json (everything), report.md (a short reading aid), per_version.csv, per_ask_public.csv
(the columns that are safe to publish), and figure.png when matplotlib is there.
"""

import csv
import json
import math
from pathlib import Path

import numpy as np

from . import judge

MAIN_GROUP = "main"
ERROR_SHARE_FLAG = 0.05          # section 1: a version in a pass with more errors and voids than this is flagged
THIRD_PASS_MAX_BAD_OVERALL = 0.05  # section 2: above this share of errors and voids, no third pass
THIRD_PASS_MAX_BAD_VERSION = 0.10
POINTED_VERSION = "2.1.303"      # section 5: reported only
PUBLIC_COLUMNS = ("plan", "group", "pass", "block", "order", "version", "mode", "effort", "requested_model",
                  "remote_flags", "unit", "family", "repeat", "outcome", "reason", "score", "context_tokens",
                  "first_request_input_tokens", "output_tokens", "thinking_tokens", "num_turns", "tool_rounds",
                  "tool_calls", "inference_geo", "elapsed_seconds", "started_at", "resent")


def version_key(v: str) -> tuple:
    return tuple(int(x) for x in v.split("."))


def load_rows(paths: list[Path]) -> list[dict]:
    rows = []
    for p in paths:
        with open(p) as f:
            rows += [json.loads(line) for line in f if line.strip()]
    return rows


def apply_resends(rows: list[dict]) -> list[dict]:
    """A resent ask takes the place of the ask it was sent for (section 1)."""
    replaced = {}
    for r in rows:
        ro = r.get("resend_of")
        if ro:
            replaced[(ro["plan"], ro["ask_id"])] = r
    out = []
    for r in rows:
        if r.get("resend_of"):
            continue
        new = replaced.get((r.get("plan"), r.get("ask_id")))
        out.append({**new, "resent": True, "block": r.get("block"), "order": r.get("order"),
                    "plan": r.get("plan")} if new else {**r, "resent": False})
    return out


# ---------------------------------------------------------------------------------------- metrics

def _scored(r):
    return r.get("outcome") == "scored"


def _tried(r):
    return (r.get("tool_calls") or 0) > 0


def _log(x):
    return math.log(x + 1.0)


METRICS = {
    "accuracy": lambda r: float(r["score"]) if _scored(r) else math.nan,
    "accuracy_bad_as_wrong": lambda r: float(r["score"]) if _scored(r) else (
        0.0 if r.get("outcome") in ("error", "void") else math.nan),
    "log_thinking": lambda r: _log(r["thinking_tokens"]) if _scored(r) and r.get("thinking_tokens") is not None
    else math.nan,
    "log_output": lambda r: _log(r["output_tokens"]) if _scored(r) and r.get("output_tokens") is not None
    else math.nan,
    "log_answer": lambda r: _log(max((r.get("output_tokens") or 0) - (r.get("thinking_tokens") or 0), 0))
    if _scored(r) and r.get("output_tokens") is not None else math.nan,
    "tried_tools": lambda r: (1.0 if _tried(r) else 0.0) if _scored(r) and r.get("tool_calls") is not None
    else math.nan,
    "log_seconds": lambda r: math.log(r["elapsed_seconds"]) if _scored(r) and (r.get("elapsed_seconds") or 0) > 0
    else math.nan,
    "accuracy_tried": lambda r: float(r["score"]) if _scored(r) and _tried(r) else math.nan,
    "accuracy_not_tried": lambda r: float(r["score"]) if _scored(r) and not _tried(r) else math.nan,
    "log_thinking_tried": lambda r: _log(r["thinking_tokens"]) if _scored(r) and _tried(r)
    and r.get("thinking_tokens") is not None else math.nan,
    "log_thinking_not_tried": lambda r: _log(r["thinking_tokens"]) if _scored(r) and not _tried(r)
    and r.get("thinking_tokens") is not None else math.nan,
}


class Main:
    """The main group's rows as arrays [item, pass, version]."""

    def __init__(self, rows: list[dict], versions: list[str] | None = None, units: list[str] | None = None):
        self.rows = [r for r in rows if r.get("group") == MAIN_GROUP and (r.get("unit") or "").startswith("item:")]
        self.versions = versions or sorted({r["version"] for r in self.rows}, key=version_key)
        self.units = units or sorted({r["unit"] for r in self.rows})
        self.passes = sorted({r["pass"] for r in self.rows})
        vi = {v: i for i, v in enumerate(self.versions)}
        ui = {u: i for i, u in enumerate(self.units)}
        pi = {p: i for i, p in enumerate(self.passes)}
        shape = (len(self.units), len(self.passes), len(self.versions))
        self.cell = np.full(shape, None, dtype=object)
        for r in self.rows:
            if r["version"] in vi and r["unit"] in ui:
                self.cell[ui[r["unit"]], pi[r["pass"]], vi[r["version"]]] = r
        asked = np.vectorize(lambda x: x is not None)(self.cell) if self.rows else np.zeros(shape, bool)
        self.complete = asked.all(axis=-1)  # [item, pass]: every version has a record

    def array(self, metric: str) -> np.ndarray:
        fn = METRICS[metric]
        out = np.full(self.cell.shape, np.nan)
        for idx, r in np.ndenumerate(self.cell):
            if r is not None and self.complete[idx[0], idx[1]]:
                out[idx] = fn(r)
        return out


def _segment_text(versions, res) -> str:
    a, b = versions[res["best_start"]], versions[res["best_end"]]
    return a if a == b else f"{a} to {b}"


def run_scan(main: Main, metric: str, *, effect: str, min_effect: float, shuffles: int, with_range: bool = True) -> dict:
    val = main.array(metric)
    if np.isnan(val).all():
        return {"metric": metric, "no_data": True}
    res = judge.judge(val, min_effect=min_effect, effect=effect, shuffles=shuffles)
    res["metric"] = metric
    res["segment"] = _segment_text(main.versions, res)
    res["first_version"], res["last_version"] = main.versions[res["best_start"]], main.versions[res["best_end"]]
    res["values"] = int((~np.isnan(val)).sum())
    for pp in res["per_pass"]:
        pp["pass"] = main.passes[pp["pass_index"]]
    for seg in res["segments_over_line"]:
        seg["first_version"], seg["last_version"] = main.versions[seg["start"]], main.versions[seg["end"]]
    if with_range:
        lo, hi = judge.bootstrap_range(val, res["best_start"], res["best_end"], effect=effect)
        res["range_95"] = [lo, hi]
    res["effect_shown"] = res["diff"] if effect == "diff" else math.exp(res["diff"]) - 1.0
    return res


# ---------------------------------------------------------------------------------------- tables

def per_version_table(main: Main) -> list[dict]:
    out = []
    for vi, v in enumerate(main.versions):
        row = {"version": v}
        tot = {"asked": 0, "scored": 0, "correct": 0.0, "bad": 0}
        for pi, p in enumerate(main.passes):
            cells = [main.cell[ui, pi, vi] for ui in range(len(main.units)) if main.complete[ui, pi]]
            scored = [r for r in cells if _scored(r)]
            bad = [r for r in cells if r.get("outcome") in ("error", "void")]
            reasons = {}
            for r in bad:
                k = f"{r['outcome']}:{r.get('reason')}"
                reasons[k] = reasons.get(k, 0) + 1
            row[f"pass{p}_asked"] = len(cells)
            row[f"pass{p}_scored"] = len(scored)
            row[f"pass{p}_correct"] = sum(r["score"] for r in scored)
            row[f"pass{p}_accuracy"] = (sum(r["score"] for r in scored) / len(scored)) if scored else None
            row[f"pass{p}_bad"] = len(bad)
            row[f"pass{p}_bad_reasons"] = reasons
            row[f"pass{p}_flag_over_5_per_cent"] = bool(cells) and len(bad) / len(cells) > ERROR_SHARE_FLAG
            tot["asked"] += len(cells)
            tot["scored"] += len(scored)
            tot["correct"] += sum(r["score"] for r in scored)
            tot["bad"] += len(bad)
        row.update(asked=tot["asked"], scored=tot["scored"], correct=tot["correct"], bad=tot["bad"],
                   accuracy=(tot["correct"] / tot["scored"]) if tot["scored"] else None,
                   bad_share=(tot["bad"] / tot["asked"]) if tot["asked"] else None)
        # reported, never used for a verdict (design file, section 5 and "5 bis"): over the scored asks
        # of every pass that counts
        scored_all = [main.cell[ui, pi, vi] for pi in range(len(main.passes)) for ui in range(len(main.units))
                      if main.complete[ui, pi] and _scored(main.cell[ui, pi, vi])]
        think = [r["thinking_tokens"] for r in scored_all if r.get("thinking_tokens") is not None]
        tried = [r for r in scored_all if _tried(r)]
        rounds = [r["tool_rounds"] for r in tried if r.get("tool_rounds") is not None]
        row.update(thinking_tokens_geometric_mean=(math.exp(sum(_log(t) for t in think) / len(think)) - 1.0) if think else None,
                   thinking_tokens_median=float(np.median(think)) if think else None,
                   asks_with_no_thinking=sum(1 for t in think if t == 0) if think else None,
                   asks_that_tried_tools=len(tried),
                   tool_rounds_mean_of_those=(sum(rounds) / len(rounds)) if rounds else None,
                   tool_rounds_max=max(rounds) if rounds else None)
        out.append(row)
    return out


def errors_and_voids_table(main: Main) -> list[dict]:
    """Section 1: every version's errors and voids by pass and reason, one line per kind."""
    out = []
    for vi, v in enumerate(main.versions):
        for pi, p in enumerate(main.passes):
            counts: dict = {}
            for ui in range(len(main.units)):
                r = main.cell[ui, pi, vi]
                if main.complete[ui, pi] and r.get("outcome") in ("error", "void"):
                    key = (r["outcome"], str(r.get("reason")))
                    counts[key] = counts.get(key, 0) + 1
            for (outcome, reason), n in sorted(counts.items()):
                out.append({"version": v, "pass": p, "outcome": outcome, "reason": reason, "asks": n})
    return out


def figure_numbers(main: Main, metric: str, *, shuffles: int, draws: int = 10_000) -> dict:
    """Section 7: one point per version with the middle 95 per cent over redrawn items, and the band the
    highest and the lowest version reach by luck when all versions are the same."""
    val = main.array(metric)
    if np.isnan(val).all():
        return {"no_data": True}
    mask = ~np.isnan(val)
    s_item, n_item = np.where(mask, val, 0.0).sum(axis=1), mask.sum(axis=1).astype(float)  # [item, V]
    mean = s_item.sum(axis=0) / np.maximum(n_item.sum(axis=0), 1)
    rng = np.random.default_rng(judge.SEED)
    pick = rng.integers(0, val.shape[0], size=(draws, val.shape[0]))
    boot = np.stack([s_item[pick[k]].sum(axis=0) / np.maximum(n_item[pick[k]].sum(axis=0), 1) for k in range(draws)])
    lo, hi = np.quantile(boot, 0.025, axis=0), np.quantile(boot, 0.975, axis=0)
    # band: shuffle the cells, take each time the highest and the lowest version mean
    flat = val.reshape(-1, val.shape[-1])
    flat = flat[~np.isnan(flat).all(axis=1)]
    tops, bottoms = [], []
    done = 0
    while done < shuffles:
        n = min(500, shuffles - done)
        order = np.argsort(rng.random((n,) + flat.shape), axis=-1)
        sh = np.take_along_axis(np.broadcast_to(flat, (n,) + flat.shape), order, axis=-1)
        m = np.nansum(sh, axis=1) / np.maximum((~np.isnan(sh)).sum(axis=1), 1)
        tops.append(m.max(axis=1))
        bottoms.append(m.min(axis=1))
        done += n
    return {"versions": main.versions, "mean": mean.tolist(), "low_95": lo.tolist(), "high_95": hi.tolist(),
            "band_top": float(np.quantile(np.concatenate(tops), 0.975)),
            "band_bottom": float(np.quantile(np.concatenate(bottoms), 0.025)),
            "overall": float(np.nanmean(val))}


def blocks_over_time(main: Main) -> list[dict]:
    """Section 5: the accuracy of all versions together, block by block in the order they ran."""
    acc = {}
    for r in main.rows:
        if _scored(r):
            k = (r["pass"], r["block"])
            a = acc.setdefault(k, [0, 0.0, r.get("started_at")])
            a[0] += 1
            a[1] += r["score"]
            a[2] = min(a[2] or r.get("started_at") or "", r.get("started_at") or a[2] or "")
    return [{"pass": k[0], "block": k[1], "scored": a[0], "accuracy": a[1] / a[0], "first_ask_at": a[2]}
            for k, a in sorted(acc.items())]


def same_prompt_groups(main: Main) -> dict:
    """Section 5: versions whose first request had the same size on every item they were scored on in the
    first pass. Same size on 78 different items is the best sign of the same prompt this run has (the
    prompts themselves are only kept for 2.1.300 and later). Reports the groups, how much the versions
    inside the groups differ (a shuffle that only moves results between versions of the same group), and
    the scan with each group taken as one unit."""
    if not main.passes:
        return {"no_data": True}
    sig = {}
    for vi, v in enumerate(main.versions):
        key = []
        for ui in range(len(main.units)):
            r = main.cell[ui, 0, vi]
            key.append(r.get("first_request_input_tokens") if r is not None and _scored(r) else None)
        sig[v] = tuple(key)

    def same(a, b):
        both = [(x, y) for x, y in zip(sig[a], sig[b]) if x is not None and y is not None]
        return len(both) >= max(1, len(main.units) // 2) and all(x == y for x, y in both)

    groups = []
    for v in main.versions:  # consecutive versions only: a group is a run of the release order
        if groups and same(groups[-1][-1], v):
            groups[-1].append(v)
        else:
            groups.append([v])
    val = main.array("accuracy")
    resid, mask = judge.residuals(val)
    index = {v: i for i, v in enumerate(main.versions)}
    gid = np.array([gi for gi, g in enumerate(groups) for _ in g])
    sums, counts = resid.sum(axis=(0, 1)), mask.sum(axis=(0, 1)).astype(float)

    def within_stat(s, c):
        total = 0.0
        for gi, g in enumerate(groups):
            if len(g) < 2:
                continue
            ids = [index[v] for v in g]
            m = s[..., ids] / np.maximum(c[..., ids], 1)
            gm = s[..., ids].sum(axis=-1, keepdims=True) / np.maximum(c[..., ids].sum(axis=-1, keepdims=True), 1)
            total = total + (c[..., ids] * (m - gm) ** 2).sum(axis=-1)
        return total

    observed = float(within_stat(sums, counts))
    rng = np.random.default_rng(judge.SEED)
    null = []
    multi = [np.array([index[v] for v in g]) for g in groups if len(g) > 1]
    if multi:
        for _ in range(2000):
            r2, m2 = resid.copy(), mask.copy()
            for ids in multi:  # deal the results of each cell again, inside the group only
                order = np.argsort(rng.random(resid.shape[:2] + (len(ids),)), axis=-1)
                r2[..., ids] = np.take_along_axis(resid[..., ids], order, axis=-1)
                m2[..., ids] = np.take_along_axis(mask[..., ids], order, axis=-1)
            null.append(float(within_stat(r2.sum(axis=(0, 1)), m2.sum(axis=(0, 1)).astype(float))))
    p_within = (1 + sum(x >= observed - 1e-12 for x in null)) / (1 + len(null)) if null else None
    # the scan with groups as units: average the versions of a group inside each cell
    grouped = np.full(val.shape[:2] + (len(groups),), np.nan)
    for gi in range(len(groups)):
        part = val[..., gid == gi]
        n = (~np.isnan(part)).sum(axis=-1)
        grouped[..., gi] = np.where(n > 0, np.nansum(part, axis=-1) / np.maximum(n, 1), np.nan)
    scan = None
    if len(groups) > 2:
        g = judge.judge(grouped, min_effect=judge.MIN_DIFF_ACCURACY, shuffles=2000)
        scan = {k: g[k] for k in ("p", "diff", "best_start", "best_end", "same_sign_every_pass", "segments")}
        scan["first_version"], scan["last_version"] = groups[g["best_start"]][0], groups[g["best_end"]][-1]
    return {"groups": groups, "groups_with_more_than_one_version": len(multi),
            "p_versions_inside_groups_differ": p_within, "scan_with_groups_as_units": scan}


# ---------------------------------------------------------------------------------------- small groups

def _item_means(rows: list[dict], metric: str) -> dict:
    fn, acc = METRICS[metric], {}
    for r in rows:
        x = fn(r)
        if not math.isnan(x):
            acc.setdefault(r["unit"], []).append(x)
    return {u: sum(v) / len(v) for u, v in acc.items()}


def paired(rows_a: list[dict], rows_b: list[dict], metric: str, *, ratio: bool = False, draws: int = 10_000) -> dict:
    """a minus b, item by item (each side: the mean of its values on that item), over the items both have."""
    a, b = _item_means(rows_a, metric), _item_means(rows_b, metric)
    units = sorted(set(a) & set(b))
    if not units:
        return {"items": 0}
    d = np.array([a[u] - b[u] for u in units])
    rng = np.random.default_rng(judge.SEED)
    boot = d[rng.integers(0, len(d), size=(draws, len(d)))].mean(axis=1)
    lo, hi = float(np.quantile(boot, 0.025)), float(np.quantile(boot, 0.975))
    out = {"items": len(units), "a": float(np.mean([a[u] for u in units])), "b": float(np.mean([b[u] for u in units])),
           "diff": float(d.mean()), "range_95": [lo, hi], "asks_a": len(rows_a), "asks_b": len(rows_b)}
    if ratio:
        out.update(ratio=math.exp(out["diff"]), ratio_range_95=[math.exp(lo), math.exp(hi)])
    return out


def small_groups(rows: list[dict]) -> dict:
    """Section 6. Every comparison reports accuracy (difference in shares) and thinking and output (ratios)."""
    by = {}
    for r in rows:
        if (r.get("unit") or "").startswith("item:"):
            by.setdefault(r.get("group"), []).append(r)
    main = by.get(MAIN_GROUP, [])

    def of(group, versions=None):
        return [r for r in by.get(group, []) if versions is None or r["version"] in versions]

    def compare(a, b):
        return {"accuracy": paired(a, b, "accuracy"), "accuracy_bad_as_wrong": paired(a, b, "accuracy_bad_as_wrong"),
                "thinking": paired(a, b, "log_thinking", ratio=True), "output": paired(a, b, "log_output", ratio=True)}

    out = {}
    for g in sorted(k for k in by if k and k != MAIN_GROUP):
        versions = sorted({r["version"] for r in by[g]}, key=version_key)
        entry = {"versions": versions, "asks": len(by[g]),
                 "scored": sum(_scored(r) for r in by[g]),
                 "accuracy": (sum(r["score"] for r in by[g] if _scored(r)) / max(1, sum(_scored(r) for r in by[g])))}
        entry["against_main_same_versions"] = compare(of(g), [r for r in main if r["version"] in versions])
        if g.startswith("effort_"):
            entry["against_main_all_versions"] = compare(of(g), main)
        if g == "notools":
            entry["against_author"] = compare(of(g), of("author", versions))
        if g == "api":
            entry["against_author_same_version"] = compare(of(g), of("author", versions))
        if g == "author":
            entry["by_version"] = {v: {"asks": len(of(g, [v])), "scored": sum(_scored(r) for r in of(g, [v])),
                                       "accuracy": (sum(r["score"] for r in of(g, [v]) if _scored(r))
                                                    / max(1, sum(_scored(r) for r in of(g, [v])))),
                                       "output_tokens_median": float(np.median([r["output_tokens"] for r in of(g, [v])
                                                                                if _scored(r)] or [math.nan]))}
                                   for v in versions}
        out[g] = entry
    return out


# ---------------------------------------------------------------------------------------- the report

def third_pass_decision(main: Main, table: list[dict], two_pass: list[dict]) -> dict:
    """Section 2. Only meaningful right after the first two passes."""
    asked = sum(t["asked"] for t in table)
    bad = sum(t["bad"] for t in table)
    worst = max((t["bad_share"] or 0.0) for t in table) if table else 0.0
    quality_ok = (not asked) or (bad / asked <= THIRD_PASS_MAX_BAD_OVERALL and worst <= THIRD_PASS_MAX_BAD_VERSION)
    drop = judge.opens_third_pass([r for r in two_pass if not r.get("no_data")])
    return {"open_third_pass": bool(drop and quality_ok), "a_scan_points_to_a_drop_below_the_opening_line": bool(drop),
            "opening_line": judge.OPEN_ALPHA, "errors_and_voids_share": (bad / asked) if asked else None,
            "worst_version_share": worst, "quality_ok": bool(quality_ok),
            "scans": [{"metric": r["metric"], "p": r["p"], "has_drop": r["has_drop"], "segment": r["segment"]}
                      for r in two_pass if not r.get("no_data")]}


def analyze(rows: list[dict], *, versions: list[str] | None = None, units: list[str] | None = None,
            shuffles: int = judge.SHUFFLES, interim: bool = False) -> dict:
    rows = apply_resends(rows)
    # Section 1: a version the server refuses to run (its asks come back "min_version", checklist B8) is
    # out of the comparison as a whole, in every pass; the other versions are compared as usual and the
    # limits on errors and voids are counted over them. Its rows stay in the public table.
    refused = sorted({r["version"] for r in rows if r.get("group") == MAIN_GROUP and r.get("outcome") == "error"
                      and r.get("reason") == "min_version"}, key=version_key)
    all_rows = rows
    if refused:
        if versions is None:
            versions = sorted({r["version"] for r in rows if r.get("group") == MAIN_GROUP}, key=version_key)
        versions = [v for v in versions if v not in refused]
        rows = [r for r in rows if not (r.get("group") == MAIN_GROUP and r["version"] in refused)]
    main = Main(rows, versions, units)
    table = per_version_table(main)
    acc = run_scan(main, "accuracy", effect="diff", min_effect=judge.MIN_DIFF_ACCURACY, shuffles=shuffles)
    acc_strict = run_scan(main, "accuracy_bad_as_wrong", effect="diff", min_effect=judge.MIN_DIFF_ACCURACY,
                          shuffles=shuffles)
    think = run_scan(main, "log_thinking", effect="ratio", min_effect=judge.MIN_RATIO_THINKING, shuffles=shuffles)
    both = (not acc.get("no_data") and not acc_strict.get("no_data") and acc["declared"] and acc_strict["declared"]
            and np.sign(acc["diff"]) == np.sign(acc_strict["diff"]))
    report = {
        "format": "ccversions-analysis-v1",
        "versions": main.versions, "versions_refused_by_the_server": refused,
        "items": len(main.units), "passes": main.passes,
        "cells_that_count": {str(p): int(main.complete[:, i].sum()) for i, p in enumerate(main.passes)},
        "rule": {"seed": judge.SEED, "shuffles": shuffles, "line": judge.ALPHA, "opening_line": judge.OPEN_ALPHA,
                 "min_diff_accuracy": judge.MIN_DIFF_ACCURACY, "min_ratio_thinking": judge.MIN_RATIO_THINKING},
        "accuracy": acc, "accuracy_errors_and_voids_as_wrong": acc_strict,
        "accuracy_difference_declared": bool(both),
        "thinking": think,
        "thinking_difference_declared": bool(not think.get("no_data") and think["declared"]),
        "per_version": table,
        "errors_and_voids": errors_and_voids_table(main) + [
            {"version": v, "pass": p, "outcome": "error", "reason": "min_version (out of the comparison)",
             "asks": sum(1 for r in all_rows if r.get("group") == MAIN_GROUP and r["version"] == v and r["pass"] == p
                         and r.get("reason") == "min_version")}
            for v in refused for p in sorted({r["pass"] for r in all_rows if r.get("group") == MAIN_GROUP
                                              and r["version"] == v})],
    }
    if interim:
        report["third_pass"] = third_pass_decision(main, table, [acc, think])
    # section 5: reported, never used for a verdict
    sec = {}
    if POINTED_VERSION in main.versions and not acc.get("no_data"):
        k = main.versions.index(POINTED_VERSION)
        val = main.array("accuracy")
        resid, mask = judge.residuals(val)
        after, before = resid[..., k:].sum() / max(1, mask[..., k:].sum()), resid[..., :k].sum() / max(1, mask[..., :k].sum())
        sec["before_and_after_2_1_303"] = {
            "accuracy_from_2_1_303_on": float(np.nanmean(val[..., k:])), "accuracy_before": float(np.nanmean(val[..., :k])),
            "difference_after_item_difficulty": float(after - before)}
    for name, metric, effect in (("output_tokens", "log_output", "ratio"), ("answer_length", "log_answer", "ratio"),
                                 ("share_that_tried_tools", "tried_tools", "diff"),
                                 ("seconds_per_ask", "log_seconds", "ratio"),
                                 ("accuracy_of_asks_that_tried_tools", "accuracy_tried", "diff"),
                                 ("accuracy_of_asks_that_did_not", "accuracy_not_tried", "diff"),
                                 ("thinking_of_asks_that_tried_tools", "log_thinking_tried", "ratio"),
                                 ("thinking_of_asks_that_did_not", "log_thinking_not_tried", "ratio")):
        r = run_scan(main, metric, effect=effect, min_effect=0.0, shuffles=min(shuffles, 2000), with_range=False)
        sec[name] = r if r.get("no_data") else {k: r[k] for k in ("metric", "segment", "p", "effect_shown", "values",
                                                                  "same_sign_every_pass", "has_drop", "drop_named")}
    sec["accuracy_block_by_block"] = blocks_over_time(main)
    if not acc.get("no_data"):
        sec["versions_with_the_same_first_request_size"] = same_prompt_groups(main)
    report["secondary"] = sec
    report["small_groups"] = small_groups(rows)
    report["figure"] = {"accuracy": figure_numbers(main, "accuracy", shuffles=min(shuffles, 10_000)),
                        "thinking": figure_numbers(main, "log_thinking", shuffles=min(shuffles, 10_000))}
    report["asks"] = {"rows": len(all_rows), "resent": sum(bool(r.get("resent")) for r in all_rows),
                      "by_group": {g: sum(1 for r in all_rows if r.get("group") == g)
                                   for g in sorted({str(r.get("group")) for r in all_rows})}}
    return report, all_rows


def _pct(x, digits=1):
    return "n/a" if x is None else f"{100 * x:.{digits}f}"


def _three_parts_line(r: dict, key: str) -> str:
    """The versions before the segment, the segment, the versions after it: each against the mean of all
    versions (points of accuracy, or per cent of thinking)."""
    t = r["three_parts"]

    def show(x):
        if x is None:
            return "none"
        return _pct(x) if key != "thinking" else _pct(math.exp(x) - 1.0)

    return (f"- against the mean of all versions: the {t['versions_before']} versions before it {show(t['before'])}, "
            f"the segment ({t['versions_in_segment']} versions) {show(t['segment'])}, "
            f"the {t['versions_after']} versions after it {show(t['after'])}")


def report_text(rep: dict) -> str:
    lines = [f"# Analysis: {len(rep['versions'])} versions, {rep['items']} items, passes {rep['passes']}", ""]
    if rep.get("versions_refused_by_the_server"):
        lines += ["Out of the comparison, because the server refused to run them (minimum version): "
                  + ", ".join(rep["versions_refused_by_the_server"]), ""]
    for name, key, unit in (("Accuracy (errors and voids left out)", "accuracy", "points"),
                            ("Accuracy (errors and voids counted as wrong)", "accuracy_errors_and_voids_as_wrong", "points"),
                            ("Thinking tokens", "thinking", "per cent")):
        r = rep[key]
        lines.append(f"## {name}")
        if r.get("no_data"):
            lines += ["no data", ""]
            continue
        rng = r.get("range_95") or [None, None]
        lines += [f"- most marked segment: {r['segment']}, {_pct(r['effect_shown'])} {unit} against the rest "
                  f"(95% range {_pct(rng[0])} to {_pct(rng[1])})",
                  f"- p = {r['p']:.4f} over {r['shuffles']} shuffles of {r['segments']} segments (line {rep['rule']['line']})",
                  "- each pass alone: " + ", ".join(
                      f"pass {pp['pass']} {_pct(pp['diff'] if key != 'thinking' else math.exp(pp['diff']) - 1.0)}"
                      for pp in r["per_pass"]),
                  _three_parts_line(r, key),
                  f"- passes the line: {r['passes_line']}; big enough: {r['big_enough']}; same sign in every pass: "
                  f"{r['same_sign_every_pass']}; declared: {r['declared']}; points to a drop: {r['has_drop']}; "
                  f"named a drop: {bool(r['declared'] and r['drop_named'])} "
                  f"(shape {r['drop_shape']}, step of {'n/a' if r['drop_support'] is None else format(r['drop_support'], '.1f')} "
                  f"standard errors; {judge.MIN_DROP_SUPPORT} asked to open a third pass, "
                  f"{judge.MIN_DROP_SUPPORT_NAMED} to name a drop)", ""]
    lines += [f"Accuracy difference declared (both ways of counting agree): {rep['accuracy_difference_declared']}",
              f"Thinking difference declared: {rep['thinking_difference_declared']}", ""]
    if "third_pass" in rep:
        t = rep["third_pass"]
        lines += [f"Third pass opens: {t['open_third_pass']} (a scan points to a drop below {t['opening_line']}: "
                  f"{t['a_scan_points_to_a_drop_below_the_opening_line']}; errors and voids "
                  f"{_pct(t['errors_and_voids_share'])} per cent, worst version {_pct(t['worst_version_share'])})", ""]
    lines.append("## Per version")
    lines.append("| version | asked | scored | accuracy % | errors and voids |")
    lines.append("|---|---|---|---|---|")
    for t in rep["per_version"]:
        lines.append(f"| {t['version']} | {t['asked']} | {t['scored']} | {_pct(t['accuracy'])} | {t['bad']} |")
    lines += ["", "## Small groups (difference to the main group, same versions, item by item)"]
    for g, e in rep["small_groups"].items():
        c = e["against_main_same_versions"]["accuracy"]
        th = e["against_main_same_versions"]["thinking"]
        if c.get("items"):
            lines.append(f"- {g} ({', '.join(e['versions'])}): accuracy {_pct(e['accuracy'])}%, {_pct(c['diff'])} points "
                         f"({_pct(c['range_95'][0])} to {_pct(c['range_95'][1])}) on {c['items']} items"
                         + (f"; thinking x{th['ratio']:.2f}" if th.get("items") else ""))
    return "\n".join(lines) + "\n"


def draw_figure(rep: dict, path: Path) -> bool:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:  # noqa: BLE001 - the figure is optional
        return False
    fig, axes = plt.subplots(2, 1, figsize=(13, 8), sharex=True)
    for ax, key, title, scale in ((axes[0], "accuracy", "Accuracy, % (all passes pooled)", 100.0),
                                  (axes[1], "thinking", "Thinking tokens, geometric mean", None)):
        f = rep["figure"][key]
        if f.get("no_data"):
            continue
        conv = (lambda x: np.array(x) * scale) if scale else (lambda x: np.exp(np.array(x)) - 1)
        x = np.arange(len(f["versions"]))
        m, lo, hi = conv(f["mean"]), conv(f["low_95"]), conv(f["high_95"])
        ax.axhspan(float(conv(f["band_bottom"])), float(conv(f["band_top"])), color="0.88",
                   label="where the lowest and the highest version land by luck if all versions are the same")
        ax.errorbar(x, m, yerr=[m - lo, hi - m], fmt="o", color="black", ecolor="0.4", capsize=2, markersize=4)
        ax.set_ylabel(title)
        ax.legend(loc="lower left", fontsize=8, frameon=False)
        ax.set_xticks(x)
        ax.set_xticklabels(f["versions"], rotation=90, fontsize=7)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return True


def write_outputs(rep: dict, rows: list[dict], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "report.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1) + "\n")
    (out_dir / "report.md").write_text(report_text(rep))
    cols = [k for k in rep["per_version"][0] if not k.endswith("_reasons")] if rep["per_version"] else []
    with open(out_dir / "per_version.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rep["per_version"])
    with open(out_dir / "errors_and_voids.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["version", "pass", "outcome", "reason", "asks"])
        w.writeheader()
        w.writerows(rep.get("errors_and_voids") or [])
    with open(out_dir / "per_ask_public.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=PUBLIC_COLUMNS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in PUBLIC_COLUMNS})
    from .grade import PUBLIC_BAD

    leaks = sorted(set(PUBLIC_BAD.findall((out_dir / "per_ask_public.csv").read_text())))
    if leaks:  # checklist H3
        (out_dir / "per_ask_public.csv").unlink()
        raise RuntimeError(f"the public table held paths or addresses {leaks[:5]}; it was deleted")
    draw_figure(rep, out_dir / "figure.png")
