"""The swap group ("对调两句话组"): Claude Code 2.1.316 and 2.1.317, each asked two ways that count, one list of items.

Written 2026-11-13, late at night, and changed 2026-11-14 after the requirements were changed. In group main
of the registered run (39 versions, 78 items, three passes, effort high) the versions from 2.1.317 on
thought less. Asked main's way, the requests that 2.1.316 and 2.1.317 really send differ in two sentences of
the system prompt only (the two sentences about building games, SENTENCES below). This group asks one list
of items on both programs, to see whether the thinking goes with the two sentences or with the program.
There are three ways to ask:

    sw_n   group main's ask on that version, its argv not changed at all. Sent in the probes only
    sw_o   group main's ask with one more pair at the end of its argv: --system-prompt <the whole prompt,
           holding 2.1.316's two sentences>. The pair --append-system-prompt <the author's text> stays
           where it is, with the same value, so every item of main's argv keeps its place
    sw_w   as sw_o, with 2.1.317's two sentences in the whole prompt

The scored passes ask the ways in [group] scored_groups (sw_o and sw_w unless the settings say otherwise),
so four cells: two programs times two ways.

This file is outside the modules the run's fingerprint covers and changes none of them. It imports
ccversions and uses its code for everything an ask is made of: ccversions.run.prepare() builds every ask as
it builds a main ask (mode stock_blocked, effort high, the model, the tools described and every call refused
by the hook, remote settings from the server not fetched, the environment built from nothing, the token
login, the working folder, the timeout, no transcript), in this group's config folders. For sw_o and sw_w
the one pair is then added (add_system_prompt). ccversions.run.Runner.execute() runs the ask and writes the
record, so the checks around an ask, the record itself (its config_dir among the rest) and how an error, a
usage limit or a void is recognised are main's own. The records keep mode "stock_blocked", so grade.py and
runcheck.py read them unchanged. Their group is sw_n, sw_o or sw_w, and each has one more field, "swap":
the way, the structure, the length and sha256 of the whole prompt (null for sw_n), the set ("set", w1, w2
and so on, or "(probe folder)"), the folder, and the path put into the whole prompt ("filled_config_dir").

The whole prompt. Claude Code sends its own system prompt as three blocks: the opening sentence, a static
block, and a dynamic block that ends with two newlines and the author's text. `extract` takes three texts
out of the kept transcripts of the unscored probes of 2026-11-13, 19:35 (SOURCE): STATIC (2.1.316's second
block), DYNAMIC_OLD and DYNAMIC_NEW (the third block of 2.1.316 and of 2.1.317, without the two newlines
and the author's text at its end), each probe's own config folder path replaced by {CONFIG_DIR}. It checks
them (take_texts) and stores them with a manifest. Every later read checks their sha256 against it.

For an ask of sw_o or sw_w, {CONFIG_DIR} is replaced by one of two paths:

    its own path    the config folder the ask itself runs in (probe steps 1 and 2)
    the set's path  the 2.1.316 worker folder of the ask's set (fill_set), for the asks of both versions,
                    so the two versions of one set send the same whole prompt to the character (the scored
                    passes, the small batch of --trial, probe steps 3 and 4)

The whole prompt is then put together by the structure the settings name ([group] structure):

    join0   STATIC, then the dynamic text
    join1   STATIC, one newline, the dynamic text
    join2   STATIC, two newlines, the dynamic text
    marker  STATIC, one newline, a line __SYSTEM_PROMPT_DYNAMIC_BOUNDARY__, one newline, the dynamic text

What the server puts between the blocks when it joins them is not known, so the first three each try one
way. Claude Code itself cuts a prompt at a line that reads __SYSTEM_PROMPT_DYNAMIC_BOUNDARY__ and sends the
two parts as two blocks. As read in the code of 2.1.316 and 2.1.317 (not yet checked by sending), the part
before that line ends with one newline and the part after it starts with one newline
(split_like_claude_code). That the appended author's text then follows the part after it, with two newlines
between, is taken from how the code joins the parts of a prompt, without following where the appended text
enters (expected_blocks). Step 2 of the probes checks both. Which structure is right is decided by the probes.

Config folders (setup-dirs), made the way dsp.py makes its own: a root of this group's own next to the main
config root ([paths] config_root, /Users/Shared/kq7/s), folders named by meaningless codes (the main
table's two letters and two digits, never 16 or 17), mode 700, each holding only a .claude.json with the
shared userID and machineID copied from the main table, every path as long as the main folders' paths.

    probe folders    one per version (the table's main codes). Only the probes that keep their
                     transcript and the outage probes go there
    worker folders   [group] sets sets (w1, w2, ...), each with one folder per version, bound to remote
                     settings off. Every scored ask and every warm-up goes there, and no transcript is kept

A folder serves one version only and never has two asks at a time. The two folders of one set are two
folders and may each have one. Which set an ask goes to is fixed when its plan is made (assign_sets). In
every block of a pass the three items take one set each, by an order of the sets the seed, the pass and
the block pick (with another number of sets than three, the items of the pass take the sets in turn by an
order the seed and the pass pick). Every ask of one item in one pass goes to that set: the 2.1.316 asks to
its 2.1.316 folder, the 2.1.317 asks to its 2.1.317 folder. One seed makes one plan.

Plans. Pass n is plan SW<n>, its resend plan SW<n>r, the small batch of --trial SWS (the program that adds
up the results takes the records by these names). A pass asks every item of [group] item_list once per
cell, in blocks of three items, shuffled by plan.make_arms with the seed [group] seed and the pass number,
so every block holds its three items once for each cell (12 asks a block, 96 a pass for 24 items and the
two ways). After a pass is complete, its asks that never reached the model are asked once more
(formal.py). The probe plans are SWP1_k to SWP4_k and the outage probes SWH_nnn. [group] stage1_passes is
read by the program that adds up the results, and not used here.

Probes (all of them the probe sentence probe:author-ok, unscored), four steps, each only after the one
before it has passed. What is compared of a probe that kept its transcript is its first request: the input
tokens, the system blocks, and everything else (OTHER_PARTS: the tools with their descriptions and input
schemas, the betas, thinking, output_config, max_tokens, context_management, the other parameters, the
model, the user message, and every extra message with its role and texts, the blobs of the transcript).

    step 1   own path, in 2.1.316's probe folder, keeping the transcript: sw_n, sw_o once with each
             structure, sw_n again. The two sw_n must agree (input tokens, system blocks, everything else
             sent). A structure passes when its input tokens, first system block and everything sent besides
             the system blocks equal sw_n's. Of the structures that pass, the first of join2, marker, join1,
             join0 is taken. The check file gets each structure's number of system blocks and their lengths,
             and every probe's cache reads and cache writes. The settings must name that structure for the
             next steps
    step 2   own path, that structure: sw_w in 2.1.316's probe folder, then sw_n, sw_o, sw_w, sw_n in
             2.1.317's. (1) Every probe answered with model claude-opus-5-5 and effort high. (2) 2.1.317's two
             sw_n agree. (3) Every sw_o and sw_w has sw_n's first system block in its folder. (4) Its other
             blocks, put back together by the structure, equal the program's own whole prompt, two newlines
             and the author's text, character for character, cut into blocks as expected_blocks says. (5)
             Everything sent besides the system blocks equals sw_n's in its folder. (6) sw_o has sw_n's
             input tokens on 2.1.316, sw_w on 2.1.317, and sw_w minus sw_o is one number in both folders
    step 3   the set's path, in 2.1.317's probe folder, keeping the transcript: sw_o then sw_w for every set.
             Each probe must pass checks 1, 3, 4 and 5 of step 2, against step 2's first sw_n of that folder.
             Each probe's input tokens go into the check file
    step 4   the set's path, in every worker folder, no transcript: sw_n, then the folder's own version's
             way (sw_o on 2.1.316, sw_w on 2.1.317). Both must answer. In a 2.1.316 folder the two input
             token numbers are equal. In a 2.1.317 folder sw_w's number equals step 3's sw_w of the same set

Running probes again sends only what has not passed. What passed counts while the three texts, this file
and the structure in the settings stay as they were (and for steps 3 and 4, per set and per folder).

Commands (the settings file defaults to 本机数据/对调两句话组/设置.toml):

    python -B swap.py extract        take the three texts out of SOURCE, check them, store them (sends nothing)
    python -B swap.py setup-dirs     create this group's config folders (sends nothing)
    python -B swap.py compare        print main's ask on both versions next to this group's three ways
                                     (sends nothing)
    python -B swap.py probes         the four probe steps, stopping at the first step that does not pass
    python -B swap.py send --trial 2 a small batch: 2 items, every cell, a plan of its own (SWS, not counted)
    python -B swap.py send           the passes ([group] passes) and their resends. Run it again after any
                                     stop: an ask that has a record is never sent again
    python -B swap.py send --passes 1-6
                                     passes 1 to 6 only (one number, such as --passes 7, is that pass only).
                                     A pass that is complete is not sent again
    python -B swap.py status         counts, the last weekly reading, the probes (no answers, no scores)

probes and send refuse, and say why, in each of these cases:
    the settings do not say allow_send = true
    another program sends (ps: a version binary of this experiment running with -p, or a runner of
    ccversions, dsp.py, nosent.py, swap.py, 程序/再验少想/driver.py or 全部发.sh), unless
    --alongside-other-sends is given
    this group's last weekly reading is at or above [group] weekly_line, unless --after-reset is given
    (send only) the four probe steps have not passed with the three texts as they are now, this file, the
    structure in the settings, every set and every worker folder it will use

What stops a send, and what happens then (dsp.py, after formal.py):
    the weekly line ([group] weekly_line)        the asks already running finish, then the command ends
    a usage limit                                the command ends (from a reading of 0.90 on, and below
                                                 that it stops for a person)
    8 asks in a row with no answer (an outage)   wait 5, 10, 20, 40, 60, 60 ... minutes, each time send one
                                                 cheap probe (mode author, effort low, 2.1.317's probe
                                                 folder). When it answers, go on. Gives up after 6 hours
    anything else (a tool ran, a dirty working   the command ends and says why
    folder, not the subscription, a signal)
At the start of every call the first ask runs alone, and the others start only after one ask of the call
came back with an answer.
"""

import argparse
import hashlib
import json
import os
import random
import re
import secrets
import subprocess
import sys
import time
import tomllib
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROGRAM = HERE.parent
PROJECT = PROGRAM.parent
if str(PROGRAM) not in sys.path:
    sys.path.insert(0, str(PROGRAM))
sys.dont_write_bytecode = True

from ccversions import checks, configdirs, envpolicy, extract, formal, grade, items as items_mod  # noqa: E402
from ccversions import modes as modes_mod, plan as plan_mod, run, settings as settings_mod, transcripts  # noqa: E402

DEFAULT_SETTINGS = PROJECT / "本机数据" / "对调两句话组" / "设置.toml"
# The registered run's files, read only (never written): its settings and third pass plan (main's ask on
# the two versions, for `compare`) and its config folder table (the shared device IDs and the code prefix).
FORMAL_SETTINGS = PROJECT / "本机数据" / "本机设置.toml"
FORMAL_STATE = PROJECT / "本机数据" / "配置文件夹.json"
FORMAL_PLAN = PROJECT / "本机数据" / "正式跑" / "plans" / "F3.json"
# Where the three texts come from: the asks of the unscored probes of 2026-11-13, 19:35, as
# `ccversions read-transcripts` wrote them (one line per ask, "system" holding the blocks really sent).
SOURCE = PROJECT / "本机数据" / "再验少想" / "probes" / "RP1_transcripts" / "asks.jsonl"
SOURCE_FILTER = {"mode": "stock_blocked", "effort_requested": "high", "warmup": False, "unit": "probe:author-ok"}
SOURCE_MAX_TOKENS = 20000  # the first request's input tokens must be below this

OLD, NEW = "2.1.316", "2.1.317"
VERSIONS = (OLD, NEW)
# The two sentences of each version, as the requirements file gives them (section one)
SENTENCES = {
    OLD: ("Do build original games, games in a genre, and games from the user's own designs and assets. "
          "Don't build a recreation of a specific existing game, even if it is renamed or called original."),
    NEW: ("Do build original games, games in a genre or with similar mechanics, and games from the user's own "
          "designs and assets. Don't build a recreation of a specific existing game (its name, characters, art, "
          "music, levels or look), even if it is renamed or called original."),
}
GROUPS = ("sw_n", "sw_o", "sw_w")
SENTENCES_OF = {"sw_n": None, "sw_o": OLD, "sw_w": NEW}  # whose two sentences the whole prompt holds
DYNAMIC_OF = {"sw_o": "DYNAMIC_OLD", "sw_w": "DYNAMIC_NEW"}
OWN_GROUP = {OLD: "sw_o", NEW: "sw_w"}  # the way that sends a version's own two sentences
LABELS = {"sw_n": "group main's ask on this version, unchanged",
          "sw_o": "group main's ask with --system-prompt <the whole prompt with 2.1.316's two sentences> added",
          "sw_w": "group main's ask with --system-prompt <the whole prompt with 2.1.317's two sentences> added"}
INTRO = "You are Claude Code, Anthropic's official CLI for Claude, running within the Claude Agent SDK."
PLACEHOLDER = "{CONFIG_DIR}"
BOUNDARY = "__SYSTEM_PROMPT_DYNAMIC_BOUNDARY__"
STATIC_BREAKPOINT = "__SYSTEM_PROMPT_STATIC_BREAKPOINT__"  # the other line Claude Code cuts a prompt at
STRUCTURES = ("join0", "join1", "join2", "marker")
# Of the structures that pass step 1, the first is taken. join2 comes first because, as read in the code of
# both programs, Claude Code itself joins the two blocks into one with two newlines when its global cache
# switch is off, and marker adds one newline on each side of the boundary.
PREFERENCE = ("join2", "marker", "join1", "join0")
DEFAULT_SCORED = ("sw_o", "sw_w")  # the ways the scored passes ask unless [group] scored_groups says otherwise
DEFAULT_PARALLEL = 2
SEPARATORS = {"join0": "", "join1": "\n", "join2": "\n\n", "marker": "\n" + BOUNDARY + "\n"}
TEXT_NAMES = ("STATIC", "DYNAMIC_OLD", "DYNAMIC_NEW")
EFFORT = "high"
BLOCK_UNITS = 3
PROBE_UNIT = "probe:author-ok"
HEALTH_VERSION = NEW  # the outage probe goes into this version's probe folder
FAIL_STREAK = plan_mod.FAIL_STREAK_STOP  # 8, as the registered run
MAX_OUTAGE_HOURS = 6  # inputs/formal_run.json max_outage_hours
MANIFEST_FORMAT = "swap-texts-v1"
CHECK_FORMAT = "swap-probe-check-v2"
SET_RE = re.compile(r"w([1-9][0-9]?)")
MAX_SETS = 40
# Command lines of other programs that send asks (looked up with ps, no process is touched)
RUNNER_MARKS = ("-m ccversions send", "-m ccversions formal", "dsp.py send", "dsp.py probes", "nosent.py send",
                "nosent.py probes", "swap.py send", "swap.py probes", "driver.py", "全部发.sh")
# Everything an ask sends besides its system blocks, compared between two probes. "extra_messages" are the
# messages of the request other than the user message, each with its role and texts (the transcript keeps
# them as blobs: the environment, the deferred tool list, the agent types, the skills, the date).
OTHER_PARTS = ("tools", "betas", "thinking", "output_config", "max_tokens", "context_management", "other_params",
               "model", "extra_message_efforts", "user_message", "extra_messages")


class SwapError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_json(path: Path, doc) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def program_sha256() -> str:
    return hashlib.sha256(Path(__file__).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def first_difference(a: str, b: str) -> str:
    n = min(len(a), len(b))
    i = next((k for k in range(n) if a[k] != b[k]), n)
    return (f"{len(a)} and {len(b)} characters, first difference at character {i}: "
            f"{a[max(0, i - 40):i + 40]!r} against {b[max(0, i - 40):i + 40]!r}")


# ------------------------------------------------------------------------------------------- settings

@dataclass
class Env:
    settings: settings_mod.Settings
    data: Path
    weekly_line: float
    parallel: int
    sets: int
    structure: str
    item_list: Path
    passes: int
    seed: str
    scored_groups: tuple = DEFAULT_SCORED
    stage1_passes: int | None = None  # read by the program that adds up the results, kept here for status only
    sleep: object = time.sleep
    find_other_sends: object = None  # replaced in the self-test
    _inputs: object = field(default=None, repr=False)

    @property
    def plans(self) -> Path:
        return self.data / "plans"

    @property
    def texts_dir(self) -> Path:
        return self.data / "说明"

    @property
    def probe_check_file(self) -> Path:
        return self.data / "探针核对.json"

    @property
    def state_file(self) -> Path:
        return self.data / "state.json"

    def run_dir(self, name: str) -> Path:
        return self.settings.raw_dir / name

    def inputs(self):
        if self._inputs is None:
            s = self.settings
            self._inputs = items_mod.load(s.item_file, s.item_file_sha256, s.probe_file)
        return self._inputs


def _whole_number(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 1


def load_env(path: str | None) -> Env:
    p = Path(path) if path else DEFAULT_SETTINGS
    s = settings_mod.load(str(p))
    g = tomllib.loads(p.read_text(encoding="utf-8")).get("group", {})
    where = f"{p}: [group]"
    unknown = sorted(set(g) - {"weekly_line", "parallel", "sets", "structure", "item_list", "passes", "seed",
                               "scored_groups", "stage1_passes"})
    if unknown:
        raise SwapError(f"{where} has unknown keys {unknown}")
    line = g.get("weekly_line")
    if not (isinstance(line, (int, float)) and not isinstance(line, bool) and 0 < line <= 1):
        raise SwapError(f"{where} weekly_line must be a share between 0 and 1, not {line!r}")
    parallel, sets, passes = g.get("parallel", DEFAULT_PARALLEL), g.get("sets", 3), g.get("passes")
    for name, value in (("parallel", parallel), ("sets", sets), ("passes", passes)):
        if not _whole_number(value):
            raise SwapError(f"{where} {name} is a whole number of at least 1, not {value!r}")
    if sets > MAX_SETS:
        raise SwapError(f"{where} sets is at most {MAX_SETS} (the two-digit codes run out above that)")
    stage1 = g.get("stage1_passes")
    if stage1 is not None and not (_whole_number(stage1) and stage1 <= passes):
        raise SwapError(f"{where} stage1_passes is a whole number from 1 to passes ({passes}), not {stage1!r}")
    scored = g.get("scored_groups", list(DEFAULT_SCORED))
    if (not isinstance(scored, list) or not scored or len(set(scored)) != len(scored)
            or not all(x in GROUPS for x in scored)):
        raise SwapError(f"{where} scored_groups is a list of ways out of {list(GROUPS)}, each once, not {scored!r}")
    structure = g.get("structure")
    if structure not in STRUCTURES:
        raise SwapError(f"{where} structure is one of {STRUCTURES}, not {structure!r}")
    item_list = g.get("item_list")
    if not isinstance(item_list, str) or not item_list:
        raise SwapError(f"{where} item_list is the path of a JSON file with the item ids")
    il = Path(item_list)
    if not il.is_absolute():
        il = p.resolve().parent / il
    seed = g.get("seed")
    if not isinstance(seed, str) or not seed.strip():
        raise SwapError(f"{where} seed is a string")
    return Env(settings=s, data=p.resolve().parent, weekly_line=float(line), parallel=parallel, sets=sets,
               structure=structure, item_list=il, passes=passes, seed=seed,
               scored_groups=tuple(x for x in GROUPS if x in scored), stage1_passes=stage1)


def item_units(env: Env) -> tuple[list[str], dict]:
    """The items to ask, as unit keys ("item:<id>"), in the file's order. The file is a JSON object whose
    "items" lists the ids. An id without the "item:" in front gets it."""
    path = env.item_list
    if not path.is_file():
        raise SwapError(f"the item list {path} does not exist")
    raw = path.read_bytes()
    doc = json.loads(raw.decode("utf-8"))
    ids = doc.get("items") if isinstance(doc, dict) else None
    if not isinstance(ids, list) or not ids or not all(isinstance(x, str) and x for x in ids):
        raise SwapError(f"{path}: \"items\" must be a list of item ids")
    units = [x if x.startswith("item:") else f"item:{x}" for x in ids]
    if len(set(units)) != len(units):
        raise SwapError(f"{path} lists an item more than once")
    inputs = env.inputs()
    for u in units:
        inputs.unit(u)  # raises on an item the item file does not have
    return units, {"file": str(path), "sha256": hashlib.sha256(raw).hexdigest(), "items": len(units),
                   "prefix_added": sum(1 for x in ids if not x.startswith("item:"))}


def _versions(env: Env) -> list:
    return json.loads(env.settings.versions_file.read_text())["versions"]


# ---------------------------------------------------------------------------------------------- texts

def read_source(path: Path) -> tuple[list[dict], str]:
    raw = path.read_bytes()
    rows = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
    return rows, hashlib.sha256(raw).hexdigest()


def pick_source_rows(rows: list[dict], where: str = "the source") -> dict:
    """For each version the one ask of SOURCE_FILTER with fewer first-request input tokens than
    SOURCE_MAX_TOKENS. There must be exactly one per version."""
    out = {}
    for v in VERSIONS:
        hits = [r for r in rows if r.get("version") == v and all(r.get(k) == x for k, x in SOURCE_FILTER.items())
                and isinstance(r.get("first_request_input_tokens"), int)
                and r["first_request_input_tokens"] < SOURCE_MAX_TOKENS]
        if len(hits) != 1:
            raise SwapError(f"{where}: {len(hits)} asks of {v} have {SOURCE_FILTER} and fewer than "
                            f"{SOURCE_MAX_TOKENS} first-request input tokens, and exactly one is expected")
        out[v] = hits[0]
    return out


def _path_forms(path: str) -> list[str]:
    """The ways a config folder path may stand in a text: as it is, without its first slash, with every
    slash a hyphen (Claude Code's project folder names), and the folder's own code."""
    p = path.rstrip("/")
    return sorted({p, p.lstrip("/"), p.replace("/", "-"), Path(p).name}, key=len, reverse=True)


def take_texts(rows: dict, author: str) -> tuple[dict, list]:
    """The three texts out of the two picked asks, and the checks they passed. Any check that fails raises
    SwapError naming the check (the numbers are those of the requirements file, and 0 and 6 are added)."""
    done = []

    def fail(number, what, detail):
        raise SwapError(f"check {number} failed ({what}): {detail}")

    what = "each ask has three system blocks of text and an absolute config folder path"
    for v in VERSIONS:
        r = rows[v]
        blocks = r.get("system")
        if not (isinstance(blocks, list) and len(blocks) == 3 and all(isinstance(x, str) for x in blocks)):
            fail("0 (added)", what, f"{v}: system is {type(blocks).__name__} with "
                 f"{len(blocks) if isinstance(blocks, list) else '-'} parts")
        if not (isinstance(r.get("config_dir"), str) and r["config_dir"].startswith("/")):
            fail("0 (added)", what, f"{v}: config_dir is {r.get('config_dir')!r}")
    done.append({"check": "0 (added)", "what": what, "ok": True})

    what = "the first block of both asks is the opening sentence " + repr(INTRO)
    for v in VERSIONS:
        if rows[v]["system"][0] != INTRO:
            fail(1, what, f"{v}'s first block is {rows[v]['system'][0][:200]!r}")
    done.append({"check": 1, "what": what, "ok": True})

    what = "the second block is the same in both asks"
    if rows[OLD]["system"][1] != rows[NEW]["system"][1]:
        fail(2, what, first_difference(rows[OLD]["system"][1], rows[NEW]["system"][1]))
    done.append({"check": 2, "what": what, "ok": True})

    what = "the third block of both asks ends with two newlines and the author's text"
    tail = "\n\n" + author
    for v in VERSIONS:
        b = rows[v]["system"][2]
        if not b.endswith(tail):
            fail(3, what, f"{v}'s third block ends with {b[-len(tail) - 20:]!r}")
    done.append({"check": 3, "what": what, "ok": True})

    static = rows[OLD]["system"][1]
    raw = {v: rows[v]["system"][2][:-len(tail)] for v in VERSIONS}
    # check 5 before check 4: a path left in would make check 4 fail for another reason than its own
    what = f"each dynamic text holds {PLACEHOLDER} at least once and its probe's config folder path no more"
    dyn = {}
    for v in VERSIONS:
        cfg = rows[v]["config_dir"]
        if PLACEHOLDER in raw[v]:
            fail(5, what, f"{v}'s third block holds {PLACEHOLDER} before it is put in")
        d = raw[v].replace(cfg, PLACEHOLDER)
        left = {f: d.count(f) for f in _path_forms(cfg) if f in d}
        if d.count(PLACEHOLDER) < 1 or left:
            fail(5, what, f"{v}: {PLACEHOLDER} {d.count(PLACEHOLDER)} times, left of {cfg}: {left or 'nothing'}")
        dyn[v] = d
    done.append({"check": 5, "what": what, "ok": True,
                 "placeholder_count": {"DYNAMIC_OLD": dyn[OLD].count(PLACEHOLDER),
                                       "DYNAMIC_NEW": dyn[NEW].count(PLACEHOLDER)}})

    what = ("DYNAMIC_OLD holds 2.1.316's two sentences once, DYNAMIC_NEW 2.1.317's once, and DYNAMIC_OLD with "
            "them replaced by 2.1.317's equals DYNAMIC_NEW")
    counts = {"2.1.316's in DYNAMIC_OLD": dyn[OLD].count(SENTENCES[OLD]),
              "2.1.317's in DYNAMIC_NEW": dyn[NEW].count(SENTENCES[NEW])}
    if set(counts.values()) != {1}:
        fail(4, what, f"times found: {counts}")
    swapped = dyn[OLD].replace(SENTENCES[OLD], SENTENCES[NEW])
    if swapped != dyn[NEW]:
        fail(4, what, "DYNAMIC_OLD with the sentences replaced against DYNAMIC_NEW: " + first_difference(swapped, dyn[NEW]))
    done.append({"check": 4, "what": what, "ok": True})

    texts = {"STATIC": static, "DYNAMIC_OLD": dyn[OLD], "DYNAMIC_NEW": dyn[NEW]}
    what = f"no text holds a line Claude Code cuts a prompt at ({BOUNDARY}, {STATIC_BREAKPOINT})"
    for name, t in texts.items():
        for m in (BOUNDARY, STATIC_BREAKPOINT):
            if m in t:
                fail("6 (added)", what, f"{name} holds {m}")
    done.append({"check": "6 (added)", "what": what, "ok": True})
    return texts, done


def extract_all(out_dir: Path, author: str, source: Path = SOURCE, *, replace: bool = False) -> dict:
    rows_all, source_sha = read_source(source)
    rows = pick_source_rows(rows_all, str(source))
    texts, done = take_texts(rows, author)
    manifest = {
        "format": MANIFEST_FORMAT, "made_at": utc_now(),
        "source_file": str(source), "source_sha256": source_sha, "source_lines": len(rows_all),
        "source_filter": {**SOURCE_FILTER, "first_request_input_tokens_below": SOURCE_MAX_TOKENS},
        "source_asks": {v: {k: rows[v].get(k) for k in ("run", "ask_id", "version", "config_dir",
                                                        "first_request_input_tokens", "shapeHash")} for v in VERSIONS},
        "how": ("STATIC is the second system block of 2.1.316's ask. DYNAMIC_OLD and DYNAMIC_NEW are the third "
                "block of 2.1.316's and of 2.1.317's ask without the two newlines and the author's text at its "
                "end, with that ask's own config folder path replaced by " + PLACEHOLDER + ". The files hold "
                "the text exactly, with no newline added."),
        "sentences": SENTENCES,
        "author_text": {"chars": len(author), "sha256": sha256_text(author)},
        "checks": done,
        "texts": [{"name": n, "file": f"{n}.txt", "chars": len(texts[n]), "sha256": sha256_text(texts[n]),
                   "placeholder_count": texts[n].count(PLACEHOLDER)} for n in TEXT_NAMES],
    }
    old = out_dir / "清单.json"
    if old.exists() and not replace:
        before = json.loads(old.read_text(encoding="utf-8"))
        if {t["name"]: t["sha256"] for t in before.get("texts", [])} != {t["name"]: t["sha256"] for t in manifest["texts"]}:
            raise SwapError(f"{old} lists other texts than these. Plans and probes made with the old texts would "
                            "no longer fit. Run with --replace only if nothing has been sent yet")
    out_dir.mkdir(parents=True, exist_ok=True)
    for n in TEXT_NAMES:
        (out_dir / f"{n}.txt").write_bytes(texts[n].encode("utf-8"))
    write_json(old, manifest)
    return manifest


@dataclass(frozen=True)
class Text:
    name: str
    file: str
    text: str
    sha256: str


def load_texts(env: Env) -> dict:
    """The three stored texts, each checked against the manifest."""
    path = env.texts_dir / "清单.json"
    if not path.is_file():
        raise SwapError(f"{path} does not exist: run `extract` first")
    m = json.loads(path.read_text(encoding="utf-8"))
    if m.get("format") != MANIFEST_FORMAT:
        raise SwapError(f"{path} is not a {MANIFEST_FORMAT} file")
    out = {}
    for row in m.get("texts") or []:
        f = env.texts_dir / row["file"]
        if not f.is_file():
            raise SwapError(f"{f} is missing (listed in {path})")
        t = f.read_bytes().decode("utf-8")
        if sha256_text(t) != row["sha256"] or len(t) != row["chars"]:
            raise SwapError(f"{f} has changed since it was stored (sha256 or length differs from {path})")
        out[row["name"]] = Text(row["name"], row["file"], t, row["sha256"])
    if sorted(out) != sorted(TEXT_NAMES):
        raise SwapError(f"{path} lists texts {sorted(out)}, expected {sorted(TEXT_NAMES)}")
    return out


def texts_sha(texts: dict) -> dict:
    return {k: texts[k].sha256 for k in TEXT_NAMES}


# ------------------------------------------------------------------------------- the whole prompt

def dynamic_text(texts: dict, group: str, config_dir) -> str:
    t = texts[DYNAMIC_OF[group]].text
    if t.count(PLACEHOLDER) < 1:
        raise SwapError(f"{DYNAMIC_OF[group]} holds no {PLACEHOLDER}")
    return t.replace(PLACEHOLDER, str(config_dir))


def whole_prompt(texts: dict, group: str, structure: str, config_dir) -> str:
    """The --system-prompt value of an ask of sw_o or sw_w in the config folder config_dir."""
    if group not in DYNAMIC_OF:
        raise SwapError(f"group {group!r} sends no whole prompt")
    if structure not in SEPARATORS:
        raise SwapError(f"unknown structure {structure!r}")
    return texts["STATIC"].text + SEPARATORS[structure] + dynamic_text(texts, group, config_dir)


def add_system_prompt(argv: list, author: str, whole: str) -> list:
    """main's argv with the pair --system-prompt <whole> added at its end. The one pair
    --append-system-prompt <the author's text> stays where it is. Anything unexpected raises."""
    if argv.count("--append-system-prompt") != 1 or "--system-prompt" in argv:
        raise SwapError("the argv does not have exactly one --append-system-prompt and no --system-prompt")
    i = argv.index("--append-system-prompt")
    if i + 1 >= len(argv) or argv[i + 1] != author:
        raise SwapError("the value after --append-system-prompt is not the author's text")
    return list(argv) + ["--system-prompt", whole]


def split_like_claude_code(text: str, marker: str = BOUNDARY) -> list:
    """A prompt cut at its first line that reads `marker` (blank space around it ignored), as the code of
    2.1.316 and 2.1.317 does it: the part before the line with one newline added at its end, the marker,
    the part after it with one newline added at its start. A part of blank space only is left out."""
    lines = text.split("\n")
    s = next((i for i, x in enumerate(lines) if x.strip() == marker), None)
    if s is None:
        return [text]
    before = "\n".join(lines[:s]) + "\n"
    after = "\n" + "\n".join(lines[s + 1:])
    return ([before] if before.strip() else []) + [marker] + ([after] if after.strip() else [])


def expected_blocks(whole: str, author: str) -> list:
    """The system blocks after the opening sentence that an ask with --system-prompt <whole> and
    --append-system-prompt <author> should send, as the code was read: with a marker line, the part before
    it is one block and the part after it with the author's text (two newlines between) another. Without
    one, the whole prompt and the author's text (two newlines between) are one block."""
    items = split_like_claude_code(whole) + [author]
    if BOUNDARY in items:
        k = items.index(BOUNDARY)
        before, after = items[:k], items[k + 1:]
        return (["\n\n".join(before)] if before else []) + (["\n\n".join(after)] if after else [])
    return ["\n\n".join(items)]


def rebuild(blocks: list, structure: str) -> str:
    """The system blocks after the opening sentence put back into one text by the structure: joined at
    the marker line for marker, with two newlines (Claude Code's own join) for the others."""
    return (BOUNDARY if structure == "marker" else "\n\n").join(blocks)


# ------------------------------------------------------------------------------------- config folders

def load_state(env: Env) -> dict | None:
    return configdirs.load_state(env.settings.config_dirs_file)


def worker_sets(state: dict) -> list[str]:
    return sorted((n for n in (state.get("sets") or {}) if SET_RE.fullmatch(n)), key=lambda n: int(n[1:]))


def sets_in_use(env: Env, state: dict) -> list[str]:
    have = worker_sets(state)
    if len(have) < env.sets:
        raise SwapError(f"the settings name {env.sets} sets of worker folders and the table has {len(have)}: "
                        "run setup-dirs")
    return have[:env.sets]


def folder_label(config_set: str | None, version: str) -> str:
    return f"{config_set or 'probe'}/{version}"


def worker_folders(state: dict, sets: list) -> list[tuple[str, str, Path]]:
    return [(n, v, configdirs.config_dir(state, v, n)) for n in sets for v in VERSIONS]


def setup_dirs(env: Env, sets: int | None = None, formal_state_path: Path | None = None) -> dict:
    """Create this group's config folders the way dsp.py creates its own: codes from the main table's two
    letters and two free digits (never 16 or 17), mode 700, a .claude.json with the shared device IDs
    copied from the main table, every path as long as the main folders' paths. Two probe folders (the
    table's main codes, one per version) and `sets` sets wN, each with one folder per version, bound to
    remote settings off. Running it again never changes an existing folder or code. It adds sets."""
    s = env.settings
    sets = sets or env.sets
    formal_state_path = formal_state_path or FORMAL_STATE
    root = Path(os.path.abspath(s.config_root))
    if not 1 <= sets <= MAX_SETS:
        raise SwapError(f"between 1 and {MAX_SETS} sets")
    main = configdirs.load_state(formal_state_path)
    if main is None or not main.get("machine_id"):
        raise SwapError(f"{formal_state_path}: the main config folder table is missing or has no machineID")
    main_root = Path(main["config_root"])
    if root == main_root or root.parent != main_root.parent or len(root.name) != len(main_root.name):
        raise SwapError(f"{root} must sit next to the main config root {main_root} with a name as long as its")
    state = load_state(env)
    created = state is None
    if state is None:
        if root.exists() and (not root.is_dir() or os.listdir(root)):
            raise SwapError(f"{root} already exists and is not empty, and this group has no table yet")
        state = {"format": configdirs.STATE_FORMAT, "created_at": utc_now(), "config_root": str(root),
                 "code_seed": secrets.token_hex(16), "prefix": main["prefix"], "codes": {},
                 "user_id": main["user_id"], "machine_id": main["machine_id"],
                 "device_ids_copied_from": str(formal_state_path), "sets": {}, "set_roots": {},
                 "set_remote_flags": {}, "swap": {"versions": list(VERSIONS),
                                                  "note": "codes: the two probe folders (kept transcripts, outage "
                                                          "probes), sets wN: one worker folder per version"}}
    if state["config_root"] != str(root):
        raise SwapError(f"the table says root {state['config_root']}, the settings say {root}")
    if (state["user_id"], state["machine_id"]) != (main["user_id"], main["machine_id"]):
        raise SwapError("this group's table holds other device IDs than the main table")
    have = worker_sets(state)
    prefix = state["prefix"]
    taken = {c[len(prefix):] for c in [*state["codes"].values(), *[x for t in state["sets"].values() for x in t.values()]]}
    banned = {v.rsplit(".", 1)[-1][-2:] for v in VERSIONS}
    pool = [f"{n:02d}" for n in range(10, 100) if f"{n:02d}" not in taken and f"{n:02d}" not in banned]
    rng = random.Random(f"{state['code_seed']}|{len(have)}|{sets}")
    need_probe = [v for v in VERSIONS if v not in state["codes"]]
    new_sets = max(0, sets - len(have))
    need = len(need_probe) + len(VERSIONS) * new_sets
    if need > len(pool):
        raise SwapError(f"only {len(pool)} free codes left, {need} needed")
    picked = rng.sample(pool, need)
    for v in need_probe:
        state["codes"][v] = prefix + picked.pop()
    for k in range(len(have) + 1, len(have) + new_sets + 1):
        name = f"w{k}"
        state["sets"][name] = {v: prefix + picked.pop() for v in VERSIONS}
        state["set_roots"][name] = str(root)
        state["set_remote_flags"][name] = "off"
    paths = [str(d) for _, _, d in configdirs.all_folders(state)]
    want_len = len(str(main_root / (prefix + "00")))
    if len(set(paths)) != len(paths) or {len(p) for p in paths} != {want_len}:
        raise SwapError("folder paths are not unique or not all as long as the main folders' paths")
    configdirs.save_state(s.config_dirs_file, state)
    if not root.is_dir():
        root.mkdir(parents=True)
        os.chmod(root, 0o700)
    for folder in (s.experiment_root, s.home_dir):
        folder.mkdir(parents=True, exist_ok=True)
    rows = []
    for set_name, v, d in configdirs.all_folders(state):
        rows.append({"set": set_name or "(probe folder)", "version": v, "folder": str(d),
                     **configdirs._prepare_folder(d, state)})
    rep = {"time": utc_now(), "created_table": created, "root": str(root), "sets": len(worker_sets(state)),
           "probe_folders": {v: str(configdirs.config_dir(state, v)) for v in VERSIONS}, "folders": rows,
           "problems": [r for r in rows if r["problems"]]}
    write_json(env.data / "建配置文件夹_报告.json", rep)
    return rep


# ---------------------------------------------------------------------------------------------- plans

def fingerprint_of(ccv: dict, texts: dict, structure: str) -> dict:
    """ccversions' own fingerprint of this group's settings and folder table, with this file, the three
    texts and the structure added: a change in any of them makes the plans made before refused (H6)."""
    parts = {**ccv["parts"], "ccversions_fingerprint": ccv["fingerprint"], "对调两句话组/swap.py": program_sha256(),
             **{f"text_{k}": v for k, v in texts_sha(texts).items()}, "structure": structure}
    return {"fingerprint": hashlib.sha256(json.dumps(parts, sort_keys=True).encode()).hexdigest()[:16], "parts": parts}


def make_context(env: Env, plan: dict, texts: dict) -> run.Context:
    ctx = run.load_context(env.settings, plan)
    ctx.fingerprint = fingerprint_of(ctx.fingerprint, texts, env.structure)
    return ctx


def current_fingerprint(env: Env, texts: dict) -> dict:
    return make_context(env, {}, texts).fingerprint


def spec_doc(groups) -> dict:
    return {"format": plan_mod.ARMS_SPEC_FORMAT, "name": "swap-20261114",
            "note": "Two programs, 2.1.316 and 2.1.317, each asking every item once per pass and way the way group "
                    "main does (mode stock_blocked, effort high, remote settings off). sw_o and sw_w add "
                    "--system-prompt <the whole prompt>, holding 2.1.316's or 2.1.317's two sentences, its "
                    "{CONFIG_DIR} filled with the 2.1.316 worker folder of the ask's set (swap.py).",
            "groups": [{"group": g, "versions": list(VERSIONS), "mode": "stock_blocked", "effort": EFFORT,
                        "remote_flags": "off", "repeats": {"swap": 1}, "note": LABELS[g]} for g in groups]}


def assign_sets(plan: dict, set_names: list, seed: str) -> dict:
    """Write into every ask of a pass plan which set of worker folders it goes to, and that its whole prompt
    is filled with that set's 2.1.316 worker folder (fill_set). Every item takes one set for the whole pass.
    With as many sets as items in a block (three), the items of each block, in the order of their ids, take
    the sets in an order random.Random('<seed>|pass<n>|sets|block<b>') shuffles, so the three items of a block
    are in three sets. With another number of sets, the items of the pass, block by block and within a block
    in an order random.Random('<seed>|pass<n>|sets|block<b>') shuffles, take the sets in turn in an order
    random.Random('<seed>|pass<n>|sets') shuffles."""
    number = plan["spec"]["pass_number"]
    blocks: dict = {}
    for a in plan["asks"]:
        blocks.setdefault(a["block"], set()).add(a["unit"])
    names = list(set_names)
    if not names:
        raise SwapError("no set of worker folders to assign")
    each = len(names) == plan["spec"]["block_units"]
    turn = list(names)
    random.Random(f"{seed}|pass{number}|sets").shuffle(turn)
    set_of, k = {}, 0
    for b in sorted(blocks):
        units = sorted(blocks[b])
        if each:
            order = list(names)
            random.Random(f"{seed}|pass{number}|sets|block{b}").shuffle(order)
            set_of.update({u: order[i] for i, u in enumerate(units)})
        else:
            random.Random(f"{seed}|pass{number}|sets|block{b}").shuffle(units)
            for u in units:
                set_of[u] = turn[k % len(turn)]
                k += 1
    for a in plan["asks"]:
        a["options"]["config_set"] = set_of[a["unit"]]
        a["fill_set"] = set_of[a["unit"]]
    return {"how": ("per block, the items in the order of their ids take the sets in the order "
                    "random.Random('<seed>|pass<n>|sets|block<b>') shuffles" if each else
                    "the items, block by block in the order random.Random('<seed>|pass<n>|sets|block<b>') shuffles, "
                    "take the sets in turn in the order random.Random('<seed>|pass<n>|sets') shuffles"),
            "sets": names, "set_of_item": dict(sorted(set_of.items())),
            "fill": "every ask of sw_o and sw_w fills {CONFIG_DIR} with the 2.1.316 worker folder of its set"}


def build_pass_plan(env: Env, inputs, state: dict, *, name: str, number: int, units: list, fingerprint: dict,
                    texts: dict, items_info: dict, sets: list | None = None) -> dict:
    set_names = list(sets) if sets is not None else sets_in_use(env, state)
    p = plan_mod.make_arms(spec_doc(env.scored_groups), name=name, round_name="swap", pass_number=number,
                           units=units, block_units=BLOCK_UNITS, seed=env.seed, inputs=inputs,
                           fingerprint=fingerprint, all_versions=_versions(env),
                           known_sets=set(state.get("sets") or {}),
                           set_bindings={n: configdirs.set_remote_flags(state, n) for n in (state.get("sets") or {})},
                           parallel=1, stop_at_weekly_utilization=env.weekly_line, fail_streak_stop=FAIL_STREAK)
    p["spec"]["parallel"] = env.parallel  # the number of asks at once, which each record holds
    for a in p["asks"]:
        a["label"] = LABELS[a["group"]]
    how = assign_sets(p, set_names, env.seed)
    p["swap"] = {"structure": env.structure, "texts_sha256": texts_sha(texts), "program_sha256": program_sha256(),
                 "item_list": items_info, "set_assignment": how, "groups": {g: LABELS[g] for g in env.scored_groups},
                 "scored_groups": list(env.scored_groups), "fill": "set",
                 "system_prompt_flag": {g: ("--system-prompt" if g in DYNAMIC_OF else None) for g in env.scored_groups}}
    return p


def _load_plan_fixing_line(env: Env, path: Path) -> dict:
    p = plan_mod.load(path)
    if p["spec"].get("stop_at_weekly_utilization") != env.weekly_line:  # the line may change, nothing else
        p["spec"]["stop_at_weekly_utilization"] = env.weekly_line
        plan_mod.save(p, path)
        log(env, "line_changed", plan=p["name"], line=env.weekly_line)
    return p


def pass_plan(env: Env, number: int, texts: dict) -> dict:
    name = f"SW{number}"
    path = env.plans / f"{name}.json"
    if path.exists():
        return _load_plan_fixing_line(env, path)
    units, info = item_units(env)
    p = build_pass_plan(env, env.inputs(), load_state(env), name=name, number=number, units=units,
                        fingerprint=current_fingerprint(env, texts), texts=texts, items_info=info)
    plan_mod.save(p, path)
    log(env, "plan_made", plan=name, asks=len(p["asks"]))
    return p


def trial_plan(env: Env, n_items: int, texts: dict) -> dict:
    path = env.plans / "SWS.json"
    if path.exists():
        p = _load_plan_fixing_line(env, path)
        if len(p["spec"]["units"]) != n_items:
            print(f"note: the small batch plan already exists with {len(p['spec']['units'])} items, and it is used")
        return p
    units, info = item_units(env)
    if not 1 <= n_items <= len(units):
        raise SwapError(f"--trial takes 1 to {len(units)} items")
    picked = set(random.Random(f"{env.seed}|trial").sample(units, n_items))
    p = build_pass_plan(env, env.inputs(), load_state(env), name="SWS", number=1,
                        units=[u for u in units if u in picked], fingerprint=current_fingerprint(env, texts),
                        texts=texts, items_info=info)
    p["spec"]["purpose"] = "small batch to look at the records before the passes, not counted"
    plan_mod.save(p, path)
    log(env, "plan_made", plan="SWS", asks=len(p["asks"]))
    return p


def resend_plan(env: Env, number: int, texts: dict) -> dict | None:
    """The asks of a complete pass that never reached the model, asked once more (formal.py)."""
    name = f"SW{number}r"
    path = env.plans / f"{name}.json"
    if path.exists():
        return _load_plan_fixing_line(env, path)
    st = read_state(env)
    if st.get(f"resend{number}_none"):
        return None
    original = plan_mod.load(env.plans / f"SW{number}.json")
    ids = [r["ask_id"] for r in grade.load_records(env.run_dir(original["name"])) if extract.never_reached_model(r)]
    if not ids:
        st[f"resend{number}_none"] = True
        write_json(env.state_file, st)
        log(env, "resend_nothing", pass_=number)
        return None
    p = plan_mod.make_resend(original, ids, name=name, fingerprint=current_fingerprint(env, texts))
    p["spec"]["stop_at_weekly_utilization"] = env.weekly_line
    p["swap"] = original.get("swap")
    plan_mod.save(p, path)
    log(env, "resend_plan_made", plan=name, asks=len(ids))
    return p


def explicit_plan(env: Env, name: str, rows: list, groups: list, structures: list, texts: dict, *,
                  effort: str = EFFORT, purpose: str, step: int | None = None, extra: dict | None = None,
                  fills: list | None = None) -> dict:
    """A probe plan: the rows in the order written, each ask's group and structure added, and for an ask
    whose whole prompt is filled with a set's 2.1.316 worker folder, that set (fill_set). An ask without
    one fills its own folder."""
    spec = {"format": plan_mod.PROBE_SPEC_FORMAT, "name": name, "effort": effort, "remote_flags": "off",
            "parallel": 1, "stop_at_weekly_utilization": env.weekly_line, "purpose": purpose, "blocks": [rows]}
    state = load_state(env)
    p = plan_mod.make_explicit(spec, inputs=env.inputs(), fingerprint=current_fingerprint(env, texts),
                               all_versions=_versions(env), known_sets=set(state.get("sets") or {}))
    fills = fills if fills is not None else [None] * len(p["asks"])
    if not len(groups) == len(structures) == len(fills) == len(p["asks"]):
        raise SwapError("internal: one group, one structure and one fill per ask expected")
    for a, g, s, f in zip(p["asks"], groups, structures, fills):
        a["group"] = g
        a["structure"] = s
        if f is not None:
            a["fill_set"] = f
    p["swap"] = {"step": step, "structure": env.structure, "texts_sha256": texts_sha(texts),
                 "program_sha256": program_sha256(), **(extra or {})}
    return p


def plan_complete(env: Env, plan: dict) -> bool:
    folder = env.run_dir(plan["name"]) / "asks"
    done = {x.stem for x in folder.glob("*.json")} if folder.is_dir() else set()
    return all(a["ask_id"] in done for a in plan["asks"])


# --------------------------------------------------------------------------------------------- runner

def structure_of(plan: dict, ask: dict) -> str | None:
    """The structure an ask is built with: its own (probe plans), else its plan's."""
    if "structure" in ask:
        return ask["structure"]
    return (plan.get("swap") or {}).get("structure")


def filled_path(state: dict, ask: dict, own: Path) -> Path:
    """The path {CONFIG_DIR} is replaced by: the 2.1.316 worker folder of the ask's fill_set, else the
    ask's own config folder."""
    fill = ask.get("fill_set")
    if fill is None:
        return Path(own)
    if fill not in (state.get("sets") or {}):
        raise SwapError(f"{ask['ask_id']}: fill_set {fill!r} is not a set of the folder table")
    return configdirs.config_dir(state, OLD, fill)


def prepare_ask(ctx: run.Context, ask: dict, texts: dict, structure: str | None, token: str | None):
    """One ask: main's own construction (run.prepare) in this group's folder the ask names. For sw_o and
    sw_w the pair --system-prompt <the whole prompt> added at the end of the argv, its {CONFIG_DIR} filled
    as filled_path says. Returns the prepared ask and what goes into the record's field "swap"."""
    p = run.prepare(ctx, ask, token=token)
    g = ask.get("group")
    info = {"group": g, "structure": structure, "whole_chars": None, "whole_sha256": None, "fill": None,
            "fill_set": None, "filled_config_dir": None}
    if g in DYNAMIC_OF:
        if structure is None:
            raise SwapError(f"{ask['ask_id']}: an ask of {g} needs a structure")
        path = filled_path(ctx.state, ask, p.config_dir)
        whole = whole_prompt(texts, g, structure, path)
        p.argv = add_system_prompt(p.argv, ctx.inputs.system_prompt, whole)
        info.update(whole_chars=len(whole), whole_sha256=sha256_text(whole), filled_config_dir=str(path),
                    fill="set" if ask.get("fill_set") else "own", fill_set=ask.get("fill_set"))
    elif g not in (None, "sw_n"):
        raise SwapError(f"{ask['ask_id']}: unknown group {g!r}")
    return p, info


def swap_field(info: dict, prep, texts: dict) -> dict | None:
    g = info["group"]
    if g not in GROUPS:
        return None
    cs = prep.options.get("config_set")
    return {"group": g, "way": LABELS[g], "sentences_of": SENTENCES_OF[g],
            "flag": "--system-prompt" if g in DYNAMIC_OF else None, "structure": info["structure"],
            "whole_chars": info["whole_chars"], "whole_sha256": info["whole_sha256"],
            "set": cs or "(probe folder)", "folder": folder_label(cs, prep.ask["version"]),
            "config_dir": str(prep.config_dir), "fill": info["fill"], "fill_set": info["fill_set"],
            "filled_config_dir": info["filled_config_dir"], "texts_sha256": texts_sha(texts)}


class SwapRunner(run.Runner):
    """ccversions' Runner with a dispatcher of its own: up to `parallel` asks at once, in the plan's order,
    never two at a time in one config folder (the folder each ask names: its set and version, or the probe
    folder of its version). A block may start before the one before it has finished. Everything about one
    ask is the Runner's own (execute, the record, the checks, the weekly line, the fail streak)."""

    def __init__(self, ctx, run_dir, *, texts: dict, parallel: int, ramp: bool = True, stop_after: int | None = None):
        super().__init__(ctx, run_dir)
        if parallel < 1:
            raise SwapError("at least one ask at a time")
        self.texts, self.parallel, self.ramp, self.stop_after = texts, parallel, ramp, stop_after
        ctx.plan["spec"]["parallel"] = parallel

    def folder_of(self, ask: dict) -> str:
        cs = plan_mod.effective_options(self.ctx.plan["spec"], ask)["config_set"]
        return str(configdirs.config_dir(self.ctx.state, ask["version"], cs))

    def build(self, ask: dict, token):
        return prepare_ask(self.ctx, ask, self.texts, structure_of(self.ctx.plan, ask), token)

    def check_builds(self, pending: list) -> None:
        """Every ask still to do is built once before anything is sent, so a plan this cannot be done for
        is refused whole before anything of it is sent."""
        for a in pending:
            self.build(a, None)

    def preflight_folders(self, pending: list) -> list[str]:
        """Before any ask of this call, for every config folder an ask still to do names: the binary is
        there, the folder carries the shared device IDs, the working folder is empty, and `--version` run
        with that folder's environment reports the version (checklist A13, A2, B2)."""
        problems, seen = [], set()
        for ask in pending:
            folder = self.folder_of(ask)
            if folder in seen:
                continue
            seen.add(folder)
            p, _ = self.build(ask, self.token)
            v, b, cdir = p.ask["version"], p.binary, p.config_dir
            if not b.is_file():
                problems.append(f"{b} is missing (I3)")
                continue
            if not cdir.is_dir():
                problems.append(f"{cdir} does not exist: run setup-dirs")
                continue
            problems += [f"{cdir}: {x}" for x in checks.device_id_problems(cdir, self.ctx.state["user_id"],
                                                                            self.ctx.state.get("machine_id"))]
            self.s.tmpdir.mkdir(parents=True, exist_ok=True)
            ws = checks.prepare_workdir(self.s.workdir)
            if ws:
                problems += ws
                continue
            watched = run.watched_folders(self.s, cdir)
            before = checks.watched_listings(watched)
            try:
                out = subprocess.run([str(b), "--version"], cwd=self.s.workdir, env=p.env, capture_output=True,
                                     text=True, timeout=120)
                text = (out.stdout + out.stderr).strip()
                ok = out.returncode == 0 and v in out.stdout
            except (OSError, subprocess.SubprocessError) as e:
                text, ok = f"error: {type(e).__name__}: {e}", False
            diffs = checks.watched_diffs(before, checks.watched_listings(watched))
            self.event("version_check", version=v, config_dir=str(cdir), ok=ok, output=text[:500], diffs=diffs)
            if not ok:
                problems.append(f"{cdir}: --version did not report {v} (B2): {text[:200]}")
        return [self.scrub(x) for x in problems]

    def run(self) -> dict:
        plan, s = self.ctx.plan, self.s
        done = self.done_ids()
        pending = sorted((a for a in plan["asks"] if a["ask_id"] not in done), key=lambda a: a["order"])
        self.check_builds(pending)
        self.run_dir.mkdir(parents=True, exist_ok=True)
        plan_copy = self.run_dir / "plan.json"
        if plan_copy.exists():
            if json.loads(plan_copy.read_text())["asks"] != plan["asks"]:
                raise run.RunError(f"{plan_copy} holds a different plan. A run folder belongs to one plan")
        else:
            plan_copy.write_text(json.dumps(plan, ensure_ascii=False, indent=1) + "\n")
        s.lock_dir.mkdir(parents=True, exist_ok=True)
        import fcntl
        runner_lock = open(s.lock_dir / "runner.lock", "w")
        try:
            fcntl.flock(runner_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as e:
            raise run.RunError("another runner of this group is working (runner.lock is held)") from e
        caffeinate = None
        self._install_stop_handlers()
        try:
            problems = self.preflight_call(needs_token=True)
            self.event("start", fingerprint=self.ctx.fingerprint, macos=checks.macos_version(),
                       terminal_install=checks.terminal_install_snapshot(s.terminal_versions_dir, s.terminal_claude_link),
                       login_method=s.login_method, problems=problems, parallel=self.parallel,
                       stop_at_weekly_utilization=plan["spec"].get("stop_at_weekly_utilization"))
            if problems:
                raise run.RunError("preflight failed: " + "; ".join(problems))
            self.token = run._read_token(s) if s.login_method == "token" else None
            if self.token is not None:
                self.event("token_read", looks_like_setup_token=self.token.startswith("sk-ant-oat"))
            caffeinate = subprocess.Popen(["caffeinate", "-i", "-m", "-w", str(os.getpid())])
            sent, planned, blocks = 0, False, 0
            if pending:
                problems = self.preflight_pass(sorted({a["version"] for a in pending}))
                if not problems:
                    problems = self.preflight_folders(pending)
                if problems:
                    self.stop("preflight: " + "; ".join(problems))
                else:
                    sent, planned, blocks = self._dispatch(pending)
            if self.stop_signal is not None:
                self.event("stop_signal", signal=self.stop_signal)
                self.stop(f"stopped by {self.stop_signal}: the asks already running were finished and recorded, "
                          "no new ask was started (D2)")
            end = {"sent": sent, "blocks_run": blocks, "stopped_between_blocks_as_asked": planned,
                   "aborted": self.abort.is_set(), "reasons": self.abort_reason,
                   "terminal_install": checks.terminal_install_snapshot(s.terminal_versions_dir, s.terminal_claude_link)}
            self.event("end", **end)
            return end
        finally:
            if caffeinate is not None:
                caffeinate.terminate()
                try:
                    caffeinate.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    caffeinate.kill()
            fcntl.flock(runner_lock, fcntl.LOCK_UN)
            runner_lock.close()
            self._restore_stop_handlers()

    def _dispatch(self, pending: list) -> tuple[int, bool, int]:
        busy: set = set()
        running = {}
        left_in_block: dict = {}
        for a in pending:
            left_in_block[a["block"]] = left_in_block.get(a["block"], 0) + 1
        started_blocks: set = set()
        sent = dispatched = 0
        answered = not self.ramp
        planned = False
        with ThreadPoolExecutor(max_workers=self.parallel) as pool:
            while pending or running:
                limit = self.parallel if answered else 1
                while len(running) < limit and pending and not self.stopping():
                    if self.stop_after is not None and dispatched >= self.stop_after:
                        planned = True
                        break
                    i = next((k for k, a in enumerate(pending) if self.folder_of(a) not in busy), None)
                    if i is None:
                        break
                    ask = pending.pop(i)
                    folder = self.folder_of(ask)
                    busy.add(folder)
                    if ask["block"] not in started_blocks:
                        started_blocks.add(ask["block"])
                        self.event("block_start", pass_=ask["pass"], block=ask["block"], asks=left_in_block[ask["block"]])
                    try:
                        prep, info = self.build(ask, self.token)
                    except Exception as e:  # noqa: BLE001 - never leave running asks unrecorded
                        busy.discard(folder)
                        self.stop(f"{ask['ask_id']}: could not build the ask: {type(e).__name__}: {e}")
                        break
                    self.event("ask_start", ask_id=ask["ask_id"], config_dir=folder, running=len(running))
                    running[pool.submit(self._safe_execute, prep)] = (ask, folder, prep, info, len(running))
                    dispatched += 1
                if not running:
                    break
                finished, _ = wait(running, return_when=FIRST_COMPLETED)
                for fut in finished:
                    ask, folder, prep, info, alongside = running.pop(fut)
                    busy.discard(folder)
                    rec = fut.result()
                    rec["swap"] = swap_field(info, prep, self.texts)
                    rec["asks_running_alongside_at_start"] = alongside
                    if rec["status"] == "refused":
                        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
                        run._atomic_write(self.run_dir / "refused" / f"{ask['ask_id']}-{stamp}.json",
                                          self.scrub(json.dumps(rec, ensure_ascii=False, indent=1) + "\n"))
                    else:
                        self.write_record(rec)
                    self.event("ask", ask_id=ask["ask_id"], status=rec["status"],
                               weekly_utilization=rec.get("weekly_utilization"),
                               five_hour_utilization=rec.get("five_hour_utilization"),
                               config_dir=folder, group=ask.get("group"))
                    self._check_weekly_line(rec)
                    self._check_fail_streak(rec)
                    sent += 1
                    if rec["status"] != "refused" and not extract.ask_failed(rec):
                        answered = True
                    left_in_block[ask["block"]] -= 1
                    if left_in_block[ask["block"]] == 0:
                        self.event("block_end", pass_=ask["pass"], block=ask["block"])
        return sent, planned, len(started_blocks)


# --------------------------------------------------------------------------------------------- driver

def read_state(env: Env) -> dict:
    return json.loads(env.state_file.read_text()) if env.state_file.exists() else {"log": []}


def log(env: Env, what: str, **data) -> None:
    st = read_state(env)
    st.setdefault("log", []).append({"time": utc_now(), "what": what, **data})
    write_json(env.state_file, st)
    print(json.dumps({"time": utc_now(), "what": what, **data}, ensure_ascii=False), flush=True)


def _vis(text: str) -> str:
    """text as macOS ps shows a command line when it does not print UTF-8 (vis(3): a byte of 128 or more as
    M- with the byte less 128, or M^ with a control character)."""
    out = []
    for b in text.encode("utf-8"):
        if b < 0x80:
            out.append(chr(b))
        else:
            c = b & 0x7F
            out.append("M-" + chr(c) if 0x20 <= c < 0x7F else "M^" + ("?" if c == 0x7F else chr(c + 0x40)))
    return "".join(out)


def other_sends(binary_template: str) -> list[str]:
    """Processes of other programs that are sending now (ps, no process is touched): a version binary of
    this experiment running with -p, or a runner of ccversions, dsp.py, nosent.py, swap.py, 再验少想's
    driver.py or 全部发.sh. This process and the ones above it are left out. ps is asked to print UTF-8, and a
    mark is also looked for as ps shows it otherwise."""
    prefix = binary_template.split("{", 1)[0]
    cut = next((i for i, ch in enumerate(prefix) if ord(ch) > 127), len(prefix))
    ascii_prefix = prefix[:cut]
    out = subprocess.run(["/bin/ps", "-axww", "-o", "pid=,ppid=,command="], capture_output=True, text=True,
                         errors="replace", env={**os.environ, "LC_ALL": "en_US.UTF-8"})
    rows = []
    for line in out.stdout.splitlines():
        parts = line.strip().split(None, 2)
        if len(parts) == 3 and parts[0].isdigit() and parts[1].isdigit():
            rows.append((int(parts[0]), int(parts[1]), parts[2]))
    parent = {pid: ppid for pid, ppid, _ in rows}
    mine, p = set(), os.getpid()
    while p and p not in mine:
        mine.add(p)
        p = parent.get(p, 0)
    marks = sorted({m for x in RUNNER_MARKS for m in (x, _vis(x))})
    hits = []
    for pid, _, cmd in rows:
        if pid in mine:
            continue
        binary = len(ascii_prefix) > 1 and ascii_prefix in cmd and "/claude -p " in cmd
        if binary or any(m in cmd for m in marks):
            hits.append(f"pid {pid}: {cmd[:160]}")
    return hits


def check_alone(env: Env, alongside: bool) -> None:
    if alongside:
        return
    finder = env.find_other_sends or other_sends
    hits = finder(env.settings.binary_template)
    if hits:
        raise SwapError("another program is sending now (every group shares the account, the working folder, HOME "
                        "and TMPDIR). Wait until it has ended, or add --alongside-other-sends. Seen: "
                        + " | ".join(hits[:4]))


def send_once(env: Env, plan: dict, texts: dict, *, parallel: int, ramp: bool = True, stop_after: int | None = None,
              alongside: bool = False) -> dict:
    if not env.settings.allow_send:
        raise SwapError("sending is switched off in the settings file (allow_send = false)")
    check_alone(env, alongside)
    ctx = make_context(env, plan, texts)
    return SwapRunner(ctx, env.run_dir(plan["name"]), texts=texts, parallel=parallel, ramp=ramp,
                      stop_after=stop_after).run()


def last_reading(env: Env, names: list | None = None) -> tuple[float | None, str | None]:
    """The latest weekly usage reading among the asks of this group (or of the named plans), by time."""
    best = (None, None)
    root = env.settings.raw_dir
    for d in sorted(root.iterdir()) if root.is_dir() else []:
        if names is not None and d.name not in names:
            continue
        f = d / "events.jsonl"
        for line in f.read_text().splitlines() if f.is_file() else []:
            try:
                e = json.loads(line)
            except ValueError:
                continue
            if e.get("event") == "ask" and e.get("weekly_utilization") is not None and (best[1] or "") <= e["time"]:
                best = (e["weekly_utilization"], e["time"])
    return best


def health_probe(env: Env, texts: dict, alongside: bool) -> bool:
    """One cheap ask in 2.1.317's probe folder: the author's probe sentence, mode author, effort low (formal.py)."""
    st = read_state(env)
    n = st.get("health_probes", 0) + 1
    st["health_probes"] = n
    write_json(env.state_file, st)
    try:
        plan = explicit_plan(env, f"SWH_{n:03d}", [{"version": HEALTH_VERSION, "mode": "author", "unit": PROBE_UNIT,
                                                    "label": "outage probe", "options": {"output_format": "stream-json"}}],
                             [None], [None], texts, effort="low", purpose="is the service answering again?")
        out = send_once(env, plan, texts, parallel=1, ramp=False, alongside=alongside)
    except (run.RunError, SwapError) as e:
        log(env, "health_probe_not_sent", error=str(e))
        return False
    recs = grade.load_records(env.run_dir(plan["name"]))
    ok = bool(recs) and not out["aborted"] and not extract.ask_failed(recs[0])
    log(env, "health_probe", n=n, ok=ok)
    return ok


def send_plan(env: Env, plan: dict, texts: dict, *, parallel: int, stop_after: int | None = None,
              alongside: bool = False) -> str:
    """Send a plan until it is complete or something stops it, as formal.Driver.send does. Returns
    "complete", "line", "usage_limit" or "paused", and raises SwapError for anything a person has to look at."""
    outage_started, attempt = None, 0
    while True:
        if plan_complete(env, plan):
            return "complete"
        out = send_once(env, plan, texts, parallel=parallel, stop_after=stop_after, alongside=alongside)
        reasons = " | ".join(out.get("reasons") or [])
        log(env, "send_ended", plan=plan["name"], sent=out["sent"], aborted=out["aborted"], reasons=reasons[:600])
        if not out["aborted"]:
            if out["stopped_between_blocks_as_asked"]:
                return "paused"
            if out["sent"] == 0 and not plan_complete(env, plan):
                raise SwapError(f"{plan['name']}: no ask could be started, and the plan is not complete")
            continue
        kinds = {("line" if "weekly usage reading" in r and "reached the plan's line" in r else
                  "usage_limit" if "usage limit reached" in r else
                  "fail_streak" if "fail streak" in r else "other") for r in (out.get("reasons") or [])}
        if "other" in kinds or not kinds:
            raise SwapError(f"{plan['name']}: stopped: {reasons[:800]}")
        if "usage_limit" in kinds:
            reading, _ = last_reading(env, [plan["name"]])
            if reading is None or reading < formal.USAGE_LIMIT_MIN_READING:
                raise SwapError(f"{plan['name']}: an ask came back with what reads like a usage-limit message while the "
                                f"last weekly reading of this plan is {reading}. Look at the last records. The same "
                                "command goes on with the asks not yet sent")
            return "usage_limit"
        if "line" in kinds:
            return "line"
        streak = (plan.get("spec") or {}).get("fail_streak_stop") or FAIL_STREAK
        if out["sent"] > 2 * streak:
            outage_started, attempt = None, 0
        outage_started = outage_started or time.monotonic()
        while True:
            waited_h = (time.monotonic() - outage_started) / 3600
            if waited_h > MAX_OUTAGE_HOURS:
                raise SwapError(f"{plan['name']}: asks kept failing for {waited_h:.1f} hours, and gave up")
            minutes = formal.WAITS_MINUTES[min(attempt, len(formal.WAITS_MINUTES) - 1)]
            attempt += 1
            log(env, "outage_wait", plan=plan["name"], minutes=minutes)
            env.sleep(minutes * 60)
            if health_probe(env, texts, alongside):
                break


def guards(env: Env, args, *, send: bool) -> tuple[dict, dict]:
    """What has to hold before anything is sent. Returns (texts, config folder table)."""
    if not env.settings.allow_send:
        raise SwapError(f"sending is switched off: {env.settings.source} says allow_send = false")
    check_alone(env, args.alongside_other_sends)
    texts = load_texts(env)
    state = load_state(env)
    if state is None or not all(v in (state.get("codes") or {}) for v in VERSIONS):
        raise SwapError("this group has no config folders yet: run setup-dirs")
    sets = sets_in_use(env, state)
    reading, when = last_reading(env)
    if reading is not None and reading >= env.weekly_line and not args.after_reset:
        raise SwapError(f"the last weekly reading of this group, {reading} at {when}, is at or above the line "
                        f"{env.weekly_line}. After the weekly reset, run the same command with --after-reset")
    if send:
        item_units(env)
        st = probe_status(env, texts, state, sets)
        if not st["steps_1_and_2_ok"]:
            raise SwapError(f"the probes have not passed for the three texts as they are now, this program and the "
                            f"structure {env.structure} ({st['why']}): run probes first")
        if st["sets_missing"]:
            raise SwapError(f"sets without step 3 passed (the whole prompts filled with the set's path): "
                            f"{st['sets_missing']}: run probes")
        if st["folders_missing"]:
            raise SwapError(f"worker folders without their two warm-up probes passed (step 4): "
                            f"{st['folders_missing']}: run probes")
    return texts, state


# --------------------------------------------------------------------------------------- probe checks

def first_request_usage(rec: dict) -> dict:
    """The cache reads and cache writes of the ask's first request (the usage of the first top-level
    assistant message of stream-json, as extract.first_request_input_tokens takes it)."""
    usage = None
    if extract.record_format(rec) == "stream-json":
        first = next((e for e in extract._stream_events(rec.get("stdout") or "") if e.get("type") == "assistant"
                      and e.get("parent_tool_use_id") in (None, "")), None)
        usage = ((first or {}).get("message") or {}).get("usage")
    usage = usage or {}
    return {"cache_read_input_tokens": usage.get("cache_read_input_tokens"),
            "cache_creation_input_tokens": usage.get("cache_creation_input_tokens")}


def request_view(rec: dict, run_dir: Path) -> dict:
    """What one probe sent in its first request, as the transcript and the record tell
    (transcripts.extract_ask). A probe without a transcript gives its tokens and answer only."""
    row = transcripts.extract_ask(rec, run_dir)
    argv = rec.get("argv") or []
    i = argv.index("--system-prompt") if "--system-prompt" in argv else None
    sw = rec.get("swap") or {}
    return {"ask_id": rec["ask_id"], "group": rec.get("group"), "version": rec.get("version"),
            "structure": sw.get("structure"), "config_dir": rec.get("config_dir"), "status": rec.get("status"),
            "fill_set": sw.get("fill_set"), "filled_config_dir": sw.get("filled_config_dir"),
            "answered": not extract.ask_failed(rec),
            "seen": bool(row.get("has_request_lines") and row.get("shape_found")),
            "tokens": extract.first_request_input_tokens(rec), **first_request_usage(rec), "system": row.get("system"),
            "model_sent": row.get("sent_model"), "effort_sent": row.get("effort_sent"),
            "system_prompt_value": argv[i + 1] if i is not None and i + 1 < len(argv) else None,
            "others": {"tools": row.get("tools"), "betas": row.get("betas"), "thinking": row.get("thinking"),
                       "output_config": row.get("output_config"), "max_tokens": row.get("max_tokens"),
                       "context_management": row.get("context_management"), "other_params": row.get("other_params"),
                       "model": row.get("sent_model"), "extra_message_efforts": row.get("blob_efforts"),
                       "user_message": row.get("user_message"),
                       "extra_messages": [{"role": b.get("role"), "texts": b.get("texts")}
                                          for b in row.get("blobs") or []]}}


def _masked(value) -> str:
    """A value as compared between two probes: the date and anything shaped like a UUID blanked
    (transcripts.mask, checklist C15)."""
    return transcripts.mask(json.dumps(value, sort_keys=True, ensure_ascii=False))


def usable(v: dict | None) -> bool:
    return v is not None and v["answered"] and v["seen"] and isinstance(v["tokens"], int)


def others_differ(a: dict, b: dict) -> list:
    return [k for k in OTHER_PARTS if _masked(a["others"][k]) != _masked(b["others"][k])]


def system_same(a: dict, b: dict) -> bool:
    return a["system"] is not None and b["system"] is not None and _masked(a["system"]) == _masked(b["system"])


def first_block_same(a: dict, b: dict) -> bool:
    return bool(a["system"]) and bool(b["system"]) and a["system"][0] == b["system"][0]


def model_effort_ok(v: dict | None) -> bool:
    return usable(v) and v["model_sent"] == modes_mod.MODEL and v["effort_sent"] == EFFORT


def brief(v: dict) -> dict:
    return {"ask_id": v["ask_id"], "group": v["group"], "version": v["version"], "structure": v["structure"],
            "status": v["status"], "answered": v["answered"], "transcript_seen": v["seen"],
            "first_request_input_tokens": v["tokens"], "cache_read_input_tokens": v["cache_read_input_tokens"],
            "cache_creation_input_tokens": v["cache_creation_input_tokens"],
            "system_blocks": len(v["system"]) if v["system"] is not None else None,
            "system_block_chars": [len(x) for x in v["system"] or []],
            "model_sent": v["model_sent"], "effort_sent": v["effort_sent"], "config_dir": v["config_dir"],
            "filled_config_dir": v["filled_config_dir"]}


def _same_pair(a: dict, b: dict) -> dict:
    out = {"both_usable": usable(a) and usable(b), "first_request_input_tokens": [a["tokens"], b["tokens"]],
           "tokens_same": a["tokens"] == b["tokens"], "system_same": system_same(a, b),
           "others_differ_in": others_differ(a, b)}
    out["ok"] = out["both_usable"] and out["tokens_same"] and out["system_same"] and not out["others_differ_in"]
    return out


def whole_prompt_check(v: dict, texts: dict, structure: str, path, author: str) -> dict:
    """Check 4 of step 2 for one probe of sw_o or sw_w whose {CONFIG_DIR} should hold `path`: the value
    after --system-prompt is the program's own whole prompt, the system blocks after the first, put back
    together by the structure, equal it with two newlines and the author's text, and they are cut as
    expected_blocks says."""
    want = whole_prompt(texts, v["group"], structure, path)
    blocks = list((v["system"] or [])[1:])
    got = rebuild(blocks, structure)
    r = {"filled_config_dir": str(path), "argv_value_is_the_programs_whole_prompt": v["system_prompt_value"] == want,
         "rebuilt_equals_whole_prompt_two_newlines_author": got == want + "\n\n" + author,
         "blocks_as_expected": blocks == expected_blocks(want, author),
         "blocks_after_the_first": len(blocks), "block_chars": [len(x) for x in blocks],
         "expected_block_chars": [len(x) for x in expected_blocks(want, author)]}
    if not r["rebuilt_equals_whole_prompt_two_newlines_author"]:
        r["first_difference"] = first_difference(got, want + "\n\n" + author)
    r["ok"] = (r["argv_value_is_the_programs_whole_prompt"] and r["rebuilt_equals_whole_prompt_two_newlines_author"]
               and r["blocks_as_expected"])
    return r


def judge_step1(views: list) -> dict:
    """Step 1 from its probes in plan order: the two sw_n agree, and for each structure, whether it passed.
    The structure taken is the first that passed in PREFERENCE."""
    out = {"ok": False, "decided": None, "asks": [brief(v) for v in views if v is not None]}
    n = [v for v in views if v is not None and v["group"] == "sw_n"]
    o = {v["structure"]: v for v in views if v is not None and v["group"] == "sw_o"}
    if any(v is None for v in views) or len(n) != 2 or sorted(o) != sorted(STRUCTURES):
        out["why"] = "the plan does not hold two sw_n probes and one sw_o probe per structure, all recorded"
        return out
    base = n[0]
    out["sw_n_twice"] = _same_pair(n[0], n[1])
    out["sw_n"] = brief(base)
    rows = {}
    for s in STRUCTURES:
        v = o[s]
        r = {"ask_id": v["ask_id"], "answered": v["answered"], "transcript_seen": v["seen"],
             "first_request_input_tokens": v["tokens"],
             "minus_sw_n": v["tokens"] - base["tokens"] if None not in (v["tokens"], base["tokens"]) else None,
             "tokens_same": v["tokens"] == base["tokens"], "first_block_same": first_block_same(v, base),
             "others_differ_in": others_differ(v, base),
             "system_blocks": len(v["system"]) if v["system"] is not None else None,
             "system_block_chars": [len(x) for x in v["system"] or []],
             "sw_n_system_blocks": len(base["system"]) if base["system"] is not None else None,
             "sw_n_system_block_chars": [len(x) for x in base["system"] or []],
             "cache_read_input_tokens": v["cache_read_input_tokens"],
             "cache_creation_input_tokens": v["cache_creation_input_tokens"]}
        r["ok"] = usable(v) and r["tokens_same"] and r["first_block_same"] and not r["others_differ_in"]
        rows[s] = r
    out["structures"] = rows
    out["passed"] = [s for s in PREFERENCE if rows[s]["ok"]]
    if not out["sw_n_twice"]["ok"]:
        out["why"] = f"the two sw_n probes do not agree: {out['sw_n_twice']}"
        return out
    if not out["passed"]:
        out["why"] = "no structure passed: " + " | ".join(
            f"{s}: tokens {r['minus_sw_n']:+d} against sw_n" if isinstance(r["minus_sw_n"], int) else f"{s}: no tokens"
            for s, r in rows.items()) + " (each structure's first block and other parts are in 'structures')"
        return out
    out["decided"] = out["passed"][0]
    out["ok"] = True
    return out


def judge_step2(step1: list, step2: list, structure: str, texts: dict, author: str) -> dict:
    """Step 2 from step 1's probes (2.1.316's two sw_n and its sw_o of the structure) and step 2's own."""
    out = {"ok": False, "structure": structure, "asks": [brief(v) for v in step2 if v is not None]}
    old_n = [v for v in step1 if v is not None and v["group"] == "sw_n"]
    old_o = [v for v in step1 if v is not None and v["group"] == "sw_o" and v["structure"] == structure]
    old_w = [v for v in step2 if v is not None and v["version"] == OLD]
    new = [v for v in step2 if v is not None and v["version"] == NEW]
    if (any(v is None for v in step2) or len(old_n) != 2 or len(old_o) != 1 or [v["group"] for v in old_w] != ["sw_w"]
            or [v["group"] for v in new] != ["sw_n", "sw_o", "sw_w", "sw_n"]):
        out["why"] = "the probes are not the ones step 2 needs, all recorded"
        return out
    old_o, old_w = old_o[0], old_w[0]
    n1, no, nw, n2 = new
    every = [*old_n, old_o, old_w, *new]
    c1 = {v["ask_id"]: {"version": v["version"], "group": v["group"], "answered": v["answered"],
                        "transcript_seen": v["seen"], "model_sent": v["model_sent"], "effort_sent": v["effort_sent"],
                        "ok": model_effort_ok(v)}
          for v in every}
    c2 = _same_pair(n1, n2)
    base = {OLD: old_n[0], NEW: n1}
    c3, c4, c5 = {}, {}, {}
    for v in (old_o, old_w, no, nw):
        key = f"{v['version']} {v['group']}"
        b = base[v["version"]]
        c3[key] = first_block_same(v, b)
        c4[key] = whole_prompt_check(v, texts, structure, v["config_dir"], author)
        c5[key] = others_differ(v, b)
    t = {k: v["tokens"] for k, v in (("old_sw_n", old_n[0]), ("old_sw_o", old_o), ("old_sw_w", old_w),
                                     ("new_sw_n", n1), ("new_sw_o", no), ("new_sw_w", nw))}
    have = None not in t.values()
    c6 = {"first_request_input_tokens": t,
          "old_sw_o_equals_sw_n": have and t["old_sw_o"] == t["old_sw_n"],
          "new_sw_w_equals_sw_n": have and t["new_sw_w"] == t["new_sw_n"],
          "sw_w_minus_sw_o": {OLD: t["old_sw_w"] - t["old_sw_o"] if have else None,
                              NEW: t["new_sw_w"] - t["new_sw_o"] if have else None}}
    c6["same_difference_in_both_folders"] = have and c6["sw_w_minus_sw_o"][OLD] == c6["sw_w_minus_sw_o"][NEW]
    c6["ok"] = c6["old_sw_o_equals_sw_n"] and c6["new_sw_w_equals_sw_n"] and c6["same_difference_in_both_folders"]
    checks_ = {"1_answered_model_effort": all(x["ok"] for x in c1.values()), "2_new_sw_n_agree": c2["ok"],
               "3_first_block": all(c3.values()), "4_whole_prompt_sent": all(x["ok"] for x in c4.values()),
               "5_other_parts": not any(c5.values()), "6_input_tokens": c6["ok"]}
    out.update({"checks": checks_, "1": c1, "2": c2, "3": c3, "4": c4, "5": c5, "6": c6})
    out["ok"] = all(checks_.values())
    if not out["ok"]:
        out["why"] = "failed: " + ", ".join(k for k, x in checks_.items() if not x)
    return out


def judge_step3(step2: list, pairs: list, structure: str, texts: dict, author: str, state: dict) -> dict:
    """Step 3 from step 2's probes and step 3's own (ask, view) pairs in plan order. Per set: sw_o then
    sw_w in 2.1.317's probe folder, {CONFIG_DIR} filled with the set's 2.1.316 worker folder. Each probe
    passes checks 1, 3, 4 and 5 of step 2, against step 2's first sw_n in 2.1.317's probe folder. A set
    whose probes are not all recorded is marked incomplete."""
    new2 = [v for v in step2 if v is not None and v["version"] == NEW]
    if any(v is None for v in step2) or [v["group"] for v in new2] != ["sw_n", "sw_o", "sw_w", "sw_n"]:
        return {"ok": False, "why": "step 2's probes are not all recorded", "sets": {}}
    base = new2[0]
    by: dict = {}
    for a, v in pairs:
        by.setdefault(a.get("fill_set"), []).append((a, v))
    sets = {}
    for name, got in by.items():
        r = {"set": name, "ok": False, "compared_with": base["ask_id"], "probes": {}}
        if name is None or [a["group"] for a, _ in got] != ["sw_o", "sw_w"] or any(a["version"] != NEW for a, _ in got):
            r["why"] = "not one sw_o and one sw_w of 2.1.317 for this set"
            sets[str(name)] = r
            continue
        if any(v is None for _, v in got):
            r["incomplete"] = True
            r["why"] = "not all recorded"
            sets[name] = r
            continue
        path = configdirs.config_dir(state, OLD, name)
        r["filled_config_dir"] = str(path)
        for a, v in got:
            c4 = whole_prompt_check(v, texts, structure, path, author)
            c4["record_says_filled_with"] = v["filled_config_dir"]
            c4["ok"] = c4["ok"] and v["filled_config_dir"] == str(path)
            c5 = others_differ(v, base)
            checks_ = {"1_answered_model_effort": model_effort_ok(v), "3_first_block": first_block_same(v, base),
                       "4_whole_prompt_sent": c4["ok"], "5_other_parts": not c5}
            r["probes"][a["group"]] = {**brief(v), "checks": checks_, "4": c4, "others_differ_in": c5,
                                       "ok": all(checks_.values())}
        r["first_request_input_tokens"] = t = {g: x["first_request_input_tokens"] for g, x in r["probes"].items()}
        # for the check file only (the step's checks do not use it): sw_w minus sw_o here and in step 2 in this folder
        r["sw_w_minus_sw_o"] = t["sw_w"] - t["sw_o"] if None not in t.values() else None
        r["step2_sw_w_minus_sw_o"] = (new2[2]["tokens"] - new2[1]["tokens"]
                                      if None not in (new2[1]["tokens"], new2[2]["tokens"]) else None)
        r["ok"] = all(x["ok"] for x in r["probes"].values())
        if not r["ok"]:
            r["why"] = "failed: " + ", ".join(f"{g} {c}" for g, x in r["probes"].items()
                                              for c, ok in x["checks"].items() if not ok)
        sets[name] = r
    return {"ok": bool(sets) and all(x["ok"] for x in sets.values()), "sets": sets}


def judge_step4(pairs: list, step3: dict) -> dict:
    """One worker folder's warm-up probes (ask, record) in plan order: sw_n, then the version's own way. Both
    must answer. In a 2.1.316 folder the two first-request input tokens are equal. In a 2.1.317 folder
    sw_w's equals the sw_w of step 3 for the same set (step3: set name -> step 3's result for it)."""
    a0 = pairs[0][0]
    version, set_name = a0["version"], (a0.get("options") or {}).get("config_set")
    groups = [a["group"] for a, _ in pairs]
    tok = [extract.first_request_input_tokens(r) for _, r in pairs]
    answered = [not extract.ask_failed(r) for _, r in pairs]
    out = {"version": version, "set": set_name, "groups": groups, "answered": answered,
           "first_request_input_tokens": tok, "config_dir": pairs[0][1].get("config_dir"),
           "filled_config_dir": ((pairs[-1][1].get("swap") or {}).get("filled_config_dir"))}
    ok = groups == ["sw_n", OWN_GROUP[version]] and all(answered) and None not in tok
    if version == OLD:
        ok = ok and tok[0] == tok[1]
    else:
        s3 = (step3.get(set_name) or {})
        want = (s3.get("first_request_input_tokens") or {}).get("sw_w") if s3.get("ok") else None
        out["step3_sw_w_tokens"] = want
        ok = ok and want is not None and tok[-1] == want
    out["ok"] = bool(ok)
    return out


def _step_plans(env: Env, step: int) -> list[dict]:
    out = [plan_mod.load(p) for p in sorted(env.plans.glob(f"SWP{step}_*.json"))] if env.plans.is_dir() else []
    return sorted(out, key=lambda p: int(p["name"].rsplit("_", 1)[1]))


def _matches(plan: dict, texts: dict, *, structure: str | None = None, **links) -> bool:
    sw = plan.get("swap") or {}
    return (sw.get("texts_sha256") == texts_sha(texts) and sw.get("program_sha256") == program_sha256()
            and (structure is None or sw.get("structure") == structure)
            and all(sw.get(k) == v for k, v in links.items()))


def _records(env: Env, plan: dict) -> dict:
    rd = env.run_dir(plan["name"])
    return {r["ask_id"]: r for r in grade.load_records(rd)} if (rd / "asks").is_dir() else {}


def views_of(env: Env, plan: dict) -> list:
    rd = env.run_dir(plan["name"])
    recs = _records(env, plan)
    return [request_view(recs[a["ask_id"]], rd) if a["ask_id"] in recs else None
            for a in sorted(plan["asks"], key=lambda a: a["order"])]


def _pending(env: Env, plans: list, fp: str) -> dict | None:
    """The latest of the plans when it is not complete and was made with the fingerprint as it is now."""
    if plans and not plan_complete(env, plans[-1]) and (plans[-1].get("fingerprint") or {}).get("fingerprint") == fp:
        return plans[-1]
    return None


@dataclass
class StepState:
    result: dict | None  # the latest passing result, else the latest complete one
    plan: dict | None  # the plan of that result
    pending: dict | None  # the latest matching plan that is not complete and can still be sent


def step_state(env: Env, step: int, texts: dict, judge, fp: str, **match) -> StepState:
    plans = [p for p in _step_plans(env, step) if _matches(p, texts, **match)]
    good = last = None
    for p in plans:
        if not plan_complete(env, p):
            continue
        r = judge(p)
        r["plan"] = p["name"]
        last = (r, p)
        if r["ok"]:
            good = (r, p)
    pick = good or last or (None, None)
    return StepState(pick[0], pick[1], _pending(env, plans, fp) if good is None else None)


def step1_state(env: Env, texts: dict, fp: str) -> StepState:
    return step_state(env, 1, texts, lambda p: judge_step1(views_of(env, p)), fp)


def step2_state(env: Env, texts: dict, fp: str, s1: StepState) -> StepState:
    author = env.inputs().system_prompt
    s1_views = views_of(env, s1.plan)
    return step_state(env, 2, texts, lambda p: judge_step2(s1_views, views_of(env, p), env.structure, texts, author),
                      fp, structure=env.structure, step1_plan=s1.plan["name"])


def step3_results(env: Env, texts: dict, s2: StepState, state: dict) -> tuple[dict, list]:
    """For each set that has step 3 probes made with the texts, this program, the structure and the step 2
    plan as they are now: its result. A passing result is never replaced, and a failing one is replaced by
    a later one. Also returns the matching plans."""
    by: dict = {}
    author = env.inputs().system_prompt
    s2_views = views_of(env, s2.plan)
    plans = [p for p in _step_plans(env, 3) if _matches(p, texts, structure=env.structure, step2_plan=s2.plan["name"])]
    for p in plans:
        asks = sorted(p["asks"], key=lambda a: a["order"])
        r = judge_step3(s2_views, list(zip(asks, views_of(env, p))), env.structure, texts, author, state)
        for name, row in r["sets"].items():
            if row.get("incomplete"):
                continue
            row["plan"] = p["name"]
            if name not in by or not by[name]["ok"]:
                by[name] = row
    return by, plans


def step4_results(env: Env, texts: dict, step3: dict) -> tuple[dict, list]:
    """For each worker folder that has warm-up probes made with the texts, this program and the structure
    as they are now: its result, judged against step 3. A passing result is never replaced, and a failing
    one is replaced by a later one. Also returns the matching plans."""
    by: dict = {}
    plans = [p for p in _step_plans(env, 4) if _matches(p, texts, structure=env.structure)]
    for p in plans:
        recs = _records(env, p)
        pairs: dict = {}
        for a in sorted(p["asks"], key=lambda a: a["order"]):
            pairs.setdefault(folder_label(a["options"].get("config_set"), a["version"]), []).append((a, recs.get(a["ask_id"])))
        for key, got in pairs.items():
            if any(r is None for _, r in got):
                continue
            row = {**judge_step4(got, step3), "plan": p["name"]}
            if key not in by or not by[key]["ok"]:
                by[key] = row
    return by, plans


def probe_status(env: Env, texts: dict, state: dict, sets: list) -> dict:
    fp = current_fingerprint(env, texts)["fingerprint"]
    s1 = step1_state(env, texts, fp)
    out = {"step1": s1.result, "step2": None, "steps_1_and_2_ok": False, "step3": {}, "step4": {}}
    why, s2 = None, None
    if not (s1.result and s1.result["ok"]):
        why = "step 1 has not passed"
    elif s1.result["decided"] != env.structure:
        why = f"step 1 took the structure {s1.result['decided']}, the settings name {env.structure}"
    else:
        s2 = step2_state(env, texts, fp, s1)
        out["step2"] = s2.result
        if not (s2.result and s2.result["ok"]):
            why = "step 2 has not passed with this structure"
    out["steps_1_and_2_ok"] = why is None
    out["why"] = why
    if why is None:
        out["step3"], _ = step3_results(env, texts, s2, state)
    out["sets_missing"] = [n for n in sets if not (out["step3"].get(n) or {}).get("ok")]
    out["step4"], _ = step4_results(env, texts, out["step3"])
    need = [folder_label(n, v) for n, v, _ in worker_folders(state, sets)]
    out["folders_missing"] = [f for f in need if not (out["step4"].get(f) or {}).get("ok")]
    out["all_ok"] = out["steps_1_and_2_ok"] and not out["sets_missing"] and not out["folders_missing"]
    return out


def write_check(env: Env, texts: dict, state: dict, sets: list) -> dict:
    st = probe_status(env, texts, state, sets)
    doc = {"format": CHECK_FORMAT, "time": utc_now(), "texts_sha256": texts_sha(texts),
           "program_sha256": program_sha256(), "structure_in_settings": env.structure,
           "fingerprint": current_fingerprint(env, texts)["fingerprint"], "sets_in_use": list(sets), **st}
    write_json(env.probe_check_file, doc)
    return doc


def _send_step(env: Env, plan: dict, texts: dict, parallel: int, args) -> str:
    plan_mod.save(plan, env.plans / f"{plan['name']}.json")
    return send_plan(env, plan, texts, parallel=parallel, alongside=args.alongside_other_sends)


def _next_name(env: Env, step: int) -> str:
    plans = _step_plans(env, step)
    return f"SWP{step}_{int(plans[-1]['name'].rsplit('_', 1)[1]) + 1 if plans else 1}"


def _probe_row(version: str, label: str, **kw) -> dict:
    return {"version": version, "mode": "stock_blocked", "unit": PROBE_UNIT, "options": {"keep_transcript": True},
            "label": label, **kw}


def step1_plan(env: Env, texts: dict) -> dict:
    rows = [_probe_row(OLD, "step 1, sw_n")]
    rows += [_probe_row(OLD, f"step 1, sw_o, structure {s}") for s in STRUCTURES]
    rows += [_probe_row(OLD, "step 1, sw_n again")]
    return explicit_plan(env, _next_name(env, 1), rows, ["sw_n", *["sw_o"] * len(STRUCTURES), "sw_n"],
                         [None, *STRUCTURES, None], texts, step=1,
                         purpose="step 1: which structure sends what 2.1.316 sends by itself (own path, kept "
                                 "transcripts)")


def step2_plan(env: Env, texts: dict, step1_name: str) -> dict:
    ways = [(OLD, "sw_w"), (NEW, "sw_n"), (NEW, "sw_o"), (NEW, "sw_w"), (NEW, "sw_n")]
    rows = [_probe_row(v, f"step 2, {v}, {g}") for v, g in ways]
    return explicit_plan(env, _next_name(env, 2), rows, [g for _, g in ways],
                         [None if g == "sw_n" else env.structure for _, g in ways], texts, step=2,
                         purpose=f"step 2: what is sent with the structure {env.structure} (own path, kept "
                                 "transcripts)",
                         extra={"step1_plan": step1_name})


def step3_plan(env: Env, texts: dict, sets: list, step2_name: str) -> dict:
    rows, groups, fills = [], [], []
    for n in sets:
        for g in ("sw_o", "sw_w"):
            rows.append(_probe_row(NEW, f"step 3, {g}, filled with the path of set {n}"))
            groups.append(g)
            fills.append(n)
    return explicit_plan(env, _next_name(env, 3), rows, groups, [env.structure] * len(rows), texts, step=3,
                         purpose="step 3: the whole prompts of the scored asks (the set's path) in 2.1.317's probe "
                                 "folder (kept transcripts)",
                         extra={"step2_plan": step2_name}, fills=fills)


def step4_plan(env: Env, texts: dict, folders: list) -> dict:
    rows, groups, structures, fills = [], [], [], []
    for set_name, v in folders:
        for g in ("sw_n", OWN_GROUP[v]):
            rows.append({"version": v, "mode": "stock_blocked", "unit": PROBE_UNIT, "warmup": True,
                         "options": {"config_set": set_name}, "label": f"step 4, warm-up, {set_name}/{v}, {g}"})
            groups.append(g)
            structures.append(None if g == "sw_n" else env.structure)
            fills.append(None if g == "sw_n" else set_name)
    return explicit_plan(env, _next_name(env, 4), rows, groups, structures, texts, step=4, fills=fills,
                         purpose="step 4: two warm-up probes in every worker folder, the set's path (checklist B5)")


def print_step1(r: dict | None) -> None:
    if r is None:
        print("step 1: no complete probes")
        return
    print(f"step 1 ({r.get('plan')}): ok {r['ok']} | structure taken {r['decided']} | passed {r.get('passed')}")
    if "sw_n_twice" in r:
        x = r["sw_n_twice"]
        print(f"  sw_n twice: same {x['ok']} | input tokens {x['first_request_input_tokens']} | system same "
              f"{x['system_same']} | other parts that differ {x['others_differ_in'] or 'none'}")
    for s, x in (r.get("structures") or {}).items():
        print(f"  {s:<6} ok {x['ok']} | input tokens {x['first_request_input_tokens']} ({x['minus_sw_n']:+d} against "
              f"sw_n) | first block same {x['first_block_same']} | other parts that differ "
              f"{x['others_differ_in'] or 'none'} | {x['system_blocks']} blocks of {x['system_block_chars']} chars "
              f"(sw_n {x['sw_n_system_block_chars']}) | cache read {x['cache_read_input_tokens']}, written "
              f"{x['cache_creation_input_tokens']}" if isinstance(x["minus_sw_n"], int) else
              f"  {s:<6} ok {x['ok']} | no input tokens | answered {x['answered']}")
    if r.get("why"):
        print(f"  why: {r['why']}")


def print_step2(r: dict | None) -> None:
    if r is None:
        print("step 2: no complete probes")
        return
    print(f"step 2 ({r.get('plan')}): ok {r['ok']} | structure {r['structure']} | checks {r.get('checks')}")
    if "6" in r:
        print(f"  input tokens {r['6']['first_request_input_tokens']} | sw_w minus sw_o {r['6']['sw_w_minus_sw_o']}")
    for k, x in (r.get("4") or {}).items():
        print(f"  {k}: whole prompt sent ok {x['ok']} | blocks after the first {x['block_chars']} (expected "
              f"{x['expected_block_chars']})" + (f" | {x['first_difference']}" if x.get("first_difference") else ""))
    if r.get("why"):
        print(f"  why: {r['why']}")


def print_step3(results: dict, sets: list) -> None:
    for n in sets:
        r = results.get(n)
        if r is None:
            print(f"step 3 set {n}: no complete probes")
            continue
        print(f"step 3 set {n} ({r.get('plan')}): ok {r['ok']} | filled with {r.get('filled_config_dir')} | input "
              f"tokens {r.get('first_request_input_tokens')} | sw_w minus sw_o {r.get('sw_w_minus_sw_o')} (step 2: "
              f"{r.get('step2_sw_w_minus_sw_o')})" + (f" | why: {r['why']}" if r.get("why") else ""))


def print_step4(results: dict, folders: list) -> None:
    for n, v, _ in folders:
        r = results.get(folder_label(n, v))
        print(f"step 4 {folder_label(n, v)}: " + (
            f"ok {r['ok']} | input tokens {r['first_request_input_tokens']}"
            + (f" (step 3's sw_w of {n}: {r.get('step3_sw_w_tokens')})" if v == NEW else "")
            + f" | answered {r['answered']} ({r['plan']})" if r else "no probes"))


def run_probes(env: Env, args) -> int:
    texts, state = guards(env, args, send=False)
    sets = sets_in_use(env, state)
    fp = current_fingerprint(env, texts)["fingerprint"]
    stop = None

    s1 = step1_state(env, texts, fp)
    if not (s1.result and s1.result["ok"]):
        p = s1.pending or step1_plan(env, texts)
        how = _send_step(env, p, texts, 1, args)
        if how != "complete":
            stop = (2, f"STOP: the step 1 probes stopped ({how})")
        s1 = step1_state(env, texts, fp)
    print_step1(s1.result)
    if stop is None and not (s1.result and s1.result["ok"]):
        stop = (1, "STOP: step 1 did not pass, and nothing more was sent. Running probes again sends step 1 once more")
    if stop is None and s1.result["decided"] != env.structure:
        stop = (1, f"STOP: step 1 took the structure {s1.result['decided']}, and the settings file "
                   f"({env.settings.source}) names {env.structure}. Write structure = \"{s1.result['decided']}\" "
                   "into [group] and run probes again: step 1 is not sent again")

    s2 = None
    if stop is None:
        s2 = step2_state(env, texts, fp, s1)
        if not (s2.result and s2.result["ok"]):
            p = s2.pending or step2_plan(env, texts, s1.plan["name"])
            how = _send_step(env, p, texts, 1, args)
            if how != "complete":
                stop = (2, f"STOP: the step 2 probes stopped ({how})")
            s2 = step2_state(env, texts, fp, s1)
        print_step2(s2.result)
        if stop is None and not (s2.result and s2.result["ok"]):
            stop = (1, "STOP: step 2 did not pass, and nothing more was sent. Running probes again sends step 2 once more")

    step3: dict = {}
    if stop is None:
        step3, plans = step3_results(env, texts, s2, state)
        need = [n for n in sets if not (step3.get(n) or {}).get("ok")]
        if need:
            p = _pending(env, plans, fp) or step3_plan(env, texts, need, s2.plan["name"])
            how = _send_step(env, p, texts, 1, args)
            if how != "complete":
                stop = (2, f"STOP: the step 3 probes stopped ({how})")
            step3, _ = step3_results(env, texts, s2, state)
        print_step3(step3, sets)
        if stop is None and any(not (step3.get(n) or {}).get("ok") for n in sets):
            stop = (1, "STOP: step 3 did not pass for every set, and no warm-up was sent. Running probes again sends "
                       "the sets that did not pass once more")

    if stop is None:
        warm, plans = step4_results(env, texts, step3)
        need = [(n, v) for n, v, _ in worker_folders(state, sets) if not (warm.get(folder_label(n, v)) or {}).get("ok")]
        if need:
            p = _pending(env, plans, fp) or step4_plan(env, texts, need)
            how = _send_step(env, p, texts, min(args.parallel or env.parallel, len(need)), args)
            if how != "complete":
                stop = (2, f"STOP: the warm-up probes stopped ({how})")
            warm, _ = step4_results(env, texts, step3)
        print_step4(warm, worker_folders(state, sets))
        if stop is None and any(not (warm.get(folder_label(n, v)) or {}).get("ok") for n, v, _ in worker_folders(state, sets)):
            stop = (1, "STOP: some worker folders did not pass step 4. Running probes again sends them once more")

    doc = write_check(env, texts, state, sets)
    print(f"written: {env.probe_check_file}")
    if stop is not None:
        print(stop[1])
        return stop[0]
    if not doc["all_ok"]:
        print(f"STOP: {doc['why'] or doc['sets_missing'] or doc['folders_missing']}")
        return 1
    print("all four probe steps have passed")
    return 0


# ------------------------------------------------------------------------------------------- commands

def cmd_extract(env: Env, args) -> int:
    author = env.inputs().system_prompt
    m = extract_all(env.texts_dir, author, replace=args.replace)
    for v, a in m["source_asks"].items():
        print(f"{v}: {a['run']} {a['ask_id']}, folder {a['config_dir']}, first request input tokens "
              f"{a['first_request_input_tokens']}")
    for c in m["checks"]:
        print(f"check {c['check']}: ok ({c['what']})")
    for t in m["texts"]:
        print(f"{t['name']}: {t['chars']} characters, sha256 {t['sha256']}, {PLACEHOLDER} {t['placeholder_count']} times")
    print(f"source: {m['source_file']} (sha256 {m['source_sha256']})")
    print(f"written: {env.texts_dir}")
    return 0


def cmd_setup_dirs(env: Env, args) -> int:
    rep = setup_dirs(env, args.sets or env.sets)
    print(json.dumps({k: rep[k] for k in ("created_table", "root", "sets", "probe_folders")}, ensure_ascii=False))
    print(f"folders {len(rep['folders'])}, problems {rep['problems'] or 'none'}, report {env.data / '建配置文件夹_报告.json'}")
    return 0 if not rep["problems"] else 1


def parse_passes(text: str | None, passes: int) -> tuple[int, int]:
    """--passes A-B (or one number A): the first and the last pass to send, within 1 and [group] passes."""
    if text is None:
        return 1, passes
    m = re.fullmatch(r"\s*([0-9]+)\s*(?:-\s*([0-9]+)\s*)?", text)
    if not m:
        raise SwapError(f"--passes takes A-B or A (whole numbers), not {text!r}")
    a, b = int(m.group(1)), int(m.group(2) or m.group(1))
    if not 1 <= a <= b <= passes:
        raise SwapError(f"--passes {text}: the passes run from 1 to {passes} ([group] passes), and A is at most B")
    return a, b


def cmd_send(env: Env, args) -> int:
    first, last = parse_passes(getattr(args, "passes", None), env.passes)
    texts, state = guards(env, args, send=True)
    parallel = args.parallel or env.parallel
    if args.trial:
        p = trial_plan(env, args.trial, texts)
        how = send_plan(env, p, texts, parallel=parallel, stop_after=args.stop_after,
                        alongside=args.alongside_other_sends)
        print(f"small batch {p['name']}: {how}")
        return 0 if how == "complete" else 2
    earlier = [n for n in range(1, first) if not (env.plans / f"SW{n}.json").exists()
               or not plan_complete(env, plan_mod.load(env.plans / f"SW{n}.json"))]
    if earlier:
        print(f"note: passes before {first} that are not complete: {earlier} (not sent by this call)")
    for number in range(first, last + 1):
        for make in (pass_plan, resend_plan):
            p = make(env, number, texts)
            if p is None:
                continue
            how = send_plan(env, p, texts, parallel=parallel, stop_after=args.stop_after,
                            alongside=args.alongside_other_sends)
            if how != "complete":
                log(env, "stopped", plan=p["name"], how=how)
                print(f"STOP: {p['name']} ended with '{how}'. The same command goes on from here.")
                return 2
    log(env, "passes_sent", first=first, last=last, passes=env.passes)
    print(f"passes {first} to {last} of {env.passes} and their resends are sent")
    return 0


def cmd_status(env: Env, args) -> int:
    for path in sorted(env.plans.glob("*.json")) if env.plans.is_dir() else []:
        p = plan_mod.load(path)
        rd = env.run_dir(p["name"])
        recs = grade.load_records(rd) if (rd / "asks").is_dir() else []
        st, by = {}, {}
        for r in recs:
            st[r["status"]] = st.get(r["status"], 0) + 1
            k = f"{r.get('version')} {r.get('group')}"
            by[k] = by.get(k, 0) + 1
        failed = sum(1 for r in recs if extract.ask_failed(r))
        print(f"{p['name']}: {len(recs)} of {len(p['asks'])} recorded | status {st} | by version and way {by} | "
              f"no answer {failed}")
    reading, when = last_reading(env)
    print(f"last weekly reading {reading} at {when} | line {env.weekly_line} | scored ways {list(env.scored_groups)} "
          f"| passes {env.passes} (first stage {env.stage1_passes})")
    try:
        texts = load_texts(env)
    except SwapError as e:
        print(f"texts: {e}")
        return 0
    state = load_state(env)
    if state is None or len(worker_sets(state)) < env.sets:
        print("probes: no config folders yet (setup-dirs)")
        return 0
    st = probe_status(env, texts, state, sets_in_use(env, state))
    s1, s2 = st["step1"] or {}, st["step2"] or {}
    print(f"probes: step 1 ok {s1.get('ok')} (structure taken {s1.get('decided')}, settings {env.structure}) | "
          f"step 2 ok {s2.get('ok')} | sets without step 3 {st['sets_missing'] or 'none'} | worker folders not yet "
          f"warmed up {st['folders_missing'] or 'none'} | send may go: {st['all_ok']}")
    return 0


def _show(value, author: str, known: dict) -> str:
    if value is None:
        return "（没有这一项）"
    if value == author:
        return f"<作者那段话：{len(author)} 字符，sha256 {sha256_text(author)[:12]}>"
    if value in known:
        return known[value]
    if value == envpolicy.REDACTED or value.startswith(envpolicy.TOKEN_PLACEHOLDER[:10]):
        return "<登录令牌：真发时才从令牌文件读，这里没读，记录里也只写 <redacted>>"
    return value


def compare_rows(mprep, main_ask: dict, ours: dict, fs, env: Env) -> list:
    """(what, main's value, {way: value}) for every part of an ask, main's and this group's three."""
    rows = []
    n = max(len(mprep.argv), *(len(p.argv) for p, _ in ours.values()))
    for i in range(n):
        rows.append((f"命令 第{i}项", mprep.argv[i] if i < len(mprep.argv) else None,
                     {g: (p.argv[i] if i < len(p.argv) else None) for g, (p, _) in ours.items()}))
    keys = sorted(set(mprep.env_record) | {k for p, _ in ours.values() for k in p.env_record})
    for k in keys:
        rows.append((f"环境变量 {k}", mprep.env_record.get(k), {g: p.env_record.get(k) for g, (p, _) in ours.items()}))
    rows.append(("工作文件夹", str(fs.workdir), {g: str(env.settings.workdir) for g in ours}))
    rows.append(("程序", str(mprep.binary), {g: str(p.binary) for g, (p, _) in ours.items()}))
    rows.append(("题目（从标准输入发）", f"{mprep.unit.key}，{len(mprep.unit.text)} 字符，sha256 {mprep.unit.text_sha256[:12]}",
                 {g: f"{p.unit.key}，{len(p.unit.text)} 字符，sha256 {p.unit.text_sha256[:12]}" for g, (p, _) in ours.items()}))
    rows.append(("跑法 / 思考力度 / 模型", f"{main_ask['mode']} / {main_ask['effort']} / {mprep.options['model']}",
                 {g: f"{p.ask['mode']} / {p.ask['effort']} / {p.options['model']}" for g, (p, _) in ours.items()}))
    strip = lambda o: json.dumps({k: v for k, v in o.items() if k != "config_set"}, sort_keys=True)  # noqa: E731
    rows.append(("这一问自己的设置（options，配置文件夹那一项不算）", strip(mprep.options),
                 {g: strip(p.options) for g, (p, _) in ours.items()}))
    rows.append(("超时", f"{modes_mod.TIMEOUT_SECONDS} 秒", {g: f"{modes_mod.TIMEOUT_SECONDS} 秒" for g in ours}))
    rows.append(("登录办法", fs.login_method, {g: env.settings.login_method for g in ours}))
    rows.append(("记录里的账号名", fs.account_label, {g: env.settings.account_label for g in ours}))
    return rows


def cmd_compare(env: Env, args) -> int:
    fs = settings_mod.load(str(FORMAL_SETTINGS))
    f3 = plan_mod.load(FORMAL_PLAN)
    mctx = run.load_context(fs, f3)
    inputs = env.inputs()
    author = inputs.system_prompt
    units, items_info = item_units(env)
    try:
        texts, source = load_texts(env), "说明/ 里存好的三段文字"
    except SwapError:
        rows_all, _ = read_source(SOURCE)
        raw, _ = take_texts(pick_source_rows(rows_all, str(SOURCE)), author)
        texts = {k: Text(k, f"{k}.txt", t, sha256_text(t)) for k, t in raw.items()}
        source = "还没运行 extract，三段文字是当场从试探提问记录里取的，没有存文件"
    state, folder_note = load_state(env), ""
    if state is None or len(worker_sets(state)) < env.sets or not all(v in state.get("codes", {}) for v in VERSIONS):
        root = str(Path(os.path.abspath(env.settings.config_root)))
        state = {"format": configdirs.STATE_FORMAT, "config_root": root, "prefix": "oz",
                 "codes": {v: f"oz??_probe_{v}" for v in VERSIONS}, "user_id": mctx.state["user_id"],
                 "machine_id": mctx.state["machine_id"],
                 "sets": {f"w{k}": {v: f"oz??_w{k}_{v}" for v in VERSIONS} for k in range(1, env.sets + 1)},
                 "set_roots": {f"w{k}": root for k in range(1, env.sets + 1)},
                 "set_remote_flags": {f"w{k}": "off" for k in range(1, env.sets + 1)}}
        folder_note = ("（还没运行 setup-dirs，文件夹名里的两位数要建的时候才抽，这里写成 oz?? 后面跟着是哪一套、哪个版本，"
                       "真的文件夹名只有 oz 加两位数）")
    sets = worker_sets(state)[:env.sets]
    plan = build_pass_plan(env, inputs, state, name="SW1", number=1, units=units,
                           fingerprint={"fingerprint": "-", "parts": {}}, texts=texts, items_info=items_info, sets=sets)
    ctx = run.Context(env.settings, inputs, state, plan, {"fingerprint": "-", "parts": {}})
    print(f"main：{FORMAL_PLAN.name} 里 main 组在这个版本上的第一问里，题目在本组题目清单里的那一问，用 ccversions.run.prepare 和 "
          f"{FORMAL_SETTINGS.name} 拼出来的。")
    print(f"本组：同一个版本、同一道题，用 swap.py 和 {env.settings.source.name} 照真发时的拼法拼出来的（计划没有存，也没发）。"
          f"用的是计划给这道题排的那一套配置文件夹{folder_note}。三段文字的来源：{source}。结构：{env.structure}。"
          f"计分的各遍只发 {'、'.join(env.scored_groups)}，sw_n 只在试探提问里发，这里照同一套文件夹拼出来对照。")
    print("登录令牌两边都没读。作者那段话、整段都写成字符数和 sha256。跟 main 一样的写「同」。\n")
    docs = []
    first = min((a for a in f3["asks"] if a["version"] == OLD and a.get("group") == "main" and a["unit"] in units),
                key=lambda a: a["order"])
    for v in VERSIONS:  # the same item on both versions: main's first ask of it on each
        main_ask = min((a for a in f3["asks"] if a["version"] == v and a.get("group") == "main"
                        and a["unit"] == first["unit"]), key=lambda a: a["order"])
        mprep = run.prepare(mctx, main_ask, token=None)
        ours, known = {}, {}
        mine = [a for a in plan["asks"] if a["version"] == v and a["unit"] == main_ask["unit"]]
        for g in GROUPS:
            ask = next((a for a in mine if a["group"] == g), None)
            if ask is None:  # a way the scored passes do not ask (sw_n): made from another ask of the item
                ask = {**mine[0], "group": g, "label": LABELS[g], "options": dict(mine[0]["options"])}
                ask.pop("fill_set", None)
            p, info = prepare_ask(ctx, ask, texts, env.structure, None)
            ours[g] = (p, info)
            if g in DYNAMIC_OF:
                path = filled_path(ctx.state, ask, p.config_dir)
                whole = whole_prompt(texts, g, env.structure, path)
                sep = {"join0": "直接接", "join1": "一个换行", "join2": "两个换行",
                       "marker": f"一个换行、一行 {BOUNDARY}、一个换行"}[env.structure]
                known[whole] = (f"<整段：STATIC（{len(texts['STATIC'].text)} 字符）+ {sep} + {DYNAMIC_OF[g]}"
                                f"（{PLACEHOLDER} 换成 {path}，这一套 {ask.get('fill_set')} 里 {OLD} 的干活文件夹），"
                                f"合起来 {len(whole)} 字符，sha256 {sha256_text(whole)[:12]}，里面是 {SENTENCES_OF[g]} 的那两句>")
        rows = compare_rows(mprep, main_ask, ours, fs, env)
        by_way = {g: [w for w, m, vs in rows if vs[g] != m] for g in GROUPS}
        sets_of = {g: (p.options.get("config_set"), str(p.config_dir)) for g, (p, _) in ours.items()}
        print(f"===== {v}：main 是 {FORMAL_PLAN.stem} {main_ask['ask_id']}，题 {main_ask['unit']}；本组三种问法用的"
              f"配置文件夹：" + "，".join(f"{g} {s} {d}" for g, (s, d) in sets_of.items()) + " =====")
        for what, mv, vs in rows:
            if all(x == mv for x in vs.values()):
                print(f"  {what:<30} {_show(mv, author, known)}   | " + " | ".join(f"{g} 同" for g in vs))
            else:
                print(f"  {what:<30} main：{_show(mv, author, known)}")
                for g, x in vs.items():
                    print(f"  {'':<30} {g}：{'同' if x == mv else _show(x, author, known)}")
        print(f"  一共 {len(rows)} 项。每种问法跟 main 不一样的项：")
        for g in GROUPS:
            print(f"    {g}：{len(by_way[g])} 项：{', '.join(by_way[g]) or '无'}")
        n = len(mprep.argv)
        want = {"sw_n": ["环境变量 CLAUDE_CONFIG_DIR"],
                **{g: [f"命令 第{n}项", f"命令 第{n + 1}项", "环境变量 CLAUDE_CONFIG_DIR"] for g in DYNAMIC_OF}}
        for g in GROUPS:
            if by_way[g] != want[g]:
                print(f"  注意：{g} 应该只差 {want[g]}，实际差的是 {by_way[g]}。")
        flag = [w for w, m, vs in rows if m == "--append-system-prompt"]
        same_pair = all(all(x == m for x in vs.values()) for w, m, vs in rows if m in ("--append-system-prompt", author))
        print(f"  --append-system-prompt 和作者那段话在 main 的{('、'.join(flag)) or '（没找到）'}，三种问法都在原位、值不变："
              f"{'是' if same_pair and flag else '否'}")
        ms, os_ = settings_mod.ask_shaping(fs), settings_mod.ask_shaping(env.settings)
        shaping = {k: [ms.get(k), os_.get(k)] for k in sorted(set(ms) | set(os_)) if ms.get(k) != os_.get(k)}
        print(f"  两份设置文件里影响提问的几项（指纹里那一份），不一样的：{shaping or '无'}"
              "（config_root 是配置文件夹放在哪，就是上面那一项；api_url 只管直接调 API 那种跑法，这个小组不用）\n")
        wholes = {g: p.argv[-1] for g, (p, _) in ours.items() if g in DYNAMIC_OF}
        docs.append({"version": v, "main_ask": main_ask["ask_id"], "unit": main_ask["unit"],
                     "set": mine[0]["options"]["config_set"],
                     "filled_config_dir": {g: info["filled_config_dir"] for g, (_, info) in ours.items()},
                     "whole_sha256": {g: sha256_text(w) for g, w in wholes.items()},
                     "rows": [[w, _show(m, author, known), {g: _show(x, author, known) for g, x in vs.items()}]
                              for w, m, vs in rows],
                     "differ_by_way": by_way, "expected": want, "main_argv_items": n,
                     "append_pair_rows": flag, "append_pair_unchanged": bool(same_pair and flag),
                     "ask_shaping_settings_that_differ": shaping})
    same = docs[0]["set"] == docs[1]["set"] and all(docs[0]["whole_sha256"][g] == docs[1]["whole_sha256"][g]
                                                    for g in DYNAMIC_OF)
    print(f"同一道题在两个版本上用的是同一套（{docs[0]['set']} 和 {docs[1]['set']}），sw_o 的整段两个版本逐字一样、sw_w 的整段两个"
          f"版本逐字一样：{'是' if same else '否'}")
    if args.out:
        Path(args.out).write_text(json.dumps({"versions": docs, "same_set_same_whole_prompts": same},
                                             ensure_ascii=False, indent=1) + "\n")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="swap.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--settings", help=f"settings file (default {DEFAULT_SETTINGS})")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sp = sub.add_parser("extract")
    sp.add_argument("--replace", action="store_true", help="overwrite stored texts that differ (only before any send)")
    sp = sub.add_parser("setup-dirs")
    sp.add_argument("--sets", type=int, help="how many sets of worker folders in all (default: [group] sets)")
    sp = sub.add_parser("compare")
    sp.add_argument("--out", help="also write the rows as JSON here")
    for name in ("probes", "send"):
        sp = sub.add_parser(name)
        sp.add_argument("--parallel", type=int, help="asks at once (default: [group] parallel)")
        sp.add_argument("--alongside-other-sends", action="store_true",
                        help="send although another program is sending now")
        sp.add_argument("--after-reset", action="store_true",
                        help="send although the last reading is at or above the line (after the weekly reset)")
        if name == "send":
            sp.add_argument("--trial", type=int, metavar="N", help="a small batch of N items, every cell (plan SWS)")
            sp.add_argument("--passes", metavar="A-B", help="send passes A to B only (or one pass: A)")
            sp.add_argument("--stop-after", type=int, metavar="K", help="start no more than K asks in this call")
    sub.add_parser("status")
    args = ap.parse_args(argv)
    try:
        env = load_env(args.settings)
        fn = {"extract": cmd_extract, "setup-dirs": cmd_setup_dirs, "compare": cmd_compare, "probes": run_probes,
              "send": cmd_send, "status": cmd_status}[args.cmd]
        return fn(env, args)
    except (SwapError, run.RunError, plan_mod.PlanError, configdirs.ConfigDirsError, settings_mod.SettingsError,
            items_mod.ItemsError, modes_mod.ModeError, envpolicy.EnvPolicyError) as e:
        print(f"STOP: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
