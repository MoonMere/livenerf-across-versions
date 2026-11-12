"""The desktop prompt group ("桌面版说明组"): the six comparisons of design file 判断标准.md, section 16.

    python -B desktop_prompt.py [--graded FILE ...] [--dsp-graded FILE ...] [--dsp-settings FILE]
                                [--desktop-asks FOLDER | --desktop-graded FILE ...] [--out FOLDER]
                                [--allow-unfinished] [--allow-partial-round3]

The group asks the 78 items on Claude Code 2.1.321 five ways, three passes each (程序/桌面版说明组/dsp.py).
A to D replace 2.1.321's own system prompt with a prompt the Claude Desktop app saved, E asks the way group
main asks. In the records the way is the field "group" (dsp_a to dsp_e) and the pass is the field "pass".

The six comparisons (section 16, table "怎么比"):

  1  B minus A               the two sections added on 15 October (the main question)    three wordings
  2  D minus E               the saved Desktop prompt in place of the command line's own  three wordings
  3  C minus B               the changes between 15 October and 12 November               size and range
  4  D minus C               the section saying the session was started from another one size and range
  5  E minus main 2.1.321    the same way of asking, another batch: do they match         size and range
  6  Desktop minus D         what the real Desktop app adds beyond the prompt, 77 items   size and range

Where the rows come from:

  main       without --graded, every 本机数据/正式跑/graded/*/graded.jsonl, and only once the registered run
             has graded all its passes (本机数据/正式跑/final/report.json exists. That file is never opened
             here). main's asks on 2.1.321 in the cells that count (section 1: every version has a record
             in that item and pass), over every pass, as desktop_vs_cli.py takes them.
  this group without --dsp-graded, the raw records of plans DSP1, DSP2, DSP3 and their resend plans DSP1r,
             DSP2r, DSP3r in the raw_dir of the group's settings file (default 本机数据/桌面版说明组/设置.toml),
             graded here with grade.py unchanged (grade_records, the author's graders, the item file and
             author code the settings name), as formal.py grades each plan. The small batch (DSPS) and the
             probes are left out. With --dsp-graded, graded rows that grade.py wrote for those plans.
             A resent ask takes the place of the ask it was sent for (analyze.apply_resends).
  Desktop    without --desktop-graded, the records dq.py wrote, picked and graded the way desktop_vs_cli.py
             does (its own pick and grade_records), on its 77 items. With --desktop-graded, the graded rows
             desktop_vs_cli.py wrote (desktop/graded/graded.jsonl).

When it runs: section 16 says the answers of this group are graded and looked at only once the Desktop
group's round 3 is sent or 00:10 UTC on 13 November 2026 (11:10 on 13 November in Melbourne) has passed.
The program checks that before it grades anything: round 3 of the Desktop group has all 77 items, or the
clock is past that time. A Desktop round 3 with some asks but not all stops it, as in desktop_vs_cli.py,
unless --allow-partial-round3 is given.

How each comparison is computed (section 16, "怎么比", and section 15 for the Desktop comparison):
for accuracy twice (errors and voids left out, and counted as wrong, section 1) and for thinking (log of
thinking tokens + 1): for each item, the mean over the passes one side has minus the mean over the passes
the other side has. The difference is the mean over the items both sides have. A side that has fewer
passes on an item (a pass that was not sent, or a pass that stopped part way) is taken with the passes it
has, and the output says how many passes each way has. Range: the items redrawn 10,000 times, seed
20261111, as analyze.paired does.

Comparisons 1 and 2 are written in section 15's three wordings. p: each item's difference given a random
sign 10,000 times, seed 20261111, p = (1 + flips whose |mean| is at least the real one) / (1 + flips).
The parts for "every part points the same way" are the three passes: pass k of one side against pass k of
the other side (both sides were sent in the same batch, shuffled together). A pass with fewer than half the
items of the comparison stays out of that check, as in section 3.
  1 clear            p < 0.01, at least 3 points (accuracy) or 10 per cent (thinking), and every pass in the
                     check with the sign of the whole.
  2 points one way   p < 0.05 and the size, short of clear.
  3 otherwise        "no difference larger than X was seen", X the end of the range furthest from zero.
Accuracy says only what holds both ways of counting: the weaker wording of the two, and wording 3 when the
two point in opposite directions (common.both_ways_of_counting).

Comparisons 3 to 6 report the difference and its range only. Comparison 5 is also checked against the line
for "clear" (the same p, size and sign check, with each pass of E against the mean of main's passes, as
section 15 does for Desktop). When accuracy (both ways) or thinking reaches it, comparisons 5 and 6, the two
that span two batches, carry a reminder in the outputs. The numbers of that check are in report.json only.

Outputs in FOLDER/desktop_prompt/ (FOLDER defaults to 本机数据/后加的两个对比): report.md, report.json, and,
when this program graded the raw records itself, graded/ (grade.py's own outputs for this group's records).
"""

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

import common
import desktop_vs_cli as dvc
from common import analyze

VERSION = "2.1.321"
# The ways and their group names as dsp.py writes them (test_desktop_prompt.py checks they still agree).
GROUPS = {"dsp_a": "A", "dsp_b": "B", "dsp_c": "C", "dsp_d": "D", "dsp_e": "E"}
GROUP_OF = {x: g for g, x in GROUPS.items()}
LETTERS = tuple(GROUPS.values())
PLANS = tuple(f"DSP{n}{suffix}" for n in (1, 2, 3) for suffix in ("", "r"))
ITEMS = 78
NOT_DELIVERABLE = tuple(dvc.NOT_DELIVERABLE)           # the one item the Desktop group cannot ask
DESKTOP_ITEMS = dvc.ITEMS_IN_GROUP                     # 77
LOOK_FROM = datetime(2026, 11, 13, 0, 10, tzinfo=timezone.utc)  # 11:10 on 13 November in Melbourne
DSP_SETTINGS = common.DATA / "桌面版说明组" / "设置.toml"
OUT_NAME = "desktop_prompt"

WHAT_DIFFERS = {
    1: ("B holds all of A's sections word for word and three more: a heading, a section on starting other "
        "sessions and a section on task lists and wrapping up (section 16, table of the five ways). A and B "
        "were sent in the same batch, shuffled together in every block."),
    2: ("D is the prompt the Desktop group's sessions saved, passed with --system-prompt in place of 2.1.321's "
        "own prompt, with the author's two sentences after it. E keeps 2.1.321's own prompt and appends the two "
        "sentences, as main does. They were sent in the same batch, shuffled together in every block. The saved "
        "prompt is not everything the Desktop app sends (section 16, limit 2)."),
}
COMPARISONS = (
    {"id": 1, "name": "B minus A", "a": ("dsp", "B"), "b": ("dsp", "A"), "write": "wordings",
     "question": "whether the two sections added on 15 October change anything (the main question of this group)"},
    {"id": 2, "name": "D minus E", "a": ("dsp", "D"), "b": ("dsp", "E"), "write": "wordings",
     "question": "whether the saved Desktop prompt in place of the command line's own prompt changes anything"},
    {"id": 3, "name": "C minus B", "a": ("dsp", "C"), "b": ("dsp", "B"), "write": "size",
     "question": "the changes between 15 October and 12 November"},
    {"id": 4, "name": "D minus C", "a": ("dsp", "D"), "b": ("dsp", "C"), "write": "size",
     "question": "the section telling the model it was started from another session"},
    {"id": 5, "name": f"E minus main on {VERSION}", "a": ("dsp", "E"), "b": ("main", None), "write": "size",
     "reminder_check": True, "two_batches": True,
     "question": ("the same way of asking on other days, in other config folders, by another sending program: "
                  "do the results match the registered run")},
    {"id": 6, "name": "Desktop minus D", "a": ("desktop", None), "b": ("dsp", "D"), "write": "size",
     "items": "desktop", "two_batches": True,
     "question": f"how much the real Desktop app still differs once its saved prompt is replayed ({DESKTOP_ITEMS} items)"},
)
REMINDER = ("Reminder (section 16): E, asked the way main asks but in this group's batch, came out clearly different "
            f"from main on {VERSION} by section 15's line ({{which}}). So this way of sending does not match the "
            "registered run, and a comparison that spans two batches, as this one does, also carries what differs "
            "between the batches: other days and hours, other config folders, another sending program.")
CLEAR_NOTE = ("Clear by section 15's line: this goes into the summary at the top of the results page, in plain words, "
              "with the difference and its range. Section 15 then asks for two more things next to it: the causes "
              "this run cannot tell apart, and how a new test would tell them apart. Section 16 gives both for this "
              "comparison, after its table of the six comparisons.")
LEAN_NOTE = "Points this way, short of the line we call clear."


# ------------------------------------------------------------------------------------ this group's rows

def load_dsp_records(raw_dir: Path) -> tuple[list[dict], dict]:
    """The raw records of the three passes and their resend plans, and how many records each plan folder holds
    (None for a plan folder that is not there)."""
    from ccversions import grade

    records, found = [], {}
    for name in PLANS:
        folder = Path(raw_dir) / name / "asks"
        if not folder.is_dir():
            found[name] = None
            continue
        recs = grade.load_records(Path(raw_dir) / name)
        found[name] = len(recs)
        records += recs
    return records, found


def counted(r: dict) -> str | None:
    """Why a record or row of this group's plans is left out, or None when it counts."""
    if r.get("group") not in GROUPS:
        return f"group {r.get('group')!r} (this program reads {sorted(GROUPS)} only)"
    if not (r.get("unit") or "").startswith("item:"):
        return f"unit {r.get('unit')!r} is not an item"
    if r.get("warmup") or not r.get("scored"):
        return "a warm-up or an ask that is not scored"
    if r.get("version") != VERSION:
        return f"version {r.get('version')} (this group asks on {VERSION})"
    return None


def pick_raw(records: list[dict]) -> tuple[list[dict], list[dict]]:
    kept, left = [], []
    for r in records:
        why = counted(r)
        if why:
            left.append({"plan": r.get("plan"), "ask_id": r.get("ask_id"), "why": why})
        else:
            kept.append(r)
    return kept, left


def grade_dsp(records: list[dict], settings_file: Path) -> list[dict]:
    """grade.py on this group's records, with what its settings file names (the author's code, the item file)."""
    from ccversions import grade, items as items_mod, settings as settings_mod

    s = settings_mod.load(str(settings_file))
    author_checks, claudecode = grade.import_author_graders(s.author_repo)
    inputs = items_mod.load(s.item_file, s.item_file_sha256, s.probe_file)
    return grade.grade_records(records, inputs, author_checks, claudecode)


def pick_rows(graded: list[dict]) -> tuple[dict, list[dict], list[str]]:
    """Graded rows of this group: resends in place of the asks they were sent for, then one list per way.
    Returns ({letter: rows}, rows left out with why, warnings)."""
    rows = analyze.apply_resends(graded)
    by = {x: [] for x in LETTERS}
    left, seen, warnings = [], {}, []
    for r in rows:
        why = counted(r)
        if why:
            left.append({"plan": r.get("plan"), "ask_id": r.get("ask_id"), "why": why})
            continue
        key = (r["group"], r["pass"], r["unit"])
        seen[key] = seen.get(key, 0) + 1
        by[GROUPS[r["group"]]].append(r)
    twice = sorted(k for k, n in seen.items() if n > 1)
    if twice:
        warnings.append(f"{len(twice)} item and pass pairs have more than one row in the same way (first: {twice[0]}). "
                        "Each way asks an item once per pass, so look at the records before reading the numbers")
    return by, left, warnings


def dsp_log_says_all_sent(settings_file: Path) -> bool | None:
    """Whether dsp.py's state file logs "all_passes_sent" (None when there is no state file)."""
    f = Path(settings_file).resolve().parent / "state.json"
    if not f.is_file():
        return None
    log = json.loads(f.read_text()).get("log") or []
    return any(e.get("what") == "all_passes_sent" for e in log)


# ------------------------------------------------------------------------------------ the other two sides

def main_rows_on(main: "analyze.Main", version: str) -> list[dict]:
    """main's asks on one version in the cells that count, on every item (desktop_vs_cli.main_rows_of keeps
    the Desktop group's 77 items only)."""
    vi = main.versions.index(version)
    return [main.cell[ui, pi, vi] for ui in range(len(main.units)) for pi in range(len(main.passes))
            if main.complete[ui, pi]]


def desktop_rows_of(graded: list[dict]) -> list[dict]:
    return [r for r in graded if r.get("group") == dvc.GROUP and (r.get("unit") or "").startswith("item:")
            and r.get("unit") not in NOT_DELIVERABLE and r.get("version") == VERSION]


def round3_items(rows: list[dict]) -> int:
    return len({r.get("unit") for r in rows if r.get("pass") == 3})


def look_allowed(desktop_round3_items: int, now: datetime) -> str | None:
    """Section 16: this group's answers are graded and looked at once the Desktop group's round 3 is sent or
    11:10 on 13 November in Melbourne has passed. None when that holds, else why not."""
    if desktop_round3_items >= DESKTOP_ITEMS or now >= LOOK_FROM:
        return None
    return (f"the Desktop group's round 3 has {desktop_round3_items} of {DESKTOP_ITEMS} items and it is "
            f"{now.astimezone(timezone.utc).isoformat(timespec='minutes')} UTC. Section 16: this group's answers are "
            f"graded and looked at only once that round is sent or after {LOOK_FROM.isoformat(timespec='minutes')} "
            "UTC (11:10 on 13 November in Melbourne)")


# ------------------------------------------------------------------------------------ the arithmetic

def compare(a_rows: list[dict], b_rows: list[dict], metric: str, effect: str, *, parts: str | None = None,
            with_p: bool = False, shuffles: int = common.SHUFFLES, draws: int = common.DRAWS) -> dict:
    """a minus b, item by item. parts: "same_pass" (pass k of a against pass k of b) or "against_mean" (pass k
    of a against the mean of b's passes), for the sign check of section 15."""
    A, B = analyze._item_means(a_rows, metric), analyze._item_means(b_rows, metric)
    units = sorted(set(A) & set(B))
    out = {"metric": metric, "effect": effect, "items": len(units),
           "a_passes": sorted({r["pass"] for r in a_rows}), "b_passes": sorted({r["pass"] for r in b_rows})}
    if not units:
        return {**out, "computable": False, "why": "no item that both sides have"}
    d = np.array([A[u] - B[u] for u in units])
    diff = float(d.mean())
    rng = np.random.default_rng(common.SEED)  # the same draws as analyze.paired
    boot = d[rng.integers(0, len(d), size=(draws, len(d)))].mean(axis=1)
    lo, hi = float(np.quantile(boot, 0.025)), float(np.quantile(boot, 0.975))
    out.update(computable=True, a_mean=float(np.mean([A[u] for u in units])),
               b_mean=float(np.mean([B[u] for u in units])), diff=diff, diff_shown=common.shown(diff, effect),
               range_95=[lo, hi], range_95_shown=[common.shown(lo, effect), common.shown(hi, effect)], draws=draws,
               a_asks_with_a_value=sum(1 for r in a_rows if not math.isnan(analyze.METRICS[metric](r))),
               b_asks_with_a_value=sum(1 for r in b_rows if not math.isnan(analyze.METRICS[metric](r))))
    if with_p:
        rng = np.random.default_rng(common.SEED)
        signs = rng.integers(0, 2, size=(shuffles, len(d))) * 2 - 1
        flipped = np.abs((signs * d).mean(axis=1))
        hits = int((flipped >= abs(diff) - 1e-12).sum())
        out.update(p=(1 + hits) / (1 + shuffles), sign_flips=shuffles)
    if parts:
        passes = sorted(set(out["a_passes"]) | (set(out["b_passes"]) if parts == "same_pass" else set()))
        res, sign_ok, checked = {}, True, 0
        for p in passes:
            Ap = analyze._item_means([r for r in a_rows if r["pass"] == p], metric)
            Bp = analyze._item_means([r for r in b_rows if r["pass"] == p], metric) if parts == "same_pass" else B
            up = sorted(set(Ap) & set(Bp))
            if not up:
                res[str(p)] = {"items": 0, "counts_for_sign": False,
                               "why_not_in_the_sign_check": "no item that both sides have in this pass"}
                continue
            dp = float(np.mean([Ap[u] - Bp[u] for u in up]))
            in_check = len(up) / len(units) >= common.MIN_SHARE_FOR_SIGN
            res[str(p)] = {"items": len(up), "diff": dp, "shown": common.shown(dp, effect), "counts_for_sign": in_check}
            if not in_check:
                res[str(p)]["why_not_in_the_sign_check"] = "fewer than half the items of the comparison"
            checked += in_check
            if in_check and np.sign(dp) != np.sign(diff):
                sign_ok = False
        out.update(parts_are=parts, passes=res, passes_in_the_sign_check=checked,
                   same_sign_every_pass=bool(sign_ok and checked > 0))
    out["per_item"] = {u: {"a": A[u], "b": B[u], "diff": float(A[u] - B[u])} for u in units}
    return out


def word(r: dict) -> dict:
    """Section 15's three wordings on a comparison computed with p and parts."""
    if not r.get("computable"):
        return {**r, "wording": None, "wording_name": "not computable"}
    big = common.big_enough(r["diff"], r["effect"])
    w = common.wording(r["p"], big, r["same_sign_every_pass"])
    return {**r, "big_enough": big, "wording": w, "wording_name": common.WORDING[w],
            "not_larger_than": common.not_larger_than(r["range_95"], r["effect"])}


SIZE_KEYS = ("metric", "effect", "items", "a_passes", "b_passes", "computable", "why", "a_mean", "b_mean", "diff",
             "diff_shown", "range_95", "range_95_shown", "draws", "a_asks_with_a_value", "b_asks_with_a_value",
             "per_item")
CHECK_KEYS = ("p", "sign_flips", "parts_are", "passes", "passes_in_the_sign_check", "same_sign_every_pass",
              "big_enough", "wording", "wording_name")


def way_summary(rows: list[dict], items: int) -> dict:
    by_pass = {}
    for r in rows:
        b = by_pass.setdefault(r["pass"], {"asks": 0, "items": set(), "scored": 0})
        b["asks"] += 1
        b["items"].add(r["unit"])
        b["scored"] += r.get("outcome") == "scored"
    passes = {str(p): {"asks": b["asks"], "items": len(b["items"]), "scored": b["scored"],
                       "complete": len(b["items"]) >= items} for p, b in sorted(by_pass.items())}
    return {"asks": len(rows), "passes_with_asks": len(passes),
            "complete_passes": sum(1 for x in passes.values() if x["complete"]), "items_in_a_complete_pass": items,
            "by_pass": passes, "outcomes": dvc._outcomes(rows) if rows else {}}


def analyse(dsp_graded: list[dict], main_rows_all: list[dict], desktop_graded: list[dict], versions: list[str], *,
            shuffles: int = common.SHUFFLES, draws: int = common.DRAWS) -> dict:
    by, left, warnings = pick_rows(dsp_graded)
    main, refused = common.main_group(main_rows_all, versions)
    cli = main_rows_on(main, VERSION) if VERSION in main.versions else []
    desk = desktop_rows_of(desktop_graded)
    rep = {"format": "desktop-prompt-v1", "version": VERSION,
           "rule": {"seed": common.SEED, "shuffles": shuffles, "draws": draws, "clear_p": common.CLEAR_P,
                    "lean_p": common.LEAN_P, "min_diff_accuracy": common.MIN_DIFF_ACCURACY,
                    "min_ratio_thinking": common.MIN_RATIO_THINKING,
                    "min_share_of_items_for_a_pass_in_the_sign_check": common.MIN_SHARE_FOR_SIGN,
                    "items_left_out_of_comparison_6": list(NOT_DELIVERABLE)},
           "ways": {x: {"group": GROUP_OF[x], **way_summary(by[x], ITEMS)} for x in LETTERS},
           "dsp_rows_left_out": left,
           "main": {"versions_refused_by_the_server": refused, "passes": main.passes,
                    **way_summary(cli, ITEMS)},
           "desktop": way_summary(desk, DESKTOP_ITEMS),
           "warnings": list(warnings), "comparisons": []}
    if VERSION not in main.versions:
        rep["main"]["why_not_computable"] = (f"{VERSION} is not among main's versions"
                                             + (" (refused by the server)" if VERSION in refused else ""))
    sides = {("main", None): cli, ("desktop", None): desk, **{("dsp", x): by[x] for x in LETTERS}}
    reminder_from = []
    for c in COMPARISONS:
        a, b = sides[c["a"]], sides[c["b"]]
        if c.get("items") == "desktop":
            a = [r for r in a if r["unit"] not in NOT_DELIVERABLE]
            b = [r for r in b if r["unit"] not in NOT_DELIVERABLE]
        entry = {k: c[k] for k in ("id", "name", "question", "write")}
        entry["two_batches"] = bool(c.get("two_batches"))
        entry["metrics"] = {}
        for metric, effect, name in common.METRICS:
            if c["write"] == "wordings":
                r = word(compare(a, b, metric, effect, parts="same_pass", with_p=True, shuffles=shuffles, draws=draws))
            elif c.get("reminder_check"):
                full = word(compare(a, b, metric, effect, parts="against_mean", with_p=True, shuffles=shuffles,
                                    draws=draws))
                r = {k: full[k] for k in SIZE_KEYS if k in full}
                r["check_for_the_reminder"] = {k: full[k] for k in CHECK_KEYS if k in full}
            else:
                r = compare(a, b, metric, effect, shuffles=shuffles, draws=draws)
            r["name"] = name
            entry["metrics"][metric] = r
        m = entry["metrics"]
        if c["write"] == "wordings":
            entry["accuracy_wording"] = common.both_ways_of_counting(m["accuracy"], m["accuracy_bad_as_wrong"])
            entry["thinking_wording"] = {"wording": m["log_thinking"].get("wording"),
                                         "wording_name": m["log_thinking"].get("wording_name")}
            entry["what_differs"] = WHAT_DIFFERS[c["id"]]
        if c.get("reminder_check"):
            chk = {k: m[k]["check_for_the_reminder"] | {"diff": m[k].get("diff")} for k in m if m[k].get("computable")}
            if len(chk) < len(m):
                entry["reminder_check"] = {"computable": False, "why": "comparison 5 could not be computed on every "
                                           "metric, so whether the reminder applies is not known"}
                rep["warnings"].append(entry["reminder_check"]["why"])
            else:
                acc = common.both_ways_of_counting(chk["accuracy"], chk["accuracy_bad_as_wrong"])
                think = chk["log_thinking"]["wording"]
                if acc["wording"] == 1:
                    reminder_from.append("accuracy")
                if think == 1:
                    reminder_from.append("thinking")
                entry["reminder_check"] = {"computable": True, "accuracy_both_ways": acc["wording_name"],
                                           "thinking": common.WORDING[think], "reaches_clear": bool(reminder_from)}
        rep["comparisons"].append(entry)
    rep["reminder"] = {"applies": bool(reminder_from), "from": reminder_from,
                       "text": REMINDER.format(which=" and ".join(reminder_from)) if reminder_from else None,
                       "on_comparisons": [c["id"] for c in COMPARISONS if c.get("two_batches")]}
    for entry in rep["comparisons"]:
        if reminder_from and entry["two_batches"]:
            entry["reminder"] = rep["reminder"]["text"]
    short = [x for x in LETTERS if rep["ways"][x]["complete_passes"] < 3]
    if short:
        def asks(x):
            return ", ".join(f"{k}: {v['asks']}" for k, v in rep["ways"][x]["by_pass"].items()) or "none"
        rep["warnings"].append("ways with fewer than three complete passes: " + ". ".join(
            f"{x} has {rep['ways'][x]['complete_passes']} complete (asks by pass {asks(x)})" for x in short)
            + ". Section 16: what was sent counts, and the comparisons use the passes each way has")
    return rep


# ------------------------------------------------------------------------------------ outputs

def _passes_line(label: str, s: dict, word_pass: str = "pass") -> str:
    by = ", ".join(f"{k}: {v['asks']}" for k, v in s["by_pass"].items()) or "none"
    n = s["passes_with_asks"]
    plural = word_pass if n == 1 else word_pass + ("es" if word_pass == "pass" else "s")
    return (f"- {label}: {n} {plural} with asks, "
            f"{s['complete_passes']} of them with all {s['items_in_a_complete_pass']} items. "
            f"Asks by {word_pass}: {by}. Outcomes {s['outcomes']}.")


def report_text(rep: dict) -> str:
    L = ["# The desktop prompt group (design file 判断标准.md, section 16)", ""]
    for w in rep.get("warnings") or []:
        L += [f"WARNING: {w}", ""]
    L += ["## How many passes each side actually has", ""]
    for x in LETTERS:
        L.append(_passes_line(f"{x} ({rep['ways'][x]['group']})", rep["ways"][x]))
    L.append(_passes_line(f"main on {VERSION}, in the cells that count", rep["main"]))
    L.append(_passes_line(f"Desktop group ({DESKTOP_ITEMS} items)", rep["desktop"], "round"))
    if rep["main"].get("why_not_computable"):
        L.append(f"- main: {rep['main']['why_not_computable']}")
    L.append("")
    for c in rep["comparisons"]:
        L += [f"## {c['id']}. {c['name']}: {c['question']}", "",
              "Written in section 15's three wordings." if c["write"] == "wordings"
              else "Difference and range only (section 16).", ""]
        for metric, r in c["metrics"].items():
            unit = "points" if r["effect"] == "diff" else "per cent"
            L.append(f"### {r['name']}")
            if not r.get("computable"):
                L += [f"- not computable: {r.get('why')}", ""]
                continue
            L.append(f"- {c['name']}: {common.pct(r['diff_shown'])} {unit} on {r['items']} items (95% range "
                     f"{common.pct(r['range_95_shown'][0])} to {common.pct(r['range_95_shown'][1])}). Passes used: "
                     f"{r['a_passes']} against {r['b_passes']}")
            if c["write"] == "wordings":
                L += [f"- p = {r['p']:.4f} over {r['sign_flips']} sign flips",
                      "- each pass: " + ", ".join(
                          f"pass {k} {common.pct(x.get('shown'))} on {x['items']} items"
                          + ("" if x["counts_for_sign"] else " (not in the sign check)") for k, x in r["passes"].items()),
                      f"- size enough: {r['big_enough']}, same sign in every pass: {r['same_sign_every_pass']}",
                      f"- wording: {r['wording_name']}"
                      + (f" (no difference larger than {common.pct(r['not_larger_than'])} {unit} was seen)"
                         if r["wording"] == 3 else "")]
            L.append("")
        if c["write"] == "wordings":
            aw, tw = c["accuracy_wording"], c["thinking_wording"]
            L += [f"Accuracy, both ways of counting together: {aw['wording_name']} ({aw.get('note')}).",
                  f"Thinking: {tw['wording_name']}.", ""]
            clear = [what for what, w in (("accuracy", aw.get("wording")), ("thinking", tw.get("wording"))) if w == 1]
            if clear:
                L += [f"{' and '.join(clear).capitalize()}: {CLEAR_NOTE}",
                      f"What differs between the two sides: {c['what_differs']}", ""]
            for what, w in (("accuracy", aw.get("wording")), ("thinking", tw.get("wording"))):
                if w == 2:
                    L += [f"{what.capitalize()}: {LEAN_NOTE}", ""]
                elif w == 3:
                    r = c["metrics"]["log_thinking" if what == "thinking" else "accuracy"]
                    if what == "accuracy":
                        nl = [c["metrics"][m]["not_larger_than"] for m in ("accuracy", "accuracy_bad_as_wrong")
                              if c["metrics"][m].get("not_larger_than") is not None]
                        x = max(nl) if nl else None
                    else:
                        x = r.get("not_larger_than")
                    unit = "per cent" if what == "thinking" else "points"
                    L += [f"{what.capitalize()}: no difference larger than {common.pct(x)} {unit} was seen.", ""]
        if c.get("reminder_check"):
            rc = c["reminder_check"]
            if rc.get("computable"):
                L += [f"Checked against section 15's line for clear, for the reminder below: accuracy both ways "
                      f"{rc['accuracy_both_ways']}, thinking {rc['thinking']}. The numbers of that check are in "
                      "report.json.", ""]
            else:
                L += [f"Check for the reminder: {rc['why']}.", ""]
        if c.get("reminder"):
            L += [c["reminder"], ""]
    return "\n".join(L) + "\n"


def write_outputs(rep: dict, out: Path, dsp_graded_here: list[dict] | None) -> None:
    out.mkdir(parents=True, exist_ok=True)
    if dsp_graded_here is not None:
        from ccversions import grade
        grade.write_outputs(dsp_graded_here, out / "graded")
    common.write_json(out / "report.json", rep)
    (out / "report.md").write_text(report_text(rep))


def main(argv=None, now: datetime | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--graded", action="append", help="a graded.jsonl of the run (default: every one under 正式跑/graded)")
    ap.add_argument("--dsp-graded", action="append", help="a graded.jsonl of this group (default: grade the raw records)")
    ap.add_argument("--dsp-settings", help=f"this group's settings file (default: {DSP_SETTINGS})")
    ap.add_argument("--desktop-asks", help=f"the Desktop group's records (default: {common.DESKTOP_ASKS})")
    ap.add_argument("--desktop-graded", action="append",
                    help="the Desktop group's graded rows as desktop_vs_cli.py wrote them (default: grade the records)")
    ap.add_argument("--versions-file", help="default: the versions file the run's settings name")
    ap.add_argument("--settings", help=f"the run's settings file (default: {common.SETTINGS_FILE})")
    ap.add_argument("--out", help=f"default: {common.OUT_DEFAULT}")
    ap.add_argument("--shuffles", type=int, default=common.SHUFFLES)
    ap.add_argument("--draws", type=int, default=common.DRAWS)
    ap.add_argument("--allow-unfinished", action="store_true",
                    help="read the run's graded rows although its final step has not run")
    ap.add_argument("--allow-partial-round3", action="store_true",
                    help="go on although the Desktop group's round 3 has some asks but not all")
    args = ap.parse_args(argv)
    now = now or datetime.now(timezone.utc)
    if args.graded:
        files = [Path(x) for x in args.graded]
    else:
        if not common.formal_finished() and not args.allow_unfinished:
            print(f"not run: {common.FORMAL_FINAL_REPORT} does not exist yet, so the registered run has not graded "
                  "all its passes. Start again when it has, or give --allow-unfinished.")
            return 2
        files = common.default_graded_files()
    if not files:
        print("not run: no graded.jsonl of the run found")
        return 2
    settings_file = Path(args.settings) if args.settings else None
    # the Desktop group first: whether round 3 is in decides whether this group may be graded yet
    if args.desktop_graded:
        desk_graded = analyze.load_rows([Path(x) for x in args.desktop_graded])
        r3 = round3_items(desktop_rows_of(desk_graded))
        desk_source = {"graded_files": args.desktop_graded}
        kept = None
    else:
        folder = Path(args.desktop_asks) if args.desktop_asks else common.DESKTOP_ASKS
        records = dvc.load_records(folder)
        kept, left = dvc.pick(records, VERSION)
        problem = dvc.rounds_problem(kept)
        if problem and not args.allow_partial_round3:
            print(f"not run: Desktop group: {problem}")
            return 2
        r3 = round3_items(kept)
        desk_source = {"records_folder": str(folder), "read": len(records), "kept": len(kept), "left_out": left,
                       "partial_round3_allowed": bool(problem)}
    why = look_allowed(r3, now)
    if why:
        print(f"not run: {why}")
        return 2
    if kept is not None:
        desk_graded = dvc.grade_records(kept, settings_file)
    dsp_settings = Path(args.dsp_settings) if args.dsp_settings else DSP_SETTINGS
    graded_here = None
    if args.dsp_graded:
        dsp_graded = analyze.load_rows([Path(x) for x in args.dsp_graded])
        dsp_source = {"graded_files": args.dsp_graded}
        all_sent = None
    else:
        from ccversions import settings as settings_mod
        raw_dir = settings_mod.load(str(dsp_settings)).raw_dir
        records, found = load_dsp_records(raw_dir)
        kept_dsp, left_dsp = pick_raw(records)
        if not kept_dsp:
            print(f"not run: no record of this group's passes under {raw_dir} (plan folders {found})")
            return 2
        dsp_graded = graded_here = grade_dsp(kept_dsp, dsp_settings)
        all_sent = dsp_log_says_all_sent(dsp_settings)
        dsp_source = {"raw_dir": str(raw_dir), "plan_folders": found, "records_read": len(records),
                      "records_kept": len(kept_dsp), "records_left_out": left_dsp,
                      "dsp_log_says_all_passes_sent": all_sent}
    versions = common.load_versions(settings_file, Path(args.versions_file) if args.versions_file else None)
    rep = analyse(dsp_graded, analyze.load_rows(files), desk_graded, versions, shuffles=args.shuffles, draws=args.draws)
    if all_sent is False:
        rep["warnings"].insert(0, "dsp.py's log has no all_passes_sent: the group stopped part way, or it is still "
                                  "being sent. If it is still being sent, run this again once it has ended")
    rep["sources"] = {"main_graded_files": [str(f) for f in files], "dsp": dsp_source, "desktop": desk_source,
                      "now_utc": now.astimezone(timezone.utc).isoformat(timespec="seconds")}
    out = (Path(args.out) if args.out else common.OUT_DEFAULT) / OUT_NAME
    write_outputs(rep, out, graded_here)
    print(f"written: {out}")
    for c in rep["comparisons"]:
        if c["write"] == "wordings":
            print(f"{c['id']}. {c['name']}: accuracy {c['accuracy_wording']['wording_name']}, "
                  f"thinking {c['thinking_wording']['wording_name']}")
    if rep["reminder"]["applies"]:
        print(f"reminder on comparisons {rep['reminder']['on_comparisons']}: E differs clearly from main "
              f"({', '.join(rep['reminder']['from'])})")
    for w in rep["warnings"]:
        print(f"WARNING: {w}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
