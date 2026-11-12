"""What the two comparisons added on 12 November 2026 share (design file 判断标准.md, section 15, and the public
preregistration, change log entry "12 November 2026, evening").

The two comparisons are time_of_day.py (asks sent inside US working hours against asks sent outside them,
group main only) and desktop_vs_cli.py (the Desktop group against main on 2.1.321, 77 items). Both are
secondary numbers: they never take part in the scan of sections 3 and 5-2 or in the third pass decision.

This file holds the paths, the fixed numbers of the rule, the US working hours, how the graded rows of the
registered run are read (through the same functions analyze.py uses), and the three wordings.
"""

import json
import math
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROGRAM = HERE.parent
PROJECT = PROGRAM.parent
sys.dont_write_bytecode = True
if str(PROGRAM) not in sys.path:
    sys.path.insert(0, str(PROGRAM))

import numpy as np  # noqa: E402

from ccversions import analyze, judge  # noqa: E402

DATA = PROJECT / "本机数据"
FORMAL = DATA / "正式跑"
FORMAL_GRADED = FORMAL / "graded"
# Only whether this file exists is looked at, never what is in it: formal.py writes it after it has graded
# every pass of the run, so its presence says the graded rows of every pass are on disk.
FORMAL_FINAL_REPORT = FORMAL / "final" / "report.json"
DESKTOP_ASKS = DATA / "Desktop组" / "asks"
SETTINGS_FILE = DATA / "本机设置.toml"
OUT_DEFAULT = DATA / "后加的两个对比"

SEED = judge.SEED                       # 20261111
DRAWS = 10_000                          # items redrawn for a range
SHUFFLES = 10_000                       # shuffles (time of day) or sign flips (Desktop) for a p value
CLEAR_P = 0.01                          # section 15: "clear" needs p below this
LEAN_P = 0.05                           # section 15: "points one way" needs p below this
MIN_DIFF_ACCURACY = judge.MIN_DIFF_ACCURACY    # 3 points, as sections 3 and 5-2
MIN_RATIO_THINKING = judge.MIN_RATIO_THINKING  # 10 per cent
MIN_SHARE_FOR_SIGN = judge.MIN_PASS_SHARE_FOR_SIGN  # a part with fewer than half the items is left out of the sign check

# (key in analyze.METRICS, "diff" for shares or "ratio" for logs, name in the report)
METRICS = (("accuracy", "diff", "accuracy (errors and voids left out)"),
           ("accuracy_bad_as_wrong", "diff", "accuracy (errors and voids counted as wrong)"),
           ("log_thinking", "ratio", "thinking tokens (log of thinking tokens + 1)"))

WORDING = {1: "clear", 2: "points one way", 3: "otherwise"}


# ------------------------------------------------------------------------------------ US working hours

def parse_time(ts: str) -> datetime:
    """An ISO time as written in the records ("...+00:00" or "...Z"). A time without a zone is taken as UTC."""
    t = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    return t.astimezone(timezone.utc)


def in_us_hours(ts: str) -> bool:
    """Section 15: Monday to Friday, 14:00 to 01:00 UTC the next day. The hour from 00:00 to 01:00 belongs to
    the day before. Moving the clock back by one hour turns this into "13:00 to 24:00 of a weekday"."""
    t = parse_time(ts) - timedelta(hours=1)
    return t.weekday() < 5 and t.hour >= 13


# ------------------------------------------------------------------------------------ the registered run

def default_graded_files() -> list[Path]:
    return sorted(FORMAL_GRADED.glob("*/graded.jsonl"))


def formal_finished() -> bool:
    return FORMAL_FINAL_REPORT.exists()


def load_versions(settings_file: Path | None, versions_file: Path | None) -> list[str]:
    """The version list the run used: a versions file given on the command line, or the one the settings name."""
    if versions_file is None:
        from ccversions import settings as settings_mod
        versions_file = settings_mod.load(str(settings_file or SETTINGS_FILE)).versions_file
    return json.loads(Path(versions_file).read_text())["versions"]


def main_group(rows: list[dict], versions: list[str]) -> tuple["analyze.Main", list[str]]:
    """The main group as analyze.analyze() lays it out: resent asks take the place of the asks they were sent
    for, a version the server refused to run is out as a whole (section 1), and a cell (one item in one pass)
    counts only when every remaining version has a record in it."""
    rows = analyze.apply_resends(rows)
    refused = sorted({r["version"] for r in rows if r.get("group") == analyze.MAIN_GROUP and r.get("outcome") == "error"
                      and r.get("reason") == "min_version"}, key=analyze.version_key)
    if refused:
        versions = [v for v in versions if v not in refused]
        rows = [r for r in rows if not (r.get("group") == analyze.MAIN_GROUP and r["version"] in refused)]
    return analyze.Main(rows, versions), refused


# ------------------------------------------------------------------------------------ sizes and wordings

def shown(x: float | None, effect: str) -> float | None:
    """A difference as it is reported: a share for accuracy, exp(x) - 1 for thinking."""
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return None
    return float(x) if effect == "diff" else float(math.exp(x) - 1.0)


def big_enough(x: float, effect: str) -> bool:
    """Section 15: at least 3 points for accuracy, at least 10 per cent for thinking."""
    if effect == "diff":
        return abs(x) >= MIN_DIFF_ACCURACY
    return abs(math.exp(x) - 1.0) >= MIN_RATIO_THINKING


def wording(p: float, big: bool, rest_ok: bool) -> int:
    """1 clear: p < 0.01, big enough, and every other condition holds. 2 points one way: p < 0.05 and big
    enough, the rest short of clear. 3 otherwise."""
    if p < CLEAR_P and big and rest_ok:
        return 1
    if p < LEAN_P and big:
        return 2
    return 3


def not_larger_than(rng: list | None, effect: str) -> float | None:
    """For wording 3, "no difference larger than X was seen": X is the end of the 95 per cent range that lies
    furthest from zero, in the units the difference is reported in."""
    if not rng or rng[0] is None or rng[1] is None:
        return None
    return max(abs(shown(rng[0], effect)), abs(shown(rng[1], effect)))


def both_ways_of_counting(a: dict, b: dict) -> dict:
    """Section 1: every accuracy result is computed twice (errors and voids left out, and counted as wrong) and only
    what holds in both is said. The weaker of the two wordings, and wording 3 when the two point in opposite
    directions."""
    ca, cb = a.get("wording"), b.get("wording")
    if ca is None or cb is None:
        return {"wording": None, "wording_name": "not computable", "note": "one of the two ways could not be computed"}
    value = lambda r: r["diff"] if "diff" in r else r["d"]  # noqa: E731  (Desktop keeps it as diff, time of day as d)
    same_sign = bool(np.sign(value(a)) == np.sign(value(b)))
    w = max(ca, cb) if same_sign else 3
    note = ("both ways agree" if ca == cb and same_sign else
            "the two ways of counting differ, and the weaker wording is the one that holds in both" if same_sign else
            "the two ways of counting point in opposite directions")
    return {"wording": w, "wording_name": WORDING[w], "note": note,
            "errors_and_voids_left_out": WORDING[ca], "errors_and_voids_as_wrong": WORDING[cb]}


def pct(x, digits=1) -> str:
    return "n/a" if x is None else f"{100 * x:.{digits}f}"


def write_json(path: Path, doc) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=1, default=_plain) + "\n")


def _plain(x):
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating,)):
        return float(x)
    if isinstance(x, (np.bool_,)):
        return bool(x)
    if isinstance(x, np.ndarray):
        return x.tolist()
    raise TypeError(f"not JSON: {type(x)}")
