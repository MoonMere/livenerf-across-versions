"""The two tests and the reported numbers of the group swap (PREREGISTRATION.md, change log, entry of
14 November 2026: the two sentences that changed at 2.1.317 are swapped between 2.1.316 and 2.1.317).

    python -B analysis.py --settings <settings .toml> --out <folder> --stage1     after passes 1 to S
    python -B analysis.py --settings <settings .toml> --out <folder>              at the end

    more options: --raw-dir, --graded-dir, --plans-dir, --units, --passes, --stage1-passes, --ways,
                  --stage1-decision, --main-graded <graded.jsonl> (repeated), --high-recheck-graded (repeated)

It grades the asks on disk with the LiveNerf author's graders (ccversions.grade, unchanged) and writes its
report into --out. Only the plans named SW<n> (pass n) and SW<n>r (the asks of pass n that never reached
the model, asked once more) are read, from --raw-dir (by default the raw_dir of the settings). Every other
plan in that folder (the probes, the trial batch SWS, the outage probes) is left unread.

Two stages. Stage 1 is passes 1 to S, the whole group is passes 1 to P. S and P are stage1_passes and
passes in [group] of the settings file (6 and 12 when they are not there).

    --stage1    Reads passes 1 to S only. Refuses, and says which pass, when one of them is not complete:
                its plan file is missing, an ask of its plan or of its resend plan has no record, or an ask
                that never reached the model was not asked once more. Writes stage1_decision.json,
                stage1_report.json and stage1_report.txt, prints the report and then a last line
                "STAGE1 stop" or "STAGE1 continue". Stop when both p by pairs are 0.01 or less, or when one
                is 0.01 or less and the other above 0.10. Otherwise continue.
    at the end  Reads stage1_decision.json (in --out unless --stage1-decision names it). Stop: reads
                passes 1 to S, declares a test when its p by pairs is 0.01 or less, and stops with an error
                when the records hold a plan of a later pass. Continue, or no decision file (the report
                says so): reads passes 1 to P and declares at 0.04. Writes report.json and report.txt and
                prints the report. A group that was cut short is computed all the same, and the report opens
                with which passes are complete.

Cells. A cell is one program (2.1.316 or 2.1.317) with one way of asking: sw_o (the text that holds the two
sentences of 2.1.316), sw_w (the text that holds those of 2.1.317), and sw_n (asked as main asks) when the
passes send it. The ways are --ways, else scored_groups in [group] of the settings (sw_o and sw_w when the
key is not there, as in swap.py). They must be the ways of the asks in the pass plans (in --plans-dir, by
default the folder plans next to the settings file, where swap.py keeps them). Without a [group], the
ways are those of the pass plans, or those of the records when no plan file is there.

Which asks count. In each pass, a question counts only where every cell has a record of it (a record of
any outcome). Asks that were asked once more carry the pass of the ask they replace, so they sit in the
same cell. In the questions and passes that count, only asks with outcome "scored" have a value. The value
of an ask is ln(thinking tokens + 1) for thinking and its score (1 right, 0 wrong) for accuracy.

One comparison works on pairs of asks. A pair counts when both of its asks have a value. D is the later
ask's value minus the earlier ask's. Each comparison cuts its pairs into layers. A question's figure is
the mean of its mean D in each layer. A question with no pair in one of the layers is left out of that
comparison and named. T is the mean of the questions' figures.

    p by pairs      each pair's D changes sign with chance one half, 10,000 times, seed 20261111.
                    p = (draws whose T is at least as far from zero as the real T, plus 1) / 10,001.
    p by questions  the same with each question's figure changing sign
    range           the questions redrawn with replacement 10,000 times, seed 20261111: the middle 95% of T

Thinking is shown as exp(T) - 1, the change in the geometric mean, with exp(range) - 1. Accuracy is
shown as T times 100, in points, with the range times 100.

The two tests, on thinking only, declared at the line of the stage (0.01 or 0.04):

    test 1, the sentences   sw_o then sw_w, same question, pass and program, with a layer per program
    test 2, the program     2.1.316 then 2.1.317, same question, pass and way, the ways sw_o and sw_w
                            only, with a layer per way

Reported with no declaration, each on thinking and on accuracy: test 1 and test 2 on accuracy, 2.1.316 sw_o
then 2.1.317 sw_w (the two cells that send their own sentences), test 1 on each program alone, test 2 on
each way alone, and when sw_n was sent, sw_n on 2.1.316 then on 2.1.317 and sw_n then the other text on
each program. Also: the two cells with their own sentences split into test 1 plus test 2, each test and
those two cells with one question left out at a time, a row for each cell, the figures of each question
with its zero-thinking and scored asks in each cell, a row for each set of config folders, a row for each
config folder, accuracy scored the two more ways of rescore.py of the two groups of 13 November (its lists
and its rescoring, as they are), and beside the two cells with their own sentences the same comparison on
the graded rows of main or high_recheck when those are given.
"""

import argparse
import json
import math
import re
import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

OLD, NEW = "2.1.316", "2.1.317"
PROGRAMS = (OLD, NEW)
ALL_WAYS = ("sw_n", "sw_o", "sw_w")
DEFAULT_WAYS = ("sw_o", "sw_w")
FOUR = tuple((v, w) for v in PROGRAMS for w in DEFAULT_WAYS)  # the four cells the two tests are made of
SEED = 20261111
DRAWS = 10_000
CHUNK = 1_000  # draws at a time, to keep memory small
STAGE1_PASSES, PASSES = 6, 12  # used when [group] of the settings has no stage1_passes or passes
STOP_AT = 0.01  # stage 1: stop when both p are at most this, or one is and the other is above OTHER_ABOVE
OTHER_ABOVE = 0.10
LINE_STOP = 0.01  # the line of the two tests when stage 1 stopped the group
LINE_CONTINUE = 0.04  # the line when both stages were sent
PLAN_NAME = re.compile(r"SW([1-9][0-9]*)(r?)")
RECHECK_FOLDERS = ("再验少想", "recheck")  # where rescore.py is, next to this folder
NO_SET = "(probe folder)"  # what swap.py writes as the set of an ask outside the worker folders

# A layer is (name, earlier cell, later cell). A cell is (version, group).
TEST_1 = (("2.1.316", (OLD, "sw_o"), (OLD, "sw_w")), ("2.1.317", (NEW, "sw_o"), (NEW, "sw_w")))
TEST_2 = (("sw_o", (OLD, "sw_o"), (NEW, "sw_o")), ("sw_w", (OLD, "sw_w"), (NEW, "sw_w")))
OWN = (("2.1.316 sw_o then 2.1.317 sw_w", (OLD, "sw_o"), (NEW, "sw_w")),)
REPORTED = {
    "own_sentences_two_cells": OWN,
    "test_1_on_2.1.316_alone": (TEST_1[0],),
    "test_1_on_2.1.317_alone": (TEST_1[1],),
    "test_2_on_sw_o_alone": (TEST_2[0],),
    "test_2_on_sw_w_alone": (TEST_2[1],),
}
REPORTED_WITH_SW_N = {
    "original_two_cells": (("sw_n", (OLD, "sw_n"), (NEW, "sw_n")),),
    "the_swap_itself_on_2.1.316": (("2.1.316", (OLD, "sw_n"), (OLD, "sw_o")),),
    "the_swap_itself_on_2.1.317": (("2.1.317", (NEW, "sw_n"), (NEW, "sw_w")),),
}
WHAT_IS_COMPARED = {
    "test_1": "sw_o then sw_w, same question, pass and program, a layer per program",
    "test_2": "2.1.316 then 2.1.317, same question, pass and way (sw_o, sw_w), a layer per way",
    "own_sentences_two_cells": "2.1.316 sw_o then 2.1.317 sw_w, same question and pass",
    "test_1_on_2.1.316_alone": "test 1, the pairs of 2.1.316 only",
    "test_1_on_2.1.317_alone": "test 1, the pairs of 2.1.317 only",
    "test_2_on_sw_o_alone": "test 2, the pairs of sw_o only",
    "test_2_on_sw_w_alone": "test 2, the pairs of sw_w only",
    "original_two_cells": "sw_n on 2.1.316 then sw_n on 2.1.317, same question and pass",
    "the_swap_itself_on_2.1.316": "sw_n then sw_o on 2.1.316, same question and pass",
    "the_swap_itself_on_2.1.317": "sw_n then sw_w on 2.1.317, same question and pass",
}


class AnalysisError(RuntimeError):
    pass


# ---------------------------------------------------------------- values of one ask

def lthink(r: dict) -> float | None:
    t = r.get("thinking_tokens")
    return None if t is None else math.log(float(t) + 1.0)


def correct(r: dict) -> float | None:
    s = r.get("score")
    return None if s is None else float(s)


def cell_name(cell: tuple) -> str:
    return f"{cell[0]} {cell[1]}"


def cells_of(ways) -> tuple:
    return tuple((v, w) for v in PROGRAMS for w in ways)


def ask_set(r: dict):
    """The set of worker folders an ask used: "set" in the record's field "swap", else the config_set of
    the ask's options (the graded rows carry the options, and swap.py puts the set there)."""
    s = (r.get("swap") or {}).get("set")
    if s in (None, NO_SET):
        s = (r.get("options") or {}).get("config_set")
    return s


# ---------------------------------------------------------------- which plans are read

def plan_names(raw_dir: Path) -> list[str]:
    """The plan folders that count, in pass order (SW<n>, then SW<n>r). Nothing else is listed."""
    found = []
    if raw_dir.is_dir():
        for p in raw_dir.iterdir():
            m = PLAN_NAME.fullmatch(p.name)
            if m and p.is_dir():
                found.append((int(m.group(1)), m.group(2), p.name))
    return [name for _, _, name in sorted(found)]


def plan_number(name: str) -> int:
    return int(PLAN_NAME.fullmatch(name).group(1))


def load_rows(raw_dir: Path, grade_plan, last: int | None = None) -> tuple[list[dict], dict, list[str], dict]:
    """The graded rows of the plans that count, up to pass `last`. grade_plan(name) gives the graded rows of
    one plan, or None when the plan has no asks yet. It is called for those plans only. Returns the rows,
    the counts of each plan read, the names of the plans after `last` (not read), and for each plan read
    its ask ids, the ids of its asks that never reached the model and the ids its asks were asked in
    place of."""
    rows, plans, beyond, detail = [], {}, [], {}
    for name in plan_names(raw_dir):
        n = plan_number(name)
        if last is not None and n > last:
            beyond.append(name)
            continue
        got = grade_plan(name)
        if got is None:
            continue
        plans[name] = {"rows": len(got), "rows_whose_pass_is_not_the_plans": sum(r.get("pass") != n for r in got)}
        detail[name] = {"ids": {str(r.get("ask_id")) for r in got},
                        "never_reached": {str(r.get("ask_id")) for r in got if r.get("never_reached_model")},
                        "resend_of": {str((r.get("resend_of") or {}).get("ask_id")) for r in got if r.get("resend_of")}}
        rows += got
    return rows, plans, beyond, detail


def read_plan(plans_dir: Path | None, name: str) -> dict | None:
    f = plans_dir / f"{name}.json" if plans_dir else None
    return json.loads(f.read_text()) if f is not None and f.is_file() else None


def ways_in_use(plans_dir: Path | None, numbers, rows: list[dict], given=None,
                given_from: str = "--ways") -> tuple[tuple, str]:
    """The ways the passes send: the given ones (--ways, or scored_groups in [group] of the settings),
    else the groups of the asks in the pass plans, else the groups of the records. Given ways that are
    not the groups of the pass plans stop the program. sw_o and sw_w must be among the ways."""
    planned, found = set(), False
    for n in numbers:
        for name in (f"SW{n}", f"SW{n}r"):
            p = read_plan(plans_dir, name)
            if p is not None:
                found = True
                planned |= {a.get("group") for a in p.get("asks", [])}
    if given:
        seen, source = set(given), given_from
        if found and planned != seen:
            raise AnalysisError(f"{given_from} says the passes send {sorted(seen)}, the pass plans send {sorted(planned)}")
    elif found:
        seen, source = planned, "the pass plans"
    else:
        seen = {r.get("group") for r in rows if r.get("version") in PROGRAMS}
        source = "the records (no plan file found)"
    ways = tuple(w for w in ALL_WAYS if w in seen)
    if not given and not found and not rows:
        ways, source = DEFAULT_WAYS, "the default (no plan file and no record)"
    if set(seen) - set(ALL_WAYS):
        raise AnalysisError(f"{source} name ways this program does not know: {sorted(set(seen) - set(ALL_WAYS))}")
    if not set(DEFAULT_WAYS) <= set(ways):
        raise AnalysisError(f"the ways from {source} are {list(ways)}: sw_o and sw_w must both be sent")
    return ways, source


def pass_gaps(plans_dir: Path | None, numbers, detail: dict) -> dict:
    """For each pass, what shows that it is not complete yet. A complete pass has an empty list."""
    out = {}
    for n in numbers:
        problems = []
        for name in (f"SW{n}", f"SW{n}r"):
            plan = read_plan(plans_dir, name)
            if plan is None:
                if name == f"SW{n}":
                    problems.append(f"no plan file {name}.json")
                continue
            have = detail.get(name, {}).get("ids", set())
            missing = [a["ask_id"] for a in plan.get("asks", []) if str(a.get("ask_id")) not in have]
            if missing:
                problems.append(f"{len(missing)} of the {len(plan.get('asks', []))} asks of {name} have no record")
        due = detail.get(f"SW{n}", {}).get("never_reached", set()) - detail.get(f"SW{n}r", {}).get("resend_of", set())
        if due:
            problems.append(f"{len(due)} asks of SW{n} never reached the model and were not asked once more")
        out[str(n)] = problems
    return out


# ---------------------------------------------------------------- which asks count

def counted(rows: list[dict], ways=DEFAULT_WAYS) -> tuple[dict, set, dict, dict]:
    """The scored asks that count, and what was left out.

    Returns slots {(question, pass, version, group): [scored asks]} over the (pass, question) cells that
    every cell has a record of, the set of those (pass, question) cells, {(pass, question): the cells
    with a record}, and the counts the report gives (section 2 of the requirements).
    """
    cells = cells_of(ways)
    mine = [r for r in rows if r.get("group") in ways and r.get("version") in PROGRAMS
            and str(r.get("unit", "")).startswith("item:")]
    have: dict = {}
    for r in mine:
        have.setdefault((r["pass"], r["unit"]), set()).add((r["version"], r["group"]))
    full = {c for c, s in have.items() if all(x in s for x in cells)}
    slots: dict = {}
    for r in mine:
        if (r["pass"], r["unit"]) in full and r.get("outcome") == "scored":
            slots.setdefault((r["unit"], r["pass"], r["version"], r["group"]), []).append(r)

    def by_cell(rs):
        out = {cell_name(c): {} for c in cells}
        for r in rs:
            o = out[cell_name((r["version"], r["group"]))]
            key = str(r.get("outcome"))
            o[key] = o.get(key, 0) + 1
        return out

    sets: dict = {}
    for r in mine:
        if (r["pass"], r["unit"]) in full:
            sets.setdefault((r["pass"], r["unit"]), set()).add(str(ask_set(r)))
    info = {"records": len(mine), "rows_read_that_are_not_of_the_cells": len(rows) - len(mine),
            "cells": len(have), "cells_with_every_cell": len(full),
            "scored_asks_that_count": sum(len(a) for a in slots.values()),
            "records_by_cell_and_outcome": by_cell(mine),
            "records_by_cell_and_outcome_in_cells_with_every_cell": by_cell(
                [r for r in mine if (r["pass"], r["unit"]) in full]),
            "asks_of_one_cell_question_and_pass_beyond_the_first_scored_one": sum(len(a) - 1 for a in slots.values()),
            "scored_asks_without_thinking_tokens": sum(r.get("thinking_tokens") is None for a in slots.values() for r in a),
            "question_passes_in_more_than_one_set": sorted(f"pass {p} {u}" for (p, u), s in sets.items() if len(s) > 1)}
    return slots, full, have, info


def pass_completeness(have: dict, full: set, numbers, units=None, gaps: dict | None = None) -> dict:
    """Which passes are complete: each question (the given ones, else those seen in the group) has every
    cell in the pass, and nothing in pass_gaps() says otherwise."""
    every = set(units) if units else {u for _, u in have}
    out = {}
    for p in numbers:
        seen = {u for q, u in have if q == p}
        done = {u for q, u in full if q == p}
        problems = (gaps or {}).get(str(p), [])
        out[str(p)] = {"questions_with_a_record": len(seen), "questions_with_every_cell": len(done & every),
                       "questions_expected": len(every), "questions_not_complete": sorted(every - done),
                       "plan_problems": problems, "complete": bool(every) and every <= done and not problems}
    return {"passes": out, "all_complete": bool(out) and all(x["complete"] for x in out.values()),
            "questions_from": "the questions given" if units else "the questions seen in the group",
            "plans_checked": gaps is not None}


def slot_values(slots: dict, value, units=None) -> dict:
    """{(question, pass, version, group): the mean value of its scored asks}, for the slots with a value.
    A slot normally holds one scored ask. If it holds more, their mean is its value, and the report
    counts the asks beyond the first."""
    out = {}
    for k, asks in slots.items():
        if units is not None and k[0] not in units:
            continue
        xs = [x for x in (value(r) for r in asks) if x is not None]
        if xs:
            out[k] = sum(xs) / len(xs)
    return out


def make_pairs(vals: dict, cells: set, layers) -> list[tuple[str, str, float]]:
    """(question, layer, D) for each (pass, question) cell and layer whose two asks both have a value."""
    out = []
    for p, u in sorted(cells):
        for name, a, b in layers:
            x, y = vals.get((u, p) + tuple(a)), vals.get((u, p) + tuple(b))
            if x is not None and y is not None:
                out.append((u, name, y - x))
    return out


# ---------------------------------------------------------------- one comparison

def sign_flip_p(c: np.ndarray, draws: int = DRAWS, seed: int = SEED) -> tuple[float, int]:
    """T = sum(c). Each entry of c changes sign with chance one half. Returns p and the number of draws
    whose T is at least as far from zero as the real T (the real T itself is the "plus 1")."""
    t = float(c.sum())
    rng = np.random.default_rng(seed)
    hits, done = 0, 0
    while done < draws:
        n = min(CHUNK, draws - done)
        signs = rng.integers(0, 2, size=(n, len(c))) * 2 - 1
        hits += int((np.abs(signs @ c) >= abs(t) - 1e-12).sum())
        done += n
    return (hits + 1) / (draws + 1), hits


def question_figures(pairs: list, layers: list[str], universe=()) -> tuple[list, dict, dict, dict]:
    """The questions that count (a pair in each layer), their figures, the D of each question and layer,
    and the questions left out with their pairs by layer."""
    by: dict = {}
    for u, layer, d in pairs:
        by.setdefault(u, {}).setdefault(layer, []).append(d)
    every = sorted(set(universe) | set(by))
    ok = [u for u in every if all(by.get(u, {}).get(layer) for layer in layers)]
    left_out = {u: {layer: len(by.get(u, {}).get(layer, [])) for layer in layers} for u in every if u not in ok}
    figures = {u: float(np.mean([np.mean(by[u][layer]) for layer in layers])) for u in ok}
    return ok, figures, by, left_out


def compare(pairs: list, layers: list[str], kind: str, universe=(), line: float | None = None,
            draws: int = DRAWS, seed: int = SEED) -> dict:
    """kind: "thinking" (values are ln(tokens + 1)) or "accuracy" (0 or 1). universe: the questions that
    could have taken part, so that a question with no pair at all is named as left out too. With a line,
    the comparison is declared when p by pairs is at most the line. Without one, "declared" is None."""
    ok, figures, by, left_out = question_figures(pairs, layers, universe)
    if not ok:
        return {"no_data": True, "kind": kind, "layers": list(layers), "questions_left_out": left_out, "line": line}
    q, n_layers = len(ok), len(layers)
    x = np.array([figures[u] for u in ok])
    t = float(x.mean())
    # T is a weighted sum of the D of the pairs: a pair in layer l of question u weighs 1 / (q * layers * n(u, l))
    c = np.array([d / (q * n_layers * len(by[u][layer])) for u in ok for layer in layers for d in by[u][layer]])
    p_pairs, hits_pairs = sign_flip_p(c, draws, seed)
    p_questions, hits_questions = sign_flip_p(x / q, draws, seed)
    rng = np.random.default_rng(seed)
    stats = x[rng.integers(0, q, size=(draws, q))].mean(1)
    low, high = float(np.percentile(stats, 2.5)), float(np.percentile(stats, 97.5))
    out = {"kind": kind, "layers": list(layers), "questions": q, "pairs": int(len(c)),
           "pairs_by_layer": {layer: sum(len(by[u][layer]) for u in ok) for layer in layers},
           "questions_left_out": left_out, "T": t, "range": [low, high],
           "range_crosses_zero": bool(low <= 0 <= high),  # zero inside the range or on one of its ends
           "p_by_pairs": p_pairs, "draws_at_least_as_far_by_pairs": hits_pairs,
           "p_by_questions": p_questions, "draws_at_least_as_far_by_questions": hits_questions, "draws": draws,
           "line": line, "declared": bool(p_pairs <= line) if line is not None else None,
           "direction": "T below zero" if t < 0 else "T above zero" if t > 0 else "T is zero",
           "question_figures": figures}
    if kind == "thinking":
        out["exp_T_minus_1"] = math.exp(t) - 1
        out["range_exp_minus_1"] = [math.exp(low) - 1, math.exp(high) - 1]
    else:
        out["points"] = t * 100
        out["range_points"] = [low * 100, high * 100]
    return out


def comparison(slots: dict, cells: set, layers, value, kind: str, universe=(), line: float | None = None,
               units=None) -> dict:
    vals = slot_values(slots, value, units)
    uni = [u for u in universe if units is None or u in units]
    return compare(make_pairs(vals, cells, layers), [name for name, _, _ in layers], kind, uni, line)


def leave_one_out(c: dict) -> dict:
    """T again with each question left out in turn: the lowest and the highest, and the questions without
    which T is less than half as far from zero as with all of them."""
    if c.get("no_data") or c["questions"] < 2:
        return {"no_data": True}
    f = c["question_figures"]
    q, total, t = len(f), sum(f.values()), c["T"]
    without = {u: (total - x) / (q - 1) for u, x in sorted(f.items())}
    lo = min(without, key=without.get)
    hi = max(without, key=without.get)
    return {"lowest": {"T": without[lo], "without": lo}, "highest": {"T": without[hi], "without": hi},
            "questions_without_which_T_is_below_half": sorted(u for u, x in without.items() if abs(x) < abs(t) / 2),
            "T_without_each": without}


def stage1_decision(p1: float, p2: float) -> str:
    """The rule of stage 1 on the two p by pairs."""
    if (p1 <= STOP_AT and p2 <= STOP_AT) or (p1 <= STOP_AT and p2 > OTHER_ABOVE) or (p2 <= STOP_AT and p1 > OTHER_ABOVE):
        return "stop"
    return "continue"


# ---------------------------------------------------------------- test 1 plus test 2

def decomposition(slots: dict, full: set, value, kind: str, draws: int = DRAWS, seed: int = SEED) -> dict:
    """On the (pass, question) cells where all four cells of the two tests have a value, the T of the two
    cells with their own sentences equals the T of test 1 plus the T of test 2, question by question.
    That is checked here (AnalysisError when it fails). Also each test's share of it, with the range from
    redrawing the questions (the same draws for all three)."""
    vals = slot_values(slots, value)
    quad = {(p, u) for p, u in full if all(vals.get((u, p) + c) is not None for c in FOUR)}
    if not quad:
        return {"no_data": True, "kind": kind}
    fig = {}
    for name, layers in (("own", OWN), ("test_1", TEST_1), ("test_2", TEST_2)):
        fig[name] = question_figures(make_pairs(vals, quad, layers), [n for n, _, _ in layers])[1]
    units = sorted(fig["own"])
    if not (units == sorted(fig["test_1"]) == sorted(fig["test_2"])):
        raise AnalysisError("decomposition: the three comparisons do not have the same questions")
    x = {k: np.array([fig[k][u] for u in units]) for k in fig}
    gap = np.abs(x["own"] - x["test_1"] - x["test_2"])
    if gap.max() > 1e-9 * max(1.0, float(np.abs(x["own"]).max())):
        worst = units[int(gap.argmax())]
        raise AnalysisError(f"decomposition: on {worst} the two cells give {fig['own'][worst]!r}, "
                            f"test 1 plus test 2 give {fig['test_1'][worst] + fig['test_2'][worst]!r}")
    t = {k: float(v.mean()) for k, v in x.items()}
    if abs(t["own"] - t["test_1"] - t["test_2"]) > 1e-9 * max(1.0, abs(t["own"])):
        raise AnalysisError(f"decomposition: T {t['own']!r} is not test 1 plus test 2 ({t['test_1'] + t['test_2']!r})")
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(units), size=(draws, len(units)))
    s = {k: v[idx].mean(1) for k, v in x.items()}
    with np.errstate(divide="ignore", invalid="ignore"):
        shares = {k: s[k] / s["own"] for k in ("test_1", "test_2")}
    finite = np.isfinite(shares["test_1"]) & np.isfinite(shares["test_2"])

    def middle(a):
        return [float(np.percentile(a, 2.5)), float(np.percentile(a, 97.5))] if len(a) else None

    ranges = {k: middle(v) for k, v in s.items()}
    return {"kind": kind, "questions": len(units), "question_passes": len(quad),
            "T": t, "range": ranges,
            "share_of_test_1": t["test_1"] / t["own"] if t["own"] else None,
            "share_of_test_2": t["test_2"] / t["own"] if t["own"] else None,
            "share_range": {k: middle(shares[k][finite]) for k in ("test_1", "test_2")},
            "draws_with_a_zero_denominator": int((~finite).sum()),
            "denominator_range_crosses_zero": bool(ranges["own"][0] <= 0 <= ranges["own"][1])}


# ---------------------------------------------------------------- rows for cells, questions, sets and folders

def _per_question(asks: list[dict], value) -> dict:
    acc: dict = {}
    for r in asks:
        x = value(r)
        if x is not None:
            acc.setdefault(r["unit"], []).append(x)
    return {u: sum(x) / len(x) for u, x in acc.items()}


def _mean(d: dict):
    return float(np.mean(list(d.values()))) if d else None


def cell_rows(slots: dict, info: dict, cells) -> dict:
    """A row for each cell, over the questions every cell has a scored ask of. Each question first gets
    its mean over the cell's asks, then the mean is taken over the questions."""
    asks = {c: [] for c in cells}
    for (_, _, v, g), a in sorted(slots.items()):
        asks[(v, g)] += a
    lt = {c: _per_question(a, lthink) for c, a in asks.items()}
    units = sorted(set.intersection(*(set(m) for m in lt.values())))
    uset = set(units)
    out = {"questions": len(units),
           "questions_some_cell_has_no_scored_ask_of": sorted(set().union(*(set(m) for m in lt.values())) - uset)}
    for c in cells:
        mine = [r for r in asks[c] if r["unit"] in uset]
        row = {"scored_asks": len(mine),
               "records_by_outcome": info["records_by_cell_and_outcome"][cell_name(c)],
               "records_by_outcome_in_cells_with_every_cell": info["records_by_cell_and_outcome_in_cells_with_every_cell"][cell_name(c)]}
        if mine:
            a_lt = _per_question(mine, lthink)
            a_zero = _per_question(mine, lambda r: None if r.get("thinking_tokens") is None else float(r["thinking_tokens"] == 0))
            a_pos = _per_question([r for r in mine if (r.get("thinking_tokens") or 0) > 0], lthink)
            tokens: dict = {}
            for r in mine:
                k = r.get("first_request_input_tokens")
                tokens[k] = tokens.get(k, 0) + 1
            row.update({
                "mean_ln_thinking": _mean(a_lt),
                "thinking_geometric_mean_tokens": math.exp(_mean(a_lt)) - 1,
                "share_zero_thinking_per_cent": _mean(a_zero) * 100,
                "thinking_geometric_mean_over_asks_above_zero": (math.exp(_mean(a_pos)) - 1) if a_pos else None,
                "questions_with_an_ask_above_zero": len(a_pos),
                "accuracy_per_cent": _mean(_per_question(mine, correct)) * 100,
                "share_that_tried_a_tool_per_cent": _mean(_per_question(mine, lambda r: float(bool(r.get("tool_calls"))))) * 100,
                "first_request_input_tokens": {str(k): tokens[k] for k in sorted(tokens, key=lambda k: (k is None, k or 0))}})
        out[cell_name(c)] = row
    return out


def question_rows(cmps: dict, slots: dict, cells) -> dict:
    """Each question's figure in the given comparisons (None where it is left out), and in each cell its
    scored asks that count and how many of them have no thinking."""
    counts: dict = {}
    for (u, _, v, g), asks in sorted(slots.items()):
        d = counts.setdefault(u, {cell_name(c): {"zero_thinking_asks": 0, "scored_asks": 0} for c in cells})
        for r in asks:
            d[cell_name((v, g))]["scored_asks"] += 1
            d[cell_name((v, g))]["zero_thinking_asks"] += int(r.get("thinking_tokens") == 0)
    every = sorted({u for c in cmps.values() for u in c.get("question_figures", {})} | set(counts))
    empty = {cell_name(c): {"zero_thinking_asks": 0, "scored_asks": 0} for c in cells}
    return {u: {**{name: c.get("question_figures", {}).get(u) for name, c in cmps.items()},
                "cells": counts.get(u, empty)} for u in every}


def set_rows(slots: dict, full: set) -> dict:
    """A row for each set of worker folders: its scored asks that count, and test 1 and test 2 on the
    pairs of that set alone (no declaration)."""
    by_set: dict = {}
    for k, asks in sorted(slots.items()):
        for r in asks:
            by_set.setdefault(str(ask_set(r)), {}).setdefault(k, []).append(r)
    out = {}
    for s in sorted(by_set):
        sl = by_set[s]
        uni = sorted({k[0] for k in sl})
        out[s] = {"asks": sum(len(a) for a in sl.values()), "question_passes": len({(k[1], k[0]) for k in sl}),
                  "test_1_thinking": comparison(sl, full, TEST_1, lthink, "thinking", uni),
                  "test_2_thinking": comparison(sl, full, TEST_2, lthink, "thinking", uni),
                  "test_1_accuracy": comparison(sl, full, TEST_1, correct, "accuracy", uni),
                  "test_2_accuracy": comparison(sl, full, TEST_2, correct, "accuracy", uni)}
    return out


def _label(folder) -> str:
    return "/".join(Path(str(folder)).parts[-2:]) if folder else str(folder)


def folder_rows(slots: dict, draws: int = DRAWS, seed: int = SEED) -> dict:
    """A row for each config folder of each program. An ask's difference is its ln thinking minus the
    mean of the asks of its question, program and way. A folder's figure is the mean difference of its
    asks. Each program gets a p: within every (question, program, way) the folders of the asks are dealt
    out again at random, and the statistic is the sum over the program's folders of (asks times the
    folder's mean difference squared). p = (draws with a statistic at least the real one, plus 1) / 10,001."""
    strata: dict = {}
    sets_of: dict = {}
    for (u, _, v, g), asks in sorted(slots.items()):
        for r in asks:
            x = lthink(r)
            if x is not None:
                f = str(r.get("config_dir"))
                strata.setdefault((v, u, g), []).append((f, x))
                sets_of.setdefault((v, f), set()).add(str(ask_set(r)))
    out = {"folders": {}, "programs": {}}
    versions_by_folder: dict = {}
    for v in PROGRAMS:
        mine = {k: s for k, s in strata.items() if k[0] == v}
        folders = sorted({f for s in mine.values() for f, _ in s})
        if not folders:
            out["programs"][v] = {"no_data": True}
            continue
        fi = {f: i for i, f in enumerate(folders)}
        parts = []
        for k in sorted(mine):
            vals = np.array([x for _, x in mine[k]])
            parts.append((vals - vals.mean(), np.array([fi[f] for f, _ in mine[k]])))
        n = np.zeros(len(folders))
        s = np.zeros(len(folders))
        for res, idx in parts:
            np.add.at(n, idx, 1)
            np.add.at(s, idx, res)
        stat = float((s ** 2 / n).sum())
        rng = np.random.default_rng(seed)
        hits, done = 0, 0
        while done < draws:
            m = min(CHUNK, draws - done)
            sd = np.zeros((m, len(folders)))
            for res, idx in parts:
                if len(res) < 2:
                    continue  # a single ask has a difference of zero wherever it goes
                order = np.argsort(rng.random((m, len(res))), axis=1)
                sd += res[order] @ np.eye(len(folders))[idx]
            hits += int(((sd ** 2 / n).sum(1) >= stat - 1e-12 * max(1.0, stat)).sum())
            done += m
        out["programs"][v] = {"folders": len(folders), "asks": int(n.sum()), "statistic": stat,
                              "p": (hits + 1) / (draws + 1), "draws_at_least_as_large": hits, "draws": draws}
        for f in folders:
            i = fi[f]
            versions_by_folder.setdefault(f, set()).add(v)
            out["folders"][f"{v} {f}"] = {"program": v, "config_dir": f, "label": _label(f),
                                          "sets": sorted(sets_of[(v, f)]), "asks": int(n[i]),
                                          "mean_ln_difference": float(s[i] / n[i]),
                                          "as_per_cent": (math.exp(s[i] / n[i]) - 1) * 100}
    out["folders_used_by_both_programs"] = sorted(f for f, vs in versions_by_folder.items() if len(vs) > 1)
    return out


# ---------------------------------------------------------------- accuracy scored two more ways

_RESCORE = None


def rescore_module():
    """rescore.py of the two groups of 13 November, as it is. It imports its own analysis.py under the
    name "analysis", which is the name of this file too, so both of its files are loaded from their
    paths under names of their own, and the name "analysis" is given back as it was."""
    global _RESCORE
    if _RESCORE is None:
        import importlib.util

        # the folder of the two groups of 13 November: 再验少想 on the computer of the run, recheck in the
        # public repository
        folder = next((HERE.parent / n for n in RECHECK_FOLDERS if (HERE.parent / n / "rescore.py").is_file()), None)
        if folder is None:
            raise RuntimeError(f"rescore.py not found in any of {RECHECK_FOLDERS} next to {HERE}")
        sys.dont_write_bytecode = True  # leave no cache files in that folder

        def load(name: str, path: Path):
            spec = importlib.util.spec_from_file_location(name, path)
            m = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(m)
            return m

        saved = sys.modules.get("analysis")
        sys.modules["analysis"] = load("recheck_analysis", folder / "analysis.py")
        try:
            _RESCORE = load("recheck_rescore", folder / "rescore.py")
        finally:
            if saved is None:
                sys.modules.pop("analysis", None)
            else:
                sys.modules["analysis"] = saved
    return _RESCORE


def two_more_ways(slots: dict, cells: set, universe, keys: dict | None = None) -> dict:
    """Accuracy of test 1, test 2 and the two cells with their own sentences scored as rescore.py's
    "sound" (the benchmark's key, on the questions in "sound" only) and "corrected" (the questions in
    "left_out" left out, the rest rescored by rescore.corrected). No declaration."""
    rs = rescore_module()
    keys = keys if keys is not None else rs.load_keys()
    sound = {"item:" + i for i in keys["sound"]}
    kept = {u for u in universe if u not in {"item:" + i for i in keys["left_out"]}}
    plan = {"sound": (sound, correct), "corrected": (kept, lambda r: rs.corrected(r, keys))}
    out = {"keys_file": rs.KEYS_FILE.name}
    for way, (units, value) in plan.items():
        out[way] = {name: comparison(slots, cells, layers, value, "accuracy", universe, units=units)
                    for name, layers in (("test_1", TEST_1), ("test_2", TEST_2), ("own_sentences_two_cells", OWN))}
    return out


# ---------------------------------------------------------------- beside: main and high_recheck

def beside(rows: list[dict], group: str, units) -> dict:
    """2.1.316 then 2.1.317 on the graded rows of another group (main, high_recheck), on the given
    questions. One ask per version, question and pass there, so a pair is the asks of the two versions
    in one question and pass."""
    uset = set(units)
    mine = [r for r in rows if r.get("group") == group and r.get("version") in PROGRAMS and r.get("unit") in uset]
    slots: dict = {}
    for r in mine:
        if r.get("outcome") == "scored":
            slots.setdefault((r["unit"], r["pass"], r["version"], group), []).append(r)
    cells = {(r["pass"], r["unit"]) for r in mine}
    layers = (("2.1.316 then 2.1.317", (OLD, group), (NEW, group)),)
    return {"group": group, "records": len(mine), "scored_asks": sum(len(a) for a in slots.values()),
            "passes": sorted({r["pass"] for r in mine}),
            "thinking": comparison(slots, cells, layers, lthink, "thinking", sorted(uset)),
            "accuracy": comparison(slots, cells, layers, correct, "accuracy", sorted(uset))}


# ---------------------------------------------------------------- the whole report

def report(rows: list[dict], *, ways=DEFAULT_WAYS, ways_source: str = "given", stage1: bool = False,
           line: float | None = LINE_CONTINUE, stage: dict | None = None, plans: dict | None = None,
           numbers=None, units=None, gaps: dict | None = None, main_rows=None, high_rows=None,
           keys: dict | None = None) -> dict:
    """stage1: the report of --stage1 (the tests carry no declaration, and the decision of stage 1 is
    made). Otherwise the tests are declared at `line`."""
    cells = cells_of(ways)
    slots, full, have, info = counted(rows, ways)
    universe = sorted(set(units) if units else {u for _, u in have})
    numbers = list(numbers) if numbers is not None else sorted({p for p, _ in have})
    tline = None if stage1 else line
    rep: dict = {"what": "group swap: the two sentences that changed at 2.1.317 swapped between 2.1.316 and 2.1.317",
                 "decided_after_the_registered_results_were_seen": True,
                 "stage": dict(stage or {}, report_of="stage 1" if stage1 else "the end", line=tline),
                 "ways": list(ways), "ways_from": ways_source, "cells": [cell_name(c) for c in cells],
                 "plans_read": plans or {}, "completeness": pass_completeness(have, full, numbers, units, gaps),
                 "counted": info}
    t1 = comparison(slots, full, TEST_1, lthink, "thinking", universe, line=tline)
    t2 = comparison(slots, full, TEST_2, lthink, "thinking", universe, line=tline)
    rep["test_1_sentences_thinking"] = t1
    rep["test_2_program_thinking"] = t2
    if stage1:
        if t1.get("no_data") or t2.get("no_data"):
            raise AnalysisError("stage 1: a test has no data, so no decision can be made")
        rep["stage1_decision"] = {"decision": stage1_decision(t1["p_by_pairs"], t2["p_by_pairs"]),
                                  "p_by_pairs": {"test_1": t1["p_by_pairs"], "test_2": t2["p_by_pairs"]},
                                  "T": {"test_1": t1["T"], "test_2": t2["T"]}}
    else:
        rep["outcome_of_the_tests"] = {name: "no data" if t.get("no_data") else
                                       f"{'declared' if t['declared'] else 'not declared'}, {t['direction']}"
                                       for name, t in (("test_1", t1), ("test_2", t2))}
    rep["test_1_sentences_accuracy_no_declaration"] = comparison(slots, full, TEST_1, correct, "accuracy", universe)
    rep["test_2_program_accuracy_no_declaration"] = comparison(slots, full, TEST_2, correct, "accuracy", universe)
    reported = dict(REPORTED, **(REPORTED_WITH_SW_N if "sw_n" in ways else {}))
    rep["reported_no_declaration"] = {
        name: {"thinking": comparison(slots, full, layers, lthink, "thinking", universe),
               "accuracy": comparison(slots, full, layers, correct, "accuracy", universe)}
        for name, layers in reported.items()}
    own = rep["reported_no_declaration"]["own_sentences_two_cells"]
    for c in (t1, t2, rep["test_1_sentences_accuracy_no_declaration"], rep["test_2_program_accuracy_no_declaration"],
              own["thinking"], own["accuracy"]):
        c["leave_one_out"] = leave_one_out(c)
    rep["decomposition"] = {"thinking": decomposition(slots, full, lthink, "thinking"),
                            "accuracy": decomposition(slots, full, correct, "accuracy")}
    rep["cell_rows"] = cell_rows(slots, info, cells)
    rep["questions"] = question_rows({
        "test_1_thinking": t1, "test_2_thinking": t2, "own_sentences_two_cells_thinking": own["thinking"],
        "test_1_accuracy": rep["test_1_sentences_accuracy_no_declaration"],
        "test_2_accuracy": rep["test_2_program_accuracy_no_declaration"],
        "own_sentences_two_cells_accuracy": own["accuracy"]}, slots, cells)
    rep["sets"] = set_rows(slots, full)
    rep["folders"] = folder_rows(slots)
    rep["accuracy_two_more_ways_no_declaration"] = two_more_ways(slots, full, universe, keys)
    same = sorted(own["thinking"].get("question_figures", {}))
    for name, group, given in (("main", "main", main_rows), ("high_recheck", "high_recheck", high_rows)):
        if given:
            rep.setdefault("beside_own_sentences_two_cells", {})[name] = beside(given, group, same)
    return rep


# ---------------------------------------------------------------- output

def _pc(x: float) -> str:
    return f"{x * 100:+.1f}%"


def _t_text(kind: str, t: float) -> str:
    return _pc(math.exp(t) - 1) if kind == "thinking" else f"{t * 100:+.2f} points"


def _fmt_cmp(name: str, c: dict, test: bool = False) -> list[str]:
    if c.get("no_data"):
        return [f"{name}: no data" + (f" | left out {len(c['questions_left_out'])}" if c.get("questions_left_out") else "")]
    if c["kind"] == "thinking":
        r = c["range_exp_minus_1"]
        size = f"{_pc(c['exp_T_minus_1'])} ({_pc(r[0])} to {_pc(r[1])})"
    else:
        size = f"{c['points']:+.2f} points ({c['range_points'][0]:+.2f} to {c['range_points'][1]:+.2f})"
    if c["declared"] is None:
        verdict = "stage 1, no declaration" if test else "no declaration"
    else:
        verdict = f"{'DECLARED' if c['declared'] else 'not declared'} at {c['line']}"
    layers = ", ".join(f"{k}: {n}" for k, n in c["pairs_by_layer"].items())
    lines = [f"{name}: {size} | p by pairs {c['p_by_pairs']:.4f} | {verdict} | {c['direction']} | "
             f"questions {c['questions']}, pairs {c['pairs']} ({layers})"]
    if test:  # the fixed line beside each test
        lines.append(f"    p by pairs {c['p_by_pairs']:.4f} | p by questions {c['p_by_questions']:.4f} | "
                     f"range crosses 0: {'yes' if c['range_crosses_zero'] else 'no'}")
    else:
        lines[0] += f" | p by questions {c['p_by_questions']:.4f}"
    if c["questions_left_out"]:
        lines.append("    left out (pairs by layer): " + " | ".join(
            f"{u} " + ", ".join(f"{k} {n}" for k, n in d.items()) for u, d in c["questions_left_out"].items()))
    loo = c.get("leave_one_out")
    if loo and not loo.get("no_data"):
        lo, hi = loo["lowest"], loo["highest"]
        lines.append(f"    one question left out: T from {_t_text(c['kind'], lo['T'])} (without {lo['without']}) "
                     f"to {_t_text(c['kind'], hi['T'])} (without {hi['without']}) | less than half as far from zero "
                     f"without: {', '.join(loo['questions_without_which_T_is_below_half']) or 'none'}")
    return lines


def _fmt_split(d: dict) -> list[str]:
    if d.get("no_data"):
        return [f"{d['kind']}: no question and pass with all four cells"]
    unit = (lambda x: f"{x:+.4f} ln") if d["kind"] == "thinking" else (lambda x: f"{x * 100:+.2f} points")
    rg = d["range"]
    out = [f"{d['kind']}: own sentences' two cells {unit(d['T']['own'])} ({unit(rg['own'][0])} to {unit(rg['own'][1])})"
           f" = test 1 {unit(d['T']['test_1'])} ({unit(rg['test_1'][0])} to {unit(rg['test_1'][1])})"
           f" + test 2 {unit(d['T']['test_2'])} ({unit(rg['test_2'][0])} to {unit(rg['test_2'][1])})"
           f" | questions {d['questions']}, question and pass cells {d['question_passes']}"]
    if d["share_of_test_1"] is None:
        out.append("    shares: the two cells' T is zero")
    else:
        sr = d["share_range"]
        note = " (the range of the denominator crosses 0)" if d["denominator_range_crosses_zero"] else ""

        def shown(k: str) -> str:
            share = f"{d['share_of_' + k] * 100:.0f}%"
            return share + (f" ({sr[k][0] * 100:.0f}% to {sr[k][1] * 100:.0f}%)" if sr[k] else "")

        out.append(f"    test 1 is {shown('test_1')} of it{note}, test 2 is {shown('test_2')}{note}")
    return out


def text_report(rep: dict) -> str:
    st = rep["stage"]
    L = [rep["what"] + ".", "Decided after the registered results were seen.", st.get("text", "")]
    if st.get("decision_p_agree_with_now") is False:
        L.append(f"  THE p OF stage1_decision.json ({json.dumps(st.get('decision_p_by_pairs'))}) ARE NOT THE p COMPUTED NOW")
    if st.get("decision_file_kept"):
        L.append(f"  {st['decision_file_kept']}")
    L.append(f"Ways sent in the passes: {', '.join(rep['ways'])} (from {rep['ways_from']})")
    comp = rep["completeness"]
    L.append(f"Passes ({comp['questions_from']}{', plan files checked' if comp['plans_checked'] else ''}): "
             f"all complete = {comp['all_complete']}")
    for p, x in comp["passes"].items():
        L.append(f"  pass {p}: {'complete' if x['complete'] else 'NOT complete'}, questions with every cell "
                 f"{x['questions_with_every_cell']} of {x['questions_expected']}, with a record {x['questions_with_a_record']}"
                 + "".join(f" | {m}" for m in x["plan_problems"]))
    if not comp["passes"]:
        L.append("  no pass is read")
    info = rep["counted"]
    L += [f"Plans read: {', '.join(rep['plans_read']) or 'none'}"
          + "".join(f" | {n} has {d['rows_whose_pass_is_not_the_plans']} rows of another pass"
                    for n, d in rep["plans_read"].items() if d["rows_whose_pass_is_not_the_plans"])
          + (f" | not read (after pass {st['last_pass_read']}): {', '.join(st['plans_not_read'])}" if st.get("plans_not_read") else ""),
          f"Records {info['records']} (rows of other groups, versions or units: {info['rows_read_that_are_not_of_the_cells']}) | "
          f"pass x question cells {info['cells']}, with every cell {info['cells_with_every_cell']} | "
          f"scored asks that count {info['scored_asks_that_count']}",
          "Records by cell and outcome: " + json.dumps(info["records_by_cell_and_outcome"])]
    for k in ("asks_of_one_cell_question_and_pass_beyond_the_first_scored_one", "scored_asks_without_thinking_tokens"):
        if info[k]:
            L.append(f"  {k.replace('_', ' ')}: {info[k]}")
    if info["question_passes_in_more_than_one_set"]:
        L.append("  QUESTION AND PASS CELLS WITH ASKS IN MORE THAN ONE SET: " + ", ".join(info["question_passes_in_more_than_one_set"]))
    L += ["", f"== The two tests (thinking), {'stage 1' if st['line'] is None else 'line ' + str(st['line'])} =="]
    L += _fmt_cmp("TEST 1, the sentences (" + WHAT_IS_COMPARED["test_1"] + ")", rep["test_1_sentences_thinking"], test=True)
    L += _fmt_cmp("TEST 2, the program (" + WHAT_IS_COMPARED["test_2"] + ")", rep["test_2_program_thinking"], test=True)
    if "stage1_decision" in rep:
        d = rep["stage1_decision"]
        L.append(f"STAGE 1 DECISION: {d['decision']} (p by pairs: test 1 {d['p_by_pairs']['test_1']:.4f}, "
                 f"test 2 {d['p_by_pairs']['test_2']:.4f})")
    else:
        o = rep["outcome_of_the_tests"]
        L.append(f"Outcome: test 1 {o['test_1']} | test 2 {o['test_2']}")
    L += ["", "== The two cells with their own sentences as test 1 plus test 2 (question and pass cells with all four cells) =="]
    L += _fmt_split(rep["decomposition"]["thinking"]) + _fmt_split(rep["decomposition"]["accuracy"])
    L += ["", "== Reported, no declaration =="]
    L += _fmt_cmp("test 1, accuracy", rep["test_1_sentences_accuracy_no_declaration"])
    L += _fmt_cmp("test 2, accuracy", rep["test_2_program_accuracy_no_declaration"])
    for name, both in rep["reported_no_declaration"].items():
        L += _fmt_cmp(f"{name} ({WHAT_IS_COMPARED[name]}), thinking", both["thinking"])
        L += _fmt_cmp(f"{name}, accuracy", both["accuracy"])
    if "sw_n" not in rep["ways"]:
        L.append("(sw_n was not sent in the passes: the three comparisons with sw_n are not reported)")
    b = rep.get("beside_own_sentences_two_cells")
    if b:
        L += ["", "== Beside the two cells with their own sentences: 2.1.316 then 2.1.317 in other groups, same questions, no declaration =="]
        for name, x in b.items():
            L.append(f"{name}: records {x['records']}, scored asks {x['scored_asks']}, passes {x['passes']}")
            L += _fmt_cmp(f"  {name}, thinking", x["thinking"]) + _fmt_cmp(f"  {name}, accuracy", x["accuracy"])
    m = rep["accuracy_two_more_ways_no_declaration"]
    L += ["", f"== Accuracy scored two more ways ({m['keys_file']}), no declaration =="]
    for way in ("sound", "corrected"):
        for name, c in m[way].items():
            L += _fmt_cmp(f"{way}, {name}", c)
    cr = rep["cell_rows"]
    cells = rep["cells"]
    L += ["", f"== Each cell, over the {cr['questions']} questions every cell has a scored ask of =="]
    if cr["questions_some_cell_has_no_scored_ask_of"]:
        L.append("  questions left out: " + ", ".join(cr["questions_some_cell_has_no_scored_ask_of"]))
    L.append("  cell          asks  thinking(geo mean)  zero%  geo mean above zero  accuracy%  tried a tool%")
    for c in cells:
        r = cr[c]
        if not r["scored_asks"]:
            L.append(f"  {c:<12}  no scored ask")
            continue
        above = r["thinking_geometric_mean_over_asks_above_zero"]
        L.append(f"  {c:<12} {r['scored_asks']:5d}  {r['thinking_geometric_mean_tokens']:12.1f}"
                 f"  {r['share_zero_thinking_per_cent']:11.1f}  {'none' if above is None else f'{above:.1f}':>12}"
                 f"  {r['accuracy_per_cent']:13.1f}  {r['share_that_tried_a_tool_per_cent']:9.1f}")
    for c in cells:
        r = cr[c]
        L.append(f"  {c}: records by outcome {json.dumps(r['records_by_outcome'])}")
        if r["scored_asks"]:
            L.append(f"  {c}: input tokens of the first request (value: asks) " + json.dumps(r["first_request_input_tokens"]))
    L += ["", "== Each question (thinking as a ln difference, accuracy in points) =="]
    names = ("test_1_thinking", "test_2_thinking", "own_sentences_two_cells_thinking",
             "test_1_accuracy", "test_2_accuracy", "own_sentences_two_cells_accuracy")
    L.append("  question                          test 1   test 2  own two  | test 1  test 2  own two")
    for u, d in rep["questions"].items():
        cols = [("    none" if d[n] is None else f"{d[n]:+8.3f}") for n in names[:3]]
        cols += [("    none" if d[n] is None else f"{d[n] * 100:+7.1f}") for n in names[3:]]
        L.append(f"  {u:<32}" + " ".join(cols[:3]) + "  | " + " ".join(cols[3:]))
    L.append("  asks with zero thinking / scored asks that count, by cell: " + ", ".join(cells))
    for u, d in rep["questions"].items():
        L.append(f"  {u:<32}" + "  ".join(f"{d['cells'][c]['zero_thinking_asks']:3d}/{d['cells'][c]['scored_asks']:<3d}" for c in cells))
    L += ["", "== Each set of worker folders (test 1 and test 2 on the pairs of the set alone, no declaration) =="]
    for s, r in rep["sets"].items():
        parts = []
        for k in ("test_1_thinking", "test_2_thinking", "test_1_accuracy", "test_2_accuracy"):
            c = r[k]
            parts.append(f"{k.replace('_', ' ')} " + ("no data" if c.get("no_data") else _t_text(c["kind"], c["T"])))
        L.append(f"  set {s}: asks {r['asks']}, question and pass cells {r['question_passes']} | " + " | ".join(parts))
    f = rep["folders"]
    L += ["", "== Each config folder (thinking: mean difference from the asks of the same question, program and way) =="]
    for v in PROGRAMS:
        pr = f["programs"][v]
        if pr.get("no_data"):
            L.append(f"  {v}: no data")
            continue
        L.append(f"  {v}: {pr['folders']} folders, {pr['asks']} asks, p {pr['p']:.4f} (no declaration)")
        for row in f["folders"].values():
            if row["program"] == v:
                L.append(f"    {row['label']:<40} set {','.join(row['sets']):<6} asks {row['asks']:4d}  "
                         f"{row['mean_ln_difference']:+.4f}  ({row['as_per_cent']:+.1f}%)")
    if f["folders_used_by_both_programs"]:
        L.append("  FOLDERS USED BY BOTH PROGRAMS: " + ", ".join(_label(x) for x in f["folders_used_by_both_programs"]))
    return "\n".join(L) + "\n"


def write_report(rep: dict, out: Path, prefix: str = "") -> str:
    out.mkdir(parents=True, exist_ok=True)
    text = text_report(rep)
    (out / f"{prefix}report.json").write_text(json.dumps(rep, indent=1) + "\n")
    (out / f"{prefix}report.txt").write_text(text)
    return text


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def load_units(path: Path) -> list[str]:
    doc = json.loads(path.read_text())
    items = doc if isinstance(doc, list) else doc.get("items") or doc.get("units")
    if not isinstance(items, list) or not items:
        raise AnalysisError(f"{path}: no list of questions (a JSON list, or one under \"items\" or \"units\")")
    return [i if str(i).startswith("item:") else f"item:{i}" for i in items]


def author_grader(s, raw_dir: Path, graded_dir: Path):
    """grade_plan(name) for load_rows: what ccversions.formal.Driver.graded does for one plan (the way the
    analysis of the two groups of 13 November grades its plans), with the plan folders in raw_dir. The
    graded rows get two things of their record that grade.py does not copy: the field "swap" (the set
    of the ask) and whether the ask never reached the model (extract.never_reached_model)."""
    from ccversions import extract, grade, items as items_mod

    bits: dict = {}

    def grade_plan(name: str):
        if not (raw_dir / name / "asks").is_dir():
            return None
        if not bits:
            bits["checks"], bits["claudecode"] = grade.import_author_graders(s.author_repo)
            bits["inputs"] = items_mod.load(s.item_file, s.item_file_sha256, s.probe_file)
        records = grade.load_records(raw_dir / name)
        rows = grade.grade_records(records, bits["inputs"], bits["checks"], bits["claudecode"])
        grade.write_outputs(rows, graded_dir / name)
        by_id = {rec.get("ask_id"): rec for rec in records}
        out = load_jsonl(graded_dir / name / "graded.jsonl")
        for r in out:
            rec = by_id.get(r.get("ask_id"), {})
            r["swap"] = rec.get("swap")
            r["never_reached_model"] = bool(rec) and extract.never_reached_model(rec)
        return out

    return grade_plan


def main(argv=None, grade_plan=None) -> int:
    from ccversions import settings as settings_mod

    ap = argparse.ArgumentParser()
    ap.add_argument("--settings", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--stage1", action="store_true", help="decide after stage 1 (passes 1 to S)")
    ap.add_argument("--stage1-decision", help="the stage1_decision.json to read at the end (default: in --out)")
    ap.add_argument("--raw-dir", help="the folder that holds the plan folders (default: raw_dir of the settings)")
    ap.add_argument("--graded-dir", help="where the graded rows go, a folder per plan (default: graded next to --raw-dir)")
    ap.add_argument("--plans-dir", help="where swap.py keeps its plans (default: plans next to the settings file)")
    ap.add_argument("--units", help="a JSON file with the questions (default: item_list in [group] of the settings)")
    ap.add_argument("--passes", type=int, help="P, the passes of both stages (default: passes in [group], else 12)")
    ap.add_argument("--stage1-passes", type=int, help="S, the passes of stage 1 (default: stage1_passes in [group], else 6)")
    ap.add_argument("--ways", help="the ways the passes send, comma separated (default: those of the pass plans)")
    ap.add_argument("--main-graded", action="append", default=[],
                    help="a graded.jsonl of the registered run, for the figures beside, given once per file")
    ap.add_argument("--high-recheck-graded", action="append", default=[],
                    help="a graded.jsonl of high_recheck, for the figures beside, given once per file")
    a = ap.parse_args(argv)
    try:
        return _run(a, settings_mod, grade_plan)
    except AnalysisError as e:
        print(f"refused: {e}", file=sys.stderr, flush=True)
        return 2


def _run(a, settings_mod, grade_plan) -> int:
    s = settings_mod.load(a.settings)
    sfile = Path(a.settings).resolve()
    # swap.py keeps the questions and the passes in [group] of the same settings file
    group = tomllib.loads(sfile.read_text(encoding="utf-8")).get("group", {})
    units_file = Path(a.units) if a.units else Path(group["item_list"]) if group.get("item_list") else None
    if units_file is not None and not units_file.is_absolute() and not a.units:
        units_file = sfile.parent / units_file
    units = load_units(units_file) if units_file else None
    big_p = a.passes if a.passes is not None else group.get("passes", PASSES)
    small_s = a.stage1_passes if a.stage1_passes is not None else group.get("stage1_passes", STAGE1_PASSES)
    if not (isinstance(big_p, int) and isinstance(small_s, int) and 1 <= small_s <= big_p):
        raise AnalysisError(f"stage 1 has {small_s!r} passes and the group {big_p!r}: 1 <= S <= P is needed")
    out = Path(a.out)
    raw = Path(a.raw_dir) if a.raw_dir else s.raw_dir
    graded = Path(a.graded_dir) if a.graded_dir else raw.parent / "graded"
    plans_dir = Path(a.plans_dir) if a.plans_dir else sfile.parent / "plans"
    decision_file = Path(a.stage1_decision) if a.stage1_decision else out / "stage1_decision.json"
    stage = {"stage1_passes": small_s, "passes": big_p}

    if a.stage1:
        last, line = small_s, None
        stage["text"] = f"Stage 1: passes 1 to {small_s} of {big_p}. No declaration, the rule of stage 1 decides."
    else:
        decision = json.loads(decision_file.read_text()) if decision_file.is_file() else None
        stage["decision_file"] = str(decision_file) if decision else None
        if decision is None:
            last, line = big_p, LINE_CONTINUE
            stage["text"] = (f"No stage1_decision.json ({decision_file}): read as both stages, passes 1 to {big_p}, "
                             f"line {LINE_CONTINUE}.")
        elif decision.get("decision") == "stop":
            last, line = small_s, LINE_STOP
            stage["text"] = f"Stopped after stage 1: passes 1 to {small_s}, line {LINE_STOP}."
        elif decision.get("decision") == "continue":
            last, line = big_p, LINE_CONTINUE
            stage["text"] = f"Both stages sent: passes 1 to {big_p}, line {LINE_CONTINUE}."
        else:
            raise AnalysisError(f"{decision_file} holds no decision stop or continue")
        if decision:
            stage.update(decision=decision["decision"], decision_computed_at=decision.get("computed_at"),
                         decision_p_by_pairs=decision.get("p_by_pairs"))
            if int(decision.get("stage1_passes", small_s)) != small_s:
                raise AnalysisError(f"{decision_file} was made with S = {decision.get('stage1_passes')}, now S = {small_s}")
    names = plan_names(raw)
    later = [n for n in names if plan_number(n) > last]
    if not a.stage1 and stage.get("decision") == "stop" and later:
        raise AnalysisError(f"stage 1 said stop, but the records hold plans after pass {small_s}: {', '.join(later)}")
    stage.update(last_pass_read=last, plans_not_read=later)
    rows, plans, _, detail = load_rows(raw, grade_plan or author_grader(s, raw, graded), last)
    numbers = list(range(1, last + 1))
    gaps = pass_gaps(plans_dir, numbers, detail) if plans_dir.is_dir() else None
    if a.stage1:
        bad = {n: m for n, m in (gaps or {str(n): ["no plan files in " + str(plans_dir)] for n in numbers}).items() if m}
        if bad:
            raise AnalysisError("stage 1 is not complete: " + " | ".join(f"pass {n}: {', '.join(m)}" for n, m in bad.items()))
    if a.ways:
        given, given_from = a.ways.split(","), "--ways"
    elif group:  # a settings file of swap.py: its scored_groups, or swap.py's default of sw_o and sw_w
        given = group.get("scored_groups", list(DEFAULT_WAYS))
        given_from = "[group] scored_groups" if "scored_groups" in group else "the default of swap.py (no scored_groups)"
    else:
        given, given_from = None, ""
    ways, ways_source = ways_in_use(plans_dir, numbers, rows, given, given_from)
    main_rows = [r for f in a.main_graded for r in load_jsonl(Path(f))]
    high_rows = [r for f in a.high_recheck_graded for r in load_jsonl(Path(f))]
    rep = report(rows, ways=ways, ways_source=ways_source, stage1=a.stage1, line=line, stage=stage, plans=plans,
                 numbers=numbers, units=units, gaps=gaps, main_rows=main_rows, high_rows=high_rows)
    rep["raw_dir"] = str(raw)
    if a.stage1:
        d = rep["stage1_decision"]
        new = {"decision": d["decision"], "p_by_pairs": d["p_by_pairs"], "T": d["T"],
               "stage1_passes": small_s, "passes": big_p,
               "rule": f"stop when both p by pairs are at most {STOP_AT}, or one is at most {STOP_AT} and the "
                       f"other above {OTHER_ABOVE}, else continue",
               "plans_read": {n: x["rows"] for n, x in plans.items()},
               "computed_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        if decision_file.is_file():
            old = json.loads(decision_file.read_text())
            if (old.get("decision"), old.get("p_by_pairs")) != (new["decision"], new["p_by_pairs"]):
                raise AnalysisError(f"{decision_file} already holds decision {old.get('decision')} with p "
                                    f"{old.get('p_by_pairs')}, now {new['decision']} with p {new['p_by_pairs']}: "
                                    "it is left as it is")
            rep["stage"]["decision_file_kept"] = f"{decision_file} already held the same decision and p, computed at {old.get('computed_at')}"
        else:
            out.mkdir(parents=True, exist_ok=True)
            decision_file.write_text(json.dumps(new, indent=1) + "\n")
        print(write_report(rep, out, "stage1_"), end="", flush=True)
        print(f"STAGE1 {d['decision']}", flush=True)
        return 0
    if stage.get("decision") == "stop":
        now = {"test_1": rep["test_1_sentences_thinking"].get("p_by_pairs"),
               "test_2": rep["test_2_program_thinking"].get("p_by_pairs")}
        rep["stage"]["decision_p_agree_with_now"] = now == stage.get("decision_p_by_pairs")
    print(write_report(rep, out), end="", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
