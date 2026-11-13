"""Extra numbers and wordings fixed in the preregistration before the reports were opened.

    python -B extra_numbers.py --author-repo DIR [--graded FILE ...] [--raw-dir DIR ...]
        [--final-report FILE] [--interim-report FILE] [--items FILE] [--out DIR]

The preregistration's change log entry "13 November 2026: extra numbers and wordings, fixed before the
reports are opened" lists 18 numbers to report beside the registered ones. This program computes items 1
to 8, 13 to 15 and 18. Items 9 to 12, 16 and 17 are done elsewhere. None of these numbers has a verdict of
its own.

Which differences are declared, and on which segment, is read from the registered program's own reports
(ccversions/analyze.py, run by ccversions/formal.py): the final report after all passes, and the interim
report after passes 1 and 2. This program never decides that again. It rebuilds the arrays of group main
from the same graded rows with the registered functions (analyze.apply_resends, analyze.Main,
analyze.METRICS, judge.residuals, judge.scan, judge.bootstrap_range), and first checks that the scans it
rebuilds name the same segments with the same sizes as the two reports. If they do not, it stops, because
its numbers would then belong to other data.

Words used below

  cell        one item in one pass. A cell counts when every version of group main has a record in it
              (section 3), exactly as analyze.Main decides.
  value       one ask's number in a counted cell: 1 or 0 for accuracy, ln(thinking tokens + 1) for thinking,
              NaN where the ask has no such number (analyze.METRICS).
  residual    a value minus the mean of the values of its cell (judge.residuals).
  difference  of a segment (a run of consecutive versions, first and last version included): the mean
              residual inside it minus the mean residual outside it, all passes pooled unless said
              otherwise. This is the registered scan's own `diff`, computed with judge.scan for that one
              segment. For accuracy it is a share (0.03 is 3 points). For thinking it is a difference of
              logs, shown as a per cent change exp(diff) - 1 of the geometric mean of thinking tokens + 1.
  range       the 2.5 and 97.5 per cent points of the difference when the 78 items are redrawn with
              replacement 10,000 times, seed 20261111 (judge.bootstrap_range).
  half, third the tests "less than half" (items 1 and 2), "halves" (item 5) and "less than a third" (item
              14) are made on the scale the scan works on: shares for accuracy, logs for thinking.

What each item computes (function in brackets)

  1  (item_1_blocked_tools) For each declared difference: (a) the share of scored asks that tried a tool,
     inside the segment and outside it, as raw shares and as a difference with its range; (b) the same
     segment's difference over the scored asks that did not try a tool, with its range. Case "may come
     from the blocked tools" when the range in (a) leaves out zero and the difference in (b) divided by
     the declared difference is below 0.5 (less than half, or the other sign).
  2  (item_2_unread_answers) An answer is read when the graded row's `answer` (LiveNerf's extract_answer on
     the final text, None without an <answer> block) has the form the item's grader accepts: for a choice
     item one letter after the grader's own trimming of spaces and round brackets, for an integer item the
     grader's integer pattern, for a rational item LiveNerf's own rational() parser. The key is not used.
     Gives each version's share of scored asks that were not read, scans that share (judge.judge, 2,000
     shuffles, no minimum size, as section 8), and for each declared accuracy difference the same
     segment's difference over read answers alone. Case "the format of the answers changed" when that
     difference divided by the declared difference (errors and voids left out) is below 0.5.
  3  (item_3_zero_thinking) For each declared thinking difference: the share of asks with zero thinking
     inside and outside, the ratio over asks with thinking above zero (the difference of the scan, on
     those asks only, as exp(diff)), the ratio of the medians, and the ratio of the totals per ask (each
     side's total divided by its number of asks, so that the number of versions on each side does not
     enter). Also the sentence that writes the per cent of section 6 as a change in the geometric mean.
  4  (item_4_pass_three_alone) For each of the scans (accuracy both ways, thinking): the segment the
     interim report ranks first on passes 1 and 2, measured on pass 3 alone with its range. Always given.
  5  (item_5_items_and_families) For each declared difference and each way of counting that names it: the
     difference with each item left out in turn (the smallest and the largest, and every item whose
     removal leaves at most half of the difference), and the difference within each family.
  6  (item_6_where_it_starts_and_ends) For each scan: the items are redrawn 2,000 times (seed 20261111),
     the scan is run on each draw without shuffles (judge.scan over every segment, the same rule as
     judge.judge for a segment that starts at the first version), and the middle 95 per cent of the first
     and of the last version of the segment ranked first is given. When either covers more than one
     version, the span is the wording.
  7  (item_7_two_ways_of_counting) For the final report and the interim report: the segments named by the
     two ways of counting, each segment's difference under both ways, and which of four cases applies,
     with its sentence.
  8  (item_8_cut_at_2_1_303) From 2.1.303 on against the versions before it: accuracy (errors and voids
     left out) with its range, and thinking as a ratio with its range. Case "range leaves out zero while
     the scan declares nothing", for each test on its own, with the fixed reason.
  13 (item_13_third_pass) For each test: the figure on passes 1 and 2 (interim report) and on all passes
     (final report), and the wording: "not confirmed by the third pass" when the two-pass test was
     declared and the final one is not, and the p < 0.05 sentence when two passes had p < 0.05 without a
     declared difference.
  14 (item_14_both_sides) The three mean residuals (before, segment, after) of every scan, and the sentence
     for a declared segment that is higher than the rest while before and after differ by less than a
     third of its difference.
  15 (item_15_unchanged_request) For each declared difference: whether each end of the segment falls
     between two versions of one group of versions that send the same first request size (the groups of
     the final report, section 8), the nearest version at which the request size did change, and the scan
     over groups (the registered one for accuracy, the same computation for thinking). The fixed sentence
     when a difference called lower starts at a version that sends the same request as the one before it.
  18 (item_18_how_thinking_is_counted) From the raw records of group main: for every version, whether the
     output tokens of the result line equal the sum over the ask's top-level assistant messages (each
     message counted once by its id, at the largest output count any of its lines carries), split by asks
     that tried a tool and asks that did not. Also the ratio of thinking of group api against group author
     on 2.1.322, copied from the final report (section 9).

Outputs in --out: extra_numbers.json (every number) and extra_numbers.md (the same, to read). No answer
text, question text or key is written. Both files are checked for paths and e-mail addresses with the
registered pattern (grade.PUBLIC_BAD) before they are kept.
"""

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROGRAM = HERE.parent
PROJECT = PROGRAM.parent
sys.dont_write_bytecode = True
if str(PROGRAM) not in sys.path:
    sys.path.insert(0, str(PROGRAM))

import numpy as np  # noqa: E402

from ccversions import analyze, extract, judge  # noqa: E402
from ccversions.grade import PUBLIC_BAD  # noqa: E402

# Default places of the real data, relative to the project folder that holds the program folder.
DATA = PROJECT / "本机数据"
FORMAL = DATA / "正式跑"
DEFAULT_PLANS = ("F1", "F1r", "F2", "F2r", "F3", "F3r")  # formal.py: name_prefix "F", passes and their resends
DEFAULT_GRADED_DIR = FORMAL / "graded"
DEFAULT_RAW_DIR = DATA / "原始记录"
DEFAULT_FINAL = FORMAL / "final" / "report.json"
DEFAULT_INTERIM = FORMAL / "interim" / "report.json"
DEFAULT_ITEMS = DATA / "题目" / "livenerf_panel_78.json"
DEFAULT_OUT = DATA / "多报的数"

ENTRY = "13 November 2026: extra numbers and wordings, fixed before the reports are opened"
ITEMS_HERE = (1, 2, 3, 4, 5, 6, 7, 8, 13, 14, 15, 18)
ITEMS_ELSEWHERE = (9, 10, 11, 12, 16, 17)

SEED = judge.SEED            # 20261111
DRAWS = 10_000               # items redrawn for a range
PLACEMENT_DRAWS = 2_000      # item 6
SCAN_SHUFFLES = 2_000        # item 2's scan, and item 15's scan over groups (section 8)
HALF = 0.5                   # items 1, 2 and 5
THIRD = 1.0 / 3.0            # item 14
LINE = judge.ALPHA           # 0.05
POINTED_VERSION = analyze.POINTED_VERSION  # "2.1.303"
MAIN = analyze.MAIN_GROUP

# The three scans of the registered report: key in the report, key in analyze.METRICS, effect, minimum size.
RUNS = {
    "accuracy": {"metric": "accuracy", "effect": "diff", "test": "accuracy", "min": judge.MIN_DIFF_ACCURACY,
                 "label": "accuracy, errors and voids left out"},
    "accuracy_errors_and_voids_as_wrong": {"metric": "accuracy_bad_as_wrong", "effect": "diff", "test": "accuracy",
                                           "min": judge.MIN_DIFF_ACCURACY,
                                           "label": "accuracy, errors and voids counted as wrong"},
    "thinking": {"metric": "log_thinking", "effect": "ratio", "test": "thinking", "min": judge.MIN_RATIO_THINKING,
                 "label": "thinking tokens"},
}
TEST_DECLARED = {"accuracy": "accuracy_difference_declared", "thinking": "thinking_difference_declared"}
FAMILY_NAMES = {"mmlupro": "MMLU-Pro", "gpqa": "GPQA", "aime": "AIME", "comps": "competition maths"}

SENTENCES = {
    "item_1": "It may come from the blocked tools: the share of asks that tried a tool differs between the segment "
              "and the other versions, and over the asks that did not try a tool the difference is less than "
              "half as large or has the other sign.",
    "item_2": "The format of the answers changed: more than half of this difference is gone when only the answers "
              "that the graders can read are counted.",
    "item_8": "The two can differ because the scan pays for choosing among {segments} segments, and a cut named "
              "beforehand does not. This cut was named by a post, which is why section 8 does not let it decide.",
    "item_13_not_confirmed": "not confirmed by the third pass",
    "item_14": "The versions before and after the segment are at about the same level.",
    "item_15": "From {x} on it is lower. {x} sends the same request as the version before it. This experiment "
               "cannot tell whether the server treats {x} differently or the cut fell here by luck.",
}


# ------------------------------------------------------------------------------------------ small helpers

def clean(x):
    """JSON-safe copy: numpy numbers to Python numbers, NaN and infinities to None, tuples to lists."""
    if isinstance(x, dict):
        return {str(k): clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [clean(v) for v in x]
    if isinstance(x, (np.bool_, bool)):
        return bool(x)
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating, float)):
        f = float(x)
        return None if math.isnan(f) or math.isinf(f) else f
    if isinstance(x, np.ndarray):
        return clean(x.tolist())
    return x


def shown(x, effect: str):
    """A difference as reported: a share for accuracy, exp(x) - 1 for thinking."""
    if x is None:
        return None
    return float(x) if effect == "diff" else float(math.exp(x) - 1.0)


def excludes_zero(rng) -> bool | None:
    if rng is None or rng[0] is None or rng[1] is None:
        return None
    return bool(rng[0] > 0 or rng[1] < 0)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def where(path: Path) -> str:
    """A path for the outputs: relative to the project folder when it lies inside it, else the name only."""
    p = Path(path).resolve()
    try:
        return str(p.relative_to(PROJECT.resolve()))
    except ValueError:
        return p.name


def seg_text(versions: list[str], a: int, b: int) -> str:
    return versions[a] if a == b else f"{versions[a]} to {versions[b]}"


def side_values(val: np.ndarray, a: int, b: int) -> tuple[np.ndarray, np.ndarray]:
    """The values that count inside versions a..b and outside them, flattened."""
    inside = val[..., a:b + 1]
    outside = np.concatenate([val[..., :a], val[..., b + 1:]], axis=-1)
    return inside[~np.isnan(inside)], outside[~np.isnan(outside)]


def seg_diff(val: np.ndarray, a: int, b: int) -> float | None:
    """The segment's difference as the registered scan computes it (judge.residuals, judge.pass_sums,
    judge.scan for this one segment), all passes of `val` pooled. None when a side has no value."""
    if np.isnan(val).all():
        return None
    resid, mask = judge.residuals(val)
    sums, counts = judge.pass_sums(resid, mask)
    s, n = sums.sum(axis=0), counts.sum(axis=0)
    if n[a:b + 1].sum() == 0 or n.sum() - n[a:b + 1].sum() == 0:
        return None
    diff, _ = judge.scan(s, n, np.array([a]), np.array([b]))
    return float(diff[0])


def seg_range(val: np.ndarray, a: int, b: int, effect: str, draws: int) -> list | None:
    """judge.bootstrap_range: the middle 95 per cent over redrawn items, shown as the difference is shown."""
    if np.isnan(val).all():
        return None
    lo, hi = judge.bootstrap_range(val, a, b, effect=effect, draws=draws, seed=SEED)
    return [lo, hi]


# ------------------------------------------------------------------------------------------ what was read

def load_panel(path: Path) -> dict:
    """{unit key: {"family", "scorer"}} from the item file. Only these two fields are read: question texts and
    keys stay where they are."""
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    return {f"item:{it['id']}": {"family": it["family"], "scorer": it["scorer"]} for it in doc["items"]}


def author_parsers(author_repo: Path):
    """LiveNerf's own rational() parser, imported from the author's repository unchanged."""
    repo = str(Path(author_repo).resolve())
    if repo not in sys.path:
        sys.path.insert(0, repo)
    from livenerf.benchmarks.data import rational  # noqa: PLC0415

    if not str(Path(sys.modules["livenerf.benchmarks.data"].__file__).resolve()).startswith(repo):
        raise RuntimeError("livenerf was imported from another place than --author-repo")
    return rational


def make_is_read(rational):
    """is_read(answer, scorer): does the answer have the form the item's grader accepts? (item 2)

    choice    LiveNerf's choice_score compares answer.strip().strip("()").strip().upper() with the key
              letter, so the form is one letter A to Z after that same trimming.
    integer   LiveNerf's integer_score removes white space and commas, then needs -?digits.
    rational  LiveNerf's rational_score needs rational(answer) to be a number.
    An answer of None (no <answer> block) is never read."""
    def is_read(answer, scorer: str) -> bool:
        if answer is None:
            return False
        if scorer == "choice":
            return re.fullmatch(r"[A-Z]", answer.strip().strip("()").strip().upper()) is not None
        if scorer == "integer":
            return re.fullmatch(r"-?\d+", re.sub(r"[\s,]", "", answer)) is not None
        if scorer == "rational":
            return rational(answer) is not None
        raise ValueError(f"unknown scorer {scorer!r}")
    return is_read


# ------------------------------------------------------------------------------------------ the data

class Context:
    """Group main laid out as the registered analysis lays it out, and the two registered reports."""

    def __init__(self, rows: list[dict], final: dict, interim: dict | None, panel: dict, is_read, *,
                 draws: int = DRAWS, placement_draws: int = PLACEMENT_DRAWS, scan_shuffles: int = SCAN_SHUFFLES):
        self.final, self.interim, self.panel, self.is_read = final, interim, panel, is_read
        self.draws, self.placement_draws, self.scan_shuffles = draws, placement_draws, scan_shuffles
        rows = analyze.apply_resends(rows)
        # analyze.analyze: a version the server refused is out of the comparison as a whole
        self.refused = sorted({r["version"] for r in rows if r.get("group") == MAIN and r.get("outcome") == "error"
                               and r.get("reason") == "min_version"}, key=analyze.version_key)
        rows = [r for r in rows if not (r.get("group") == MAIN and r.get("version") in self.refused)]
        self.rows = rows
        self.versions = list(final["versions"])
        self.main = analyze.Main(rows, list(self.versions))
        self.V = len(self.versions)
        self.passes = list(self.main.passes)
        self._cache: dict = {}
        missing = sorted(u for u in self.main.units if u not in panel)
        if missing:
            raise RuntimeError(f"units not in the item file: {missing[:5]}")

    # extra values per ask, beside analyze.METRICS
    def _extra(self, name: str):
        sc = analyze._scored  # noqa: SLF001 - the registered test of "scored"

        def thinking(r):
            return r.get("thinking_tokens") if sc(r) else None

        def read(r):
            return self.is_read(r.get("answer"), self.panel[r["unit"]]["scorer"])

        return {
            "unread": lambda r: (0.0 if read(r) else 1.0) if sc(r) else math.nan,
            "accuracy_read": lambda r: float(r["score"]) if sc(r) and read(r) else math.nan,
            "thinking_tokens": lambda r: float(thinking(r)) if thinking(r) is not None else math.nan,
            "log_thinking_above_zero": lambda r: math.log(thinking(r) + 1.0)
            if thinking(r) is not None and thinking(r) > 0 else math.nan,
        }[name]

    def array(self, name: str) -> np.ndarray:
        """val[item, pass, version] for a key of analyze.METRICS or one of the extra values above. Only cells
        that count get values (analyze.Main.complete)."""
        if name not in self._cache:
            if name in analyze.METRICS:
                self._cache[name] = self.main.array(name)
            else:
                fn = self._extra(name)
                out = np.full(self.main.cell.shape, np.nan)
                for idx, r in np.ndenumerate(self.main.cell):
                    if r is not None and self.main.complete[idx[0], idx[1]]:
                        out[idx] = fn(r)
                self._cache[name] = out
        return self._cache[name]

    def pass_index(self, passes: list) -> list[int]:
        return [self.passes.index(p) for p in passes if p in self.passes]

    def index(self, version: str) -> int:
        return self.versions.index(version)


# ------------------------------------------------------------------------------------------ checks

def _close(a, b, tol=1e-9) -> bool:
    if a is None or b is None:
        return a is None and b is None
    return abs(float(a) - float(b)) <= tol * max(1.0, abs(float(a)), abs(float(b)))


def rebuilt_scan(ctx: Context, key: str, passes: list[int] | None = None) -> dict:
    """judge.judge on the rebuilt array with a single shuffle: every number that does not come from
    shuffles (best segment, diff, z, sign per pass, three parts, step) is the registered program's."""
    run = RUNS[key]
    val = ctx.array(run["metric"])
    return judge.judge(val, passes=passes, min_effect=run["min"], effect=run["effect"], shuffles=1)


def check_reports(ctx: Context) -> dict:
    """Do the rebuilt arrays give the reports' own segments and sizes? Returns the problems found."""
    problems, compared = [], []
    rep_refused = list(ctx.final.get("versions_refused_by_the_server") or [])
    if rep_refused != ctx.refused:
        problems.append(f"versions refused: report {rep_refused}, rows {ctx.refused}")
    if list(ctx.final.get("passes") or []) != ctx.passes:
        problems.append(f"passes: report {ctx.final.get('passes')}, rows {ctx.passes}")
    for label, rep, passes in (("final", ctx.final, None),
                               ("interim", ctx.interim, None if ctx.interim is None else ctx.interim.get("passes"))):
        if rep is None:
            continue
        if list(rep.get("versions") or []) != ctx.versions:
            problems.append(f"{label}: the version list differs from the final report's")
            continue
        idx = None if passes is None else ctx.pass_index(passes)
        if passes is not None and len(idx) != len(passes):
            problems.append(f"{label}: passes {passes} are not all in the rows")
            continue
        for key in RUNS:
            r = rep.get(key) or {}
            if r.get("no_data"):
                continue
            got = rebuilt_scan(ctx, key, idx)
            for name in ("best_start", "best_end"):
                if got[name] != r.get(name):
                    problems.append(f"{label} {key}: {name} {got[name]} against the report's {r.get(name)}")
            for name in ("diff", "z", "drop_support"):
                if not _close(got[name], r.get(name)):
                    problems.append(f"{label} {key}: {name} {got[name]} against the report's {r.get(name)}")
            for part in ("before", "segment", "after"):
                if not _close(got["three_parts"][part], (r.get("three_parts") or {}).get(part)):
                    problems.append(f"{label} {key}: three_parts {part} differs")
            compared.append(f"{label} {key}")
    sec = (ctx.final.get("secondary") or {}).get("before_and_after_2_1_303")
    if sec and POINTED_VERSION in ctx.versions:
        k = ctx.index(POINTED_VERSION)
        got = seg_diff(ctx.array("accuracy"), k, ctx.V - 1)
        if not _close(got, sec.get("difference_after_item_difficulty")):
            problems.append(f"before and after {POINTED_VERSION}: {got} against the report's "
                            f"{sec.get('difference_after_item_difficulty')}")
        compared.append(f"final before and after {POINTED_VERSION}")
    return {"ok": not problems, "problems": problems, "compared": compared}


# ------------------------------------------------------------------------------------------ declared

def declared_differences(final: dict) -> list[dict]:
    """The declared differences of the final report. An accuracy difference is declared when both ways of
    counting declare one with the same sign (analyze.analyze). When the two name different segments, both
    segments are listed (item 7 asks that neither is given alone)."""
    out = []
    if final.get("accuracy_difference_declared"):
        segs: dict = {}
        for key in ("accuracy", "accuracy_errors_and_voids_as_wrong"):
            r = final[key]
            segs.setdefault((r["best_start"], r["best_end"]), []).append(key)
        for (a, b), keys in segs.items():
            out.append({"test": "accuracy", "start": a, "end": b, "named_by": keys})
    if final.get("thinking_difference_declared"):
        r = final["thinking"]
        out.append({"test": "thinking", "start": r["best_start"], "end": r["best_end"], "named_by": ["thinking"]})
    for d in out:
        lead = final[d["named_by"][0]]
        d.update(diff=lead["diff"], effect="diff" if d["test"] == "accuracy" else "ratio",
                 drop_named=bool(lead.get("drop_named")), first_version=final["versions"][d["start"]],
                 last_version=final["versions"][d["end"]])
        d["segment"] = seg_text(final["versions"], d["start"], d["end"])
    return out


def base_metric(test: str) -> str:
    return "accuracy" if test == "accuracy" else "log_thinking"


# ------------------------------------------------------------------------------------------ item 1

def item_1_blocked_tools(ctx: Context, declared: list[dict]) -> dict:
    out = []
    tried = ctx.array("tried_tools")
    for d in declared:
        a, b, effect = d["start"], d["end"], d["effect"]
        vin, vout = side_values(tried, a, b)
        d_tried = seg_diff(tried, a, b)
        r_tried = seg_range(tried, a, b, "diff", ctx.draws)
        base = seg_diff(ctx.array(base_metric(d["test"])), a, b)
        nt = ctx.array("accuracy_not_tried" if d["test"] == "accuracy" else "log_thinking_not_tried")
        d_nt = seg_diff(nt, a, b)
        r_nt = seg_range(nt, a, b, effect, ctx.draws) if d_nt is not None else None
        a_holds = excludes_zero(r_tried)
        share = None if d_nt is None or not base else d_nt / base
        b_holds = None if share is None else share < HALF
        holds = bool(a_holds and b_holds)
        out.append({
            "test": d["test"], "segment": d["segment"], "start": a, "end": b,
            "a_tried_a_tool": {"share_inside": float(vin.mean()) if vin.size else None,
                               "share_outside": float(vout.mean()) if vout.size else None,
                               "asks_inside": int(vin.size), "asks_outside": int(vout.size),
                               "difference": d_tried, "range_95": r_tried, "range_leaves_out_zero": a_holds},
            "b_asks_that_did_not_try_a_tool": {"difference": d_nt, "difference_shown": shown(d_nt, effect),
                                               "range_95_shown": r_nt,
                                               "declared_difference_same_asks_as_the_scan": base,
                                               "declared_difference_shown": shown(base, effect),
                                               "share_of_the_declared_difference": share,
                                               "less_than_half_or_other_sign": b_holds},
            "case": "may come from the blocked tools" if holds else (
                "cannot be computed" if a_holds is None or b_holds is None else "does not hold"),
            "sentence_to_add": SENTENCES["item_1"] if holds else None,
        })
    return {"item": 1, "title": "Blocked tools", "for_each_declared_difference": out,
            "nothing_declared": not declared}


# ------------------------------------------------------------------------------------------ item 2

def scan_summary(ctx: Context, val: np.ndarray, *, effect: str, min_effect: float, shuffles: int) -> dict:
    """judge.judge with the given shuffles (section 8: 2,000 and no minimum size), the fields analyze.py keeps
    for a secondary scan, and the segment in versions."""
    if np.isnan(val).all():
        return {"no_data": True}
    r = judge.judge(val, min_effect=min_effect, effect=effect, shuffles=shuffles)
    return {"segment": seg_text(ctx.versions, r["best_start"], r["best_end"]), "best_start": r["best_start"],
            "best_end": r["best_end"], "diff": r["diff"], "effect_shown": shown(r["diff"], effect), "z": r["z"],
            "p": r["p"], "shuffles": r["shuffles"], "same_sign_every_pass": r["same_sign_every_pass"],
            "has_drop": r["has_drop"], "drop_named": r["drop_named"], "three_parts": r["three_parts"],
            "values": int((~np.isnan(val)).sum())}


def item_2_unread_answers(ctx: Context, declared: list[dict]) -> dict:
    unread = ctx.array("unread")
    per_version = []
    for vi, v in enumerate(ctx.versions):
        col = unread[..., vi]
        n = int((~np.isnan(col)).sum())
        k = int(np.nansum(col))
        per_version.append({"version": v, "scored_asks": n, "not_read": k, "share_not_read": (k / n) if n else None})
    scan = scan_summary(ctx, unread, effect="diff", min_effect=0.0, shuffles=ctx.scan_shuffles)
    out = []
    for d in declared:
        if d["test"] != "accuracy":
            continue
        a, b = d["start"], d["end"]
        base = seg_diff(ctx.array("accuracy"), a, b)
        d_read = seg_diff(ctx.array("accuracy_read"), a, b)
        share = None if d_read is None or not base else d_read / base
        holds = share is not None and share < HALF
        vin, vout = side_values(unread, a, b)
        out.append({"segment": d["segment"], "start": a, "end": b,
                    "declared_difference_errors_and_voids_left_out": base,
                    "difference_over_read_answers": d_read, "share_left": share,
                    "share_not_read_inside": float(vin.mean()) if vin.size else None,
                    "share_not_read_outside": float(vout.mean()) if vout.size else None,
                    "case": "the format of the answers changed" if holds else (
                        "cannot be computed" if share is None else "does not hold"),
                    "sentence": SENTENCES["item_2"] if holds else None})
    return {"item": 2, "title": "Answers that could not be read", "per_version": per_version,
            "all_versions": {"scored_asks": int((~np.isnan(unread)).sum()), "not_read": int(np.nansum(unread))},
            "scan_of_the_share_not_read": scan, "for_each_declared_accuracy_difference": out,
            "no_declared_accuracy_difference": not out}


# ------------------------------------------------------------------------------------------ item 3

def item_3_zero_thinking(ctx: Context, declared: list[dict]) -> dict:
    out = []
    tok = ctx.array("thinking_tokens")
    for d in declared:
        if d["test"] != "thinking":
            continue
        a, b = d["start"], d["end"]
        vin, vout = side_values(tok, a, b)
        d_pos = seg_diff(ctx.array("log_thinking_above_zero"), a, b)
        med_in = float(np.median(vin)) if vin.size else None
        med_out = float(np.median(vout)) if vout.size else None
        mean_in = float(vin.mean()) if vin.size else None
        mean_out = float(vout.mean()) if vout.size else None
        pct = shown(d["diff"], "ratio")
        word = "lower" if pct < 0 else "higher"
        out.append({
            "segment": d["segment"], "start": a, "end": b,
            "asks_inside": int(vin.size), "asks_outside": int(vout.size),
            "share_zero_inside": float((vin == 0).mean()) if vin.size else None,
            "share_zero_outside": float((vout == 0).mean()) if vout.size else None,
            "ratio_over_asks_above_zero": None if d_pos is None else math.exp(d_pos),
            "median_inside": med_in, "median_outside": med_out,
            "ratio_of_medians": (med_in / med_out) if med_in is not None and med_out else None,
            "total_inside": float(vin.sum()), "total_outside": float(vout.sum()),
            "ratio_of_totals_per_ask": (mean_in / mean_out) if mean_in is not None and mean_out else None,
            "declared_per_cent": pct,
            "sentence": f"Inside {d['segment']} the geometric mean of thinking tokens plus one is "
                        f"{abs(100 * pct):.1f}% {word} than in the other versions, after the difficulty of each "
                        "item is taken out.",
        })
    return {"item": 3, "title": "Zero thinking", "for_each_declared_thinking_difference": out,
            "no_declared_thinking_difference": not out}


# ------------------------------------------------------------------------------------------ item 4

def item_4_pass_three_alone(ctx: Context) -> dict:
    if ctx.interim is None:
        return {"item": 4, "title": "A size the choice of segment did not see", "not_computed": "no interim report"}
    third = [p for p in ctx.passes if p not in (ctx.interim.get("passes") or [])]
    if not third:
        return {"item": 4, "title": "A size the choice of segment did not see", "not_computed": "no pass after the "
                "interim report"}
    idx = ctx.pass_index(third)
    out = {}
    for key, run in RUNS.items():
        ir = ctx.interim.get(key) or {}
        if ir.get("no_data"):
            out[key] = {"no_data": True}
            continue
        a, b = ctx.index(ir["first_version"]), ctx.index(ir["last_version"])
        val = ctx.array(run["metric"])[:, idx, :]
        d = seg_diff(val, a, b)
        out[key] = {"label": run["label"], "segment_ranked_first_on_passes_1_and_2": seg_text(ctx.versions, a, b),
                    "start": a, "end": b, "two_pass_difference": ir["diff"],
                    "two_pass_shown": shown(ir["diff"], run["effect"]),
                    "pass_alone": third, "difference": d, "difference_shown": shown(d, run["effect"]),
                    "range_95_shown": seg_range(val, a, b, run["effect"], ctx.draws) if d is not None else None,
                    "values": int((~np.isnan(val)).sum())}
    return {"item": 4, "title": "A size the choice of segment did not see", "scans": out,
            "note": "The interim report written after pass 2 is published in full beside these numbers."}


# ------------------------------------------------------------------------------------------ item 5

def item_5_items_and_families(ctx: Context, declared: list[dict]) -> dict:
    units = ctx.main.units
    out = []
    for d in declared:
        a, b, effect = d["start"], d["end"], d["effect"]
        for key in d["named_by"]:
            val = ctx.array(RUNS[key]["metric"])
            full = seg_diff(val, a, b)
            loo = []
            for i, u in enumerate(units):
                x = seg_diff(np.delete(val, i, axis=0), a, b)
                loo.append({"item": u, "difference": x, "share_left": None if x is None or not full else x / full})
            known = [e for e in loo if e["difference"] is not None]
            lo = min(known, key=lambda e: e["difference"]) if known else None
            hi = max(known, key=lambda e: e["difference"]) if known else None
            halving = [e for e in known if e["share_left"] is not None and e["share_left"] <= HALF]
            fams = {}
            for fam in sorted({ctx.panel[u]["family"] for u in units}):
                idx = [i for i, u in enumerate(units) if ctx.panel[u]["family"] == fam]
                x = seg_diff(val[idx], a, b)
                fams[fam] = {"name": FAMILY_NAMES.get(fam, fam), "items": len(idx), "difference": x,
                             "difference_shown": shown(x, effect)}
            out.append({"test": d["test"], "way_of_counting": key, "segment": d["segment"], "start": a, "end": b,
                        "difference": full, "difference_shown": shown(full, effect),
                        "smallest_with_one_item_left_out": lo, "largest_with_one_item_left_out": hi,
                        "items_whose_removal_halves_it": halving, "by_family": fams, "each_item_left_out": loo})
    return {"item": 5, "title": "One item or one family", "for_each_declared_difference": out,
            "nothing_declared": not declared}


# ------------------------------------------------------------------------------------------ item 6

def placement(val: np.ndarray, draws: int, seed: int = SEED) -> dict:
    """Redraw the items `draws` times and run the scan on each draw, without shuffles. Returns the first and
    the last version index of the segment ranked first in each draw, with the registered rule that a
    segment starting at the first version is reported as the segment right after it."""
    resid, mask = judge.residuals(val)
    s_item = resid.sum(axis=1)                  # [item, V], all passes pooled
    n_item = mask.sum(axis=1).astype(float)
    n_items, n_versions = val.shape[0], val.shape[-1]
    starts, ends = judge.segments(n_versions)
    flip = np.arange(len(starts))
    for j in np.where(starts == 0)[0]:
        flip[j] = int(np.where((starts == ends[j] + 1) & (ends == n_versions - 1))[0][0])
    rng = np.random.default_rng(seed)
    firsts, lasts = [], []
    done = 0
    while done < draws:
        k = min(500, draws - done)
        pick = rng.integers(0, n_items, size=(k, n_items))
        _, z = judge.scan(s_item[pick].sum(axis=1), n_item[pick].sum(axis=1), starts, ends)
        best = flip[np.abs(z).argmax(axis=1)]
        firsts.append(starts[best])
        lasts.append(ends[best])
        done += k
    return {"first": np.concatenate(firsts), "last": np.concatenate(lasts)}


def middle_95(idx: np.ndarray) -> tuple[int, int]:
    """The 2.5 and 97.5 per cent points of a list of version indexes, each an index that occurred."""
    return (int(np.quantile(idx, 0.025, method="inverted_cdf")),
            int(np.quantile(idx, 0.975, method="inverted_cdf")))


def item_6_where_it_starts_and_ends(ctx: Context) -> dict:
    out = {}
    for key, run in RUNS.items():
        r = ctx.final.get(key) or {}
        if r.get("no_data"):
            out[key] = {"no_data": True}
            continue
        p = placement(ctx.array(run["metric"]), ctx.placement_draws)
        f_lo, f_hi = middle_95(p["first"])
        l_lo, l_hi = middle_95(p["last"])
        same = float(np.mean((p["first"] == r["best_start"]) & (p["last"] == r["best_end"])))
        v = ctx.versions
        start_words = v[f_lo] if f_lo == f_hi else f"a version from {v[f_lo]} to {v[f_hi]}"
        end_words = v[l_lo] if l_lo == l_hi else f"a version from {v[l_lo]} to {v[l_hi]}"
        spans = f_lo != f_hi or l_lo != l_hi
        declared = bool(ctx.final.get(TEST_DECLARED[run["test"]]))
        out[key] = {"label": run["label"], "segment_ranked_first": seg_text(v, r["best_start"], r["best_end"]),
                    "first_version_middle_95": [v[f_lo], v[f_hi]], "last_version_middle_95": [v[l_lo], v[l_hi]],
                    "share_of_draws_with_the_same_segment": same, "draws": ctx.placement_draws,
                    "case": "a span" if spans else "single versions",
                    "wording": f"starts at {start_words} and ends at {end_words}",
                    "wording_goes_into_the_summary": declared and spans}
    return {"item": 6, "title": "Where the segment starts and ends", "scans": out}


# ------------------------------------------------------------------------------------------ item 7

def item_7_two_ways_of_counting(ctx: Context) -> dict:
    out = {}
    for label, rep in (("final", ctx.final), ("interim", ctx.interim)):
        if rep is None:
            continue
        A, B = rep.get("accuracy") or {}, rep.get("accuracy_errors_and_voids_as_wrong") or {}
        if A.get("no_data") or B.get("no_data"):
            out[label] = {"no_data": True}
            continue
        idx = ctx.pass_index(rep.get("passes") or ctx.passes)
        vals = {k: ctx.array(RUNS[k]["metric"])[:, idx, :] for k in ("accuracy", "accuracy_errors_and_voids_as_wrong")}
        segs = []
        for key, r in (("accuracy", A), ("accuracy_errors_and_voids_as_wrong", B)):
            a, b = r["best_start"], r["best_end"]
            segs.append({"named_by": key, "segment": seg_text(ctx.versions, a, b), "start": a, "end": b,
                         "declared_by_this_way": bool(r.get("declared")), "p": r.get("p"),
                         "difference_errors_and_voids_left_out": seg_diff(vals["accuracy"], a, b),
                         "difference_errors_and_voids_as_wrong": seg_diff(vals["accuracy_errors_and_voids_as_wrong"],
                                                                          a, b)})
        same = (A["best_start"], A["best_end"]) == (B["best_start"], B["best_end"])
        both = bool(A.get("declared") and B.get("declared"))
        agree = bool(np.sign(A["diff"]) == np.sign(B["diff"]))
        line = bool(rep.get("accuracy_difference_declared"))

        def pts(x):
            return "n/a" if x is None else f"{100 * x:+.1f} points"

        sa, sb = segs
        both_text = (f"{sa['segment']} ({pts(A['diff'])}) with errors and voids left out, and {sb['segment']} "
                     f"({pts(B['diff'])}) with them counted as wrong")
        if both and not agree:
            case = "both declare a difference, with opposite signs"
            sentence = (f"Both ways of counting declare an accuracy difference, with opposite signs: {both_text}. "
                        "The registered line declares an accuracy difference only when the two signs agree, so it "
                        "declares none here.")
        elif both and not same:
            case = "both declare a difference, on different segments"
            sentence = f"Both ways of counting declare an accuracy difference, on different segments: {both_text}."
        elif not same:
            case = "different segments"
            sentence = f"The two ways of counting name different segments: {both_text}."
        else:
            case = "same segment"
            sentence = None
        out[label] = {"passes": rep.get("passes"), "segments": segs, "same_segment": same,
                      "both_declare": both, "signs_agree": agree, "registered_line_declares": line,
                      "case": case, "sentence": sentence}
    return {"item": 7, "title": "Two ways of counting that name different segments", "reports": out}


# ------------------------------------------------------------------------------------------ item 8

def item_8_cut_at_2_1_303(ctx: Context) -> dict:
    if POINTED_VERSION not in ctx.versions:
        return {"item": 8, "title": f"Before and after {POINTED_VERSION}",
                "not_computed": f"{POINTED_VERSION} is not among the versions compared"}
    k = ctx.index(POINTED_VERSION)
    end = ctx.V - 1
    acc = ctx.array("accuracy")
    th = ctx.array("log_thinking")
    d_acc, r_acc = seg_diff(acc, k, end), seg_range(acc, k, end, "diff", ctx.draws)
    d_th, r_th = seg_diff(th, k, end), seg_range(th, k, end, "ratio", ctx.draws)
    segments = int(len(judge.segments(ctx.V)[0]))
    out = {"accuracy": {"accuracy_from_on": float(np.nanmean(acc[..., k:])), "accuracy_before": float(np.nanmean(acc[..., :k])),
                        "difference": d_acc, "range_95": r_acc, "range_leaves_out_zero": excludes_zero(r_acc),
                        "scan_declares": bool(ctx.final.get("accuracy_difference_declared"))},
           "thinking": {"ratio": None if d_th is None else math.exp(d_th),
                        "ratio_range_95": None if r_th is None else [1 + r_th[0], 1 + r_th[1]],
                        "range_leaves_out_one": excludes_zero(r_th),
                        "scan_declares": bool(ctx.final.get("thinking_difference_declared"))}}
    for test, e in out.items():
        leaves = e.get("range_leaves_out_zero", e.get("range_leaves_out_one"))
        if leaves and not e["scan_declares"]:
            e["case"] = "range leaves out zero while the scan declares nothing"
            e["sentence"] = SENTENCES["item_8"].format(segments=segments)
        else:
            e["case"] = "no special wording"
            e["sentence"] = None
    return {"item": 8, "title": f"Before and after {POINTED_VERSION} (secondary)", "cut_at": POINTED_VERSION,
            "versions_from_on": ctx.V - k, "versions_before": k, **out}


# ------------------------------------------------------------------------------------------ item 13

def _conditions(r: dict) -> dict:
    return {"p": r.get("p"), "p_below_line": bool(r.get("passes_line")), "big_enough": bool(r.get("big_enough")),
            "same_sign_every_pass": bool(r.get("same_sign_every_pass")), "declared": bool(r.get("declared")),
            "segment": r.get("segment"), "diff": r.get("diff")}


def third_pass_wording(two_declared: bool, three_declared: bool, two_p_below: list[str]) -> tuple[str, str]:
    """The case and sentence of item 13 for one test. two_p_below: the ways of counting that had p < 0.05 on
    two passes."""
    if two_declared and three_declared:
        return "declared on two passes and on all passes", "Declared on passes 1 and 2 and on all passes."
    if two_declared:
        return "not confirmed by the third pass", "Declared on passes 1 and 2, " + SENTENCES["item_13_not_confirmed"] + "."
    if two_p_below:
        tail = " It is declared on all passes." if three_declared else " It is not declared on all passes either."
        return ("two passes had only p < 0.05",
                f"On passes 1 and 2 the scan had p < 0.05 ({', '.join(two_p_below)}) but did not meet all three "
                "conditions for a declared difference." + tail)
    if three_declared:
        return "declared on all passes only", "Not declared on passes 1 and 2. Declared on all passes."
    return "declared on neither", "Not declared on passes 1 and 2, and not declared on all passes."


def item_13_third_pass(ctx: Context) -> dict:
    if ctx.interim is None:
        return {"item": 13, "title": "Not confirmed by the third pass", "not_computed": "no interim report"}
    out = {}
    for test, keys in (("accuracy", ("accuracy", "accuracy_errors_and_voids_as_wrong")), ("thinking", ("thinking",))):
        two = {k: _conditions(ctx.interim.get(k) or {}) for k in keys}
        three = {k: _conditions(ctx.final.get(k) or {}) for k in keys}
        two_declared = bool(ctx.interim.get(TEST_DECLARED[test]))
        three_declared = bool(ctx.final.get(TEST_DECLARED[test]))
        below = [RUNS[k]["label"] for k in keys if two[k]["p_below_line"]]
        case, sentence = third_pass_wording(two_declared, three_declared, below)
        out[test] = {"passes_1_and_2": {"declared": two_declared, "ways": two},
                     "all_passes": {"declared": three_declared, "ways": three}, "case": case, "sentence": sentence}
    return {"item": 13, "title": "Not confirmed by the third pass", "interim_passes": ctx.interim.get("passes"),
            "final_passes": ctx.final.get("passes"), "tests": out}


# ------------------------------------------------------------------------------------------ item 14

def item_14_both_sides(ctx: Context) -> dict:
    out = {}
    for key, run in RUNS.items():
        r = ctx.final.get(key) or {}
        if r.get("no_data"):
            out[key] = {"no_data": True}
            continue
        t = r["three_parts"]
        declared = bool(ctx.final.get(TEST_DECLARED[run["test"]]))
        e = {"label": run["label"], "segment": r.get("segment"), "before": t["before"], "segment_part": t["segment"],
             "after": t["after"], "versions_before": t["versions_before"],
             "versions_in_segment": t["versions_in_segment"], "versions_after": t["versions_after"],
             "shown": {k: shown(t[k], run["effect"]) for k in ("before", "segment", "after")}, "diff": r["diff"],
             "declared": declared}
        if declared and r["diff"] > 0 and t["before"] is not None and t["after"] is not None:
            gap = abs(t["before"] - t["after"])
            e["gap_before_after"] = gap
            e["third_of_the_difference"] = r["diff"] * THIRD
            holds = gap < r["diff"] * THIRD
            e["case"] = "higher than both sides, which are at about the same level" if holds else "does not hold"
            e["sentence"] = SENTENCES["item_14"] if holds else None
        else:
            e["case"] = "not a declared segment higher than the rest with versions on both sides"
            e["sentence"] = None
        out[key] = e
    return {"item": 14, "title": "A segment that is higher than both sides", "scans": out}


# ------------------------------------------------------------------------------------------ item 15

def group_scan(ctx: Context, groups: list[list[str]], metric: str, effect: str, min_effect: float) -> dict | None:
    """The scan with each group of versions as one unit, as analyze.same_prompt_groups does it for accuracy:
    inside each cell the values of a group's versions are averaged, then judge.judge with 2,000 shuffles."""
    if len(groups) <= 2:
        return None
    val = ctx.array(metric)
    gid = np.array([gi for gi, g in enumerate(groups) for _ in g])
    grouped = np.full(val.shape[:2] + (len(groups),), np.nan)
    for gi in range(len(groups)):
        part = val[..., gid == gi]
        n = (~np.isnan(part)).sum(axis=-1)
        grouped[..., gi] = np.where(n > 0, np.nansum(part, axis=-1) / np.maximum(n, 1), np.nan)
    g = judge.judge(grouped, min_effect=min_effect, effect=effect, shuffles=ctx.scan_shuffles)
    out = {k: g[k] for k in ("p", "diff", "best_start", "best_end", "same_sign_every_pass", "segments", "declared")}
    out["first_version"], out["last_version"] = groups[g["best_start"]][0], groups[g["best_end"]][-1]
    out["effect_shown"] = shown(g["diff"], effect)
    return out


def boundaries(groups: list[list[str]], versions: list[str], a: int, b: int) -> dict:
    """Where the two ends of versions a..b fall against the groups. A boundary at index i lies between
    versions i - 1 and i. The request size changes at the first version of every group but the first."""
    gof = {v: gi for gi, g in enumerate(groups) for v in g}
    changes = [i for i in range(1, len(versions)) if gof[versions[i - 1]] != gof[versions[i]]]

    def at(i):
        if i <= 0 or i >= len(versions):
            return {"boundary": None, "inside_a_group": False}
        inside = gof[versions[i - 1]] == gof[versions[i]]
        e = {"between": [versions[i - 1], versions[i]], "inside_a_group": inside}
        if inside and changes:
            best = min(abs(c - i) for c in changes)
            e["nearest_versions_where_the_request_changed"] = [versions[c] for c in changes if abs(c - i) == best]
        elif inside:
            e["nearest_versions_where_the_request_changed"] = []
        return e

    return {"start": at(a), "end": at(b + 1)}


def item_15_unchanged_request(ctx: Context, declared: list[dict]) -> dict:
    sp = (ctx.final.get("secondary") or {}).get("versions_with_the_same_first_request_size") or {}
    groups = sp.get("groups")
    if not groups:
        return {"item": 15, "title": "A boundary where nothing was sent differently",
                "not_computed": "the final report has no groups of versions that send the same thing"}
    reg = sp.get("scan_with_groups_as_units")
    rebuilt = group_scan(ctx, groups, "accuracy", "diff", judge.MIN_DIFF_ACCURACY)
    agree = None
    if reg and rebuilt:
        agree = (reg["best_start"] == rebuilt["best_start"] and reg["best_end"] == rebuilt["best_end"]
                 and _close(reg["diff"], rebuilt["diff"])
                 and (ctx.scan_shuffles != SCAN_SHUFFLES or _close(reg["p"], rebuilt["p"])))
    scans = {"accuracy": {"registered": reg, "rebuilt": rebuilt, "registered_and_rebuilt_agree": agree}}
    if any(d["test"] == "thinking" for d in declared):
        scans["thinking"] = {"computed_here": group_scan(ctx, groups, "log_thinking", "ratio",
                                                         judge.MIN_RATIO_THINKING)}
    out = []
    for d in declared:
        a, b = d["start"], d["end"]
        bd = boundaries(groups, ctx.versions, a, b)
        # where a difference called lower starts: a low segment starts the drop, a high one ends right before it
        x = a if d["diff"] < 0 else b + 1
        drop_at = None
        if d["drop_named"] and 0 < x < ctx.V:
            drop_at = ctx.versions[x]
        sentence, case, adapted = None, "no fixed sentence", None
        same_as_before = drop_at is not None and boundaries(groups, ctx.versions, x, x)["start"]["inside_a_group"]
        if drop_at is not None and same_as_before:
            case = "a drop is declared from a version that sends the same request as the version before it"
            sentence = SENTENCES["item_15"].format(x=drop_at)
            if d["diff"] < 0 and b < ctx.V - 1:
                adapted = (f"The segment ends at {ctx.versions[b]}, before the newest version. The fixed sentence "
                           f"was written for \"from X on\". For this segment it reads: Versions {d['segment']} are "
                           f"lower. {drop_at} sends the same request as the version before it. This experiment "
                           f"cannot tell whether the server treats {drop_at} differently or the cut fell here by "
                           "luck.")
        out.append({"test": d["test"], "segment": d["segment"], "start": a, "end": b, "boundaries": bd,
                    "called_lower": d["drop_named"], "drop_starts_at": drop_at,
                    "that_version_sends_the_same_request_as_the_one_before": bool(same_as_before),
                    "case": case, "sentence": sentence, "adapted_sentence": adapted,
                    "condition_outside_this_program": "The sentence is used if the checks of section 10 find no "
                                                      "fault. This program does not run those checks."
                    if sentence else None,
                    "scan_over_groups": scans.get(d["test"])})
    return {"item": 15, "title": "A boundary where nothing was sent differently", "groups": groups,
            "scans_over_groups": scans, "for_each_declared_difference": out, "nothing_declared": not declared}


# ------------------------------------------------------------------------------------------ item 18

def message_output_tokens(events: list[dict]) -> dict:
    """The top-level assistant messages of one stream-json output: each message id once, at the largest output
    token count any of its lines carries. Also whether the lines of one message carried different counts."""
    per_id: dict = {}
    order: list = []
    differ = False
    for i, e in enumerate(events):
        if e.get("type") != "assistant" or e.get("parent_tool_use_id") not in (None, ""):
            continue
        msg = e.get("message") or {}
        key = msg.get("id") or f"line-{i}"
        n = (msg.get("usage") or {}).get("output_tokens")
        if n is None:
            continue
        if key in per_id:
            differ = differ or per_id[key] != n
            per_id[key] = max(per_id[key], n)
        else:
            per_id[key] = n
            order.append(key)
    return {"messages": len(order), "sum": sum(per_id.values()) if per_id else None,
            "last": per_id[order[-1]] if order else None, "lines_of_one_message_differ": differ}


def read_raw(raw_dirs: list[Path]) -> dict:
    """{(pass, version, unit): numbers} for group main, from the raw records, a resent ask in place of the ask
    it was sent for (as analyze.apply_resends does with the graded rows)."""
    recs, replaced = [], set()
    for d in raw_dirs:
        for path in sorted((Path(d) / "asks").glob("*.json")):
            rec = json.loads(path.read_text(encoding="utf-8"))
            if rec.get("group") != MAIN or not str(rec.get("unit") or "").startswith("item:"):
                continue
            ro = rec.get("resend_of")
            if ro:
                replaced.add((ro.get("plan"), ro.get("ask_id")))
            fmt = extract.record_format(rec)
            if fmt == "stream-json":
                events = extract._stream_events(rec.get("stdout") or "")  # noqa: SLF001 - the registered line reader
                res = next((e for e in reversed(events) if e.get("type") == "result"), None) or {}
                m = message_output_tokens(events)
            else:  # group main always asks in stream-json; anything else has no messages to add up
                res = extract.parse(rec.get("stdout") or "", fmt)["result"] or {}
                m = {"messages": 0, "sum": None, "last": None, "lines_of_one_message_differ": False}
            recs.append(((rec.get("plan"), rec.get("ask_id")),
                         (rec.get("pass"), rec.get("version"), rec.get("unit")),
                         {"result_output_tokens": (res.get("usage") or {}).get("output_tokens"), **m}))
    return {key: v for ident, key, v in recs if ident not in replaced}


def item_18_how_thinking_is_counted(ctx: Context, raw: dict | None) -> dict:
    sg = ((ctx.final.get("small_groups") or {}).get("api") or {}).get("against_author_same_version") or {}
    api = {"thinking": sg.get("thinking"), "versions": ((ctx.final.get("small_groups") or {}).get("api") or {}).get(
        "versions"), "source": "final report, small_groups.api.against_author_same_version (section 9)"}
    out = {"item": 18, "title": "How thinking is counted", "api_against_author_on_2_1_322": api}
    if not raw:
        out["per_version"] = None
        out["not_computed"] = "no raw records were given"
        return out
    rows = []
    totals = {s: {"asks": 0, "equal": 0, "equal_to_last_message_only": 0, "other": 0, "not_comparable": 0}
              for s in ("tried_a_tool", "did_not")}
    missing = 0
    for vi, v in enumerate(ctx.versions):
        entry = {"version": v}
        for side in ("tried_a_tool", "did_not"):
            entry[side] = {"asks": 0, "equal": 0, "equal_to_last_message_only": 0, "other": 0, "not_comparable": 0,
                           "lines_of_one_message_differ": 0}
        for ui, u in enumerate(ctx.main.units):
            for pi, p in enumerate(ctx.passes):
                r = ctx.main.cell[ui, pi, vi]
                if r is None or not ctx.main.complete[ui, pi] or not analyze._scored(r):  # noqa: SLF001
                    continue
                x = raw.get((p, v, u))
                if x is None:
                    missing += 1
                    continue
                side = "tried_a_tool" if analyze._tried(r) else "did_not"  # noqa: SLF001
                e = entry[side]
                e["asks"] += 1
                e["lines_of_one_message_differ"] += int(x["lines_of_one_message_differ"])
                if x["result_output_tokens"] is None or x["sum"] is None:
                    e["not_comparable"] += 1
                elif x["result_output_tokens"] == x["sum"]:
                    e["equal"] += 1
                elif x["result_output_tokens"] == x["last"]:
                    e["equal_to_last_message_only"] += 1
                else:
                    e["other"] += 1
        for side in ("tried_a_tool", "did_not"):
            e = entry[side]
            e["all_equal"] = e["asks"] > 0 and e["equal"] == e["asks"]
            for k in totals[side]:
                totals[side][k] += e[k]
        rows.append(entry)
    out.update(per_version=rows, all_versions=totals, scored_asks_without_a_raw_record=missing,
               note="Output tokens of the result line against the sum over the ask's top-level assistant "
                    "messages, each message counted once by its id at the largest count its lines carry. "
                    "\"equal to last message only\" means the result line holds the count of the last message "
                    "alone.")
    return out


# ------------------------------------------------------------------------------------------ all of it

def compute(ctx: Context, raw: dict | None) -> dict:
    declared = declared_differences(ctx.final)
    return {
        "format": "extra-numbers-v1", "registration_entry": ENTRY,
        "items_in_this_program": list(ITEMS_HERE), "items_done_elsewhere": list(ITEMS_ELSEWHERE),
        "settings": {"seed": SEED, "draws": ctx.draws, "placement_draws": ctx.placement_draws,
                     "scan_shuffles": ctx.scan_shuffles},
        "versions": ctx.versions, "passes": ctx.passes,
        "declared": {"accuracy": bool(ctx.final.get("accuracy_difference_declared")),
                     "thinking": bool(ctx.final.get("thinking_difference_declared")), "differences": declared},
        "items": {
            "1": item_1_blocked_tools(ctx, declared),
            "2": item_2_unread_answers(ctx, declared),
            "3": item_3_zero_thinking(ctx, declared),
            "4": item_4_pass_three_alone(ctx),
            "5": item_5_items_and_families(ctx, declared),
            "6": item_6_where_it_starts_and_ends(ctx),
            "7": item_7_two_ways_of_counting(ctx),
            "8": item_8_cut_at_2_1_303(ctx),
            "13": item_13_third_pass(ctx),
            "14": item_14_both_sides(ctx),
            "15": item_15_unchanged_request(ctx, declared),
            "18": item_18_how_thinking_is_counted(ctx, raw),
        },
    }


# ------------------------------------------------------------------------------------------ the text

def _pts(x, digits=1):
    return "n/a" if x is None else f"{100 * x:+.{digits}f}"


def _pct(x, digits=1):
    return "n/a" if x is None else f"{100 * x:.{digits}f}%"


def _show(x, effect):
    """A difference in points for accuracy, a per cent change for thinking (x already shown)."""
    if x is None:
        return "n/a"
    return f"{100 * x:+.1f} points" if effect == "diff" else f"{100 * x:+.1f}%"


def _rng(r, effect):
    if not r:
        return "n/a"
    return f"{_show(r[0], effect)} to {_show(r[1], effect)}"


def _n_versions(n: int) -> str:
    return f"{n} version" if n == 1 else f"{n} versions"


def report_text(rep: dict) -> str:
    it = rep["items"]
    L = [f"# Extra numbers (preregistration change log, \"{rep['registration_entry']}\")", "",
         f"Items computed here: {', '.join(map(str, rep['items_in_this_program']))}. Items "
         f"{', '.join(map(str, rep['items_done_elsewhere']))} are done elsewhere. None of these numbers has a "
         "verdict of its own.", "",
         f"Versions: {len(rep['versions'])}, passes {rep['passes']}. Seed {rep['settings']['seed']}, "
         f"{rep['settings']['draws']} redraws for a range, {rep['settings']['placement_draws']} for item 6, "
         f"{rep['settings']['scan_shuffles']} shuffles for the scans of items 2 and 15.", ""]
    chk = rep.get("checks_against_the_registered_reports")
    if chk:
        L += [f"Check against the registered reports: {'passed' if chk['ok'] else 'FAILED'} "
              f"({len(chk['compared'])} scans compared).", ""]
        L += [f"- WARNING: {p}" for p in chk["problems"]]
    dec = rep["declared"]
    L += [f"Declared by the registered program: accuracy {dec['accuracy']}, thinking {dec['thinking']}."]
    for d in dec["differences"]:
        L.append(f"- {d['test']}: {d['segment']} ({_show(shown(d['diff'], d['effect']), d['effect'])}), named by "
                 f"{', '.join(d['named_by'])}, called lower: {d['drop_named']}")
    L.append("")

    i1 = it["1"]
    L += ["## Item 1. Blocked tools", ""]
    if i1["nothing_declared"]:
        L += ["No difference is declared, so this item has nothing to report.", ""]
    for e in i1["for_each_declared_difference"]:
        a, b = e["a_tried_a_tool"], e["b_asks_that_did_not_try_a_tool"]
        eff = "diff" if e["test"] == "accuracy" else "ratio"
        L += [f"**{e['test']}, {e['segment']}**", "",
              f"- (a) share of asks that tried a tool: {_pct(a['share_inside'])} inside ({a['asks_inside']} asks), "
              f"{_pct(a['share_outside'])} outside ({a['asks_outside']} asks); difference after item difficulty "
              f"{_pts(a['difference'])} points, range {_pts((a['range_95'] or [None])[0])} to "
              f"{_pts((a['range_95'] or [None, None])[1])}; leaves out zero: {a['range_leaves_out_zero']}",
              f"- (b) over the asks that did not try a tool: {_show(b['difference_shown'], eff)} (range "
              f"{_rng(b['range_95_shown'], eff)}), against the declared {_show(b['declared_difference_shown'], eff)}; "
              f"share of the declared difference {('n/a' if b['share_of_the_declared_difference'] is None else format(b['share_of_the_declared_difference'], '.2f'))}",
              f"- case: {e['case']}"]
        if e["sentence_to_add"]:
            L.append(f"- sentence to add: {e['sentence_to_add']}")
        L.append("")

    i2 = it["2"]
    L += ["## Item 2. Answers that could not be read", "",
          f"All versions: {i2['all_versions']['not_read']} of {i2['all_versions']['scored_asks']} scored asks not read.",
          ""]
    s = i2["scan_of_the_share_not_read"]
    if not s.get("no_data"):
        L += [f"Scan of the share not read (secondary, {s['shuffles']} shuffles, no minimum size): {s['segment']}, "
              f"{_pts(s['diff'])} points against the rest, p = {s['p']:.4f}, same sign every pass "
              f"{s['same_sign_every_pass']}.", ""]
    L += ["| version | scored asks | not read | share |", "|---|---|---|---|"]
    L += [f"| {r['version']} | {r['scored_asks']} | {r['not_read']} | {_pct(r['share_not_read'])} |"
          for r in i2["per_version"]]
    L.append("")
    if i2["no_declared_accuracy_difference"]:
        L += ["No accuracy difference is declared, so there is no difference over read answers to report.", ""]
    for e in i2["for_each_declared_accuracy_difference"]:
        L += [f"**{e['segment']}**: declared {_pts(e['declared_difference_errors_and_voids_left_out'])} points, over "
              f"read answers {_pts(e['difference_over_read_answers'])} points (share left "
              f"{'n/a' if e['share_left'] is None else format(e['share_left'], '.2f')}). Case: {e['case']}."
              + (f" Sentence: {e['sentence']}" if e["sentence"] else ""), ""]

    i3 = it["3"]
    L += ["## Item 3. Zero thinking", ""]
    if i3["no_declared_thinking_difference"]:
        L += ["No thinking difference is declared, so this item has nothing to report.", ""]
    for e in i3["for_each_declared_thinking_difference"]:
        def ratio(x):
            return "n/a" if x is None else f"{x:.3f}"
        L += [f"**{e['segment']}**", "",
              f"- share of asks with zero thinking: {_pct(e['share_zero_inside'])} inside, "
              f"{_pct(e['share_zero_outside'])} outside",
              f"- ratio over asks with thinking above zero: {ratio(e['ratio_over_asks_above_zero'])}",
              f"- ratio of medians: {ratio(e['ratio_of_medians'])} ({e['median_inside']} against {e['median_outside']})",
              f"- ratio of totals per ask: {ratio(e['ratio_of_totals_per_ask'])} (totals {e['total_inside']:.0f} over "
              f"{e['asks_inside']} asks, {e['total_outside']:.0f} over {e['asks_outside']} asks)",
              f"- sentence: {e['sentence']}", ""]

    i4 = it["4"]
    L += ["## Item 4. A size the choice of segment did not see", ""]
    if i4.get("not_computed"):
        L += [f"Not computed: {i4['not_computed']}.", ""]
    else:
        for key, e in i4["scans"].items():
            if e.get("no_data"):
                continue
            eff = RUNS[key]["effect"]
            L.append(f"- {e['label']}: {e['segment_ranked_first_on_passes_1_and_2']} ranked first on passes 1 and 2 "
                     f"({_show(e['two_pass_shown'], eff)}); on pass {', '.join(map(str, e['pass_alone']))} alone "
                     f"{_show(e['difference_shown'], eff)}, range {_rng(e['range_95_shown'], eff)}")
        L += ["", i4["note"], ""]

    i5 = it["5"]
    L += ["## Item 5. One item or one family", ""]
    if i5["nothing_declared"]:
        L += ["No difference is declared, so this item has nothing to report.", ""]
    for e in i5["for_each_declared_difference"]:
        eff = "diff" if e["test"] == "accuracy" else "ratio"
        lo, hi = e["smallest_with_one_item_left_out"], e["largest_with_one_item_left_out"]
        L += [f"**{e['test']}, {e['segment']}, {RUNS[e['way_of_counting']]['label']}**: "
              f"{_show(e['difference_shown'], eff)}", "",
              f"- one item left out: smallest {_show(shown(lo['difference'], eff), eff)} (without {lo['item']}), "
              f"largest {_show(shown(hi['difference'], eff), eff)} (without {hi['item']})",
              "- items whose removal leaves half or less: " + (", ".join(
                  f"{x['item']} ({_show(shown(x['difference'], eff), eff)})" for x in e["items_whose_removal_halves_it"])
                  or "none"),
              "- within each family: " + ", ".join(
                  f"{f['name']} ({f['items']} items) {_show(f['difference_shown'], eff)}" for f in e["by_family"].values()),
              ""]

    i6 = it["6"]
    L += ["## Item 6. Where the segment starts and ends", ""]
    for key, e in i6["scans"].items():
        if e.get("no_data"):
            continue
        L.append(f"- {e['label']}: {e['segment_ranked_first']}; over {e['draws']} redraws it {e['wording']} "
                 f"(middle 95%); the same segment in {_pct(e['share_of_draws_with_the_same_segment'])} of draws; "
                 f"case: {e['case']}; goes into the summary: {e['wording_goes_into_the_summary']}")
    L.append("")

    i7 = it["7"]
    L += ["## Item 7. Two ways of counting", ""]
    for label, e in i7["reports"].items():
        if e.get("no_data"):
            continue
        L.append(f"**{label} report (passes {e['passes']})**: case {e['case']}; the registered line declares: "
                 f"{e['registered_line_declares']}")
        for sg in e["segments"]:
            L.append(f"- named by {RUNS[sg['named_by']]['label']}: {sg['segment']}, declared by this way "
                     f"{sg['declared_by_this_way']}; difference {_pts(sg['difference_errors_and_voids_left_out'])} "
                     f"points with errors and voids left out, {_pts(sg['difference_errors_and_voids_as_wrong'])} "
                     "points with them counted as wrong")
        if e["sentence"]:
            L.append(f"- sentence: {e['sentence']}")
        L.append("")

    i8 = it["8"]
    L += [f"## Item 8. {i8['title']}", ""]
    if i8.get("not_computed"):
        L += [f"Not computed: {i8['not_computed']}.", ""]
    else:
        a, t = i8["accuracy"], i8["thinking"]
        L += [f"- accuracy: {_pct(a['accuracy_from_on'])} from {i8['cut_at']} on ({i8['versions_from_on']} versions), "
              f"{_pct(a['accuracy_before'])} before ({i8['versions_before']} versions); difference after item "
              f"difficulty {_pts(a['difference'])} points, range {_rng(a['range_95'], 'diff')}; case: {a['case']}",
              f"- thinking: ratio {('n/a' if t['ratio'] is None else format(t['ratio'], '.3f'))}, range "
              f"{('n/a' if not t['ratio_range_95'] else format(t['ratio_range_95'][0], '.3f') + ' to ' + format(t['ratio_range_95'][1], '.3f'))}; "
              f"case: {t['case']}"]
        for e in (a, t):
            if e["sentence"]:
                L.append(f"- sentence: {e['sentence']}")
        L.append("")

    i13 = it["13"]
    L += ["## Item 13. Not confirmed by the third pass", ""]
    if i13.get("not_computed"):
        L += [f"Not computed: {i13['not_computed']}.", ""]
    else:
        for test, e in i13["tests"].items():
            L.append(f"**{test}**: case {e['case']}. Sentence: {e['sentence']}")
            for span, part in (("passes 1 and 2", e["passes_1_and_2"]), ("all passes", e["all_passes"])):
                for key, w in part["ways"].items():
                    eff = RUNS[key]["effect"]
                    L.append(f"- {span}, {RUNS[key]['label']}: {w['segment']}, "
                             f"{_show(shown(w['diff'], eff), eff)}, p = "
                             f"{('n/a' if w['p'] is None else format(w['p'], '.4f'))}, big enough {w['big_enough']}, "
                             f"same sign every pass {w['same_sign_every_pass']}, declared {w['declared']}")
            L.append("")

    i14 = it["14"]
    L += ["## Item 14. Before, segment, after", ""]
    for key, e in i14["scans"].items():
        if e.get("no_data"):
            continue
        eff = RUNS[key]["effect"]
        sh = e["shown"]
        L.append(f"- {e['label']}, {e['segment']}: {_n_versions(e['versions_before'])} before "
                 f"{_show(sh['before'], eff)}, the segment ({_n_versions(e['versions_in_segment'])}) "
                 f"{_show(sh['segment'], eff)}, {_n_versions(e['versions_after'])} after {_show(sh['after'], eff)} "
                 f"(against the mean of all versions); case: {e['case']}"
                 + (f"; sentence: {e['sentence']}" if e["sentence"] else ""))
    L.append("")

    i15 = it["15"]
    L += ["## Item 15. A boundary where nothing was sent differently", ""]
    if i15.get("not_computed"):
        L += [f"Not computed: {i15['not_computed']}.", ""]
    else:
        L.append("Groups of versions that send the same first request size: "
                 + "; ".join(g[0] if len(g) == 1 else f"{g[0]} to {g[-1]}" for g in i15["groups"]))
        L.append("")
        if i15["nothing_declared"]:
            L += ["No difference is declared, so no boundary is looked at.", ""]
        for e in i15["for_each_declared_difference"]:
            L.append(f"**{e['test']}, {e['segment']}**")
            for end in ("start", "end"):
                bd = e["boundaries"][end]
                if bd.get("between") is None:
                    L.append(f"- {end}: at the edge of the version list")
                else:
                    L.append(f"- {end}: between {bd['between'][0]} and {bd['between'][1]}, inside one group: "
                             f"{bd['inside_a_group']}"
                             + (f"; nearest version where the request changed: "
                                f"{', '.join(bd['nearest_versions_where_the_request_changed'])}"
                                if bd["inside_a_group"] else ""))
            sc = e["scan_over_groups"] or {}
            eff = "diff" if e["test"] == "accuracy" else "ratio"
            for name, g in sc.items():
                if isinstance(g, dict):
                    L.append(f"- scan over groups ({name}): {g['first_version']} to {g['last_version']}, "
                             f"difference {_show(shown(g['diff'], eff), eff)}, p = {g['p']:.4f}")
            if "registered_and_rebuilt_agree" in sc:
                L.append(f"- the rebuilt scan over groups agrees with the registered one: "
                         f"{sc['registered_and_rebuilt_agree']}")
            L.append(f"- case: {e['case']}")
            if e["sentence"]:
                L.append(f"- sentence: {e['sentence']}")
                L.append(f"- {e['condition_outside_this_program']}")
            if e["adapted_sentence"]:
                L.append(f"- {e['adapted_sentence']}")
            L.append("")

    i18 = it["18"]
    L += ["## Item 18. How thinking is counted", ""]
    th = (i18["api_against_author_on_2_1_322"] or {}).get("thinking") or {}
    if th.get("items"):
        L += [f"Thinking of group api against group author on 2.1.322 (section 9, from the final report): ratio "
              f"{th['ratio']:.3f}, range {th['ratio_range_95'][0]:.3f} to {th['ratio_range_95'][1]:.3f}, "
              f"{th['items']} items.", ""]
    if i18.get("per_version"):
        L += [i18["note"], "",
              "| version | tried a tool: asks | equal | last message only | other | did not: asks | equal | last message only | other |",
              "|---|---|---|---|---|---|---|---|---|"]
        for r in i18["per_version"]:
            t, n = r["tried_a_tool"], r["did_not"]
            L.append(f"| {r['version']} | {t['asks']} | {t['equal']} | {t['equal_to_last_message_only']} | "
                     f"{t['other'] + t['not_comparable']} | {n['asks']} | {n['equal']} | "
                     f"{n['equal_to_last_message_only']} | {n['other'] + n['not_comparable']} |")
        L += ["", f"Scored asks without a raw record: {i18['scored_asks_without_a_raw_record']}.", ""]
    else:
        L += [f"Per version: not computed ({i18.get('not_computed')}).", ""]
    return "\n".join(L) + "\n"


def write_outputs(rep: dict, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    text_json = json.dumps(clean(rep), ensure_ascii=False, indent=1) + "\n"
    text_md = report_text(clean(rep))
    for name, text in (("extra_numbers.json", text_json), ("extra_numbers.md", text_md)):
        leaks = sorted(set(PUBLIC_BAD.findall(text)))
        if leaks:
            raise RuntimeError(f"{name} would hold paths or addresses {leaks[:5]}; nothing was written")
    (out_dir / "extra_numbers.json").write_text(text_json, encoding="utf-8")
    (out_dir / "extra_numbers.md").write_text(text_md, encoding="utf-8")


# ------------------------------------------------------------------------------------------ command line

def default_files(base: Path, names=DEFAULT_PLANS, leaf: str | None = None) -> list[Path]:
    out = []
    for n in names:
        p = base / n / leaf if leaf else base / n
        if p.exists():
            out.append(p)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--graded", action="append", type=Path,
                    help="graded.jsonl of the registered run (repeat); default graded/F1, F1r, F2, F2r, F3, F3r")
    ap.add_argument("--raw-dir", action="append", type=Path,
                    help="a plan's raw record folder, the one that holds asks/ (repeat); default the same plans")
    ap.add_argument("--final-report", type=Path, default=DEFAULT_FINAL)
    ap.add_argument("--interim-report", type=Path, default=DEFAULT_INTERIM)
    ap.add_argument("--items", type=Path, default=DEFAULT_ITEMS, help="the item file (only id, family and scorer are read)")
    ap.add_argument("--author-repo", type=Path, help="LiveNerf's repository, for its rational() parser")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--draws", type=int, default=DRAWS)
    ap.add_argument("--placement-draws", type=int, default=PLACEMENT_DRAWS)
    ap.add_argument("--scan-shuffles", type=int, default=SCAN_SHUFFLES)
    ap.add_argument("--no-raw", action="store_true", help="leave out the per version part of item 18")
    ap.add_argument("--allow-mismatch", action="store_true",
                    help="write the outputs even when the rebuilt scans differ from the reports (marked as failed)")
    args = ap.parse_args(argv)

    if args.author_repo is None:
        print("not run: --author-repo is needed (LiveNerf's repository, for the form of a rational answer)")
        return 2
    if not args.final_report.is_file():
        print(f"not run: no final report at {args.final_report}")
        return 2
    graded = args.graded or default_files(DEFAULT_GRADED_DIR, leaf="graded.jsonl")
    if not graded:
        print("not run: no graded rows found")
        return 2
    raw_dirs = [] if args.no_raw else (args.raw_dir or default_files(DEFAULT_RAW_DIR))
    final = json.loads(args.final_report.read_text(encoding="utf-8"))
    interim = json.loads(args.interim_report.read_text(encoding="utf-8")) if args.interim_report.is_file() else None
    panel = load_panel(args.items)
    is_read = make_is_read(author_parsers(args.author_repo))
    ctx = Context(analyze.load_rows(graded), final, interim, panel, is_read, draws=args.draws,
                  placement_draws=args.placement_draws, scan_shuffles=args.scan_shuffles)
    checks = check_reports(ctx)
    if not checks["ok"] and not args.allow_mismatch:
        for p in checks["problems"]:
            print("MISMATCH:", p)
        print("not run: the rebuilt scans differ from the registered reports, so these are not the same data")
        return 2
    raw = read_raw(raw_dirs) if raw_dirs else None
    rep = compute(ctx, raw)
    rep["checks_against_the_registered_reports"] = checks
    rep["inputs"] = {"graded": [{"file": where(p), "sha256": file_sha256(p)} for p in graded],
                     "raw_dirs": [where(p) for p in raw_dirs],
                     "final_report": {"file": where(args.final_report), "sha256": file_sha256(args.final_report)},
                     "interim_report": None if interim is None else {
                         "file": where(args.interim_report), "sha256": file_sha256(args.interim_report)},
                     "items": {"file": where(args.items), "sha256": file_sha256(args.items)}}
    write_outputs(rep, args.out)
    print(json.dumps({"written": [where(args.out / "extra_numbers.json"), where(args.out / "extra_numbers.md")],
                      "checks_ok": checks["ok"], "declared": rep["declared"]["accuracy"] or rep["declared"]["thinking"]},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
