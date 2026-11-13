"""Accuracy scored two more ways, beside the benchmark's key. Nothing here is a declared test.

Added on 13 November 2026 while the group xhigh_recheck was being sent, before any answer or score of
xhigh_recheck or high_recheck had been looked at. What is scored how is fixed by
rescore_keys_20261113.json, which is read off the item audit of the LiveNerf authors.

    original   every question, the benchmark's key: the figure analysis.py gives
    sound      the benchmark's key, on the questions the audit classes as sound only
    corrected  The questions in "left_out" are left out. On a question in "also_accepted" an ask that
               gave the listed option is right as well. On the question in "replaced" an ask is right
               when it gave the listed value and wrong otherwise. Every other ask keeps its score.

Which asks count, the ten versions, the two groups of five, the question range and the two p values
are those of analysis.py (its functions are used as they are).

    python -B rescore.py --settings <settings.toml> --out <folder> [--main-graded <graded.jsonl> ...]
"""

import argparse
import json
import sys
from pathlib import Path

import analysis as A

HERE = Path(__file__).resolve().parent
KEYS_FILE = HERE / "rescore_keys_20261113.json"
WAYS = ("original", "sound", "corrected")


def load_keys(path: Path = KEYS_FILE) -> dict:
    return json.loads(path.read_text())


def item(r: dict) -> str:
    return r["unit"].split(":", 1)[1]


def _norm(x) -> str:
    return "" if x is None else str(x).strip().replace(",", "")


def corrected(r: dict, keys: dict) -> float:
    i = item(r)
    if i in keys["replaced"]:
        return 1.0 if _norm(r.get("answer")) == keys["replaced"][i] else 0.0
    if i in keys["also_accepted"] and _norm(r.get("answer")) == keys["also_accepted"][i]:
        return 1.0
    return float(r["score"])


def _eleventh(asks: list[dict], value, units: list[str]) -> dict:
    m = A.cell_means([r for r in asks if r["version"] == A.ELEVENTH], value).get(A.ELEVENTH, {})
    have = [m[u] for u in units if u in m]
    return {"accuracy_per_cent": (sum(have) / len(have) * 100) if have else None, "questions": len(have)}


def ways(asks: list[dict], keys: dict, which=WAYS) -> dict:
    """asks: the scored asks that count (analysis.counted). One comparison of the later five versions
    with the earlier five per way of scoring, none with a declaration."""
    sound = {"item:" + i for i in keys["sound"]}
    left = {"item:" + i for i in keys["left_out"]}
    plan = {"original": (asks, A.correct),
            "sound": ([r for r in asks if r["unit"] in sound], A.correct),
            "corrected": ([r for r in asks if r["unit"] not in left], lambda r: corrected(r, keys))}
    out = {}
    for name in which:
        sub, value = plan[name]
        c = A.one_comparison(sub, value, "accuracy")
        if not c.get("no_data"):
            c["version_2_1_323"] = _eleventh(sub, value, sorted({r["unit"] for r in sub}))
        out[name] = c
    return out


def report(xrows: list[dict], hrows: list[dict], mrows: list[dict], keys: dict, more: list[str], which=WAYS) -> dict:
    rep: dict = {"what": "accuracy scored two more ways, no declared test", "keys_file": KEYS_FILE.name}
    if xrows:
        asks, info = A.counted(xrows, "xhigh_recheck")
        rep["xhigh_recheck"] = {"scored_asks_that_count": info["scored_asks_that_count"], **ways(asks, keys, which)}
    if hrows:
        s1, s2 = set(range(1, 13)), set(range(13, 25))
        a1, i1 = A.counted(hrows, "high_recheck", passes=s1)
        rep["high_recheck_stage_1"] = {"scored_asks_that_count": i1["scored_asks_that_count"], **ways(a1, keys, which)}
        _, i2 = A.counted(hrows, "high_recheck", passes=s2)
        if i2["records"]:
            both, ib = A.counted(hrows, "high_recheck", passes=s1 | s2)
            rep["high_recheck_both_stages"] = {"scored_asks_that_count": ib["scored_asks_that_count"],
                                               **ways(both, keys, which)}
    if mrows:
        asks = [r for r in mrows if r.get("group") == "main" and r.get("outcome") == "scored" and r["version"] in A.TEN]
        on24 = {"item:" + i for i in more}
        rep["main_on_the_78_seen_before_this_was_written"] = {"scored_asks": len(asks), **ways(asks, keys, which)}
        sub = [r for r in asks if r["unit"] in on24]
        rep["main_on_the_24_seen_before_this_was_written"] = {"scored_asks": len(sub), **ways(sub, keys, which)}
    return rep


def text_report(rep: dict) -> str:
    lines = [rep["what"], ""]
    for name, block in rep.items():
        if not isinstance(block, dict):
            continue
        lines.append(name)
        for way in WAYS:
            c = block.get(way)
            if c is None:
                continue
            if c.get("no_data"):
                lines.append(f"  {way:<10} no question with a scored ask from each of the ten versions")
                continue
            e = c["version_2_1_323"]
            e_txt = "none" if e["accuracy_per_cent"] is None else f"{e['accuracy_per_cent']:.1f}% on {e['questions']} questions"
            lines.append(f"  {way:<10} {c['questions']:>2} questions  later five minus earlier five "
                         f"{c['difference_points']:+.2f} points (range {c['range_points'][0]:+.2f} to {c['range_points'][1]:+.2f})"
                         f"  p over the 252 splits {c['p']:.3f}  p shuffling asks {c['ask_shuffle_for_comparison_only']['p']:.4f}"
                         f"  no declaration  2.1.323: {e_txt}")
        lines.append("")
    return "\n".join(lines)


def main(argv=None) -> int:
    from ccversions import formal, settings as settings_mod

    ap = argparse.ArgumentParser()
    ap.add_argument("--settings", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--main-graded", action="append", default=[],
                    help="a graded.jsonl of the registered run, given once per pass")
    ap.add_argument("--ways", default=",".join(WAYS), help="which ways of scoring, comma separated")
    ap.add_argument("--main-only", action="store_true", help="leave the two new groups unread")
    a = ap.parse_args(argv)
    which = tuple(w for w in a.ways.split(",") if w)
    keys = load_keys()
    more = json.loads((HERE / "items_think_more_24.json").read_text())["items"]
    xrows, hrows, mrows = [], [], []
    if not a.main_only:
        s = settings_mod.load(a.settings)
        for f in formal.Driver(s, HERE / "run_x.json").graded([f"X{n}{x}" for n in range(1, 6) for x in ("", "r")]):
            xrows += A.load_jsonl(f)
        for f in formal.Driver(s, HERE / "run_h.json").graded([f"H{n}{x}" for n in range(1, 25) for x in ("", "r")]):
            hrows += A.load_jsonl(f)
    for f in a.main_graded:
        mrows += A.load_jsonl(Path(f))
    rep = report(xrows, hrows, mrows, keys, more, which)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "rescore.json").write_text(json.dumps(rep, indent=1) + "\n")
    (out / "rescore.txt").write_text(text_report(rep))
    print(text_report(rep), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
