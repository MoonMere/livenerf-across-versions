"""The check of the small trial's first segment: does one pass of the 78 panel items on 2.1.316 today come
out like 2.1.316 and the versions before it did in mid November? (Small trial of 22 November 2026, rules
section 4.)

    python -B old_pass_check.py --graded <graded.jsonl> [--graded <graded.jsonl of the resend>] \
        --mid-november <k05 table .tsv> --out <folder>

It reads graded rows (ccversions grade, one graded.jsonl per plan; a resend's rows take the place of the
asks they were sent for) and the table of mid November with one row per panel item, three columns: item,
old_versions_share_without_thinking (the share of asks without thinking over the versions up to 2.1.316)
and old_versions_median_thinking_tokens (the median thinking tokens over those asks, zeros included). It
writes report.json and report.txt.

"Without thinking" means a scored ask whose thinking_tokens is 0. First the rows are checked to be one pass
of the 78 items: the table has 78 items, no item has more than one ask, no ask is of an item outside the
table. Then the four conditions, all of which must hold for "matches":

  1  at least 77 of the 78 items have a scored ask (outcome "scored") in this pass, and every scored ask
     carries a thinking token count. One item may go without: in mid November 2 of the 7,956 asks of the
     versions up to 2.1.316 were void. An item without a scored ask has no ask that can count in 2 to 4.
  2  of the five items the versions up to 2.1.316 almost never thought on in mid November (FIVE below,
     named in the rules), at least four have an ask without thinking
  3  of the items those versions always thought on in mid November (share without thinking 0 in the
     table; 63 items), at most two have an ask without thinking
  4  over the items that thought in this pass: each ask's thinking tokens divided by the item's mid
     November median; the geometric mean of those ratios lies between 0.75 and 1.33 (both included).
     An item whose mid November median is 0 has no ratio and is left out (it is named in the report).

Everything below main() works on plain rows, so test_old_pass_check.py can run it on made-up rows.
"""

import argparse
import csv
import json
import math
import sys
from pathlib import Path

FIVE = ("mmlupro-3000", "mmlupro-3672", "mmlupro-443", "mmlupro-4920", "mmlupro-5498")
ITEMS = 78
MIN_SCORED = 77
ALWAYS = 63
RATIO_LOW, RATIO_HIGH = 0.75, 1.33
MIN_FIVE_WITHOUT = 4
MAX_ALWAYS_WITHOUT = 2
SHARE_COL, MEDIAN_COL = "old_versions_share_without_thinking", "old_versions_median_thinking_tokens"


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


def load_mid_november(path: Path) -> dict:
    """{item id: {"share_without": float, "median": float}} from the table of mid November."""
    with open(path, encoding="utf-8", newline="") as f:
        return {r["item"]: {"share_without": float(r[SHARE_COL]), "median": float(r[MEDIAN_COL])}
                for r in csv.DictReader(f, delimiter="\t")}


# ---------------------------------------------------------------- the check

def item_of(r: dict) -> str:
    return str(r["unit"]).removeprefix("item:")


def has_tokens(r: dict) -> bool:
    t = r.get("thinking_tokens")
    return isinstance(t, (int, float)) and not isinstance(t, bool) and t >= 0


def check(rows: list[dict], mid: dict, group: str | None = "small_trial_old") -> dict:
    rows = [r for r in rows if str(r.get("unit", "")).startswith("item:") and (group is None or r.get("group") == group)]
    by_item: dict = {}
    for r in rows:
        by_item.setdefault(item_of(r), []).append(r)
    panel = sorted(mid)
    scored = {i: [r for r in by_item.get(i, []) if r.get("outcome") == "scored"] for i in panel}

    # the rows are one pass of the 78 items
    more_than_one = sorted(i for i in panel if len(by_item.get(i, [])) > 1)
    not_in_table = sorted(set(by_item) - set(mid))
    rows_ok = {"items_in_table": len(panel), "expected": ITEMS, "items_with_more_than_one_ask": more_than_one,
               "items_not_in_the_table": not_in_table,
               "holds": len(panel) == ITEMS and not more_than_one and not not_in_table}

    # 1
    not_scored = sorted(i for i in panel if not scored[i])
    no_tokens = sorted(i for i in panel if scored[i] and not all(has_tokens(r) for r in scored[i]))
    with_scored = len(panel) - len(not_scored)
    c1 = {"items_in_table": len(panel), "items_with_a_scored_ask": with_scored, "needed": MIN_SCORED,
          "items_without_a_scored_ask": not_scored, "items_whose_scored_ask_has_no_thinking_tokens": no_tokens,
          "outcomes": _count(r.get("outcome") for r in rows),
          "holds": with_scored >= MIN_SCORED and not no_tokens}

    def without(i):  # this pass has an ask of item i without thinking
        return any(has_tokens(r) and r["thinking_tokens"] == 0 for r in scored[i])

    def thought(i):
        return [r for r in scored[i] if has_tokens(r) and r["thinking_tokens"] > 0]

    # 2
    five = {i: {"without_thinking_now": without(i) if i in scored else None,
                "mid_november_share_without": (mid.get(i) or {}).get("share_without")} for i in FIVE}
    n_five = sum(bool(v["without_thinking_now"]) for v in five.values())
    c2 = {"items": five, "without_thinking_now": n_five, "needed": MIN_FIVE_WITHOUT,
          "all_five_in_table": all(i in mid for i in FIVE), "holds": all(i in mid for i in FIVE) and n_five >= MIN_FIVE_WITHOUT}

    # 3
    always = sorted(i for i in panel if mid[i]["share_without"] == 0)
    always_without = sorted(i for i in always if without(i))
    c3 = {"items_always_thinking_in_mid_november": len(always), "expected": ALWAYS,
          "of_those_without_thinking_now": always_without, "allowed": MAX_ALWAYS_WITHOUT,
          "holds": len(always) == ALWAYS and len(always_without) <= MAX_ALWAYS_WITHOUT}

    # 4
    logs, used, left_out = [], [], []
    for i in panel:
        for r in thought(i):
            m = mid[i]["median"]
            if m > 0:
                ratio = r["thinking_tokens"] / m
                logs.append(math.log(ratio))
                used.append({"item": i, "thinking_tokens": r["thinking_tokens"], "mid_november_median": m, "ratio": ratio})
            else:
                left_out.append({"item": i, "thinking_tokens": r["thinking_tokens"], "mid_november_median": m})
    gm = math.exp(sum(logs) / len(logs)) if logs else None
    c4 = {"items_that_thought": len({u["item"] for u in used} | {x["item"] for x in left_out}),
          "ratios_used": len(used), "left_out_median_zero": left_out, "geometric_mean": gm,
          "low": RATIO_LOW, "high": RATIO_HIGH,
          "lowest_ratio": min((u["ratio"] for u in used), default=None),
          "highest_ratio": max((u["ratio"] for u in used), default=None),
          "holds": gm is not None and RATIO_LOW <= gm <= RATIO_HIGH, "ratios": used}

    return {"rows_are_one_pass_of_the_78": rows_ok, "condition_1_scored_with_tokens": c1,
            "condition_2_five_rarely_thinking": c2, "condition_3_always_thinking": c3, "condition_4_thinking_ratio": c4,
            "matches": rows_ok["holds"] and c1["holds"] and c2["holds"] and c3["holds"] and c4["holds"],
            "asks_read": len(rows), "resent_asks": sum(1 for r in rows if r.get("resent"))}


def _count(values) -> dict:
    out: dict = {}
    for v in values:
        out[str(v)] = out.get(str(v), 0) + 1
    return dict(sorted(out.items()))


# ---------------------------------------------------------------- output

def text_report(rep: dict) -> str:
    r0 = rep["rows_are_one_pass_of_the_78"]
    c1, c2, c3, c4 = (rep[k] for k in ("condition_1_scored_with_tokens", "condition_2_five_rarely_thinking",
                                        "condition_3_always_thinking", "condition_4_thinking_ratio"))
    yes = lambda b: "holds" if b else "DOES NOT HOLD"  # noqa: E731
    gm = "none" if c4["geometric_mean"] is None else f"{c4['geometric_mean']:.3f}"
    L = ["Small trial, first segment: the 78 panel items once on 2.1.316, set beside mid November (rules section 4).",
         f"Asks read: {rep['asks_read']} (resent: {rep['resent_asks']}); outcomes {json.dumps(c1['outcomes'])}",
         f"The rows are one pass of the {r0['expected']} items: {yes(r0['holds'])}. {r0['items_in_table']} items in the table"
         + (f"; more than one ask: {r0['items_with_more_than_one_ask']}" if r0["items_with_more_than_one_ask"] else "")
         + (f"; not in the table: {r0['items_not_in_the_table']}" if r0["items_not_in_the_table"] else ""), "",
         f"1. At least {c1['needed']} of the {c1['items_in_table']} items have a scored ask, and every scored ask has a "
         f"thinking token count: {yes(c1['holds'])}. {c1['items_with_a_scored_ask']} items scored"
         + (f"; without a scored ask: {c1['items_without_a_scored_ask']}" if c1["items_without_a_scored_ask"] else "")
         + (f"; no token count: {c1['items_whose_scored_ask_has_no_thinking_tokens']}"
            if c1["items_whose_scored_ask_has_no_thinking_tokens"] else ""),
         f"2. At least {c2['needed']} of the five rarely thinking items answered without thinking: {yes(c2['holds'])}. "
         f"{c2['without_thinking_now']} of 5: " + ", ".join(f"{i} {'without' if v['without_thinking_now'] else 'with'}"
                                                          for i, v in c2["items"].items()),
         f"3. At most {c3['allowed']} of the {c3['items_always_thinking_in_mid_november']} always thinking items answered "
         f"without thinking: {yes(c3['holds'])}. {len(c3['of_those_without_thinking_now'])}"
         + (f": {c3['of_those_without_thinking_now']}" if c3["of_those_without_thinking_now"] else ""),
         f"4. Geometric mean of (thinking tokens now / mid November median) between {c4['low']} and {c4['high']}: "
         f"{yes(c4['holds'])}. {gm} over {c4['ratios_used']} items"
         + (f" (lowest {c4['lowest_ratio']:.3f}, highest {c4['highest_ratio']:.3f})" if c4["ratios_used"] else "")
         + (f"; left out, median 0 in mid November: {[x['item'] for x in c4['left_out_median_zero']]}" if c4["left_out_median_zero"] else ""),
         "", f"MATCHES MID NOVEMBER: {'yes' if rep['matches'] else 'no'}"]
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--graded", action="append", required=True, help="a graded.jsonl; give it once per plan")
    ap.add_argument("--mid-november", required=True, help="the table of mid November, one row per panel item")
    ap.add_argument("--group", default="small_trial_old", help="the group of the rows to read")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    rows = []
    for f in a.graded:
        rows += load_jsonl(Path(f))
    rep = check(apply_resends(rows), load_mid_november(Path(a.mid_november)), a.group)
    rep["inputs"] = {"graded": [Path(f).name for f in a.graded], "mid_november": Path(a.mid_november).name}
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (out / "report.txt").write_text(text_report(rep), encoding="utf-8")
    print(text_report(rep), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
