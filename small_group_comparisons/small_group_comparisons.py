"""Three small groups against group main, as fixed in the preregistration's change log of 13 November 2026.

    python -B small_group_comparisons.py --livenerf-daily FILE [--graded FILE ...] [--final-report FILE]
        [--settings FILE] [--s3-raw-root DIR] [--nosent-raw-root DIR] [--a3-raw-root DIR]
        [--desktop-prompt-report FILE] [--out DIR] [--draws N] [--allow-partial]

The groups are `nosent` (main's ask without LiveNerf's two sentences, 2.1.280 and 2.1.322, three passes in
plans NS1, NS2, NS3 and their resend plans NS1r, NS2r, NS3r), `flags_on` (four versions with the remote flags fetched,
passes 1 and 2 in the registered run and pass 3 in plan S3) and `author` on 2.1.280 (passes 1 and 2 in the
registered run, pass 3 in plan S3). None of these numbers carries a verdict, and none takes part in the tests
of sections 5 and 6.

Words used below

  item by item  section 9: for each item, each side's mean over its answers, then the difference for each
                item, then the mean of those differences over the items both sides have. Done by analyze.paired, the
                function the registered report uses for every small group.
  range         the 2.5 and 97.5 per cent points of the figure when the items are redrawn with replacement
                10,000 times, seed 20261111 (the scheme of analyze.paired).
  four measures accuracy with errors and voids left out, accuracy with them counted as wrong (section 3 asks
                for both), thinking tokens and output tokens. The last two are ratios: exp of the mean
                difference of ln(tokens + 1), as analyze.paired gives them.
  main          group main's graded rows of the registered run, a resent ask in place of the ask it was sent
                for, a version the server refused left out, all three passes: exactly the rows
                analyze.small_groups compares the small groups with.
  read          item 2 of the entry on extra numbers: the graded row's answer has the form the item's grader
                accepts (extra_numbers.make_is_read, with LiveNerf's own rational() parser). The key is not used.

What is computed, and where it is asked for (function in brackets)

  Entry "a group without LiveNerf's two sentences, and a third pass ...", "How it is compared":
   1  (nosent_against_main) nosent minus main on the same version, the four measures with ranges, for
      2.1.280, for 2.1.322 and for the two together (each side pooled over both versions, item by item, as
      analyze.small_groups pools the versions of a group).
   2  (nosent_gap) on each item, (nosent on 2.1.322 minus nosent on 2.1.280) and (main on 2.1.322 minus main
      on 2.1.280), and the first minus the second. Each of the three is averaged over the items all four sides
      have, with a range. The four measures, thinking and output as ratios.
   3  (nosent_unread) for nosent and for main, on each version and on the two together: scored asks, how
      many were not read, the share not read, accuracy over all scored asks and over the read answers alone.
      Beside them, item by item with a range, nosent minus main for the share not read and for the accuracy
      over read answers.
   5  (flags_on_against_main, author_against_main, author_against_livenerf_range) section 9 on three passes,
      with the figure on two passes beside it. flags_on against the same 4 versions in main, the 4 together.
      author on 2.1.280 against main on 2.1.280, and against LiveNerf's daily numbers: does this group's
      accuracy and median output tokens over its answers fall between the lowest and the highest daily value
      LiveNerf published, before 3 November and from 3 November on, for each pass and for the passes pooled.
  Its "Limits", first point:
   L1 (a_day_apart) author on 2.1.322, pass 3 (plan A3, sent on 13 November) minus its passes 1 and 2, item
      by item, the four measures. And arm e of the desktop-prompt group against main on 2.1.321, copied from
      the report of added_comparisons/desktop_prompt.py (comparison 5) when that report is given.
  Entry "extra numbers and wordings, fixed before the reports are opened":
   9  (item_9_same_day) for each pass of author on 2.1.280: its accuracy (errors and voids left out, as
      LiveNerf counts) minus LiveNerf's published accuracy for the same UTC day, and the range of this group's
      figure. A pass whose asks were sent on more than one UTC day is compared with the mean of those days'
      LiveNerf figures, each day weighted by this group's scored asks sent on it, and each day is also shown
      on its own. "They differ" when LiveNerf's figure lies outside the range. Then comes the sentence of item 9.
  16  (item_16_flags_on) for each difference the registered final report declares (read with
      extra_numbers.declared_differences, never decided again here): does the segment fall between versions
      flags_on covers (at least one of its 4 versions inside the segment and one outside)? If so, flags_on's
      own difference between its versions inside and outside the segment, item by item on its three passes
      (on two passes beside it), and main's on the same 4 versions. flags_on "shows it" when every way of
      counting of that test has the declared sign and a range that leaves out zero. Then one of the three
      wordings of item 16.

Before any of this (check_against_final_report): analyze.small_groups is run on the graded rows read here, and
its entries for flags_on and author (passes 1 and 2) must equal those of the registered final report, every
number of them, ranges included. The version list, the refused versions and the passes must be the same too.
If anything differs, nothing is written: the rows read here would not be the rows the report was made from.

The records of the added plans go through grade.py unchanged (grade_records, LiveNerf's own graders and the
item file named by the registered settings), and analyze.apply_resends puts a resent ask in place of the ask it
was sent for. A plan whose folder is missing is "not sent". A plan that lacks some of its asks, or has asks
that never reached the model and have no resend yet, is "partly sent". Either of these in S3 or NS1 to NS3
stops the program, unless --allow-partial is given: then it computes on what is there and every figure
says which passes and how many asks it used. A resend that points to no ask read, two rows for one ask, a
record without the fields that place a resend and an arm (plan, ask_id, pass, group, version, unit, scored,
warmup, resend_of), or a row of another pass than its plan's, stops it always. So does a registered run whose
rows do not give the final report's numbers.

LiveNerf's daily file must be a copy downloaded after the last ask of author on 2.1.280: an older copy lacks the
days of the later passes, and the program then says so and leaves those days out of item 9.

Outputs in --out: small_group_comparisons.json and small_group_comparisons.md. Neither holds an answer, a
question text, a key or an item name. Both are checked for paths and e-mail addresses (grade.PUBLIC_BAD) before
they are kept.
"""

import argparse
import csv
import importlib.util
import json
import math
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROGRAM = HERE.parent
PROJECT = PROGRAM.parent
sys.dont_write_bytecode = True
if str(PROGRAM) not in sys.path:
    sys.path.insert(0, str(PROGRAM))

import numpy as np  # noqa: E402

from ccversions import analyze, extract, grade, judge  # noqa: E402


def _load_extra_numbers():
    """extra_numbers.py from its own folder, loaded by its file name. Its folder is not put on the import path,
    because it holds a fake_data.py of its own."""
    if "extra_numbers" in sys.modules:
        return sys.modules["extra_numbers"]
    for folder in ("多报的数", "extra_numbers"):
        f = PROGRAM / folder / "extra_numbers.py"
        if f.is_file():
            spec = importlib.util.spec_from_file_location("extra_numbers", f)
            mod = importlib.util.module_from_spec(spec)
            sys.modules["extra_numbers"] = mod
            spec.loader.exec_module(mod)
            return mod
    raise ImportError("extra_numbers.py not found next to this program's folder")


xn = _load_extra_numbers()

# Default places of the real data, relative to the project folder that holds the program folder.
DATA = PROJECT / "本机数据"
DEFAULT_GRADED_DIR = DATA / "正式跑" / "graded"
FORMAL_PLANS = ("F1", "F1r", "F2", "F2r", "F3", "F3r")  # the files formal.py analyses: passes and their resends
DEFAULT_FINAL = DATA / "正式跑" / "final" / "report.json"
DEFAULT_SETTINGS = DATA / "本机设置.toml"
DEFAULT_S3_ROOT = DATA / "小组第三遍" / "原始记录"
DEFAULT_NOSENT_ROOT = DATA / "去掉两句话组" / "原始记录"
DEFAULT_A3_ROOT = DATA / "API第三遍" / "原始记录"
DEFAULT_DSP_REPORT = DATA / "后加的两个对比" / "desktop_prompt" / "report.json"
DEFAULT_OUT = DATA / "小组对比"

ENTRY_NOSENT = ("13 November 2026: a group without LiveNerf's two sentences, and a third pass for `flags_on` and "
                "for `author` on 2.1.280")
ENTRY_EXTRA = "13 November 2026: extra numbers and wordings, fixed before the reports are opened"

SEED = judge.SEED            # 20261111
DRAWS = 10_000
MAIN = analyze.MAIN_GROUP
NOSENT, FLAGS, AUTHOR, API = "nosent", "flags_on", "author", "api"
NOSENT_VERSIONS = ("2.1.280", "2.1.322")
FLAGS_VERSIONS = ("2.1.280", "2.1.299", "2.1.308", "2.1.322")
AUTHOR_VERSION = "2.1.280"
A3_VERSION = "2.1.322"

# (plan, its resend plan, the pass its asks carry, the arms it asks: group and version)
S3_PLANS = (("S3", "S3r", 3, tuple((FLAGS, v) for v in FLAGS_VERSIONS) + ((AUTHOR, AUTHOR_VERSION),)),)
NOSENT_PLANS = tuple((f"NS{n}", f"NS{n}r", n, tuple((NOSENT, v) for v in NOSENT_VERSIONS)) for n in (1, 2, 3))
# A3 also holds group api. Only author on 2.1.322 is used here (api's rows are listed as left out)
A3_PLANS = (("A3", "A3r", 3, ((AUTHOR, A3_VERSION),)),)
RECORD_FIELDS = ("plan", "ask_id", "pass", "group", "version", "unit", "scored", "warmup", "resend_of")

# (name in the outputs, key in analyze.METRICS, reported as a ratio)
MEASURES = (("accuracy", "accuracy", False), ("accuracy_bad_as_wrong", "accuracy_bad_as_wrong", False),
            ("thinking", "log_thinking", True), ("output", "log_output", True))
MEASURE_LABELS = {"accuracy": "accuracy, errors and voids left out",
                  "accuracy_bad_as_wrong": "accuracy, errors and voids counted as wrong",
                  "thinking": "thinking tokens", "output": "output tokens"}
TEST_WAYS = {"accuracy": (("accuracy", "accuracy", False), ("accuracy_bad_as_wrong", "accuracy_bad_as_wrong", False)),
             "thinking": (("thinking", "log_thinking", True),)}

# LiveNerf's published daily numbers (results/daily.csv): the rows of its measured model over all 78 items.
LIVENERF_MODEL = "claudecode/claude-opus-5-5"
LIVENERF_ARM = "measured"
LIVENERF_FAMILY = "all"
LIVENERF_CLI = "2.1.280"
SPLIT_DATE = "2026-11-03"    # section 9: before 3 November, and from 3 November on
PERIOD_LABELS = {"before_3_november": "before 3 November", "from_3_november_on": "from 3 November on"}

REGISTERED_IN = {
    "nosent_against_main": (ENTRY_NOSENT, "How it is compared, point 1: nosent against main on the same version, "
                            "using the three passes main has, for 2.1.280, for 2.1.322 and for the two together"),
    "nosent_gap": (ENTRY_NOSENT, "How it is compared, point 2: whether the two sentences change the gap between "
                   "the two versions"),
    "nosent_unread": (ENTRY_NOSENT, "How it is compared, point 3: answers that could not be read (item 2 of the "
                      "entry on extra numbers) and the accuracy over the read answers alone, for both sides"),
    "flags_on_against_main": (ENTRY_NOSENT, "How it is compared, point 5, with section 9: flags_on against the same "
                              "4 versions in main, the 4 together, on three passes, two passes beside it"),
    "author_against_main": (ENTRY_NOSENT, "How it is compared, point 5, with section 9: author on 2.1.280 against "
                            "main on 2.1.280, on three passes, two passes beside it"),
    "author_against_livenerf_range": (ENTRY_NOSENT, "How it is compared, point 5, with section 9: do accuracy and "
                                      "the median output tokens fall inside LiveNerf's daily range, before 3 "
                                      "November and from 3 November on"),
    "a_day_apart": (ENTRY_NOSENT, "Limits, point 1: two comparisons that show what a day's gap does to the same "
                    "way of asking, reported beside the nosent result"),
    "item_9": (ENTRY_EXTRA, "item 9: author on 2.1.280 against LiveNerf on the same days"),
    "item_16": (ENTRY_EXTRA, "item 16: flags_on against main, three wordings"),
}
NO_VERDICT = ("Difference and range only. None of these numbers carries a verdict or one of the three wordings "
              "(point 4 of \"How it is compared\").")

SENTENCES = {
    "item_9": ("In pass {p} this group's accuracy ({acc}) differs from LiveNerf's published accuracy for {days} "
               "({ref}) by {diff}. Comparisons between versions are made inside one account and do not depend "
               "on it."),
    "item_16_shown": ("Group main shows a declared {test} difference for {segment} ({size}). It falls between "
                      "versions that flags_on covers ({inside} inside, {outside} outside), and flags_on shows it "
                      "too ({flags_size}, range {flags_range})."),
    "item_16_not_shown": ("The {test} difference for {segment} was seen with the remote flags not fetched and was "
                          "not seen with them fetched. Four versions can only see about 7 points."),
    "item_16_cannot": "No declared difference falls between versions that flags_on covers, so this group cannot "
                      "speak to it.",
}

LIMITS = (
    "nosent was sent on 13 November 2026. The passes of main it is compared with were sent on 11 and 12 November, "
    "and no main ask was sent beside it. The two comparisons under \"a day apart\" show what a day's gap does to "
    "the same way of asking.",
    "nosent covers two versions. It says nothing about the other 37.",
    "The remote flags that flags_on fetched on 13 November may differ from those of 11 and 12 November.",
    "In pass 3 flags_on and author on 2.1.280 were sent on their own. In passes 1 and 2 they sat among the asks "
    "of the 39 versions.",
    "The asks of nosent and of the third pass were added after the yes or no line of the two tests had been seen.",
    "If the weekly usage line of 0.99 was reached, the asks went on after the usage of the account was reset. "
    "\"When the asks were sent\" gives each plan's longest wait between two asks, in hours.",
    "Each group has few answers. With three passes on each side, two ways of asking one version differ by about 4 "
    "points by chance alone (worked out from the 4.9 points of one version answering the 78 items once, not "
    "simulated).",
)


class Stop(RuntimeError):
    """Something that has to be looked at before any number is written."""


# ------------------------------------------------------------------------------------------ small helpers

def utc_day(ts) -> str | None:
    """The UTC date of a time as written in the records. A time without a zone is taken as UTC."""
    t = _time(ts)
    return None if t is None else t.date().isoformat()


def passes_of(rows: list[dict]) -> list:
    return sorted({r.get("pass") for r in rows if r.get("pass") is not None})


def boot_range(d: np.ndarray, draws: int) -> list[float]:
    """The middle 95 per cent of the mean of d when its items are redrawn: the draws of analyze.paired."""
    rng = np.random.default_rng(SEED)
    boot = d[rng.integers(0, len(d), size=(draws, len(d)))].mean(axis=1)
    return [float(np.quantile(boot, 0.025)), float(np.quantile(boot, 0.975))]


def item_means(rows: list[dict], fn) -> dict:
    """{unit: mean of fn(row) over the rows of that unit where fn gives a number}, as analyze._item_means."""
    acc: dict = {}
    for r in rows:
        x = fn(r)
        if not math.isnan(x):
            acc.setdefault(r["unit"], []).append(x)
    return {u: sum(v) / len(v) for u, v in acc.items()}


def paired_fn(rows_a: list[dict], rows_b: list[dict], fn, *, ratio: bool = False, draws: int = DRAWS) -> dict:
    """analyze.paired with a function of a row in place of a key of analyze.METRICS."""
    a, b = item_means(rows_a, fn), item_means(rows_b, fn)
    units = sorted(set(a) & set(b))
    if not units:
        return {"items": 0}
    d = np.array([a[u] - b[u] for u in units])
    lo, hi = boot_range(d, draws)
    out = {"items": len(units), "a": float(np.mean([a[u] for u in units])), "b": float(np.mean([b[u] for u in units])),
           "diff": float(d.mean()), "range_95": [lo, hi], "asks_a": len(rows_a), "asks_b": len(rows_b)}
    if ratio:
        out.update(ratio=math.exp(out["diff"]), ratio_range_95=[math.exp(lo), math.exp(hi)])
    return out


def compare4(rows_a: list[dict], rows_b: list[dict], draws: int) -> dict:
    """a minus b, item by item, the four measures (analyze.paired, as analyze.small_groups calls it)."""
    return {"measures": {name: analyze.paired(rows_a, rows_b, key, ratio=ratio, draws=draws)
                         for name, key, ratio in MEASURES},
            "passes": {"a": passes_of(rows_a), "b": passes_of(rows_b)},
            "asks": {"a": len(rows_a), "b": len(rows_b)}}


def excludes_zero(rng) -> bool | None:
    if not rng or rng[0] is None or rng[1] is None:
        return None
    return bool(rng[0] > 0 or rng[1] < 0)


def where(path) -> str:
    return xn.where(Path(path))


def item_rows(rows: list[dict], group: str, versions=None) -> list[dict]:
    return [r for r in rows if r.get("group") == group and (r.get("unit") or "").startswith("item:")
            and (versions is None or r.get("version") in versions)]


# ------------------------------------------------------------------------------------------ grading

class Grader:
    """grade.py's grading and item 2's test of "read", for one set of inputs (the item file, LiveNerf's code)."""

    def __init__(self, inputs, author_checks, claudecode, rational):
        self.inputs, self.author_checks, self.claudecode = inputs, author_checks, claudecode
        self.is_read = xn.make_is_read(rational)

    @classmethod
    def from_settings(cls, settings_file: Path) -> "Grader":
        """The registered settings: LiveNerf's repository (its graders and its rational() parser) and the item
        file with its sha256, as formal.py grades every pass."""
        from ccversions import items as items_mod, settings as settings_mod

        s = settings_mod.load(str(settings_file))
        author_checks, claudecode = grade.import_author_graders(s.author_repo)
        rational = xn.author_parsers(s.author_repo)
        inputs = items_mod.load(s.item_file, s.item_file_sha256, s.probe_file)
        return cls(inputs, author_checks, claudecode, rational)

    def grade(self, records: list[dict]) -> list[dict]:
        return grade.grade_records(records, self.inputs, self.author_checks, self.claudecode)

    def units(self) -> list[str]:
        return self.inputs.item_keys()

    def scorer(self, unit: str) -> str:
        return self.inputs.unit(unit).scorer

    def read(self, row: dict) -> bool:
        return self.is_read(row.get("answer"), self.scorer(row["unit"]))


# ------------------------------------------------------------------------------------------ the added plans

def _time(ts) -> datetime | None:
    if not ts:
        return None
    try:
        t = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except ValueError:
        return None
    return (t if t.tzinfo else t.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)


def send_times(records: list[dict]) -> dict:
    """When the asks of a plan and its resends were started (UTC), and the longest wait between two asks one
    after the other. The entry's limits ask for the hours of a gap if the weekly usage line was reached."""
    ts = sorted(t for t in (_time(r.get("started_at")) for r in records) if t is not None)
    if not ts:
        return {"asks_with_a_time": 0}
    gaps = [(b - a, a, b) for a, b in zip(ts, ts[1:])]
    out = {"asks_with_a_time": len(ts), "first": ts[0].isoformat(), "last": ts[-1].isoformat(),
           "utc_days": sorted({t.date().isoformat() for t in ts})}
    if gaps:
        g, a, b = max(gaps)
        out.update(longest_gap_hours=g.total_seconds() / 3600, longest_gap_from=a.isoformat(),
                   longest_gap_to=b.isoformat())
    return out


def read_plan(root: Path, name: str) -> list[dict] | None:
    """The raw records of one plan folder (root/name/asks/*.json). None when the folder is not there."""
    folder = Path(root) / name
    if not (folder / "asks").is_dir():
        return None
    return grade.load_records(folder)


def plan_pair(root: Path, name: str, resend_name: str, pass_number: int, arms: tuple, grader: Grader) -> tuple[dict, list]:
    """One pass plan and its resend plan: what is there, whether it is whole, and its graded rows with resends
    in place. Returns (status, rows of the plan's arms)."""
    recs, recs_r = read_plan(root, name), read_plan(root, resend_name)
    st = {"plan": name, "resend_plan": resend_name, "pass": pass_number,
          "arms": [f"{g} {v}" for g, v in arms], "records": None if recs is None else len(recs),
          "resend_records": None if recs_r is None else len(recs_r), "problems": []}
    if not recs:
        st["state"] = "not sent"
        st["problems"] = [] if not recs_r else [f"{resend_name} has records but {name} has none"]
        if st["problems"]:
            st["state"] = "problem"
        return st, []
    recs_r = recs_r or []
    lacking = Counter(k for r in recs + recs_r for k in RECORD_FIELDS if k not in r)
    st["records_lacking_a_field"] = dict(sorted(lacking.items()))
    if lacking:
        st["problems"].append(f"records lack fields this program needs to place resends and arms: {dict(lacking)}")
    by_id = {r.get("ask_id"): r for r in recs}
    if len(by_id) != len(recs):
        st["problems"].append(f"{name}: {len(recs) - len(by_id)} ask ids occur more than once")
    orphans, other, replaced = [], [], set()
    for r in recs_r:
        ro = r.get("resend_of")
        if not isinstance(ro, dict) or ro.get("plan") != name or ro.get("ask_id") not in by_id:
            orphans.append(r.get("ask_id"))
            continue
        o = by_id[ro["ask_id"]]
        if any(o.get(k) != r.get(k) for k in ("group", "version", "unit", "pass")):
            other.append(r.get("ask_id"))
        replaced.add(ro["ask_id"])
    if orphans:
        st["problems"].append(f"{resend_name}: {len(orphans)} resends point to no ask of {name} that was read "
                              f"(first: {orphans[0]})")
    if other:
        st["problems"].append(f"{resend_name}: {len(other)} resends differ from the ask they replace in group, version, "
                              f"item or pass (first: {other[0]})")
    marked = [r.get("ask_id") for r in recs if r.get("resend_of")]
    if marked:
        st["problems"].append(f"{name}: {len(marked)} records of the pass plan are marked as resends")
    st["send_times"] = send_times(recs + recs_r)
    never = sorted(r.get("ask_id") for r in recs if extract.never_reached_model(r))
    pending = [a for a in never if a not in replaced]
    st.update(resends=len(recs_r), resends_with_their_ask=len(replaced), never_reached_the_model=len(never),
              never_reached_and_not_resent=len(pending))
    rows = analyze.apply_resends(grader.grade(recs + recs_r))
    want = set(arms)
    kept, left = [], Counter()
    for r in rows:
        why = None
        if (r.get("group"), r.get("version")) not in want:
            why = f"arm {r.get('group')} {r.get('version')} is not one this program uses from {name}"
        elif not (r.get("unit") or "").startswith("item:"):
            why = "not an item"
        elif r.get("warmup") or not r.get("scored"):
            why = "a warm-up or an ask that is not scored"
        if why:
            left[why] += 1
        else:
            kept.append(r)
    st["rows_left_out"] = dict(left)
    units = grader.units()
    have = Counter((r["group"], r["version"], r["unit"]) for r in kept)
    twice = sorted(k for k, n in have.items() if n > 1)
    if twice:
        st["problems"].append(f"{name}: {len(twice)} asks have more than one row (first: {twice[0][0]} {twice[0][1]})")
    missing = Counter(f"{g} {v}" for g, v in arms for u in units if (g, v, u) not in have)
    st["asks_expected"] = len(arms) * len(units)
    st["asks_present"] = sum(1 for g, v in arms for u in units if (g, v, u) in have)
    st["asks_missing_by_arm"] = dict(sorted(missing.items()))
    bad_pass = sorted({r.get("pass") for r in kept} - {pass_number}, key=str)
    if bad_pass:
        st["problems"].append(f"{name}: rows of pass {bad_pass}, where the plan asks pass {pass_number}")
    st["outcomes"] = dict(sorted(Counter(f"{r['group']} {r['version']}: {r['outcome']}" for r in kept).items()))
    st["state"] = ("problem" if st["problems"] else
                   "partly sent" if missing or pending else "complete")
    return st, kept


def read_source(root: Path, plans: tuple, grader: Grader) -> tuple[list[dict], list]:
    statuses, rows = [], []
    for name, rname, p, arms in plans:
        st, kept = plan_pair(root, name, rname, p, arms, grader)
        st["root"] = where(root)
        statuses.append(st)
        rows += kept
    return statuses, rows


# ------------------------------------------------------------------------------------------ the registered run

class Formal:
    """The graded rows of the registered run laid out as analyze.analyze lays them out for analyze.small_groups."""

    def __init__(self, rows: list[dict]):
        rows = analyze.apply_resends(rows)
        self.resent = sum(bool(r.get("resent")) for r in rows)
        self.refused = sorted({r["version"] for r in rows if r.get("group") == MAIN and r.get("outcome") == "error"
                               and r.get("reason") == "min_version"}, key=analyze.version_key)
        self.rows = [r for r in rows if not (r.get("group") == MAIN and r.get("version") in self.refused)]
        self.main = item_rows(self.rows, MAIN)
        self.passes = passes_of(self.main)

    def main_on(self, versions) -> list[dict]:
        return [r for r in self.main if r["version"] in versions]


def _numbers_differ(got, want, tol: float = 1e-9) -> bool:
    if isinstance(want, float) and math.isnan(want):
        return not (isinstance(got, float) and math.isnan(got))
    if isinstance(got, float) and math.isnan(got):
        return True
    return abs(float(got) - float(want)) > tol * max(1.0, abs(float(got)), abs(float(want)))


def differences(got, want, path: str) -> list[str]:
    """Where a value computed here differs from the report's (every key of the report's value is compared)."""
    if isinstance(want, dict):
        if not isinstance(got, dict):
            return [f"{path}: the report has a mapping, the rows give {type(got).__name__}"]
        out = [f"{path}.{k}: in the report, not given by the rows" for k in want if k not in got]
        out += [f"{path}.{k}: given by the rows, not in the report" for k in got if k not in want]
        for k in want:
            if k in got:
                out += differences(got[k], want[k], f"{path}.{k}")
        return out
    if isinstance(want, list):
        if not isinstance(got, list) or len(got) != len(want):
            return [f"{path}: the report has {want}, the rows give {got}"]
        out = []
        for i, (g, w) in enumerate(zip(got, want)):
            out += differences(g, w, f"{path}[{i}]")
        return out
    if isinstance(want, bool) or want is None or isinstance(want, str):
        return [] if got == want else [f"{path}: the report has {want!r}, the rows give {got!r}"]
    if isinstance(want, (int, float)) and isinstance(got, (int, float, np.integer, np.floating)) \
            and not isinstance(got, bool):
        return [f"{path}: the report has {want!r}, the rows give {got!r}"] if _numbers_differ(got, want) else []
    return [f"{path}: the report has {want!r}, the rows give {got!r}"]


def check_against_final_report(formal: Formal, final: dict) -> dict:
    """analyze.small_groups on the rows read here, against the final report: groups flags_on and author on
    passes 1 and 2, every number. Also the version list, the refused versions and the passes."""
    problems, compared = [], []
    if list(final.get("versions_refused_by_the_server") or []) != formal.refused:
        problems.append(f"versions refused by the server: report {final.get('versions_refused_by_the_server')}, "
                        f"rows {formal.refused}")
    if list(final.get("passes") or []) != formal.passes:
        problems.append(f"passes of main: report {final.get('passes')}, rows {formal.passes}")
    have_versions = sorted({r["version"] for r in formal.main}, key=analyze.version_key)
    if list(final.get("versions") or []) != have_versions:
        problems.append("the versions of main in the rows differ from the report's version list")
    sg_report = final.get("small_groups") or {}
    sg_rows = analyze.small_groups(formal.rows)  # draws 10,000, the registered default
    for g in (FLAGS, AUTHOR):
        if g not in sg_report:
            problems.append(f"the final report has no small group {g}")
            continue
        if g not in sg_rows:
            problems.append(f"the rows have no small group {g}")
            continue
        problems += differences(sg_rows[g], sg_report[g], f"small_groups.{g}")
        compared.append(f"small_groups.{g}")
    return {"ok": not problems, "problems": problems, "compared": compared}


# ------------------------------------------------------------------------------------------ nosent

def nosent_against_main(formal: Formal, nosent: list[dict], draws: int) -> dict:
    out = {"registered_in": REGISTERED_IN["nosent_against_main"]}
    for label, versions in (("2.1.280", ("2.1.280",)), ("2.1.322", ("2.1.322",)), ("both_versions", NOSENT_VERSIONS)):
        a, b = item_rows(nosent, NOSENT, versions), formal.main_on(versions)
        out[label] = {"versions": list(versions), "a": "nosent", "b": "main", **compare4(a, b, draws)}
    return out


def _gap_parts(n280, n322, m280, m322, fn, ratio: bool, draws: int) -> dict:
    A, B, C, D = (item_means(x, fn) for x in (n322, n280, m322, m280))
    units = sorted(set(A) & set(B) & set(C) & set(D))
    if not units:
        return {"items": 0}
    g_n = np.array([A[u] - B[u] for u in units])
    g_m = np.array([C[u] - D[u] for u in units])
    out = {"items": len(units)}
    for name, d in (("nosent_322_minus_280", g_n), ("main_322_minus_280", g_m),
                    ("nosent_gap_minus_main_gap", g_n - g_m)):
        lo, hi = boot_range(d, draws)
        e = {"diff": float(d.mean()), "range_95": [lo, hi]}
        if ratio:
            e.update(ratio=math.exp(e["diff"]), ratio_range_95=[math.exp(lo), math.exp(hi)])
        out[name] = e
    return out


def nosent_gap(formal: Formal, nosent: list[dict], draws: int) -> dict:
    n280, n322 = item_rows(nosent, NOSENT, ("2.1.280",)), item_rows(nosent, NOSENT, ("2.1.322",))
    m280, m322 = formal.main_on(("2.1.280",)), formal.main_on(("2.1.322",))
    out = {"registered_in": REGISTERED_IN["nosent_gap"],
           "note": "Each item counts when all four sides have a value on it, so that the third figure is the first "
                   "minus the second. For thinking and output the figures are ratios of ratios.",
           "passes": {"nosent": passes_of(n280 + n322), "main": passes_of(m280 + m322)}, "measures": {}}
    for name, key, ratio in MEASURES:
        out["measures"][name] = _gap_parts(n280, n322, m280, m322, analyze.METRICS[key], ratio, draws)
    return out


def _read_counts(rows: list[dict], grader: Grader) -> dict:
    scored = [r for r in rows if analyze._scored(r)]  # noqa: SLF001 - the registered test of "scored"
    read = [r for r in scored if grader.read(r)]
    bad = [r for r in rows if r.get("outcome") in ("error", "void")]
    return {"asks": len(rows), "scored": len(scored), "not_read": len(scored) - len(read),
            "share_not_read": (len(scored) - len(read)) / len(scored) if scored else None,
            "accuracy_all_scored": (sum(r["score"] for r in scored) / len(scored)) if scored else None,
            "errors_and_voids": len(bad),
            "accuracy_bad_as_wrong": (sum(r["score"] for r in scored) / (len(scored) + len(bad))) if scored or bad
            else None,
            "read": len(read), "accuracy_over_read": (sum(r["score"] for r in read) / len(read)) if read else None}


def nosent_unread(formal: Formal, nosent: list[dict], grader: Grader, draws: int) -> dict:
    sc = analyze._scored  # noqa: SLF001

    def unread(r):
        return (0.0 if grader.read(r) else 1.0) if sc(r) else math.nan

    def acc_read(r):
        return float(r["score"]) if sc(r) and grader.read(r) else math.nan

    out = {"registered_in": REGISTERED_IN["nosent_unread"],
           "definition": "A scored answer is read when the graded row's answer (LiveNerf's extract_answer: the last "
                         "<answer> block, None without one) has the form the item's grader accepts: one letter for "
                         "a choice item after the grader's trimming of spaces and round brackets, an integer for an "
                         "integer item, a number LiveNerf's rational() parses for a rational item. The key is not "
                         "used (item 2 of the entry on extra numbers)."}
    lacking = [r for r in formal.main + nosent if sc(r) and "answer" not in r]
    if lacking:
        out["not_computable"] = f"{len(lacking)} scored rows have no answer field"
        return out
    for label, versions in (("2.1.280", ("2.1.280",)), ("2.1.322", ("2.1.322",)), ("both_versions", NOSENT_VERSIONS)):
        a, b = item_rows(nosent, NOSENT, versions), formal.main_on(versions)
        out[label] = {"versions": list(versions), "nosent": _read_counts(a, grader), "main": _read_counts(b, grader),
                      "nosent_minus_main_item_by_item": {
                          "share_not_read": paired_fn(a, b, unread, draws=draws),
                          "accuracy_over_read": paired_fn(a, b, acc_read, draws=draws)}}
    return out


# ------------------------------------------------------------------------------------------ flags_on and author

def flags_on_against_main(formal: Formal, s3: list[dict], draws: int) -> dict:
    two = item_rows(formal.rows, FLAGS)
    added = item_rows(s3, FLAGS)
    main = formal.main_on(FLAGS_VERSIONS)
    return {"registered_in": REGISTERED_IN["flags_on_against_main"], "versions": list(FLAGS_VERSIONS),
            "two_passes": {"note": "the registered report's own figure (small_groups.flags_on.against_main_same_versions)",
                           **compare4(two, main, draws)},
            "three_passes": {"note": "added: pass 3 is plan S3, sent on 13 November 2026", **compare4(two + added, main, draws)}}


def author_against_main(formal: Formal, s3: list[dict], draws: int) -> dict:
    two = item_rows(formal.rows, AUTHOR, (AUTHOR_VERSION,))
    added = item_rows(s3, AUTHOR, (AUTHOR_VERSION,))
    main = formal.main_on((AUTHOR_VERSION,))
    return {"registered_in": REGISTERED_IN["author_against_main"], "version": AUTHOR_VERSION,
            "note": "The registered report compares author with main on its two versions together. This is 2.1.280 alone.",
            "two_passes": compare4(two, main, draws),
            "three_passes": {"note": "added: pass 3 is plan S3, sent on 13 November 2026", **compare4(two + added, main, draws)}}


def load_livenerf(path: Path) -> dict:
    """LiveNerf's daily rows of its measured model over all items, by UTC date."""
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if (r.get("model") == LIVENERF_MODEL and r.get("arm") == LIVENERF_ARM and r.get("family") == LIVENERF_FAMILY
                    and str(r.get("cli_version") or "").startswith(LIVENERF_CLI) and r.get("score") not in (None, "")
                    and r.get("output_tokens_median") not in (None, "")):
                rows.append({"date": r["date_utc"], "scored": int(r["scored"]), "samples": int(r["samples"]),
                             "score": float(r["score"]), "output_tokens_median": float(r["output_tokens_median"])})
    by_day: dict = {}
    for r in rows:
        by_day.setdefault(r["date"], []).append(r)
    days = {}
    for d, rs in sorted(by_day.items()):
        n = sum(x["scored"] for x in rs)
        days[d] = {"runs": len(rs), "scored": n,
                   "score": (sum(x["score"] * x["scored"] for x in rs) / n) if n else None,
                   "output_tokens_median": float(np.mean([x["output_tokens_median"] for x in rs]))}
    return {"days": days, "rows": len(rows), "first_day": min(days) if days else None,
            "last_day": max(days) if days else None,
            "days_with_more_than_one_run": sorted(d for d, e in days.items() if e["runs"] > 1)}


def livenerf_periods(ln: dict) -> dict:
    out = {}
    for name, test in (("before_3_november", lambda d: d < SPLIT_DATE), ("from_3_november_on", lambda d: d >= SPLIT_DATE)):
        days = {d: e for d, e in ln["days"].items() if test(d) and e["score"] is not None}
        if not days:
            out[name] = {"days": 0}
            continue
        acc = [e["score"] for e in days.values()]
        med = [e["output_tokens_median"] for e in days.values()]
        out[name] = {"days": len(days), "first_day": min(days), "last_day": max(days),
                     "accuracy_lowest": min(acc), "accuracy_highest": max(acc),
                     "output_tokens_median_lowest": min(med), "output_tokens_median_highest": max(med)}
    return out


def _side_numbers(rows: list[dict]) -> dict:
    scored = [r for r in rows if analyze._scored(r)]  # noqa: SLF001
    bad = [r for r in rows if r.get("outcome") in ("error", "void")]
    out_tok = [r["output_tokens"] for r in scored if r.get("output_tokens") is not None]
    return {"asks": len(rows), "scored": len(scored), "errors_and_voids": len(bad),
            "accuracy": (sum(r["score"] for r in scored) / len(scored)) if scored else None,
            "accuracy_bad_as_wrong": (sum(r["score"] for r in scored) / (len(scored) + len(bad)))
            if scored or bad else None,
            "output_tokens_median": float(np.median(out_tok)) if out_tok else None}


def _inside(x, lo, hi):
    if x is None or lo is None or hi is None:
        return None
    return bool(lo <= x <= hi)


def author_against_livenerf_range(formal: Formal, s3: list[dict], ln: dict) -> dict:
    periods = livenerf_periods(ln)
    rows = item_rows(formal.rows, AUTHOR, (AUTHOR_VERSION,)) + item_rows(s3, AUTHOR, (AUTHOR_VERSION,))
    figures = {f"pass_{p}": {"passes": [p], **_side_numbers([r for r in rows if r.get("pass") == p])}
               for p in passes_of(rows)}
    two = [r for r in rows if r.get("pass") in (1, 2)]
    figures["passes_1_and_2_pooled"] = {"passes": passes_of(two), **_side_numbers(two)}
    figures["all_passes_pooled"] = {"passes": passes_of(rows), "added": True, **_side_numbers(rows)}
    for f in figures.values():
        f["inside"] = {}
        for name, per in periods.items():
            if not per.get("days"):
                f["inside"][name] = None
                continue
            f["inside"][name] = {
                "accuracy": _inside(f["accuracy"], per["accuracy_lowest"], per["accuracy_highest"]),
                "accuracy_bad_as_wrong": _inside(f["accuracy_bad_as_wrong"], per["accuracy_lowest"],
                                                 per["accuracy_highest"]),
                "output_tokens_median": _inside(f["output_tokens_median"], per["output_tokens_median_lowest"],
                                                per["output_tokens_median_highest"])}
    return {"registered_in": REGISTERED_IN["author_against_livenerf_range"], "version": AUTHOR_VERSION,
            "range_is": "The range runs from the lowest to the highest daily value LiveNerf published in the period, "
                        "both ends inside it. LiveNerf's daily accuracy and median output tokens are over its samples "
                        "without an error (livenerf/record.py), so this group's accuracy leaves out errors and voids "
                        "and its median output tokens are over its scored asks. Each pass is one answer to each of the "
                        "78 items, as one day of LiveNerf is. The passes pooled are given beside them.",
            "livenerf_periods": periods, "this_group": figures}


def _pass_accuracy(rows: list[dict], draws: int) -> dict:
    """Accuracy over the scored asks, and its range when the items are redrawn (the share over the drawn items'
    scored asks)."""
    sums, counts = {}, {}
    for r in rows:
        if analyze._scored(r):  # noqa: SLF001
            sums[r["unit"]] = sums.get(r["unit"], 0.0) + float(r["score"])
            counts[r["unit"]] = counts.get(r["unit"], 0) + 1
    units = sorted(counts)
    if not units:
        return {"items": 0, "scored": 0, "accuracy": None, "range_95": None}
    s = np.array([sums[u] for u in units])
    n = np.array([counts[u] for u in units], dtype=float)
    rng = np.random.default_rng(SEED)
    pick = rng.integers(0, len(units), size=(draws, len(units)))
    boot = s[pick].sum(axis=1) / n[pick].sum(axis=1)
    return {"items": len(units), "scored": int(n.sum()), "accuracy": float(s.sum() / n.sum()),
            "range_95": [float(np.quantile(boot, 0.025)), float(np.quantile(boot, 0.975))]}


def item_9_same_day(formal: Formal, s3: list[dict], ln: dict, draws: int) -> dict:
    rows = item_rows(formal.rows, AUTHOR, (AUTHOR_VERSION,)) + item_rows(s3, AUTHOR, (AUTHOR_VERSION,))
    out = {"registered_in": REGISTERED_IN["item_9"], "version": AUTHOR_VERSION,
           "how": "This group's accuracy in the pass, errors and voids left out, minus LiveNerf's published accuracy "
                  "for the UTC day of its asks. When the scored asks of a pass fall on more than one UTC day, LiveNerf's "
                  "figure is the mean of those days' figures, each weighted by this group's scored asks on that day, "
                  "and each day is also given on its own. The range is this group's, from redrawing the items. The "
                  "difference's range is that range minus LiveNerf's figure. \"They differ\" when LiveNerf's figure lies "
                  "outside this group's range.", "passes": {}}
    days = ln["days"]

    def piece(rs):
        acc = _pass_accuracy(rs, draws)
        day_n = Counter(utc_day(r.get("started_at")) for r in rs if analyze._scored(r))  # noqa: SLF001
        missing = sorted(d for d in day_n if d is None or d not in days or days[d]["score"] is None)
        e = {**acc, "scored_asks_by_utc_day": {str(d): n for d, n in sorted(day_n.items(), key=lambda kv: str(kv[0]))}}
        if not day_n or missing:
            e.update(livenerf=None, difference=None, difference_range_95=None, differ=None,
                     why_not=f"LiveNerf publishes no figure for {', '.join(map(str, missing)) or 'these asks'} in the "
                             "file given")
            return e
        ref = sum(days[d]["score"] * n for d, n in day_n.items()) / sum(day_n.values())
        e.update(livenerf=ref, livenerf_days={d: days[d]["score"] for d in sorted(day_n)},
                 difference=None if acc["accuracy"] is None else acc["accuracy"] - ref,
                 difference_range_95=None if not acc["range_95"] else [acc["range_95"][0] - ref, acc["range_95"][1] - ref])
        e["differ"] = None if not acc["range_95"] else bool(ref < acc["range_95"][0] or ref > acc["range_95"][1])
        return e

    for p in passes_of(rows):
        rs = [r for r in rows if r.get("pass") == p]
        e = piece(rs)
        e["added"] = p not in (1, 2)
        e["asks"] = len(rs)
        e["accuracy_bad_as_wrong"] = _side_numbers(rs)["accuracy_bad_as_wrong"]
        e["difference_bad_as_wrong"] = (None if e.get("livenerf") is None or e["accuracy_bad_as_wrong"] is None
                                        else e["accuracy_bad_as_wrong"] - e["livenerf"])
        if len(e["scored_asks_by_utc_day"]) > 1:
            e["each_day"] = {d: piece([r for r in rs if utc_day(r.get("started_at")) == d])
                             for d in e["scored_asks_by_utc_day"]}
        e["sentence"] = None
        if e.get("differ"):
            e["sentence"] = SENTENCES["item_9"].format(
                p=p, acc=f"{100 * e['accuracy']:.1f}%", days=", ".join(e["livenerf_days"]),
                ref=f"{100 * e['livenerf']:.1f}%", diff=f"{100 * e['difference']:+.1f} points")
        out["passes"][str(p)] = e
    return out


# ------------------------------------------------------------------------------------------ item 16

def item_16_flags_on(formal: Formal, s3: list[dict], final: dict, draws: int) -> dict:
    versions = list(final["versions"])
    declared = xn.declared_differences(final)
    flags_all = item_rows(formal.rows, FLAGS) + item_rows(s3, FLAGS)
    flags_two = item_rows(formal.rows, FLAGS)
    entries = []
    for d in declared:
        a, b = d["start"], d["end"]
        known = [v for v in FLAGS_VERSIONS if v in versions]
        inside = [v for v in known if a <= versions.index(v) <= b]
        outside = [v for v in known if v not in inside]
        e = {"test": d["test"], "segment": d["segment"], "named_by": d["named_by"], "declared_diff": d["diff"],
             "declared_shown": xn.shown(d["diff"], d["effect"]), "flags_on_versions_inside": inside,
             "flags_on_versions_outside": outside, "covered": bool(inside and outside)}
        if not e["covered"]:
            e.update(case="cannot speak to it", sentence=None)
            entries.append(e)
            continue
        ways = TEST_WAYS[d["test"]]
        flags = {name: analyze.paired(item_rows(flags_all, FLAGS, inside), item_rows(flags_all, FLAGS, outside), key,
                                      ratio=ratio, draws=draws) for name, key, ratio in ways}
        flags2 = {name: analyze.paired(item_rows(flags_two, FLAGS, inside), item_rows(flags_two, FLAGS, outside), key,
                                       ratio=ratio, draws=draws) for name, key, ratio in ways}
        main = {name: analyze.paired(formal.main_on(inside), formal.main_on(outside), key, ratio=ratio, draws=draws)
                for name, key, ratio in ways}
        shows = {}
        for name, _, _ in ways:
            r = flags[name]
            shows[name] = bool(r.get("items") and np.sign(r["diff"]) == np.sign(d["diff"]) and excludes_zero(r["range_95"]))
        shown_all = all(shows.values())
        e.update(flags_on_three_passes=flags, flags_on_passes_1_and_2=flags2, main_same_four_versions=main,
                 flags_on_shows_it_by_way=shows, flags_on_shows_it=shown_all,
                 flags_on_passes=passes_of(flags_all))
        lead = flags[ways[0][0]]
        if shown_all:
            e["case"] = "flags_on shows it too"
            e["sentence"] = SENTENCES["item_16_shown"].format(
                test=d["test"], segment=d["segment"], size=_fmt(e["declared_shown"], d["effect"]),
                inside=", ".join(inside), outside=", ".join(outside),
                flags_size=_fmt(xn.shown(lead["diff"], d["effect"]), d["effect"]),
                flags_range=_fmt_range([xn.shown(x, d["effect"]) for x in lead["range_95"]], d["effect"]))
        else:
            e["case"] = "flags_on does not show it"
            e["sentence"] = SENTENCES["item_16_not_shown"].format(test=d["test"], segment=d["segment"])
        entries.append(e)
    covered = [e for e in entries if e["covered"]]
    return {"registered_in": REGISTERED_IN["item_16"], "flags_on_versions": list(FLAGS_VERSIONS),
            "how": "Which differences are declared is read from the registered final report. A difference falls "
                   "between versions that flags_on covers when at least one of the 4 versions is inside the segment "
                   "and at least one outside. flags_on's difference is its versions inside the segment minus its "
                   "versions outside, item by item over its three passes. It shows the declared difference when, in "
                   "every way of counting of that test (accuracy: errors and voids left out and counted as wrong), "
                   "it has the declared sign and its range leaves out zero. main's difference on the same 4 versions "
                   "and flags_on's on its two passes are given beside it.",
            "declared_differences": entries,
            "nothing_declared": not declared,
            "summary_sentence": None if covered else SENTENCES["item_16_cannot"],
            "sentences": [e["sentence"] for e in covered]}


# ------------------------------------------------------------------------------------------ a day apart

def a_day_apart(formal: Formal, a3: list[dict], a3_status: list[dict], dsp_report: dict | None,
                dsp_path: Path, draws: int) -> dict:
    out = {"registered_in": REGISTERED_IN["a_day_apart"]}
    if not a3:
        out["author_2_1_322_pass_3_against_passes_1_and_2"] = {
            "not_computed": "plan A3 is not there: " + ", ".join(f"{s['plan']} {s['state']}" for s in a3_status)}
    else:
        p3 = item_rows(a3, AUTHOR, (A3_VERSION,))
        p12 = item_rows(formal.rows, AUTHOR, (A3_VERSION,))
        out["author_2_1_322_pass_3_against_passes_1_and_2"] = {
            "a": "author on 2.1.322, pass 3 (plan A3, 13 November 2026)",
            "b": "author on 2.1.322, passes 1 and 2 (11 and 12 November 2026)",
            "a3_state": [s["state"] for s in a3_status], **compare4(p3, p12, draws)}
    if dsp_report is None:
        out["desktop_prompt_e_against_main_on_2_1_321"] = {
            "not_computed": f"no report of desktop_prompt.py at {where(dsp_path)}. Run it first, or give "
                            "--desktop-prompt-report"}
    else:
        c5 = next((c for c in dsp_report.get("comparisons") or [] if c.get("id") == 5), None)
        if c5 is None:
            out["desktop_prompt_e_against_main_on_2_1_321"] = {"not_computed": "that report has no comparison 5"}
        else:
            keep = ("effect", "items", "a_passes", "b_passes", "computable", "why", "a_mean", "b_mean", "diff",
                    "diff_shown", "range_95", "range_95_shown", "draws")
            out["desktop_prompt_e_against_main_on_2_1_321"] = {
                "source": f"comparison 5 ({c5.get('name')}) of {where(dsp_path)}, copied unchanged",
                "metrics": {m: {k: v for k, v in (r or {}).items() if k in keep}
                            for m, r in (c5.get("metrics") or {}).items()},
                "reminder_check_of_that_report": c5.get("reminder_check")}
    return out


# ------------------------------------------------------------------------------------------ all of it

def compute(formal: Formal, final: dict, s3: list[dict], nosent: list[dict], a3: list[dict], ln: dict,
            grader: Grader, *, a3_status: list[dict], dsp_report: dict | None, dsp_path: Path, draws: int) -> dict:
    return {
        "nosent_against_main": nosent_against_main(formal, nosent, draws),
        "nosent_gap": nosent_gap(formal, nosent, draws),
        "nosent_unread": nosent_unread(formal, nosent, grader, draws),
        "flags_on_against_main": flags_on_against_main(formal, s3, draws),
        "author_against_main": author_against_main(formal, s3, draws),
        "author_against_livenerf_range": author_against_livenerf_range(formal, s3, ln),
        "item_9": item_9_same_day(formal, s3, ln, draws),
        "item_16": item_16_flags_on(formal, s3, final, draws),
        "a_day_apart": a_day_apart(formal, a3, a3_status, dsp_report, dsp_path, draws),
    }


def resend_fields(formal_raw: list[dict], statuses: dict) -> dict:
    """Whether the rows carry what analyze.apply_resends needs (plan, ask_id, resend_of)."""
    lacking = Counter(k for r in formal_raw for k in ("plan", "ask_id", "resend_of") if k not in r)
    out = {"registered_run": {"rows": len(formal_raw), "rows_lacking_a_field": dict(lacking),
                              "resends": sum(1 for r in formal_raw if r.get("resend_of"))}}
    for src, sts in statuses.items():
        for st in sts:
            out[st["plan"]] = {k: st.get(k) for k in ("records", "resend_records", "records_lacking_a_field", "resends",
                                                       "resends_with_their_ask", "never_reached_the_model",
                                                       "never_reached_and_not_resent")}
    return out


# ------------------------------------------------------------------------------------------ the text

def _fmt(x, effect: str) -> str:
    """A difference as shown: points for accuracy (effect diff), a per cent change for a ratio (x already shown)."""
    if x is None:
        return "n/a"
    return f"{100 * x:+.1f} points" if effect == "diff" else f"{100 * x:+.1f}%"


def _fmt_range(r, effect: str) -> str:
    if not r or r[0] is None:
        return "n/a"
    return f"{_fmt(r[0], effect)} to {_fmt(r[1], effect)}"


def _yes(x) -> str:
    return "n/a" if x is None else ("yes" if x else "no")


def _pc(x) -> str:
    return "n/a" if x is None else f"{100 * x:.1f}%"


def _measure_cell(r: dict, ratio: bool) -> str:
    if not r.get("items"):
        return "no item both sides have"
    if ratio:
        lo, hi = r["ratio_range_95"]
        return f"ratio {r['ratio']:.3f} ({lo:.3f} to {hi:.3f})"
    lo, hi = r["range_95"]
    return f"{100 * r['diff']:+.1f} points ({100 * lo:+.1f} to {100 * hi:+.1f})"


def _sides(r: dict, ratio: bool) -> str:
    if not r.get("items"):
        return ""
    if ratio:
        return f"{math.exp(r['a']) - 1:.0f} | {math.exp(r['b']) - 1:.0f}"
    return f"{_pc(r['a'])} | {_pc(r['b'])}"


def _compare_table(c: dict, a_name: str, b_name: str) -> list[str]:
    L = [f"| measure | items | {a_name} | {b_name} | {a_name} minus {b_name} (95% range) | asks {a_name} | asks {b_name} |",
         "|---|---|---|---|---|---|---|"]
    for name, _, ratio in MEASURES:
        r = c["measures"][name]
        L.append(f"| {MEASURE_LABELS[name]} | {r.get('items', 0)} | {_sides(r, ratio) or ' | '} | "
                 f"{_measure_cell(r, ratio)} | {r.get('asks_a', c['asks']['a'])} | {r.get('asks_b', c['asks']['b'])} |")
    L.append(f"\nPasses used: {a_name} {c['passes']['a']}, {b_name} {c['passes']['b']}. Thinking and output tokens are "
             "geometric means of tokens + 1, minus 1. Their difference is a ratio.")
    return L


def _registered(e: dict) -> str:
    entry, part = e["registered_in"]
    return f"Asked for by the change log entry \"{entry}\", {part}."


def report_text(rep: dict) -> str:
    n = rep["numbers"]
    L = ["# Three small groups against group main (added after the registered run)", "",
         f"Seed {rep['settings']['seed']}, {rep['settings']['draws']} redraws of the items for every range. "
         "Item by item as section 9 defines it. " + NO_VERDICT, ""]
    if rep["warnings"]:
        L += ["## Warnings", ""] + [f"- WARNING: {w}" for w in rep["warnings"]] + [""]
    chk = rep["check_against_the_final_report"]
    L += ["## Check against the registered final report", "",
          f"analyze.small_groups on the rows read here gives the final report's numbers for {', '.join(chk['compared'])}: "
          f"{'yes, every number' if chk['ok'] else 'NO'}.", ""]
    L += ["## What was read", "", "| plan | state | asks present of expected | resends | never reached the model, no resend |",
          "|---|---|---|---|---|"]
    for src in ("S3", "nosent", "A3"):
        for st in rep["sources"][src]:
            L.append(f"| {st['plan']} | {st['state']} | {st.get('asks_present', 0)} of {st.get('asks_expected', 'n/a')} | "
                     f"{st.get('resends', 0)} | {st.get('never_reached_and_not_resent', 0)} |")
    L += ["", "When the asks were sent (UTC, the plan and its resends together):", "",
          "| plan | first ask | last ask | longest wait between two asks (hours) |", "|---|---|---|---|"]
    for src in ("S3", "nosent", "A3"):
        for st in rep["sources"][src]:
            t = st.get("send_times") or {}
            gap = "n/a" if t.get("longest_gap_hours") is None else f"{t['longest_gap_hours']:.2f}"
            L.append(f"| {st['plan']} | {t.get('first', 'n/a')} | {t.get('last', 'n/a')} | {gap} |")
    f = rep["sources"]["registered_run"]
    L += ["", f"Registered run: {f['rows']} graded rows, {f['resent']} resent asks in place of the asks they replace, "
              f"versions refused by the server {f['refused'] or 'none'}, passes {f['passes']}.",
          f"LiveNerf's daily file: {rep['sources']['livenerf_daily']['rows']} rows of its measured model, "
          f"{rep['sources']['livenerf_daily']['first_day']} to {rep['sources']['livenerf_daily']['last_day']}.", ""]

    e = n["nosent_against_main"]
    L += ["## 1. nosent against main on the same version", "", _registered(e), ""]
    for label in ("2.1.280", "2.1.322", "both_versions"):
        L += [f"**{label.replace('_', ' ')}**", ""] + _compare_table(e[label], "nosent", "main") + [""]

    g = n["nosent_gap"]
    L += ["## 2. Does leaving out the two sentences change the gap between 2.1.280 and 2.1.322?", "", _registered(g),
          g["note"], "",
          "| measure | items | nosent: 2.1.322 minus 2.1.280 | main: 2.1.322 minus 2.1.280 | nosent's gap minus main's gap |",
          "|---|---|---|---|---|"]
    for name, _, ratio in MEASURES:
        r = g["measures"][name]
        if not r.get("items"):
            L.append(f"| {MEASURE_LABELS[name]} | 0 | | | |")
            continue
        cells = [_measure_cell({**r[k], "items": 1}, ratio)
                 for k in ("nosent_322_minus_280", "main_322_minus_280", "nosent_gap_minus_main_gap")]
        L.append(f"| {MEASURE_LABELS[name]} | {r['items']} | " + " | ".join(cells) + " |")
    L += ["", f"Passes used: nosent {g['passes']['nosent']}, main {g['passes']['main']}.", ""]

    u = n["nosent_unread"]
    L += ["## 3. Answers the graders could not read", "", _registered(u), u["definition"], ""]
    if u.get("not_computable"):
        L += [f"Not computed: {u['not_computable']}.", ""]
    else:
        L += ["| versions | side | scored asks | not read | share not read | accuracy, all scored | errors and voids | "
              "accuracy, errors and voids as wrong | accuracy, read answers only |", "|---|---|---|---|---|---|---|---|---|"]
        for label in ("2.1.280", "2.1.322", "both_versions"):
            for side in ("nosent", "main"):
                c = u[label][side]
                L.append(f"| {label.replace('_', ' ')} | {side} | {c['scored']} | {c['not_read']} | {_pc(c['share_not_read'])} | "
                         f"{_pc(c['accuracy_all_scored'])} | {c['errors_and_voids']} | {_pc(c['accuracy_bad_as_wrong'])} | "
                         f"{_pc(c['accuracy_over_read'])} |")
        L += ["", "Item by item, nosent minus main:", ""]
        for label in ("2.1.280", "2.1.322", "both_versions"):
            d = u[label]["nosent_minus_main_item_by_item"]
            L.append(f"- {label.replace('_', ' ')}: share not read {_measure_cell(d['share_not_read'], False)}, "
                     f"accuracy over read answers {_measure_cell(d['accuracy_over_read'], False)}")
        L.append("")

    fo = n["flags_on_against_main"]
    L += ["## 5a. flags_on against main on the same 4 versions (section 9)", "", _registered(fo), ""]
    for key, title in (("three_passes", "Three passes (added)"), ("two_passes", "Two passes (the registered report's figure)")):
        L += [f"**{title}**", ""] + _compare_table(fo[key], "flags_on", "main") + [""]

    am = n["author_against_main"]
    L += ["## 5b. author on 2.1.280 against main on 2.1.280 (section 9)", "", _registered(am), am["note"], ""]
    for key, title in (("three_passes", "Three passes (added)"), ("two_passes", "Two passes")):
        L += [f"**{title}**", ""] + _compare_table(am[key], "author", "main") + [""]

    lr = n["author_against_livenerf_range"]
    L += ["## 5c. author on 2.1.280 against LiveNerf's daily range (section 9)", "", _registered(lr), lr["range_is"], ""]
    for name, per in lr["livenerf_periods"].items():
        if per.get("days"):
            L.append(f"- LiveNerf {PERIOD_LABELS[name]}: {per['days']} days ({per['first_day']} to {per['last_day']}), "
                     f"accuracy {_pc(per['accuracy_lowest'])} to {_pc(per['accuracy_highest'])}, median output tokens "
                     f"{per['output_tokens_median_lowest']:.1f} to {per['output_tokens_median_highest']:.1f}")
        else:
            L.append(f"- LiveNerf {PERIOD_LABELS[name]}: no day in the file given")
    L += ["", "| figure | passes | scored | accuracy | accuracy, errors and voids as wrong | median output tokens | "
              "inside before 3 Nov (accuracy, the same as wrong, output) | inside from 3 Nov on (the same three) |",
          "|---|---|---|---|---|---|---|---|"]
    for name, fg in lr["this_group"].items():
        ins = []
        for per in ("before_3_november", "from_3_november_on"):
            x = fg["inside"].get(per)
            ins.append("n/a" if x is None else f"{_yes(x['accuracy'])}, {_yes(x['accuracy_bad_as_wrong'])}, "
                                                 f"{_yes(x['output_tokens_median'])}")
        med = "n/a" if fg["output_tokens_median"] is None else f"{fg['output_tokens_median']:.1f}"
        L.append(f"| {name.replace('_', ' ')}{' (added)' if fg.get('added') else ''} | {fg['passes']} | {fg['scored']} | "
                 f"{_pc(fg['accuracy'])} | {_pc(fg['accuracy_bad_as_wrong'])} | {med} | {ins[0]} | {ins[1]} |")
    L.append("")

    i9 = n["item_9"]
    L += ["## Item 9. author on 2.1.280 against LiveNerf on the same days", "", _registered(i9), i9["how"], "",
          "| pass | scored asks by UTC day | accuracy (95% range) | LiveNerf | difference (95% range) | differ | "
          "accuracy, errors and voids as wrong, minus LiveNerf |", "|---|---|---|---|---|---|---|"]
    for p, e9 in i9["passes"].items():
        days = ", ".join(f"{d}: {k}" for d, k in e9["scored_asks_by_utc_day"].items())
        acc = "n/a" if e9["accuracy"] is None else f"{_pc(e9['accuracy'])} ({_pc(e9['range_95'][0])} to {_pc(e9['range_95'][1])})"
        L.append(f"| {p}{' (added)' if e9['added'] else ''} | {days} | {acc} | {_pc(e9.get('livenerf'))} | "
                 f"{_fmt(e9.get('difference'), 'diff')} ({_fmt_range(e9.get('difference_range_95'), 'diff')}) | "
                 f"{_yes(e9.get('differ'))} | {_fmt(e9.get('difference_bad_as_wrong'), 'diff')} |")
    L.append("")
    for p, e9 in i9["passes"].items():
        if e9.get("why_not"):
            L.append(f"- pass {p}: not computed, {e9['why_not']}")
        for d, piece in (e9.get("each_day") or {}).items():
            L.append(f"- pass {p}, {d} alone: {_pc(piece['accuracy'])} on {piece['scored']} scored asks, LiveNerf "
                     f"{_pc(piece.get('livenerf'))}, difference {_fmt(piece.get('difference'), 'diff')} "
                     f"({_fmt_range(piece.get('difference_range_95'), 'diff')})")
        if e9.get("sentence"):
            L.append(f"- sentence: {e9['sentence']}")
    L.append("")

    i16 = n["item_16"]
    L += ["## Item 16. flags_on against main", "", _registered(i16), i16["how"], ""]
    if i16["nothing_declared"]:
        L += ["The final report declares no difference.", ""]
    for e16 in i16["declared_differences"]:
        eff = "diff" if e16["test"] == "accuracy" else "ratio"
        L.append(f"**{e16['test']}, {e16['segment']}** (declared {_fmt(e16['declared_shown'], eff)}, named by "
                 f"{', '.join(e16['named_by'])}): flags_on versions inside {e16['flags_on_versions_inside'] or 'none'}, "
                 f"outside {e16['flags_on_versions_outside'] or 'none'}. Case: {e16['case']}")
        if e16["covered"]:
            for way in e16["flags_on_three_passes"]:
                ratio = way == "thinking"
                L.append(f"- {MEASURE_LABELS[way]}: flags_on three passes {_measure_cell(e16['flags_on_three_passes'][way], ratio)}, "
                         f"flags_on two passes {_measure_cell(e16['flags_on_passes_1_and_2'][way], ratio)}, main on the "
                         f"same 4 versions {_measure_cell(e16['main_same_four_versions'][way], ratio)}, shows it "
                         f"{_yes(e16['flags_on_shows_it_by_way'][way])}")
        if e16.get("sentence"):
            L.append(f"- sentence: {e16['sentence']}")
        L.append("")
    if i16["summary_sentence"]:
        L += [f"Sentence: {i16['summary_sentence']}", ""]

    da = n["a_day_apart"]
    L += ["## What a day apart does to the same way of asking", "", _registered(da), ""]
    x = da["author_2_1_322_pass_3_against_passes_1_and_2"]
    if x.get("not_computed"):
        L += [f"author on 2.1.322, pass 3 against passes 1 and 2: not computed, {x['not_computed']}.", ""]
    else:
        L += ["**author on 2.1.322, pass 3 (13 November) minus passes 1 and 2 (11 and 12 November)**", ""]
        L += _compare_table(x, "pass 3", "passes 1 and 2") + [""]
    y = da["desktop_prompt_e_against_main_on_2_1_321"]
    if y.get("not_computed"):
        L += [f"Arm e of the desktop-prompt group against main on 2.1.321: not given, {y['not_computed']}.", ""]
    else:
        L += [f"**Arm e of the desktop-prompt group minus main on 2.1.321** ({y['source']})", ""]
        for m, r in y["metrics"].items():
            if r.get("computable"):
                eff = r.get("effect") or ("ratio" if m.startswith("log_") else "diff")
                L.append(f"- {m}: {_fmt(r.get('diff_shown'), eff)} ({_fmt_range(r.get('range_95_shown'), eff)}) on "
                         f"{r.get('items')} items, passes {r.get('a_passes')} against {r.get('b_passes')}")
            else:
                L.append(f"- {m}: not computable{', ' + r['why'] if r.get('why') else ''}")
        if y.get("reminder_check_of_that_report"):
            L.append("- that report's own check of this comparison (its section 16 reminder) is copied in the JSON "
                     "output")
        L.append("")

    L += ["## Resends", "", "A resent ask takes the place of the ask it was sent for (analyze.apply_resends). The fields it "
          "needs are plan, ask_id and resend_of:", ""]
    for k, v in rep["resend_fields"].items():
        L.append(f"- {k}: {json.dumps(v, ensure_ascii=False)}")
    L += ["", "## Limits", ""] + [f"- {x}" for x in rep["limits"]] + [""]
    return "\n".join(L)


def write_outputs(rep: dict, out_dir: Path) -> list[Path]:
    text_json = json.dumps(xn.clean(rep), ensure_ascii=False, indent=1) + "\n"
    text_md = report_text(xn.clean(rep))
    for name, text in (("json", text_json), ("md", text_md)):
        leaks = sorted(set(grade.PUBLIC_BAD.findall(text)))
        if leaks:
            raise Stop(f"the {name} output would hold paths or addresses {leaks[:5]}. Nothing was written")
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = [out_dir / "small_group_comparisons.json", out_dir / "small_group_comparisons.md"]
    paths[0].write_text(text_json, encoding="utf-8")
    paths[1].write_text(text_md, encoding="utf-8")
    return paths


# ------------------------------------------------------------------------------------------ command line

def run(args, grader: Grader | None = None) -> int:
    final_path = Path(args.final_report)
    if not final_path.is_file():
        raise Stop(f"no final report at {where(final_path)}: the registered run has not been analysed yet")
    files = [Path(x) for x in args.graded] if args.graded else [
        DEFAULT_GRADED_DIR / n / "graded.jsonl" for n in FORMAL_PLANS if (DEFAULT_GRADED_DIR / n / "graded.jsonl").is_file()]
    if not files:
        raise Stop("no graded.jsonl of the registered run found")
    if not args.livenerf_daily:
        raise Stop("--livenerf-daily is needed: a copy of LiveNerf's results/daily.csv downloaded after the last day "
                   "of this experiment's asks")
    daily = Path(args.livenerf_daily)
    if not daily.is_file():
        raise Stop(f"no file at {where(daily)}")
    grader = grader or Grader.from_settings(Path(args.settings))
    final = json.loads(final_path.read_text(encoding="utf-8"))
    formal_raw = analyze.load_rows(files)
    formal = Formal(formal_raw)

    statuses, rows = {}, {}
    for src, root, plans in (("S3", args.s3_raw_root, S3_PLANS), ("nosent", args.nosent_raw_root, NOSENT_PLANS),
                             ("A3", args.a3_raw_root, A3_PLANS)):
        statuses[src], rows[src] = read_source(Path(root), plans, grader)
    problems = [f"{st['plan']}: {p}" for sts in statuses.values() for st in sts for p in st["problems"]]
    if problems:
        raise Stop("records that have to be looked at first: " + " | ".join(problems))
    warnings = []
    unfinished = [st for src in ("S3", "nosent") for st in statuses[src] if st["state"] != "complete"]
    if unfinished:
        words = ". ".join(f"{st['plan']} {st['state']} ({st.get('asks_present', 0)} of {st.get('asks_expected', 'its')} "
                          f"asks, {st.get('never_reached_and_not_resent', 0)} never reached the model and are not "
                          f"resent yet)" for st in unfinished)
        if not args.allow_partial:
            raise Stop(f"not every plan is whole: {words}. If they are still being sent, wait. If they stopped for "
                       "good, give --allow-partial")
        warnings.append(f"computed although not every plan is whole: {words}. Every figure says which passes and "
                        "how many asks it used.")
    a3_unfinished = [st for st in statuses["A3"] if st["state"] not in ("complete", "not sent")]
    if a3_unfinished:
        warnings.append("plan A3 is not whole: " + ". ".join(f"{st['plan']} {st['state']}" for st in a3_unfinished))
    ln = load_livenerf(daily)
    if ln["days_with_more_than_one_run"]:
        warnings.append(f"LiveNerf's file has more than one run on {ln['days_with_more_than_one_run']}. Their mean, "
                        "weighted by scored samples, stands for the day")
    last_ask_day = max((utc_day(r.get("started_at")) or "" for r in item_rows(rows["S3"], AUTHOR)), default="")
    if ln["last_day"] is None or (last_ask_day and ln["last_day"] < last_ask_day):
        warnings.append(f"LiveNerf's file ends on {ln['last_day']}, before the last UTC day of author's asks on "
                        f"{AUTHOR_VERSION} ({last_ask_day}): download a newer copy")

    check = check_against_final_report(formal, final)
    if not check["ok"]:
        raise Stop("the rows read here do not give the final report's numbers for flags_on and author: "
                   + " | ".join(check["problems"][:20]))
    dsp_path = Path(args.desktop_prompt_report)
    dsp_report = json.loads(dsp_path.read_text(encoding="utf-8")) if dsp_path.is_file() else None

    rep = {"format": "small-group-comparisons-v1",
           "registration_entries": [ENTRY_NOSENT, ENTRY_EXTRA],
           "settings": {"seed": SEED, "draws": args.draws},
           "warnings": warnings,
           "check_against_the_final_report": check,
           "sources": {"registered_run": {"files": [where(p) for p in files], "rows": len(formal_raw),
                                          "resent": formal.resent, "refused": formal.refused, "passes": formal.passes,
                                          "final_report": where(final_path),
                                          "final_report_sha256": xn.file_sha256(final_path)},
                       "S3": statuses["S3"], "nosent": statuses["nosent"], "A3": statuses["A3"],
                       "livenerf_daily": {"file": where(daily), "sha256": xn.file_sha256(daily), "rows": ln["rows"],
                                          "first_day": ln["first_day"], "last_day": ln["last_day"]},
                       "desktop_prompt_report": where(dsp_path) if dsp_report is not None else None},
           "resend_fields": resend_fields(formal_raw, statuses),
           "numbers": compute(formal, final, rows["S3"], rows["nosent"], rows["A3"], ln, grader,
                              a3_status=statuses["A3"], dsp_report=dsp_report, dsp_path=dsp_path, draws=args.draws),
           "limits": list(LIMITS)}
    paths = write_outputs(rep, Path(args.out))
    print(json.dumps({"written": [where(p) for p in paths], "warnings": len(warnings)}, ensure_ascii=False))
    return 0


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--graded", action="append",
                    help="a graded.jsonl of the registered run (repeat). Default: graded/F1 to graded/F3r, those there")
    ap.add_argument("--final-report", default=str(DEFAULT_FINAL), help="the registered final report.json")
    ap.add_argument("--settings", default=str(DEFAULT_SETTINGS),
                    help="the registered settings (LiveNerf's repository and the item file, for grading)")
    ap.add_argument("--s3-raw-root", default=str(DEFAULT_S3_ROOT), help="the folder that holds S3/asks (and S3r/asks)")
    ap.add_argument("--nosent-raw-root", default=str(DEFAULT_NOSENT_ROOT),
                    help="the folder that holds NS1/asks to NS3r/asks")
    ap.add_argument("--a3-raw-root", default=str(DEFAULT_A3_ROOT), help="the folder that holds A3/asks (and A3r/asks)")
    ap.add_argument("--desktop-prompt-report", default=str(DEFAULT_DSP_REPORT),
                    help="report.json of added_comparisons/desktop_prompt.py, for its comparison 5")
    ap.add_argument("--livenerf-daily", help="LiveNerf's results/daily.csv, a copy downloaded after the last ask")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--draws", type=int, default=DRAWS)
    ap.add_argument("--allow-partial", action="store_true",
                    help="compute although S3 or NS1 to NS3 are not whole (marked in the outputs)")
    return ap


def main(argv=None, grader: Grader | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        return run(args, grader)
    except Stop as e:
        print(f"not run: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
