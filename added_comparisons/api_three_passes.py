"""Group api against group author on 2.1.322, on three passes (design file 判断标准.md, section 17, and the
public preregistration, change log entry "13 November 2026: a third pass for group `api`").

    python -B api_three_passes.py [--graded FILE ...] [--third-run-dir FOLDER] [--out FOLDER]

The registered run asked both groups on passes 1 and 2, and its report gives the comparison on two passes
(analyze.small_groups, entry api, "against_author_same_version"). On 13 November 2026 the two groups were asked
once more, together, in a plan of their own (pass 3, plan A3). This program gives the same comparison on three
passes. It is a secondary number: it takes no part in the scan of sections 3 and 5-2 or in the third pass
decision of the registered run.

What it does, step by step:

  rows 1, 2  the graded rows of the registered run (本机数据/正式跑/graded/*/graded.jsonl), read only once the
             run has graded all its passes (本机数据/正式跑/final/report.json exists, a file never opened
             here), resent asks put in place of the asks they were sent for (analyze.apply_resends), then only
             the scored items of group api and of group author on 2.1.322.
  rows 3     the records of the added pass (本机数据/API第三遍/原始记录/A3/asks) go through grade.py unchanged
             (grade_records, the author's graders), with the settings of the registered run.
  compare    analyze.paired, the function the registered report uses for this line: for every item each side
             is the mean of its values on that item, the difference is api minus author, the figure is the
             mean of the differences over the items both sides have, and the range is the 2.5 and 97.5 per
             cent points of 10,000 redraws of the items (seed 20261111). Four measures, as in section 6:
             accuracy with errors and voids left out, accuracy with them counted as wrong, thinking tokens and
             output tokens (both as ratios, from the mean difference of log(tokens + 1)).

It is computed three times: on passes 1 and 2 (this must equal the registered report's own figure, and the
program says whether the rows it used are the same number of asks), on pass 3 alone, and on the three passes
together. No wording ("clear", "points one way") is attached: section 9 gives none for this line.

Outputs in FOLDER/api_three_passes/: report.json, report.md, per_item.csv, and graded/ (grade.py's own
outputs for the records of the added pass: graded.jsonl, summary.json, public_table.csv).
"""

import argparse
import csv
import math
import sys
from pathlib import Path

import common
from common import analyze

GROUP_A = "api"
GROUP_B = "author"
VERSION = "2.1.322"
ITEMS = 78
THIRD_RUN_DIR = common.DATA / "API第三遍" / "原始记录" / "A3"
ADDED_PASS = 3

# (name in the report, key in analyze.METRICS, reported as a ratio)
MEASURES = (("accuracy", "accuracy", False), ("accuracy_bad_as_wrong", "accuracy_bad_as_wrong", False),
            ("thinking", "log_thinking", True), ("output", "log_output", True))

LIMITS = (
    "Pass 3 of these two groups was sent on 13 November 2026 in Melbourne, passes 1 and 2 on 11 and 12 November. "
    "The two groups were sent together in every pass, so the comparison between them does not depend on the day. "
    "Whether each group's own mean over three passes depends on the day cannot be told apart.",
    "In pass 3 the two groups were sent on their own. In passes 1 and 2 they sat inside the 39 versions of group "
    "main.",
    "Group author on 2.1.280 has no third pass. The comparison with the figures the LiveNerf author publishes "
    "stays on two passes.",
    "The other small groups (flags_on, notools, effort_medium, effort_xhigh, effort_max, fable) stay on two "
    "passes.",
    "The third pass was decided after the registered run had finished sending and after its log line had been "
    "seen that says, yes or no, whether each of the two tests declared a difference on three passes. No answer "
    "to a scored question and no score of any group had been read.",
)


def side(rows: list[dict], group: str) -> list[dict]:
    """The item asks of one side: group api (it only has 2.1.322), or group author on 2.1.322."""
    return [r for r in rows if r.get("group") == group and r.get("version") == VERSION
            and (r.get("unit") or "").startswith("item:")]


def compare(a: list[dict], b: list[dict], draws: int) -> dict:
    return {name: analyze.paired(a, b, key, ratio=ratio, draws=draws) for name, key, ratio in MEASURES}


def counts(rows: list[dict]) -> dict:
    out: dict = {}
    for r in rows:
        k = f"pass {r.get('pass')}: {r.get('outcome')}"
        out[k] = out.get(k, 0) + 1
    return dict(sorted(out.items()))


def by_pass(rows: list[dict]) -> dict:
    """Accuracy of one side in each pass, errors and voids left out."""
    out = {}
    for p in sorted({r.get("pass") for r in rows}):
        scored = [r for r in rows if r.get("pass") == p and r.get("outcome") == "scored"]
        out[str(p)] = {"asks": sum(1 for r in rows if r.get("pass") == p), "scored": len(scored),
                       "accuracy": (sum(r["score"] for r in scored) / len(scored)) if scored else None}
    return out


def third_pass_problem(third: list[dict]) -> str | None:
    """None when the added pass is whole: 78 item asks on each side, all of them pass 3."""
    for g in (GROUP_A, GROUP_B):
        rows = side(third, g)
        units = {r["unit"] for r in rows}
        if len(rows) != ITEMS or len(units) != ITEMS:
            return (f"the added pass has {len(rows)} item asks on {len(units)} items for group {g} on {VERSION}, "
                    f"{ITEMS} are expected. If it is still being sent, wait until it is done. If it stopped for "
                    "good, give --allow-partial-third-pass")
        if {r.get("pass") for r in rows} != {ADDED_PASS}:
            return f"the added pass has asks of group {g} that are not pass {ADDED_PASS}"
    return None


def analyse(formal_rows: list[dict], third_rows: list[dict], *, draws: int = common.DRAWS) -> dict:
    formal_rows = analyze.apply_resends(formal_rows)
    third_rows = analyze.apply_resends(third_rows)
    a12, b12 = side(formal_rows, GROUP_A), side(formal_rows, GROUP_B)
    a3, b3 = side(third_rows, GROUP_A), side(third_rows, GROUP_B)
    other = sorted({f"{r.get('group')} {r.get('version')}" for r in third_rows
                    if (r.get("unit") or "").startswith("item:")} - {f"{GROUP_A} {VERSION}", f"{GROUP_B} {VERSION}"})
    rep = {
        "format": "ccversions-api-three-passes-v1",
        "comparison": f"group {GROUP_A} minus group {GROUP_B} on {VERSION}, item by item",
        "draws": draws, "seed": common.SEED,
        "asks": {"api": {"passes_1_2": counts(a12), "added_pass": counts(a3)},
                 "author": {"passes_1_2": counts(b12), "added_pass": counts(b3)}},
        "passes_of_the_registered_run_used": sorted({r.get("pass") for r in a12 + b12}),
        "groups_in_the_added_pass_not_used": other,
        "by_pass": {"api": by_pass(a12 + a3), "author": by_pass(b12 + b3)},
        "two_passes": compare(a12, b12, draws),
        "added_pass_alone": compare(a3, b3, draws),
        "three_passes": compare(a12 + a3, b12 + b3, draws),
        "limits": list(LIMITS),
    }
    rep["per_item"] = per_item(a12 + a3, b12 + b3)
    return rep


def per_item(a: list[dict], b: list[dict]) -> list[dict]:
    out = []
    means = {name: (analyze._item_means(a, key), analyze._item_means(b, key)) for name, key, _ in MEASURES}
    for u in sorted({r["unit"] for r in a + b}):
        row = {"unit": u}
        for name, _, _ in MEASURES:
            ma, mb = means[name]
            row[f"{name}_api"], row[f"{name}_author"] = ma.get(u), mb.get(u)
            row[f"{name}_diff"] = (ma[u] - mb[u]) if u in ma and u in mb else None
        out.append(row)
    return out


def _line(name: str, r: dict, ratio: bool) -> str:
    if not r.get("items"):
        return f"| {name} | no item both sides have | | | |"
    if ratio:
        lo, hi = r["ratio_range_95"]
        return (f"| {name} | {r['items']} | {math.exp(r['a']) - 1:.0f} | {math.exp(r['b']) - 1:.0f} | "
                f"{100 * (r['ratio'] - 1):+.1f}% ({100 * (lo - 1):+.1f}% to {100 * (hi - 1):+.1f}%) |")
    lo, hi = r["range_95"]
    return (f"| {name} | {r['items']} | {common.pct(r['a'])}% | {common.pct(r['b'])}% | "
            f"{100 * r['diff']:+.1f} points ({100 * lo:+.1f} to {100 * hi:+.1f}) |")


def report_text(rep: dict) -> str:
    names = {"accuracy": "accuracy, errors and voids left out", "accuracy_bad_as_wrong": "accuracy, errors and voids as wrong",
             "thinking": "thinking tokens (geometric mean)", "output": "output tokens (geometric mean)"}
    out = ["# Group api against group author on 2.1.322, three passes", "",
           "Secondary number, added on 13 November 2026 (判断标准.md, section 17). The difference is api minus "
           "author, item by item. The range is the 95 per cent range from redrawing the items.", ""]
    for key, title in (("two_passes", "Passes 1 and 2 (the figure of the registered report)"),
                       ("added_pass_alone", "Pass 3 alone (added, sent on 13 November 2026)"),
                       ("three_passes", "Passes 1, 2 and 3 together (added)")):
        out += [f"## {title}", "", "| measure | items | api | author | api minus author |", "|---|---|---|---|---|"]
        out += [_line(names[name], rep[key][name], ratio) for name, _, ratio in MEASURES]
        out.append("")
    out += ["## Asks", ""]
    for g in ("api", "author"):
        out.append(f"- {g}: passes 1 and 2 {rep['asks'][g]['passes_1_2']}, added pass {rep['asks'][g]['added_pass']}")
        out.append(f"  accuracy by pass: " + ", ".join(
            f"pass {p} {common.pct(x['accuracy'])}% of {x['scored']}" for p, x in rep["by_pass"][g].items()))
    if rep["groups_in_the_added_pass_not_used"]:
        out.append(f"- in the added pass and not used: {rep['groups_in_the_added_pass_not_used']}")
    out += ["", "## Limits", ""] + [f"- {x}" for x in rep["limits"]] + [""]
    return "\n".join(out)


def write_outputs(rep: dict, third_graded: list[dict], out: Path) -> None:
    from ccversions import grade

    out.mkdir(parents=True, exist_ok=True)
    grade.write_outputs(third_graded, out / "graded")
    rows = rep.pop("per_item")
    common.write_json(out / "report.json", rep)
    (out / "report.md").write_text(report_text(rep))
    with open(out / "per_item.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ["unit"])
        w.writeheader()
        w.writerows(rows)


def grade_third(run_dir: Path, settings_file: Path | None) -> list[dict]:
    from ccversions import grade, items as items_mod, settings as settings_mod

    s = settings_mod.load(str(settings_file or common.SETTINGS_FILE))
    author_checks, claudecode = grade.import_author_graders(s.author_repo)
    inputs = items_mod.load(s.item_file, s.item_file_sha256, s.probe_file)
    return grade.grade_records(grade.load_records(run_dir), inputs, author_checks, claudecode)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--graded", action="append", help="a graded.jsonl of the run (default: every one under 正式跑/graded)")
    ap.add_argument("--third-run-dir", help=f"default: {THIRD_RUN_DIR}")
    ap.add_argument("--settings", help=f"default: {common.SETTINGS_FILE}")
    ap.add_argument("--out", help=f"default: {common.OUT_DEFAULT}")
    ap.add_argument("--draws", type=int, default=common.DRAWS)
    ap.add_argument("--allow-unfinished", action="store_true",
                    help="read the run's graded rows although its final step has not run")
    ap.add_argument("--allow-partial-third-pass", action="store_true",
                    help="go on although the added pass does not have 78 asks on each side")
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
    run_dir = Path(args.third_run_dir) if args.third_run_dir else THIRD_RUN_DIR
    if not (run_dir / "asks").is_dir():
        print(f"not run: {run_dir / 'asks'} is not a folder")
        return 2
    third = grade_third(run_dir, Path(args.settings) if args.settings else None)
    problem = third_pass_problem(analyze.apply_resends(third))
    if problem and not args.allow_partial_third_pass:
        print(f"not run: {problem}")
        return 2
    rep = analyse(analyze.load_rows(files), third, draws=args.draws)
    rep["graded_files"] = [str(f) for f in files]
    rep["added_pass_records"] = {"folder": str(run_dir), "read": len(third), "partial_allowed": bool(problem)}
    out = (Path(args.out) if args.out else common.OUT_DEFAULT) / "api_three_passes"
    write_outputs(rep, third, out)
    print(f"written: {out}")
    for key in ("two_passes", "three_passes"):
        r = rep[key]["accuracy"]
        print(f"{key}: items {r.get('items')}, asks api {r.get('asks_a')}, asks author {r.get('asks_b')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
