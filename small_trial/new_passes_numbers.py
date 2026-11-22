"""The numbers of the small trial's second segment: 200 new MMLU-Pro items, five passes on 2.1.316, and the
blind reading of the same items by five readers. (Small trial of 22 November 2026, rules section 6, and
section 7 points 1 and 2.)

    python -B new_passes_numbers.py --graded <graded.jsonl> [--graded ...] \
        --judgments <batch table .tsv> [--judgments ...] --key-table <code table .json> \
        [--main-reads <.tsv>] --out <folder>

Inputs
  --graded      graded rows (ccversions grade), one graded.jsonl per plan: the five passes and their resends.
                A resend's row takes the place of the ask it was sent for.
  --judgments   one table per batch of readers, tab separated, columns code, my_answer, confidence, verdict,
                reason, recognized. verdict is one of the five words in VERDICTS.
  --key-table   the code table: a JSON list of {"code", "batch", "question_id", "key", ...}. It ties each
                reader's code to its item ("mmlupro-<question_id>") and to the item's key (the answer the
                bank marks as correct).
  --main-reads  optional, the main conversation's own reading of items the readers flagged (rules section 5):
                tab separated, a column code and a column of labels (--main-reads-column, default clear_flaw).
                A label in --main-reads-yes (default yes,是) means a clearly written flaw; any other label that is
                not empty means read, no clear flaw. Until the table is given, the share of flagged items with a
                clear flaw is reported as not given.

Which asks count: outcome "scored". An ask "without thinking" is a scored ask whose thinking_tokens is 0;
"thought" is a scored ask with thinking_tokens above 0. "Flagged" is an item whose reader gave any verdict
but 站得住 (it holds). "Not flagged" is an item the readers read and gave 站得住. Every number of section 6
is computed over all 200 items and over the items not flagged, except the readers' own shares.

M, for one item with n scored asks of which k are without thinking: k(n-k)/(n(n-1)), which is k(5-k)/20
when n = 5, the rules' formula. It estimates p(1-p) without bias for the item's share p of asks without
thinking. M is the mean over items with n >= 2. Its 90% range: the items are drawn again with replacement
BOOT times (seed SEED), and the 5th and 95th percentiles of M are taken.

Section 7 point 1 reads M over the items not flagged: 0.005 or more, usable; 0.002 up to 0.005, marginal;
below 0.002, not usable as it is. The band of M itself counts. The bands of the two ends of the 90% range are
reported beside it, and whether the range crosses a line. Point 2: more
than half the items flagged, ask whether to use each item's original four options; otherwise keep the
MMLU-Pro form and scale the pool by the share not flagged: the whole pool (POOL), and the pool without the
TRIAL items of this trial, which never enter the registered comparison.

Everything below main() works on plain rows, so test_new_passes_numbers.py can run it on made-up rows.
"""

import argparse
import csv
import json
import math
import statistics
import sys
from pathlib import Path

import numpy as np

HOLDS = "站得住"  # the item holds: exactly one best option
VERDICTS = (HOLDS, "不止一个选项说得通", "没有选项是对的", "题面缺东西", "判不了")  # holds, more than one, none right, something missing, cannot judge
JUDGMENT_COLUMNS = ("code", "my_answer", "confidence", "verdict", "reason", "recognized")
YES = ("yes", "是")
BOOT = 2000
SEED = 20261122
LINE_USABLE, LINE_MARGINAL = 0.005, 0.002
POOL = 2037  # the pool of section 3 of the rules
TRIAL = 200  # the items of this trial, taken from that pool
THINK_LONG = 1000
PASSES = 5
GROUP = "small_trial_new"


# ---------------------------------------------------------------- reading

def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def apply_resends(rows: list[dict]) -> list[dict]:
    """A resent ask takes the place of the ask it was sent for (as ccversions/analyze.py does)."""
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
        out.append({**new, "resent": True} if new else {**r, "resent": False})
    return out


def load_tsv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def readers(judgment_files: list[Path], key_table: list[dict]) -> tuple[dict, dict]:
    """{item: judgment row with its code and key} and what did not fit."""
    by_code = {k["code"]: k for k in key_table}
    out, problems = {}, {"unknown_codes": [], "repeated_codes": [], "bad_verdicts": [], "missing_columns": {}}
    for path in judgment_files:
        rows = load_tsv(path)
        cols = set(rows[0]) if rows else set()
        missing = [c for c in JUDGMENT_COLUMNS if c not in cols]
        if missing:
            problems["missing_columns"][path.name] = missing
        for r in rows:
            code = (r.get("code") or "").strip()
            k = by_code.get(code)
            if k is None:
                problems["unknown_codes"].append(code)
                continue
            item = f"mmlupro-{k['question_id']}"
            if item in out:
                problems["repeated_codes"].append(code)
                continue
            verdict = (r.get("verdict") or "").strip()
            if verdict not in VERDICTS:
                problems["bad_verdicts"].append({"code": code, "verdict": verdict})
            out[item] = {"code": code, "batch": k.get("batch"), "key": k["key"], "verdict": verdict,
                         "my_answer": (r.get("my_answer") or "").strip(), "confidence": (r.get("confidence") or "").strip(),
                         "recognized": (r.get("recognized") or "").strip()}
    return out, problems


def main_reads(path: Path | None, key_table: list[dict], column: str = "clear_flaw", yes=YES) -> dict | None:
    """{item: its label} for the rows with a known code and a label that is not empty, or None when not given."""
    if path is None:
        return None
    by_code = {k["code"]: f"mmlupro-{k['question_id']}" for k in key_table}
    rows = load_tsv(path)
    if rows and column not in rows[0]:
        raise SystemExit(f"--main-reads: {path.name} has no column {column!r}; columns: {list(rows[0])}")
    out = {}
    for r in rows:
        label = (r.get(column) or "").strip()
        if (r.get("code") or "").strip() in by_code and label:
            out[by_code[r["code"].strip()]] = label
    return out


# ---------------------------------------------------------------- one item, one ask

def item_of(r: dict) -> str:
    return str(r["unit"]).removeprefix("item:")


def tokens(r: dict) -> float:
    return float(r["thinking_tokens"])


def scored(rows: list[dict]) -> list[dict]:
    return [r for r in rows if r.get("outcome") == "scored" and isinstance(r.get("thinking_tokens"), (int, float))]


def per_item(rows: list[dict], items: list[str]) -> dict:
    """{item: its figures} over the scored asks of each item."""
    asks: dict = {i: [] for i in items}
    for r in scored(rows):
        if item_of(r) in asks:
            asks[item_of(r)].append(r)
    out = {}
    for i, a in asks.items():
        n = len(a)
        zero = [r for r in a if tokens(r) == 0]
        thought = [r for r in a if tokens(r) > 0]
        k = len(zero)
        logs = [math.log(tokens(r)) for r in thought]
        out[i] = {
            "n": n, "k": k,
            "pq": k * (n - k) / (n * (n - 1)) if n >= 2 else None,
            "thought": len(thought),
            "median_thinking": statistics.median([tokens(r) for r in thought]) if thought else None,
            "sd_ln_thinking": statistics.stdev(logs) if len(logs) >= 2 else None,
            "correct": sum(float(r.get("score") or 0) for r in a),
            "correct_thought": sum(float(r.get("score") or 0) for r in thought),
            "correct_without": sum(float(r.get("score") or 0) for r in zero),
        }
    return out


# ---------------------------------------------------------------- the numbers of section 6

def m_with_range(figs: dict, boot: int = BOOT, seed: int = SEED) -> dict:
    vals = np.array([f["pq"] for f in figs.values() if f["pq"] is not None], dtype=float)
    if not len(vals):
        return {"M": None, "items": 0}
    rng = np.random.default_rng(seed)
    draws = vals[rng.integers(0, len(vals), size=(boot, len(vals)))].mean(axis=1)
    return {"M": float(vals.mean()), "range_90": [float(np.percentile(draws, 5)), float(np.percentile(draws, 95))],
            "items": int(len(vals)), "draws": boot, "seed": seed}


def spread(values: list[float]) -> dict:
    v = sorted(x for x in values if x is not None)
    if not v:
        return {"n": 0}
    q = np.percentile(v, [10, 25, 50, 75, 90])
    return {"n": len(v), "min": v[0], "p10": float(q[0]), "p25": float(q[1]), "median": float(q[2]),
            "p75": float(q[3]), "p90": float(q[4]), "max": v[-1], "mean": float(np.mean(v))}


def higher_or_lower(a: list[float], b: list[float]) -> dict:
    """Median of the per-item medians in set a, beside the same in set b."""
    a = [x for x in a if x is not None]
    b = [x for x in b if x is not None]
    if not a or not b:
        return {"items": len(a), "other_items": len(b), "median": None, "other_median": None, "direction": "no data"}
    ma, mb = statistics.median(a), statistics.median(b)
    return {"items": len(a), "other_items": len(b), "median": ma, "other_median": mb,
            "direction": "higher" if ma > mb else "lower" if ma < mb else "equal"}


def numbers(rows: list[dict], items: list[str], flagged: set) -> dict:
    """Section 6 over one set of items. `flagged` is the set of flagged items (for the comparison)."""
    figs = per_item(rows, items)
    mine = [r for r in scored(rows) if item_of(r) in figs]
    zero = [r for r in mine if tokens(r) == 0]
    thought = [r for r in mine if tokens(r) > 0]
    full = [f for f in figs.values() if f["n"] == PASSES]
    never_right = sorted(i for i, f in figs.items() if f["n"] and f["correct"] == 0)
    mostly_wrong = sorted(i for i, f in figs.items() if f["n"] and f["correct"] < f["n"] / 2)
    med = {i: f["median_thinking"] for i, f in figs.items()}
    no_count = [r for r in rows if r.get("outcome") == "scored" and item_of(r) in figs
                and not isinstance(r.get("thinking_tokens"), (int, float))]
    return {
        "items": len(items),
        "scored_asks": len(mine),
        "scored_asks_without_a_token_count": len(no_count),
        "items_by_scored_asks": _count(f["n"] for f in figs.values()),
        "share_without_thinking": len(zero) / len(mine) if mine else None,
        "k_items_with_five_scored_asks": {str(k): sum(1 for f in full if f["k"] == k) for k in range(PASSES + 1)},
        "M": m_with_range(figs),
        "items_that_thought": sum(1 for f in figs.values() if f["thought"]),
        "median_thinking_per_item": spread([f["median_thinking"] for f in figs.values()]),
        "sd_ln_thinking_per_item": spread([f["sd_ln_thinking"] for f in figs.values()]),
        "items_median_thinking_above_1000": sum(1 for f in figs.values() if (f["median_thinking"] or 0) > THINK_LONG),
        "share_correct": sum(float(r.get("score") or 0) for r in mine) / len(mine) if mine else None,
        "share_correct_thought": sum(float(r.get("score") or 0) for r in thought) / len(thought) if thought else None,
        "share_correct_without_thinking": sum(float(r.get("score") or 0) for r in zero) / len(zero) if zero else None,
        "asks_thought": len(thought), "asks_without_thinking": len(zero),
        "items_thought_not_all_correct": sorted(i for i, f in figs.items() if f["thought"] and f["correct_thought"] < f["thought"]),
        "items_without_thinking_with_a_wrong_ask": sorted(i for i, f in figs.items() if f["k"] and f["correct_without"] < f["k"]),
        "items_never_right": never_right,
        "items_mostly_wrong": mostly_wrong,
        "thinking_flagged_vs_rest": higher_or_lower([med[i] for i in figs if i in flagged], [med[i] for i in figs if i not in flagged]),
        "thinking_never_right_vs_rest": higher_or_lower([med[i] for i in never_right], [med[i] for i in figs if i not in never_right]),
        "thinking_mostly_wrong_vs_rest": higher_or_lower([med[i] for i in mostly_wrong], [med[i] for i in figs if i not in mostly_wrong]),
    }


def time_and_usage(rows: list[dict]) -> dict:
    secs = [float(r["elapsed_seconds"]) for r in rows if isinstance(r.get("elapsed_seconds"), (int, float))]
    timed = sorted((r for r in rows if r.get("started_at") and r.get("weekly_utilization") is not None),
                   key=lambda r: r["started_at"])
    first, last = (timed[0], timed[-1]) if timed else (None, None)
    return {"asks": len(rows), "seconds_per_ask": spread(secs), "seconds_total": sum(secs),
            "weekly_reading_first": first["weekly_utilization"] if first else None,
            "weekly_reading_last": last["weekly_utilization"] if last else None,
            "weekly_reading_moved": (last["weekly_utilization"] - first["weekly_utilization"]) if timed else None,
            "first_ask_at": first["started_at"] if first else None, "last_ask_at": last["started_at"] if last else None,
            "asks_without_a_reading": len(rows) - len(timed)}


def band(m: float | None) -> str | None:
    if m is None:
        return None
    return "usable" if m >= LINE_USABLE else "marginal" if m >= LINE_MARGINAL else "not usable as it is"


def section_7(m: dict, flagged_share: float | None, readers_complete: bool, pool: int = POOL) -> dict:
    if m.get("M") is None:
        p1 = {"no_data": True}
    else:
        at_point, at_low, at_high = band(m["M"]), band(m["range_90"][0]), band(m["range_90"][1])
        p1 = {"M": m["M"], "range_90": m["range_90"], "band_of_M": at_point, "range_crosses_a_line": at_low != at_high,
              "band_of_range_low": at_low, "band_of_range_high": at_high,
              "band_that_counts": at_point, "lines": {"usable": LINE_USABLE, "marginal": LINE_MARGINAL},
              "provisional_readers_not_complete": not readers_complete}
    if flagged_share is None:
        p2 = {"no_data": True}
    else:
        over = flagged_share > 0.5
        p2 = {"share_flagged": flagged_share, "more_than_half": over,
              "what_next": "ask whether to use each item's original four options" if over
              else "keep the MMLU-Pro form (up to ten options)",
              "pool": pool, "pool_left_at_this_share": None if over else pool * (1 - flagged_share),
              "pool_without_the_trial_items": pool - TRIAL,
              "pool_without_the_trial_items_left_at_this_share": None if over else (pool - TRIAL) * (1 - flagged_share),
              "provisional_readers_not_complete": not readers_complete}
    return {"point_1_usable": p1, "point_2_reading": p2}


def report(rows: list[dict], key_table: list[dict], judged: dict, reader_problems: dict, reads: dict | None,
           group: str | None = GROUP, yes=YES) -> dict:
    rows = [r for r in rows if str(r.get("unit", "")).startswith("item:") and (group is None or r.get("group") == group)]
    items = sorted({f"mmlupro-{k['question_id']}" for k in key_table})
    in_rows = {item_of(r) for r in rows}
    flagged = {i for i in items if i in judged and judged[i]["verdict"] != HOLDS}
    not_flagged = sorted(i for i in items if i in judged and judged[i]["verdict"] == HOLDS)
    not_read = sorted(i for i in items if i not in judged)
    complete = not not_read and not any(reader_problems[k] for k in ("unknown_codes", "repeated_codes", "bad_verdicts")) \
        and not reader_problems["missing_columns"]
    all_items = numbers(rows, items, flagged)
    holding = numbers(rows, not_flagged, flagged)
    reading = {
        "items_read": len(judged), "items_not_read": not_read, "complete": complete, "problems": reader_problems,
        "verdicts": {v: sum(1 for i in items if i in judged and judged[i]["verdict"] == v) for v in VERDICTS},
        "share_flagged": len(flagged) / len(judged) if judged else None,
        "flagged": len(flagged),
        "holds_but_reader_answer_differs_from_key": sorted(
            i for i in not_flagged if judged[i]["my_answer"] != judged[i]["key"]),
        "recognized_yes": sum(1 for i in judged if judged[i]["recognized"] in YES),
    }
    if reads is None:
        reading["main_conversation_reads"] = {"given": False}
    else:
        yes_set = {y.lower() for y in yes}
        read_flagged = {i: v for i, v in reads.items() if i in flagged}
        clear = sum(1 for v in read_flagged.values() if v.lower() in yes_set)
        reading["main_conversation_reads"] = {
            "given": True, "flagged_items_read": len(read_flagged), "flagged_items": len(flagged),
            "read_enough": len(read_flagged) >= min(30, len(flagged)),
            "labels": _count(read_flagged.values()), "labels_meaning_a_clear_flaw": sorted(yes),
            "clear_flaw": clear,
            "share_with_a_clear_flaw": clear / len(read_flagged) if read_flagged else None,
            "read_but_not_flagged": sorted(set(reads) - flagged)}
    section_8 = {"items_thought_not_all_correct": all_items["items_thought_not_all_correct"],
                 "holds_but_reader_answer_differs_from_key": reading["holds_but_reader_answer_differs_from_key"]}
    section_8["to_check"] = sorted(set(section_8["items_thought_not_all_correct"]) | set(section_8["holds_but_reader_answer_differs_from_key"]))
    return {
        "group": group, "items": len(items), "items_with_rows": len(in_rows & set(items)),
        "rows_not_of_these_items": len(in_rows - set(items)),
        "outcomes": _count(r.get("outcome") for r in rows), "resent_asks": sum(1 for r in rows if r.get("resent")),
        "passes_seen": sorted({r.get("pass") for r in rows if r.get("pass") is not None}),
        "all_200": all_items, "not_flagged": holding, "reading": reading,
        "time_and_usage": time_and_usage(rows),
        "section_7": section_7(holding["M"], reading["share_flagged"], complete),
        "section_8_lists": section_8,
    }


def _count(values) -> dict:
    out: dict = {}
    for v in values:
        out[str(v)] = out.get(str(v), 0) + 1
    return dict(sorted(out.items()))


# ---------------------------------------------------------------- output

def _f(x, nd=4):
    return "none" if x is None else f"{x:.{nd}f}"


def _set_lines(name: str, n: dict) -> list[str]:
    m = n["M"]
    med, sd = n["median_thinking_per_item"], n["sd_ln_thinking_per_item"]
    L = [f"== {name}: {n['items']} items, {n['scored_asks']} scored asks; items by scored asks {json.dumps(n['items_by_scored_asks'])} ==",
         f"asks without thinking: {_f(n['share_without_thinking'])} ({n['asks_without_thinking']} of {n['scored_asks']})",
         f"k, items with five scored asks: {json.dumps(n['k_items_with_five_scored_asks'])}",
         (f"M = {_f(m['M'], 5)}, 90% range {_f(m['range_90'][0], 5)} to {_f(m['range_90'][1], 5)} over {m['items']} items"
          if m.get("M") is not None else "M: no data"),
         f"items that thought: {n['items_that_thought']}; per-item median thinking tokens (asks that thought): "
         + (f"median {med['median']:.0f}, p25 {med['p25']:.0f}, p75 {med['p75']:.0f}, min {med['min']:.0f}, max {med['max']:.0f}"
            if med.get("n") else "no data"),
         "per-item SD of ln(thinking tokens): " + (f"median {sd['median']:.3f}, p25 {sd['p25']:.3f}, p75 {sd['p75']:.3f} over {sd['n']} items"
                                                   if sd.get("n") else "no data"),
         f"items with median thinking above 1,000: {n['items_median_thinking_above_1000']}",
         f"share of asks matching the key: all {_f(n['share_correct'])}, thought {_f(n['share_correct_thought'])}, "
         f"without thinking {_f(n['share_correct_without_thinking'])}",
         f"items whose asks that thought were not all right: {len(n['items_thought_not_all_correct'])}; "
         f"items with a wrong ask without thinking: {len(n['items_without_thinking_with_a_wrong_ask'])}",
         f"items never right: {len(n['items_never_right'])}; mostly wrong: {len(n['items_mostly_wrong'])}"]
    for k, label in (("thinking_flagged_vs_rest", "flagged items"), ("thinking_never_right_vs_rest", "items never right"),
                     ("thinking_mostly_wrong_vs_rest", "items mostly wrong")):
        c = n[k]
        L.append(f"median thinking of {label}: {c['direction']} ({_f(c['median'], 0)} over {c['items']} items, "
                 f"the rest {_f(c['other_median'], 0)} over {c['other_items']})")
    return L


def text_report(rep: dict) -> str:
    rd, t, s7 = rep["reading"], rep["time_and_usage"], rep["section_7"]
    mr = rd["main_conversation_reads"]
    L = ["Small trial, second segment: 200 new items, five passes on 2.1.316, and the blind reading (rules sections 6 and 7).",
         f"items {rep['items']}, with rows {rep['items_with_rows']}; outcomes {json.dumps(rep['outcomes'])}; resent {rep['resent_asks']}; "
         f"passes {rep['passes_seen']}", ""]
    L += _set_lines("all 200 items", rep["all_200"]) + [""]
    L += _set_lines("items not flagged by the readers", rep["not_flagged"]) + [""]
    L += [f"== reading: {rd['items_read']} items read, complete {rd['complete']} ==",
          f"verdicts: {json.dumps(rd['verdicts'], ensure_ascii=False)}",
          f"share flagged: {_f(rd['share_flagged'])} ({rd['flagged']} items)",
          "main conversation's reads: " + ("not given" if not mr["given"] else
                                           f"{mr['flagged_items_read']} of {mr['flagged_items']} flagged read (enough: {mr['read_enough']}), "
                                           f"labels {json.dumps(mr['labels'], ensure_ascii=False)}, clear flaw {mr['clear_flaw']}, "
                                           f"share {_f(mr['share_with_a_clear_flaw'])}"),
          f"items that hold but the reader's answer differs from the key: {len(rd['holds_but_reader_answer_differs_from_key'])}",
          f"items the readers say they recognised: {rd['recognized_yes']}"]
    if any(rd["problems"][k] for k in rd["problems"]):
        L.append("problems in the readers' tables: " + json.dumps(rd["problems"], ensure_ascii=False))
    sp = t["seconds_per_ask"]
    L += ["", f"== time and usage: {t['asks']} asks ==",
          "seconds per ask: " + (f"median {sp['median']:.1f}, mean {sp['mean']:.1f}, max {sp['max']:.1f}" if sp.get("n") else "no data")
          + f"; total {t['seconds_total'] / 3600:.2f} hours",
          f"weekly reading: {t['weekly_reading_first']} at the first ask, {t['weekly_reading_last']} at the last, moved {t['weekly_reading_moved']}"]
    p1, p2 = s7["point_1_usable"], s7["point_2_reading"]
    L += ["", "== section 7 =="]
    L.append("point 1: no data" if p1.get("no_data") else
             f"point 1: M over items not flagged {_f(p1['M'], 5)} (90% range {_f(p1['range_90'][0], 5)} to {_f(p1['range_90'][1], 5)}); "
             f"range crosses a line: {p1['range_crosses_a_line']} (low end: {p1['band_of_range_low']}, high end: "
             f"{p1['band_of_range_high']}); BAND THAT COUNTS, the band of M: {p1['band_that_counts']}"
             + ("; PROVISIONAL, the readers' tables are not complete" if p1["provisional_readers_not_complete"] else ""))
    L.append("point 2: no data" if p2.get("no_data") else
             f"point 2: share flagged {_f(p2['share_flagged'])}; more than half: {p2['more_than_half']}; {p2['what_next']}"
             + (f"; pool of {p2['pool']} at this share: {p2['pool_left_at_this_share']:.0f}, without the trial's items "
                f"({p2['pool_without_the_trial_items']}): {p2['pool_without_the_trial_items_left_at_this_share']:.0f}"
                if p2["pool_left_at_this_share"] is not None else "")
             + ("; PROVISIONAL, the readers' tables are not complete" if p2["provisional_readers_not_complete"] else ""))
    L += ["", f"section 8 lists: {len(rep['section_8_lists']['items_thought_not_all_correct'])} items whose asks that thought "
              f"were not all right, {len(rep['section_8_lists']['holds_but_reader_answer_differs_from_key'])} that hold with the "
              f"reader's answer off the key, {len(rep['section_8_lists']['to_check'])} together"]
    return "\n".join(L) + "\n"


def per_item_table(rows: list[dict], key_table: list[dict], judged: dict, group: str | None = GROUP) -> str:
    rows = [r for r in rows if str(r.get("unit", "")).startswith("item:") and (group is None or r.get("group") == group)]
    items = sorted({f"mmlupro-{k['question_id']}" for k in key_table})
    figs = per_item(rows, items)
    code = {f"mmlupro-{k['question_id']}": k["code"] for k in key_table}
    head = ["item", "code", "verdict", "n", "k", "pq", "thought", "median_thinking", "sd_ln_thinking", "correct",
            "correct_thought", "correct_without"]
    lines = ["\t".join(head)]
    for i in items:
        f = figs[i]
        lines.append("\t".join(str(x) for x in [i, code[i], (judged.get(i) or {}).get("verdict", ""), f["n"], f["k"],
                                                 "" if f["pq"] is None else round(f["pq"], 4), f["thought"],
                                                 "" if f["median_thinking"] is None else f["median_thinking"],
                                                 "" if f["sd_ln_thinking"] is None else round(f["sd_ln_thinking"], 4),
                                                 f["correct"], f["correct_thought"], f["correct_without"]]))
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--graded", action="append", required=True, help="a graded.jsonl; give it once per plan")
    ap.add_argument("--judgments", action="append", default=[], help="a readers' batch table; give it once per batch")
    ap.add_argument("--key-table", required=True)
    ap.add_argument("--main-reads", help="the main conversation's reads of flagged items (a code column and a label column)")
    ap.add_argument("--main-reads-column", default="clear_flaw", help="the column of --main-reads that holds the labels")
    ap.add_argument("--main-reads-yes", default=",".join(YES), help="comma list of the labels that mean a clear flaw")
    ap.add_argument("--group", default=GROUP)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    rows = []
    for f in a.graded:
        rows += load_jsonl(Path(f))
    rows = apply_resends(rows)
    key_table = json.loads(Path(a.key_table).read_text(encoding="utf-8"))
    judged, problems = readers([Path(p) for p in a.judgments], key_table)
    yes = tuple(x.strip() for x in a.main_reads_yes.split(",") if x.strip())
    reads = main_reads(Path(a.main_reads) if a.main_reads else None, key_table, a.main_reads_column, yes)
    rep = report(rows, key_table, judged, problems, reads, a.group, yes)
    rep["inputs"] = {"graded": [Path(f).name for f in a.graded], "judgments": [Path(f).name for f in a.judgments],
                     "key_table": Path(a.key_table).name, "main_reads": Path(a.main_reads).name if a.main_reads else None,
                     "main_reads_column": a.main_reads_column, "main_reads_yes": list(yes)}
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (out / "report.txt").write_text(text_report(rep), encoding="utf-8")
    (out / "per_item.tsv").write_text(per_item_table(rows, key_table, judged, a.group), encoding="utf-8")
    print(text_report(rep), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
