"""Time of day: asks of group main sent inside US working hours against asks sent outside them (design file
判断标准.md, section 15, "时段的对比", and the public preregistration, change log, "Time of day").

    python -B time_of_day.py [--graded FILE ...] [--out FOLDER] [--allow-unfinished]

Without --graded it reads every 本机数据/正式跑/graded/*/graded.jsonl, and only once the registered run has
graded all its passes (本机数据/正式跑/final/report.json exists, and that file is never opened here).

What it computes, for accuracy twice (errors and voids left out, and counted as wrong, section 1) and for thinking:

  cells       one item in one pass is a cell. A cell counts when every version of main has a record in it
              (section 1). Its value y is the mean over the 39 versions of the asks that count. Its share s
              is the share of those same asks sent inside US working hours (common.in_us_hours).
  d           least squares over all cells: y = item level + pass level + d * s. d is inside minus outside,
              with item difficulty and whole-pass differences taken out. Thinking: exp(d) - 1 as well.
  range       the items redrawn with replacement 10,000 times (seed 20261111), the fit done again each time,
              the middle 95 per cent of d.
  p           inside each pass, the shares s are dealt to the items at random, 10,000 times (seed 20261111), and
              p = (1 + shuffles whose |d| is at least the real |d|) / (1 + shuffles).
  parts       the same fit with one d for every pass whose shares vary (pass 1 holds the US morning and early
              afternoon, pass 2 the US afternoon and evening). A pass whose asks are all inside or all
              outside has no d of its own. The sign check uses the two parts section 15 names, passes 1 and
              2. A d of pass 3, if it has one, is reported beside them.
  pass gap    the three pass levels of the fit with one d, the largest difference between two of them.
  hours       not judged: for each hour of the day (UTC) the mean of the asks sent in that hour, after the item
              and pass levels of a fit without d are taken out.
  wording     1 clear: p < 0.01, |d| at least 3 points (accuracy) or 10 per cent (thinking), every part with
              the sign of d, and |d| larger than the pass gap. 2 points one way: p < 0.05 and the size, short
              of clear. 3 otherwise: "no difference larger than X was seen", X from the range.

Outputs in FOLDER/time_of_day/: report.json, report.md, cells.csv, hours.csv.
"""

import argparse
import csv
import math
import sys
from datetime import timedelta
from pathlib import Path

import numpy as np

import common
from common import analyze

LIMITS = (
    "In passes 1 and 2, all the asks inside US working hours were sent on one US working day, Wednesday 11 "
    "November 2026.",
    "That day was a US federal holiday (Veterans Day). A clear result is a difference between these hours on "
    "these days.",
)
CAUSES = (
    "the server under more load in busy hours",
    "something changed on the server side during these two days",
    "11 November was a US federal holiday and may not be like an ordinary working day",
)
RETEST = "the same items asked over several days, several times inside and outside these hours"
PARTS = ("1", "2")  # section 15: "分开看两段", the inside hours of pass 1 and of pass 2
LIMITS_DAY = "2026-11-11"


# ------------------------------------------------------------------------------------ cells

def cells(main: "analyze.Main", metric: str) -> list[dict]:
    """Every cell that counts and holds at least one value of the metric."""
    val = main.array(metric)
    out = []
    for ui in range(len(main.units)):
        for pi in range(len(main.passes)):
            if not main.complete[ui, pi]:
                continue
            idx = np.where(~np.isnan(val[ui, pi]))[0]
            if len(idx) == 0:
                continue
            asks = [(float(val[ui, pi, vi]), main.cell[ui, pi, vi].get("started_at")) for vi in idx]
            timed = [t for _, t in asks if t]
            if not timed:
                continue
            out.append({"unit": main.units[ui], "pass": main.passes[pi], "y": float(val[ui, pi, idx].mean()),
                        "n": int(len(idx)), "share_inside": sum(common.in_us_hours(t) for t in timed) / len(timed),
                        "asks_without_time": len(asks) - len(timed), "asks": asks})
    return out


# ------------------------------------------------------------------------------------ the fit

class Layout:
    """The cells as arrays: y[n], item[n] (0..I-1), pas[n] (0..P-1), s[n]. X0 holds the item and pass levels
    (one column per item, one per pass but the first)."""

    def __init__(self, cl: list[dict]):
        self.units = sorted({c["unit"] for c in cl})
        self.passes = sorted({c["pass"] for c in cl})
        ui = {u: i for i, u in enumerate(self.units)}
        pi = {p: i for i, p in enumerate(self.passes)}
        self.y = np.array([c["y"] for c in cl], float)
        self.item = np.array([ui[c["unit"]] for c in cl], int)
        self.pas = np.array([pi[c["pass"]] for c in cl], int)
        self.s = np.array([c["share_inside"] for c in cl], float)
        n, n_i, n_p = len(cl), len(self.units), len(self.passes)
        self.X0 = np.zeros((n, n_i + n_p - 1))
        self.X0[np.arange(n), self.item] = 1.0
        for k in range(1, n_p):
            self.X0[self.pas == k, n_i + k - 1] = 1.0

    def part_columns(self) -> tuple[list[int], np.ndarray]:
        """For the fit with one d per pass: the passes that can have their own d (their shares vary and the
        column keeps the design at full rank), and those columns."""
        keep, cols = [], []
        base = self.X0
        for k in range(len(self.passes)):
            col = np.where(self.pas == k, self.s, 0.0)
            if np.ptp(self.s[self.pas == k]) <= 0:
                continue
            trial = np.column_stack([base] + cols + [col])
            if np.linalg.matrix_rank(trial) == trial.shape[1]:
                keep.append(k)
                cols.append(col)
        return keep, (np.column_stack(cols) if cols else np.zeros((len(self.y), 0)))


def _solve(X: np.ndarray, y: np.ndarray):
    beta, _, rank, _ = np.linalg.lstsq(X, y, rcond=None)
    return beta, int(rank) == X.shape[1]


def fit_one_d(lay: Layout) -> dict:
    X = np.column_stack([lay.X0, lay.s])
    beta, full = _solve(X, lay.y)
    n_i = len(lay.units)
    levels = [0.0] + [float(b) for b in beta[n_i:n_i + len(lay.passes) - 1]]
    out = {"identifiable": bool(full),
           "pass_levels_against_pass_1": {str(p): levels[k] for k, p in enumerate(lay.passes)},
           "largest_gap_between_passes": float(max(levels) - min(levels))}
    out["d"] = float(beta[-1]) if out["identifiable"] else None
    return out


def fit_without_d(lay: Layout) -> np.ndarray:
    """The item level plus the pass level of every cell, from the fit with no d."""
    beta, _ = _solve(lay.X0, lay.y)
    return lay.X0 @ beta


def fit_parts(lay: Layout) -> dict:
    keep, cols = lay.part_columns()
    if not keep:
        return {"d_by_pass": {}, "passes_without_own_d": [str(p) for p in lay.passes]}
    beta, _ = _solve(np.column_stack([lay.X0, cols]), lay.y)
    d = beta[lay.X0.shape[1]:]
    return {"d_by_pass": {str(lay.passes[k]): float(d[j]) for j, k in enumerate(keep)},
            "passes_without_own_d": [str(p) for k, p in enumerate(lay.passes) if k not in keep]}


def permutation_p(lay: Layout, d_obs: float, shuffles: int, seed: int = common.SEED) -> dict:
    """Inside each pass, deal the shares to the items at random and fit again. With the item and pass levels
    fixed, d = s'My / s'Ms, M taking out the item and pass levels, so every shuffle costs one product."""
    X0 = lay.X0
    M = np.eye(len(lay.y)) - X0 @ np.linalg.pinv(X0)
    My = M @ lay.y
    rng = np.random.default_rng(seed)
    S = np.empty((shuffles, len(lay.y)))
    for k in range(len(lay.passes)):
        idx = np.where(lay.pas == k)[0]
        S[:, idx] = rng.permuted(np.tile(lay.s[idx], (shuffles, 1)), axis=1)
    den = np.einsum("ij,ij->i", S @ M, S)
    num = S @ My
    ok = den > 1e-12
    d = num[ok] / den[ok]
    hits = int((np.abs(d) >= abs(d_obs) - 1e-12).sum())
    return {"p": (1 + hits) / (1 + int(ok.sum())), "shuffles": int(ok.sum()),
            "shuffles_where_d_could_not_be_fitted": int((~ok).sum())}


def bootstrap(lay: Layout, draws: int, seed: int = common.SEED) -> dict:
    """The items redrawn with replacement, and each drawn item brings all its cells. An item drawn k times weighs k,
    which gives the same fit as k copies of it."""
    keep, cols = lay.part_columns()
    n_i = len(lay.units)
    X1 = np.column_stack([lay.X0, lay.s])
    X2 = np.column_stack([lay.X0, cols])
    rng = np.random.default_rng(seed)
    pick = rng.integers(0, n_i, size=(draws, n_i))
    one = np.full(draws, np.nan)
    parts = np.full((draws, len(keep)), np.nan)
    for k in range(draws):
        w = np.bincount(pick[k], minlength=n_i).astype(float)[lay.item]
        rows = w > 0
        sw = np.sqrt(w[rows])
        y = lay.y[rows] * sw
        for X, slot in ((X1, "one"), (X2, "parts")):
            if slot == "parts" and not keep:
                continue
            Xr = X[rows] * sw[:, None]
            used = np.abs(Xr).sum(axis=0) > 0
            if slot == "one" and not used[-1]:
                continue
            if slot == "parts" and not used[-len(keep):].all():
                continue
            beta, full = _solve(Xr[:, used], y)
            if not full:
                continue
            if slot == "one":
                one[k] = beta[-1]
            else:
                parts[k] = beta[-len(keep):]

    def rng95(x):
        x = x[~np.isnan(x)]
        return [float(np.quantile(x, 0.025)), float(np.quantile(x, 0.975))] if len(x) else None

    return {"range_95": rng95(one), "draws_used": int((~np.isnan(one)).sum()),
            "parts_range_95": {str(lay.passes[k]): rng95(parts[:, j]) for j, k in enumerate(keep)}}


def hours(cl: list[dict], lay: Layout, effect: str) -> list[dict]:
    """Not judged (section 15): per hour of the day in UTC, the mean of the asks sent in that hour, after the
    item and pass levels of the fit without d are taken out."""
    level = fit_without_d(lay)
    acc = {h: {"asks": 0, "sum": 0.0, "by_pass": {}} for h in range(24)}
    for c, lv in zip(cl, level):
        for v, t in c["asks"]:
            if not t:
                continue
            h = common.parse_time(t).hour
            a = acc[h]
            a["asks"] += 1
            a["sum"] += v - lv
            a["by_pass"][str(c["pass"])] = a["by_pass"].get(str(c["pass"]), 0) + 1
    out = []
    for h in range(24):
        a = acc[h]
        m = float(a["sum"] / a["asks"]) if a["asks"] else None
        out.append({"hour_utc": h, "asks": a["asks"], "asks_by_pass": a["by_pass"], "mean_after_item_and_pass": m,
                    "shown": common.shown(m, effect) if m is not None else None})
    return out


# ------------------------------------------------------------------------------------ one metric

def one_metric(main: "analyze.Main", metric: str, effect: str, *, shuffles: int, draws: int) -> dict:
    cl = cells(main, metric)
    out = {"metric": metric, "effect": effect, "cells": len(cl)}
    if not cl:
        return {**out, "identifiable": False, "wording": None, "wording_name": "not computable",
                "why": "no cell that counts"}
    lay = Layout(cl)
    by_pass = {}
    for p in lay.passes:
        sh = lay.s[lay.pas == lay.passes.index(p)]
        by_pass[str(p)] = {"cells": int(len(sh)), "share_of_items": len(sh) / max(1, len(main.units)),
                           "mean_share_inside": float(sh.mean()), "cells_all_inside": int((sh == 1).sum()),
                           "cells_all_outside": int((sh == 0).sum()), "cells_mixed": int(((sh > 0) & (sh < 1)).sum())}
    out["cells_by_pass"] = by_pass
    out["asks_without_time"] = sum(c["asks_without_time"] for c in cl)
    one = fit_one_d(lay)
    out.update(one)
    out["pass_gap_shown"] = common.shown(one["largest_gap_between_passes"], effect)
    out["hours"] = hours(cl, lay, effect)
    if not one["identifiable"]:
        return {**out, "wording": None, "wording_name": "not computable",
                "why": "the shares inside US working hours do not vary inside any pass, so d cannot be told apart "
                       "from the item and pass levels"}
    d = one["d"]
    out["d_shown"] = common.shown(d, effect)
    out.update(permutation_p(lay, d, shuffles))
    bs = bootstrap(lay, draws)
    out["range_95"], out["draws_used"] = bs["range_95"], bs["draws_used"]
    out["range_95_shown"] = [common.shown(x, effect) for x in bs["range_95"]] if bs["range_95"] else None
    parts = fit_parts(lay)
    out["passes_without_own_d"] = parts["passes_without_own_d"]
    out["parts"] = {}
    sign_ok, checked = True, 0
    for p, dp in parts["d_by_pass"].items():
        # The parts of the sign check are the two that section 15 and the preregistration name, the inside hours
        # of pass 1 and of pass 2. Another pass that has a d of its own is reported beside them. A pass in which
        # fewer than half the items count would also be left out, as in section 3.
        named = p in PARTS
        half = by_pass[p]["share_of_items"] >= common.MIN_SHARE_FOR_SIGN
        counted = named and half
        out["parts"][p] = {"d": dp, "shown": common.shown(dp, effect), "range_95": bs["parts_range_95"].get(p),
                           "counts_for_sign": counted,
                           **({} if counted else {"why_not_in_the_sign_check": (
                               "not one of the two parts section 15 names (passes 1 and 2)" if not named else
                               "fewer than half the items count in this pass")})}
        checked += counted
        if counted and np.sign(dp) != np.sign(d):
            sign_ok = False
    out["parts_in_the_sign_check"] = checked
    out["same_sign_every_part"] = bool(sign_ok and checked > 0)  # no part to check: the condition is not met
    out["big_enough"] = common.big_enough(d, effect)
    out["larger_than_pass_gap"] = abs(d) > one["largest_gap_between_passes"]
    w = common.wording(out["p"], out["big_enough"], out["same_sign_every_part"] and out["larger_than_pass_gap"])
    out["wording"], out["wording_name"] = w, common.WORDING[w]
    out["not_larger_than"] = common.not_larger_than(bs["range_95"], effect)
    return out


def share_inside_by_pass(rows: list[dict]) -> dict:
    """Asks sent inside US working hours, by pass: main, and every group together (section 15 gives 63 and 49
    per cent for passes 1 and 2, every group counted). Resent asks count at the time they were resent."""
    out = {"main": {}, "all_groups": {}}
    for r in analyze.apply_resends(rows):
        if not r.get("started_at") or r.get("pass") is None:
            continue
        inside = common.in_us_hours(r["started_at"])
        for key in ("all_groups",) + (("main",) if r.get("group") == analyze.MAIN_GROUP else ()):
            a = out[key].setdefault(str(r["pass"]), [0, 0])
            a[0] += inside
            a[1] += 1
    return {k: {p: {"asks": n, "inside": i, "share_inside": i / n} for p, (i, n) in sorted(v.items())}
            for k, v in out.items()}


def us_days_of_inside_asks(rows: list[dict]) -> dict:
    """The US working day each main ask inside US working hours belongs to (its UTC time less one hour, as in
    common.in_us_hours). The first limit of section 15 says they all belong to Wednesday 11 November."""
    out = {}
    for r in analyze.apply_resends(rows):
        if r.get("group") == analyze.MAIN_GROUP and r.get("started_at") and common.in_us_hours(r["started_at"]):
            day = (common.parse_time(r["started_at"]) - timedelta(hours=1)).date().isoformat()
            out[day] = out.get(day, 0) + 1
    return dict(sorted(out.items()))


def analyse(rows: list[dict], versions: list[str], *, shuffles: int = common.SHUFFLES,
            draws: int = common.DRAWS) -> dict:
    main, refused = common.main_group(rows, versions)
    rep = {"format": "two-comparisons-time-of-day-v1",
           "rule": {"seed": common.SEED, "shuffles": shuffles, "draws": draws, "clear_p": common.CLEAR_P,
                    "lean_p": common.LEAN_P, "min_diff_accuracy": common.MIN_DIFF_ACCURACY,
                    "min_ratio_thinking": common.MIN_RATIO_THINKING,
                    "us_working_hours": "Monday to Friday, 14:00 to 01:00 UTC the next day, by the time an ask was sent"},
           "versions": main.versions, "versions_refused_by_the_server": refused, "passes": main.passes,
           "items": len(main.units),
           "cells_that_count": {str(p): int(main.complete[:, i].sum()) for i, p in enumerate(main.passes)},
           "share_inside_by_pass": share_inside_by_pass(rows), "metrics": {}}
    for metric, effect, name in common.METRICS:
        r = one_metric(main, metric, effect, shuffles=shuffles, draws=draws)
        r["name"] = name
        rep["metrics"][metric] = r
    rep["accuracy_wording"] = common.both_ways_of_counting(rep["metrics"]["accuracy"],
                                                           rep["metrics"]["accuracy_bad_as_wrong"])
    t = rep["metrics"]["log_thinking"]
    rep["thinking_wording"] = {"wording": t.get("wording"), "wording_name": t.get("wording_name")}
    rep["limits"] = list(LIMITS)
    rep["us_days_of_inside_asks"] = us_days_of_inside_asks(rows)
    other = [d for d in rep["us_days_of_inside_asks"] if d != LIMITS_DAY]
    if other:
        rep["warning"] = (f"main has asks inside US working hours on {other} as well as on {LIMITS_DAY}. If they are "
                          f"the end of pass 3, the result gives the days as they were (change log, 12 November "
                          f"evening). If any is in pass 1 or 2, the first limit sentence is wrong and needs new words")
    rep["causes_to_list_if_clear"] = list(CAUSES)
    rep["test_that_would_tell_them_apart"] = RETEST
    return rep


# ------------------------------------------------------------------------------------ outputs

def report_text(rep: dict) -> str:
    L = [f"# Time of day: inside US working hours against outside, group main",
         "",
         f"{len(rep['versions'])} versions, {rep['items']} items, passes {rep['passes']}, cells that count "
         f"{rep['cells_that_count']}. Secondary numbers (section 8 of the preregistration).", ""]
    if rep["versions_refused_by_the_server"]:
        L += ["Out of the comparison (refused by the server): " + ", ".join(rep["versions_refused_by_the_server"]), ""]
    L.append("Asks sent inside US working hours, by pass: " + ", ".join(
        f"pass {p} {common.pct(v['share_inside'])}% (main), "
        f"{common.pct(rep['share_inside_by_pass']['all_groups'][p]['share_inside'])}% (every group)"
        for p, v in rep["share_inside_by_pass"]["main"].items()))
    L.append("")
    for metric, r in rep["metrics"].items():
        unit = "points" if r["effect"] == "diff" else "per cent"
        L.append(f"## {r['name']}")
        if r.get("wording") is None:
            L += [f"- not computable: {r.get('why')}", ""]
            continue
        rg = r.get("range_95_shown") or [None, None]
        L += [f"- inside minus outside: {common.pct(r['d_shown'])} {unit} (95% range {common.pct(rg[0])} to "
              f"{common.pct(rg[1])}, {r['draws_used']} draws)",
              f"- p = {r['p']:.4f} over {r['shuffles']} shuffles of the items inside each pass",
              "- each pass on its own: " + (", ".join(
                  f"pass {p} {common.pct(x['shown'])}" + ("" if x["counts_for_sign"] else " (not in the sign check)")
                  for p, x in r["parts"].items()) or "none")
              + (f". No d of its own: pass {', '.join(r['passes_without_own_d'])}" if r["passes_without_own_d"] else ""),
              f"- largest difference between two pass levels: {common.pct(r['pass_gap_shown'])} {unit}",
              f"- size enough: {r['big_enough']}, same sign in every part: {r['same_sign_every_part']}, "
              f"larger than the pass gap: {r['larger_than_pass_gap']}",
              f"- wording: {r['wording_name']}"
              + (f" (no difference larger than {common.pct(r['not_larger_than'])} {unit} was seen)"
                 if r["wording"] == 3 else ""), ""]
    aw = rep["accuracy_wording"]
    L += [f"Accuracy, both ways of counting together: {aw['wording_name']} ({aw.get('note')})",
          f"Thinking: {rep['thinking_wording']['wording_name']}", "",
          "Limits that go beside any time of day result:"] + [f"- {x}" for x in rep["limits"]]
    L.append("US working day of the asks inside US working hours (main): " + (", ".join(
        f"{d} {n} asks" for d, n in rep["us_days_of_inside_asks"].items()) or "none"))
    if rep.get("warning"):
        L.append(f"WARNING: {rep['warning']}")
    if aw.get("wording") == 1 or rep["thinking_wording"].get("wording") == 1:
        L += ["", "Clear: the causes this run cannot tell apart:"] + [f"- {x}" for x in rep["causes_to_list_if_clear"]]
        L += [f"A test that would tell them apart: {rep['test_that_would_tell_them_apart']}."]
    return "\n".join(L) + "\n"


def write_outputs(rep: dict, rows: list[dict], versions: list[str], out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    common.write_json(out / "report.json", rep)
    (out / "report.md").write_text(report_text(rep))
    main, _ = common.main_group(rows, versions)
    per = {}
    for metric, _, _ in common.METRICS:
        for c in cells(main, metric):
            k = (c["unit"], c["pass"])
            per.setdefault(k, {"unit": c["unit"], "pass": c["pass"]})
            per[k][metric] = c["y"]
            per[k][f"{metric}_asks"] = c["n"]
            per[k][f"{metric}_share_inside"] = c["share_inside"]
    cols = ["unit", "pass"] + [f"{m}{x}" for m, _, _ in common.METRICS for x in ("", "_asks", "_share_inside")]
    with open(out / "cells.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(per[k] for k in sorted(per, key=lambda k: (k[1], k[0])))
    with open(out / "hours.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["metric", "hour_utc", "asks", "mean_after_item_and_pass", "shown"])
        for metric, r in rep["metrics"].items():
            for h in r.get("hours") or []:
                w.writerow([metric, h["hour_utc"], h["asks"], h["mean_after_item_and_pass"], h["shown"]])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--graded", action="append", help="a graded.jsonl of the run (default: every one under 正式跑/graded)")
    ap.add_argument("--versions-file", help="default: the versions file the settings name")
    ap.add_argument("--settings", help=f"default: {common.SETTINGS_FILE}")
    ap.add_argument("--out", help=f"default: {common.OUT_DEFAULT}")
    ap.add_argument("--shuffles", type=int, default=common.SHUFFLES)
    ap.add_argument("--draws", type=int, default=common.DRAWS)
    ap.add_argument("--allow-unfinished", action="store_true",
                    help="read the run's graded rows although its final step has not run")
    args = ap.parse_args(argv)
    if args.graded:
        files = [Path(x) for x in args.graded]
    else:
        if not common.formal_finished() and not args.allow_unfinished:
            print(f"not run: {common.FORMAL_FINAL_REPORT} does not exist yet, so the registered run has not graded "
                  "all its passes. Start again when it has, or give --allow-unfinished.")
            return 2
        files = common.default_graded_files()
    if not files:
        print("not run: no graded.jsonl found")
        return 2
    rows = analyze.load_rows(files)
    versions = common.load_versions(Path(args.settings) if args.settings else None,
                                    Path(args.versions_file) if args.versions_file else None)
    rep = analyse(rows, versions, shuffles=args.shuffles, draws=args.draws)
    rep["graded_files"] = [str(f) for f in files]
    out = Path(args.out) if args.out else common.OUT_DEFAULT
    write_outputs(rep, rows, versions, out / "time_of_day")
    print(f"written: {out / 'time_of_day'}")
    print(f"accuracy: {rep['accuracy_wording']['wording_name']}, thinking: {rep['thinking_wording']['wording_name']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
