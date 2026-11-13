"""Self-test of swap.py (the swap group) with a stand-in for Claude Code.

    本机数据/python环境/bin/python -B 程序/对调两句话组/test_swap.py        (from the project folder)

No Claude Code is started and nothing goes over the network. The stand-in is a short Python script written
into a new temporary folder under /private/tmp, once per version (2.1.316 and 2.1.317). It answers
`--version`, reads the question from stdin and prints what Claude Code prints in stream-json (an init line,
a usage reading, the answer, a result line). Its own system prompt is the three texts the tests take out of
the real probe transcripts: the opening sentence, STATIC, and the version's dynamic text with its config
folder put in and the appended author's text after it. Given --system-prompt, it cuts that prompt at a
marker line and makes blocks the way the code of 2.1.317 was read to do it (system_blocks below). Its
first-request input tokens are the characters (or, if a control file says so, the words) of its system
blocks joined the way the control file says the server joins them, plus its tools, the question and the
extra messages, so a prompt that would read differently to the model shows another number. A probe that
keeps its transcript writes a session file with the request lines Claude Code writes (api-request-shape,
api-request-blob, api-request). Small files in a control folder tell it what to do: which weekly reading
to report (from which call on), to fail as in an outage, to answer with a usage-limit refusal, to try a
tool and get the hook's refusal, how to join and count. It writes one line per call into the control
folder, and marks its config folder busy while it runs, so the tests can count what was sent, how many
ran at once, and whether two asks ever shared a folder.

The probe checks are also tested on transcripts made up here, with the same code that writes the
stand-in's (fake_probe).

What is real here: the probe transcripts the three texts come from, the item file and probe file of the
registered run, the item list, the version list and the author's grading code (all read only), and for the
side by side command, the registered run's settings, config folder table and third pass plan and this
group's settings (read only). Everything written goes into the temporary folders, which are removed at
the end. The login token is made up for the test. Nothing is read from or written to /Users/Shared/kq7 or
/private/tmp/ws, which the sends running tonight use.

The weekly line the tests stop at is the one in the group's real settings file ([group] weekly_line).
"""

import argparse
import contextlib
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import tomllib
import unittest
import uuid
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import swap  # noqa: E402
from ccversions import checks, configdirs, extract, grade, items as items_mod, modes, plan as plan_mod, run  # noqa: E402
from ccversions import runcheck  # noqa: E402

REAL_SETTINGS = swap.DEFAULT_SETTINGS
REAL = tomllib.loads(REAL_SETTINGS.read_text(encoding="utf-8"))
LINE = REAL["group"]["weekly_line"]  # the line the tests stop at, as the real settings file has it
TOKEN = "sk-ant-oat01-" + "Q" * 60  # made up for the test
TMP_ROOT = Path("/private/tmp")
OLD, NEW = swap.OLD, swap.NEW
PROBE_TEXT = "Reply with <answer>OK</answer>."

# Shared by the stand-in and the made-up transcripts of the probe tests.
STAND_IN_PARTS = r'''
import hashlib, json
BOUNDARY = "__SYSTEM_PROMPT_DYNAMIC_BOUNDARY__"
INTRO_CLI = "You are Claude Code, Anthropic's official CLI for Claude, running within the Claude Agent SDK."
INTRO_AGENT = "You are a Claude agent, built on Anthropic's Claude Agent SDK."
TOOLS = [{"name": "Bash", "description": "Run a shell command.",
          "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}},
         {"name": "Read", "description": "Read a file.",
          "input_schema": {"type": "object", "properties": {"file_path": {"type": "string"}}, "required": ["file_path"]}}]
BETAS = ["claude-code-20250219", "oauth-2025-04-20", "effort-2025-11-24"]


def split_at_marker(text):
    lines = text.split("\n")
    s = next((i for i, x in enumerate(lines) if x.strip() == BOUNDARY), None)
    if s is None:
        return [text]
    d = "\n".join(lines[:s]) + "\n"
    m = "\n" + "\n".join(lines[s + 1:])
    return ([d] if d.strip() else []) + [BOUNDARY] + ([m] if m.strip() else [])


def system_blocks(custom, append, builtin, cfg):
    intro = INTRO_CLI if append is not None else INTRO_AGENT
    if custom is None:
        dyn = builtin["dynamic"].replace("{CONFIG_DIR}", cfg)
        return [intro, builtin["static"], dyn + ("\n\n" + append if append else "")]
    items = split_at_marker(custom) + ([append] if append else [])
    if BOUNDARY in items:
        k = items.index(BOUNDARY)
        before, after = items[:k], items[k + 1:]
        return [intro] + (["\n\n".join(before)] if before else []) + (["\n\n".join(after)] if after else [])
    return [intro, "\n\n".join(items)]


def blob_texts(date):
    return ["<system-reminder>\nAttribution for git commits.\n</system-reminder>\n",
            "# Environment\n - Primary working directory: /private/tmp/ws\nToday's date is " + date + "."]


def count(text, how):
    return len(text.split()) if how == "words" else len(text)


def first_request_tokens(system, tools, user, blobs, join, how):
    return (count(join.join(system), how) + count(json.dumps(tools, sort_keys=True), how) + count(user, how)
            + sum(count(b, how) for b in blobs))


def transcript_lines(sid, system, tools, user, blobs, model, effort):
    shape = {"system": [{"type": "text", "text": s} for s in system], "tools": tools}
    h = hashlib.sha256(json.dumps(shape, sort_keys=True).encode()).hexdigest()
    out = [{"type": "user", "sessionId": sid, "message": {"role": "user", "content": user}},
           {"type": "api-request-shape", "sessionId": sid, "shapeHash": h, "shape": shape}]
    hashes = []
    for t in blobs:
        msg = {"role": "user", "content": [{"type": "text", "text": t}]}
        hb = hashlib.sha256(json.dumps(msg, sort_keys=True).encode()).hexdigest()
        hashes.append(hb)
        out.append({"type": "api-request-blob", "sessionId": sid, "hash": hb, "message": msg})
    out.append({"type": "api-request", "sessionId": sid, "shapeHash": h, "tail": hashes,
                "params": {"model": model, "betas": BETAS, "max_tokens": 128000, "thinking": {"type": "adaptive"},
                           "context_management": {"edits": []}, "output_config": {"effort": effort}}})
    return out


def stdout_lines(model, in_tok, answer, util=0.10, limit=False, tool_block=None, version="2.1.317"):
    usage1 = {"input_tokens": in_tok, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0, "output_tokens": 5}
    out = [{"type": "system", "subtype": "init", "tools": ["Bash", "Read"], "mcp_servers": [], "model": model,
            "apiKeySource": "none", "claude_code_version": version, "permissionMode": "default"},
           {"type": "rate_limit_event", "rate_limit_info": {"status": "rejected" if limit else "allowed",
            "rateLimitType": "seven_day", "overageStatus": "rejected", "isUsingOverage": False,
            "unifiedWindows": {"seven_day": {"utilization": util}, "five_hour": {"utilization": 0.2}}}}]
    if limit:
        out.append({"type": "result", "subtype": "error_during_execution", "is_error": True, "num_turns": 1,
                    "result": "You've hit your usage limit.", "stop_reason": None,
                    "usage": {"input_tokens": 0, "output_tokens": 0}, "modelUsage": {}, "permission_denials": []})
        return out
    if tool_block:
        out += [{"type": "assistant", "parent_tool_use_id": None, "message": {"id": "m1", "model": model, "usage": usage1,
                 "content": [{"type": "tool_use", "id": "tu1", "name": "Bash", "input": {"command": "ls"}}]}},
                {"type": "user", "parent_tool_use_id": None, "message": {"content": [{"type": "tool_result",
                 "tool_use_id": "tu1", "is_error": True, "content": "PreToolUse:Bash hook error: " + tool_block}]}}]
    out += [{"type": "assistant", "parent_tool_use_id": None, "message": {"id": "m2", "model": model, "usage": usage1,
             "content": [{"type": "text", "text": answer}]}},
            {"type": "result", "subtype": "success", "is_error": False, "num_turns": 2 if tool_block else 1,
             "result": answer, "stop_reason": "end_turn", "terminal_reason": "completed", "duration_ms": 900,
             "usage": {"input_tokens": in_tok, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0,
                       "output_tokens": 50, "inference_geo": "global", "output_tokens_details": {"thinking_tokens": 30}},
             "modelUsage": {model: {"costBasis": "list", "outputTokens": 50}}, "permission_denials": []}]
    return out
'''

STAND_IN = "#!@PYTHON@ -I\n" + STAND_IN_PARTS + r'''
import os, sys, time, uuid
CONTROL = "@CONTROL@"
VERSION = "@VERSION@"
BLOCK = "@BLOCK@"
argv = sys.argv[1:]
if argv == ["--version"]:
    print(VERSION + " (Claude Code)")
    sys.exit(0)


def c(name, default=None, strip=True):
    p = os.path.join(CONTROL, name)
    if not os.path.exists(p):
        return default
    v = open(p).read()
    return v.strip() if strip else v


def sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def val(flag):
    return argv[argv.index(flag) + 1] if flag in argv else None


text = sys.stdin.read()
cfg = os.environ["CLAUDE_CONFIG_DIR"]
token = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN", "")
calls = os.path.join(CONTROL, "calls")
os.makedirs(calls, exist_ok=True)
me = "%.6f-%s" % (time.time(), uuid.uuid4().hex[:8])
n_before = len(os.listdir(calls))
busy = os.path.join(cfg, ".busy")
try:
    os.close(os.open(busy, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
except FileExistsError:
    open(os.path.join(CONTROL, "violation-" + me), "w").write(cfg)
    busy = None
custom, append = val("--system-prompt"), val("--append-system-prompt")
model, effort, fmt = val("--model"), val("--effort"), val("--output-format")
builtin = json.load(open(os.path.join(CONTROL, "builtin_" + VERSION + ".json")))
system = system_blocks(custom, append, builtin, cfg)
blobs = blob_texts("2026-11-13")
in_tok = first_request_tokens(system, TOOLS, text, blobs, c("server_join", "\n\n", strip=False), c("tokenizer", "chars"))
row = {"cfg": cfg, "version": VERSION, "custom_sha256": sha(custom) if custom is not None else None,
       "append_sha256": sha(append) if append is not None else None, "stdin_sha256": sha(text), "effort": effort,
       "model": model, "fmt": fmt, "start": time.time(), "n_before": n_before,
       "kept": "--no-session-persistence" not in argv, "tokens": in_tok}
path = os.path.join(calls, me + ".json")
json.dump(row, open(path, "w"))
time.sleep(float(c("sleep", "0.03")))
util = float(c("util", "0.10"))
after = c("util_after")
if after:
    k, v = after.split()
    if n_before >= int(k):
        util = float(v)
print("debug: login " + token, file=sys.stderr)


def end(code):
    row["end"] = time.time()
    json.dump(row, open(path, "w"))
    if busy:
        os.remove(busy)
    sys.exit(code)


if c("fail"):
    print("API Error: Connection error.", file=sys.stderr)
    end(1)
limit = bool(c("limit"))
tool = sha(text) in (c("tool_shas") or "").split()
if row["kept"]:
    d = os.path.join(cfg, "projects", "-private-tmp-ws")
    os.makedirs(d, exist_ok=True)
    sid = str(uuid.uuid4())
    lines = transcript_lines(sid, system, TOOLS, text, blobs, model, effort) + [{"type": "echo", "token": token}]
    with open(os.path.join(d, sid + ".jsonl"), "w") as f:
        f.write("".join(json.dumps(x) + "\n" for x in lines))
answer = "<answer>OK</answer>" if "<answer>OK</answer>" in text else "<answer>" + c("answer", "A") + "</answer>"
print("\n".join(json.dumps(x) for x in stdout_lines(model, in_tok, answer, util, limit, BLOCK if tool else None, VERSION)))
end(1 if limit else 0)
'''

NS: dict = {}
exec(STAND_IN_PARTS, NS)  # the same functions the stand-in uses, for the made-up transcripts


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def quiet(fn, *a, **kw):
    """Run fn with its printed lines caught. Returns (result, printed text)."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        out = fn(*a, **kw)
    return out, buf.getvalue()


def real_author() -> str:
    s = REAL["paths"]
    return items_mod.load(Path(s["item_file"]), s["item_file_sha256"], Path(s["probe_file"])).system_prompt


class Base(unittest.TestCase):
    sets = 3
    parallel = 2  # as the real settings
    passes = 3

    @classmethod
    def setUpClass(cls):
        # the three texts, taken once from the real probe transcripts into a temporary folder
        cls.author = real_author()
        cls.text_dir = Path(tempfile.mkdtemp(prefix="swap-texts-", dir=TMP_ROOT))
        cls.manifest = swap.extract_all(cls.text_dir, cls.author)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.text_dir, ignore_errors=True)

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="swap-test-", dir=TMP_ROOT))
        t = self.tmp
        self.control = t / "control"
        self.control.mkdir()
        texts = {n: (self.text_dir / f"{n}.txt").read_bytes().decode("utf-8") for n in swap.TEXT_NAMES}
        self.builtin = {OLD: {"static": texts["STATIC"], "dynamic": texts["DYNAMIC_OLD"]},
                        NEW: {"static": texts["STATIC"], "dynamic": texts["DYNAMIC_NEW"]}}
        for v in swap.VERSIONS:
            (self.control / f"builtin_{v}.json").write_text(json.dumps(self.builtin[v]))
            b = t / "bins" / v / "claude"
            b.parent.mkdir(parents=True)
            b.write_text(STAND_IN.replace("@PYTHON@", sys.executable).replace("@CONTROL@", str(self.control))
                         .replace("@BLOCK@", modes.BLOCK_MESSAGE).replace("@VERSION@", v))
            os.chmod(b, 0o555)
            (b.parent / "manifest.json").write_text(json.dumps({"version": v, "platforms": {"darwin-arm64": {
                "checksum": checks.file_sha256(b), "size": b.stat().st_size}}}))
        exp = t / "exp"
        (exp / "c").mkdir(parents=True)
        os.chmod(exp, 0o700)
        self.formal_state = t / "formal_state.json"
        self.formal_state.write_text(json.dumps({
            "format": configdirs.STATE_FORMAT, "config_root": str(exp / "c"), "code_seed": "x", "prefix": "oz",
            "codes": {OLD: "oz55", NEW: "oz95"}, "user_id": "a" * 64, "machine_id": "b" * 64}))
        tok = t / "tok"
        tok.write_text(TOKEN + "\n")
        os.chmod(tok, 0o600)
        data = t / "data"
        data.mkdir()
        shutil.copytree(self.text_dir, data / "说明")
        self.data = data
        self.write_settings()
        self.saved = swap.FORMAL_STATE
        swap.FORMAL_STATE = self.formal_state
        self.env = self.load()
        self.slept = []

    def write_settings(self, **group):
        t, p = self.tmp, REAL["paths"]
        exp = t / "exp"
        g = {"weekly_line": LINE, "parallel": self.parallel, "sets": self.sets, "structure": '"join2"',
             "item_list": json.dumps(REAL["group"]["item_list"], ensure_ascii=False), "passes": self.passes,
             "seed": json.dumps(REAL["group"]["seed"])}
        g.update(group)
        allow = g.pop("allow_send", "true")
        lines = [
            "[paths]",
            *[f'{k} = "{p[k]}"' for k in ("author_repo", "livenerf_cache", "item_file", "item_file_sha256", "probe_file",
                                         "versions_file", "platform")],
            f'binary_template = "{t}/bins/{{version}}/claude"',
            f'manifest_template = "{t}/bins/{{version}}/manifest.json"',
            f'experiment_root = "{exp}"', f'config_root = "{exp}/s"', f'home_dir = "{exp}/h"',
            f'workdir = "{t}/ws"', f'tmpdir = "{t}/tmpd"', f'config_dirs_file = "{self.data}/配置文件夹.json"',
            f'raw_dir = "{self.data}/原始记录"', f'raw_mirror_dir = "{t}/mirror"', f'lock_dir = "{self.data}/locks"',
            "[env]", *[f'{k} = "{v}"' for k, v in REAL["env"].items()],
            "[login]", 'method = "token"', 'account_label = "test"', f'token_file = "{t}/tok"',
            "[send]", f"allow_send = {allow}",
            "[scan]", "leak_markers = " + json.dumps(REAL["scan"]["leak_markers"], ensure_ascii=False),
            "[group]", *[f"{k} = {v}" for k, v in g.items()],
        ]
        (self.data / "设置.toml").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def load(self):
        env = swap.load_env(str(self.data / "设置.toml"))
        env.sleep = self.fake_sleep
        env.find_other_sends = lambda template: []  # this machine may be sending for another group right now
        return env

    def reload(self, **group):
        self.write_settings(**group)
        self.env = self.load()

    def tearDown(self):
        swap.FORMAL_STATE = self.saved
        shutil.rmtree(self.tmp, ignore_errors=True)

    # -- helpers
    def fake_sleep(self, seconds):
        """The outage waits: time passes at once, and the service is back (the stand-in stops failing)."""
        self.slept.append(seconds)
        (self.control / "fail").unlink(missing_ok=True)

    def ctl(self, name, value=None):
        f = self.control / name
        if value is None:
            f.unlink(missing_ok=True)
        else:
            f.write_text(str(value))

    def args(self, **kw):
        base = {"parallel": None, "alongside_other_sends": False, "after_reset": False, "trial": None,
                "stop_after": None, "sets": None, "replace": False, "out": None, "passes": None}
        base.update(kw)
        return argparse.Namespace(**base)

    def calls(self) -> list[dict]:
        d = self.control / "calls"
        return [json.loads(p.read_text()) for p in sorted(d.glob("*.json"))] if d.is_dir() else []

    def violations(self) -> list:
        return sorted(self.control.glob("violation-*"))

    def texts(self):
        return swap.load_texts(self.env)

    def prepare(self):
        quiet(swap.cmd_setup_dirs, self.env, self.args())
        rc, out = quiet(swap.run_probes, self.env, self.args())
        self.assertEqual(rc, 0, out)
        return out

    def small_pass_plans(self, n_items: int, passes: int):
        """Plans SW1..SWn on the first n items of the item list only (made with swap's own code), so a whole
        send with its resends is quick (4 asks per item and pass). `send` then takes these plans as they are."""
        texts = self.texts()
        units, info = swap.item_units(self.env)
        state = swap.load_state(self.env)
        fp = swap.current_fingerprint(self.env, texts)
        for k in range(1, passes + 1):
            p = swap.build_pass_plan(self.env, self.env.inputs(), state, name=f"SW{k}", number=k, units=units[:n_items],
                                     fingerprint=fp, texts=texts, items_info=info)
            plan_mod.save(p, self.env.plans / f"SW{k}.json")
        self.env.passes = passes

    def runcheck_ok(self, name, failed_without_output=()):
        rep = runcheck.check(self.env.run_dir(name), self.env.inputs())
        h1 = dict(rep["h1_missing_fields"])
        for i in failed_without_output:
            if h1.get(i) == ["stdout"]:
                del h1[i]
        what = {k: rep[k] for k in ("missing", "unexpected_records", "record_differs_from_plan", "sent_more_than_once",
                                    "fingerprint_mismatch", "records_without_an_ask_event", "ask_events_without_a_record")}
        self.assertFalse(any(what.values()), what)
        self.assertEqual(h1, {})
        self.assertFalse(rep["stdin_sha256"]["mismatch"])
        self.assertEqual(rep["stock_blocked"]["asks_where_a_tool_ran"], [])
        return rep

    def spans(self, calls):
        return [(c["start"], c["end"], c["cfg"], c["version"]) for c in calls if c.get("end")]

    # -- made-up probes (the probe checks)
    def fake_probe(self, run_dir: Path, *, ask_id: str, order: int, group: str, version: str, structure, config_dir,
                   tweak: dict | None = None, how: str = "chars", join: str = "\n\n", kept: bool = True,
                   fill_set: str | None = None, fill_path=None) -> dict:
        """One probe's record and kept transcript, as the stand-in would make them. The whole prompt of sw_o
        and sw_w holds fill_path (the set's path) if given, else config_dir (its own path). `tweak` changes
        one part of what was sent: tokens (added to the input tokens), intro (the first block), extra_tool (one
        more tool), last_char (the last character of the last block), blob (a word of the extra message with
        the environment), model, effort, no_answer. The input tokens are counted before the change, so each
        tweak changes one thing only."""
        texts, author = self.texts(), self.author
        argv = modes.build_argv(f"/x/{version}/claude", modes.MODES["stock_blocked"], author, "high",
                                keep_transcript=kept)
        custom = filled = None
        if group in swap.DYNAMIC_OF:
            filled = fill_path if fill_path is not None else config_dir
            custom = swap.whole_prompt(texts, group, structure, filled)
            argv = swap.add_system_prompt(argv, author, custom)
        system = NS["system_blocks"](custom, author, self.builtin[version], str(config_dir))
        tools = json.loads(json.dumps(NS["TOOLS"]))
        blobs = NS["blob_texts"]("2026-11-13")
        tokens = NS["first_request_tokens"](system, tools, PROBE_TEXT, blobs, join, how)
        tw = tweak or {}
        tokens += tw.get("tokens", 0)
        if "intro" in tw:
            system[0] = tw["intro"]
        if tw.get("extra_tool"):
            tools.append({"name": "Extra", "description": "One more.", "input_schema": {"type": "object"}})
        if tw.get("last_char"):
            last = system[-1]
            system[-1] = last[:-1] + ("X" if last[-1] != "X" else "Y")
        if tw.get("blob"):
            blobs[1] = blobs[1].replace("Primary working directory", "Main working directory")
        model, effort = tw.get("model", modes.MODEL), tw.get("effort", "high")
        if kept:
            sid = str(uuid.uuid4())
            d = run_dir / "transcripts" / ask_id / "projects" / "-private-tmp-ws"
            d.mkdir(parents=True, exist_ok=True)
            lines = NS["transcript_lines"](sid, system, tools, PROBE_TEXT, blobs, model, effort)
            (d / f"{sid}.jsonl").write_text("".join(json.dumps(x) + "\n" for x in lines))
        out = NS["stdout_lines"](model, tokens, "<answer>OK</answer>", version=version)
        if tw.get("no_answer"):
            out = out[:2]
        rec = {"format": run.RECORD_FORMAT, "ask_id": ask_id, "plan": run_dir.name, "order": order, "version": version,
               "mode": "stock_blocked", "effort": "high", "unit": swap.PROBE_UNIT, "warmup": not kept, "scored": False,
               "group": group, "options": {"keep_transcript": kept}, "argv": argv, "config_dir": str(config_dir),
               "status": "done", "returncode": 0, "stdout": "\n".join(json.dumps(x) for x in out),
               "swap": {"group": group, "structure": structure, "fill_set": fill_set,
                        "filled_config_dir": None if filled is None else str(filled)}}
        (run_dir / "asks").mkdir(parents=True, exist_ok=True)
        (run_dir / "asks" / f"{ask_id}.json").write_text(json.dumps(rec))
        return rec


# ---------------------------------------------------------------------------------------------- texts

class TextTests(Base):
    def rows(self):
        rows, _ = swap.read_source(swap.SOURCE)
        return rows, swap.pick_source_rows(rows)

    def test_texts_from_the_real_probes(self):
        """The three texts, against a second way of taking them out of the two probes."""
        rows, picked = self.rows()
        m = self.manifest
        self.assertEqual([c["ok"] for c in m["checks"]], [True] * 7)
        self.assertEqual(m["source_sha256"], hashlib.sha256(swap.SOURCE.read_bytes()).hexdigest())
        texts = self.texts()
        a, b = picked[OLD], picked[NEW]
        self.assertEqual((a["run"], a["mode"], a["effort_requested"], a["unit"], a["warmup"]),
                         ("RP1", "stock_blocked", "high", "probe:author-ok", False))
        self.assertEqual(texts["STATIC"].text, a["system"][1])
        self.assertEqual(texts["STATIC"].text, b["system"][1])
        for v, name, r in ((OLD, "DYNAMIC_OLD", a), (NEW, "DYNAMIC_NEW", b)):
            t = texts[name].text
            self.assertEqual(t.count("{CONFIG_DIR}"), 1)
            self.assertNotIn(r["config_dir"], t)
            # put the folder and the author's text back: the block as it was sent
            self.assertEqual(t.replace("{CONFIG_DIR}", r["config_dir"]) + "\n\n" + self.author, r["system"][2])
            self.assertEqual(t.count(swap.SENTENCES[v]), 1)
        self.assertEqual(texts["DYNAMIC_OLD"].text.replace(swap.SENTENCES[OLD], swap.SENTENCES[NEW]),
                         texts["DYNAMIC_NEW"].text)
        for x in texts.values():
            self.assertEqual(sha(x.text), x.sha256)
        print(f"\n  texts: " + ", ".join(f"{k} {len(x.text)} chars sha256 {x.sha256[:12]}" for k, x in texts.items()))

    def test_each_check_stops(self):
        """Every check of the texts stops `extract` when it does not hold, and says which check."""
        rows, picked = self.rows()
        author = self.author
        cfg = {v: picked[v]["config_dir"] for v in swap.VERSIONS}

        def changed(fn):
            rs = json.loads(json.dumps(rows))
            p = swap.pick_source_rows(rs)
            fn(p)
            return rs

        def dyn(v, f):
            return lambda p: p[v]["system"].__setitem__(2, f(p[v]["system"][2]))

        cases = {
            "check 0": lambda p: p[NEW]["system"].pop(1),
            "check 1": lambda p: p[NEW]["system"].__setitem__(0, "You are a Claude agent, built on Anthropic's Claude Agent SDK."),
            "check 2": lambda p: p[NEW]["system"].__setitem__(1, p[NEW]["system"][1].replace("Harness", "Harnesz")),
            "check 3": dyn(OLD, lambda d: d[:-len(author) - 2] + "\n" + author),
            "check 4 (old sentences twice)": dyn(OLD, lambda d: d.replace(swap.SENTENCES[OLD], swap.SENTENCES[OLD] + " "
                                                                         + swap.SENTENCES[OLD])),
            "check 4 (new sentences missing)": dyn(NEW, lambda d: d.replace(swap.SENTENCES[NEW], swap.SENTENCES[OLD])),
            "check 4 (another difference)": dyn(NEW, lambda d: d.replace("pronoun", "pronown", 1)),
            "check 5 (no folder path)": dyn(NEW, lambda d: d.replace(cfg[NEW], cfg[NEW][:-1] + "0")),
            "check 5 (a path form left)": dyn(OLD, lambda d: d.replace("# Memory", "# Memory " + cfg[OLD].replace("/", "-"), 1)),
            "check 6": lambda p: [p[v]["system"].__setitem__(1, p[v]["system"][1] + "\n" + swap.STATIC_BREAKPOINT)
                                  for v in swap.VERSIONS],
        }
        for k, (name, fn) in enumerate(cases.items()):
            rs = changed(fn)
            src = self.tmp / f"src-{k}.jsonl"
            src.write_text("".join(json.dumps(r) + "\n" for r in rs))
            out = self.tmp / f"out-{k}"
            with self.assertRaises(swap.SwapError, msg=name) as e:
                swap.extract_all(out, author, source=src)
            self.assertTrue(str(e.exception).startswith(name.split(" (")[0] + " "), (name, str(e.exception)[:300]))
            self.assertFalse((out / "清单.json").exists(), name)
        # two asks of one version that fit: no choice is made
        src = self.tmp / "two.jsonl"
        src.write_text("".join(json.dumps(r) + "\n" for r in rows + [picked[OLD]]))
        with self.assertRaises(swap.SwapError) as e:
            swap.extract_all(self.tmp / "out-two", author, source=src)
        self.assertIn("exactly one is expected", str(e.exception))

    def test_stored_texts_are_checked(self):
        f = self.env.texts_dir / "STATIC.txt"
        original = f.read_bytes()
        f.write_bytes(original + b" ")
        with self.assertRaises(swap.SwapError) as e:
            swap.load_texts(self.env)
        self.assertIn("has changed since it was stored", str(e.exception))
        f.write_bytes(original)
        swap.load_texts(self.env)
        # other texts over stored ones: refused without --replace
        rows, picked = self.rows()
        rs = json.loads(json.dumps(rows))
        p = swap.pick_source_rows(rs)
        for v in swap.VERSIONS:
            p[v]["system"][1] = p[v]["system"][1].replace("Harness", "Harnesz")
        src = self.tmp / "other.jsonl"
        src.write_text("".join(json.dumps(r) + "\n" for r in rs))
        with self.assertRaises(swap.SwapError) as e:
            swap.extract_all(self.env.texts_dir, self.author, source=src)
        self.assertIn("--replace", str(e.exception))
        swap.extract_all(self.env.texts_dir, self.author, source=src, replace=True)
        self.assertNotEqual(swap.load_texts(self.env)["STATIC"].sha256, self.manifest["texts"][0]["sha256"])


# ----------------------------------------------------------------------------------------------- argv

class ArgvTests(Base):
    def test_only_the_pair_is_added(self):
        """sw_n is exactly what run.prepare builds. sw_o and sw_w are that with --system-prompt <whole> added
        at the end. --append-system-prompt and the author's text stay where they were. In the scored asks
        the whole prompt holds the 2.1.316 worker folder of the ask's set, for both versions, so one set and
        one way send the same whole prompt on both versions."""
        quiet(swap.setup_dirs, self.env)
        texts, state = self.texts(), swap.load_state(self.env)
        units, info = swap.item_units(self.env)
        p = swap.build_pass_plan(self.env, self.env.inputs(), state, name="SW1", number=1, units=units[:6],
                                 fingerprint={"fingerprint": "-", "parts": {}}, texts=texts, items_info=info)
        ctx = run.Context(self.env.settings, self.env.inputs(), state, p, {"fingerprint": "-", "parts": {}})
        self.assertEqual({a["group"] for a in p["asks"]}, {"sw_o", "sw_w"})
        wholes: dict = {}
        for a in p["asks"]:
            ours, info_ = swap.prepare_ask(ctx, a, texts, "join2", None)
            plain = run.prepare(ctx, a, token=None)
            self.assertEqual(ours.env, plain.env)
            self.assertEqual(ours.config_dir, configdirs.config_dir(state, a["version"], a["options"]["config_set"]))
            i = plain.argv.index("--append-system-prompt")
            self.assertEqual(ours.argv.index("--append-system-prompt"), i)
            self.assertEqual(ours.argv[i + 1], self.author)
            whole = ours.argv[-1]
            self.assertEqual(ours.argv, plain.argv + ["--system-prompt", whole])
            set_path = configdirs.config_dir(state, OLD, a["fill_set"])
            self.assertEqual(a["fill_set"], a["options"]["config_set"])
            self.assertEqual(info_["filled_config_dir"], str(set_path))
            dyn = texts[swap.DYNAMIC_OF[a["group"]]].text.replace("{CONFIG_DIR}", str(set_path))
            self.assertEqual(whole, texts["STATIC"].text + "\n\n" + dyn)
            self.assertNotIn("{CONFIG_DIR}", whole)
            self.assertEqual(whole.count(str(set_path)), 1)
            if a["version"] == NEW:
                self.assertNotIn(str(ours.config_dir), whole)  # a 2.1.317 ask holds the 2.1.316 folder's path
            self.assertEqual(whole.count(swap.SENTENCES[swap.SENTENCES_OF[a["group"]]]), 1)
            self.assertEqual(info_["whole_sha256"], sha(whole))
            wholes.setdefault((a["fill_set"], a["group"]), {}).setdefault(a["version"], set()).add(whole)
        for key, by in wholes.items():  # one set, one way: the same whole prompt on both versions
            self.assertEqual(sorted(by), sorted(swap.VERSIONS), key)
            self.assertEqual(len(by[OLD] | by[NEW]), 1, key)
        # sw_n: the ask exactly as run.prepare builds it
        a = {**p["asks"][0], "group": "sw_n"}
        a.pop("fill_set")
        ours, info_ = swap.prepare_ask(ctx, a, texts, None, None)
        self.assertEqual(ours.argv, run.prepare(ctx, a, token=None).argv)
        self.assertNotIn("--system-prompt", ours.argv)
        self.assertEqual((info_["whole_sha256"], info_["filled_config_dir"]), (None, None))
        with self.assertRaises(swap.SwapError):
            swap.add_system_prompt(plain.argv + ["--system-prompt", "x"], self.author, "y")

    def test_four_structures_and_the_two_paths(self):
        """What each structure puts together, and the blocks Claude Code should cut it into (the stand-in's
        system_blocks, written after the code, agrees). {CONFIG_DIR} is the ask's own folder without a
        fill_set and the 2.1.316 worker folder of the set with one."""
        texts = self.texts()
        folder = Path("/Users/Shared/kq7/s/oz42")
        st = texts["STATIC"].text
        for g in ("sw_o", "sw_w"):
            dyn = texts[swap.DYNAMIC_OF[g]].text.replace("{CONFIG_DIR}", str(folder))
            for s, sep in (("join0", ""), ("join1", "\n"), ("join2", "\n\n"),
                           ("marker", "\n__SYSTEM_PROMPT_DYNAMIC_BOUNDARY__\n")):
                whole = swap.whole_prompt(texts, g, s, folder)
                self.assertEqual(whole, st + sep + dyn, s)
                blocks = swap.expected_blocks(whole, self.author)
                if s == "marker":
                    self.assertEqual(blocks, [st + "\n", "\n" + dyn + "\n\n" + self.author])
                else:
                    self.assertEqual(blocks, [whole + "\n\n" + self.author])
                self.assertEqual(swap.rebuild(blocks, s), whole + "\n\n" + self.author)
                self.assertEqual(NS["system_blocks"](whole, self.author, self.builtin[OLD], str(folder)),
                                 [swap.INTRO] + blocks)
        with self.assertRaises(swap.SwapError):
            swap.whole_prompt(texts, "sw_o", "join3", folder)
        state = {"config_root": "/r/c", "codes": {OLD: "oz55", NEW: "oz95"},
                 "sets": {"w1": {OLD: "oz31", NEW: "oz64"}}, "set_roots": {"w1": "/r/s"}}
        own = Path("/r/s/oz64")
        self.assertEqual(swap.filled_path(state, {"ask_id": "x"}, own), own)
        self.assertEqual(swap.filled_path(state, {"ask_id": "x", "fill_set": "w1"}, own), Path("/r/s/oz31"))
        with self.assertRaises(swap.SwapError):
            swap.filled_path(state, {"ask_id": "x", "fill_set": "w2"}, own)


# ---------------------------------------------------------------------------------------------- plans

class PlanTests(Base):
    def test_pass_plan_blocks_and_sets(self):
        """A pass on the real 24 items with the default settings: 96 asks, no sw_n, 8 blocks of 12, each with
        its three items once in each of the four cells, shuffled. Every ask of one item in one pass is in one
        set, and the three items of a block are in three sets. One seed makes one plan."""
        quiet(swap.setup_dirs, self.env)
        texts, state = self.texts(), swap.load_state(self.env)
        units, info = swap.item_units(self.env)
        self.assertEqual(len(units), 24)
        self.assertEqual(self.env.scored_groups, ("sw_o", "sw_w"))
        fp = {"fingerprint": "-", "parts": {}}

        def plan(number, sets=None):
            return swap.build_pass_plan(self.env, self.env.inputs(), state, name=f"SW{number}", number=number,
                                        units=units, fingerprint=fp, texts=texts, items_info=info, sets=sets)

        cells = [(v, g) for v in swap.VERSIONS for g in ("sw_o", "sw_w")]
        firsts = []
        for k in (1, 2, 3):
            p = plan(k)
            self.assertEqual(len(p["asks"]), 96)
            self.assertNotIn("sw_n", {a["group"] for a in p["asks"]})
            self.assertEqual(p["spec"]["seed"], REAL["group"]["seed"])
            self.assertEqual(p["spec"]["parallel"], self.parallel)
            blocks = {}
            for a in p["asks"]:
                self.assertEqual((a["mode"], a["effort"], a["options"]["remote_flags"]), ("stock_blocked", "high", "off"))
                self.assertEqual(set(a["options"]), {"remote_flags", "config_set"})
                self.assertEqual(a["fill_set"], a["options"]["config_set"])
                blocks.setdefault(a["block"], []).append(a)
            self.assertEqual(len(blocks), 8)
            self.assertEqual({len(x) for x in blocks.values()}, {12})
            mixed = 0
            for b, asks in blocks.items():
                per = {c: sorted(a["unit"] for a in asks if (a["version"], a["group"]) == c) for c in cells}
                self.assertEqual(len({tuple(x) for x in per.values()}), 1, f"pass {k} block {b}")
                self.assertEqual({len(x) for x in per.values()}, {3})
                set_of = {}
                for a in asks:
                    set_of.setdefault(a["unit"], set()).add(a["options"]["config_set"])
                self.assertEqual({len(x) for x in set_of.values()}, {1})  # one item, one set, all four cells
                self.assertEqual(sorted(x for v in set_of.values() for x in v), ["w1", "w2", "w3"])  # three sets
                order = [(a["version"], a["group"]) for a in sorted(asks, key=lambda a: a["order"])]
                mixed += order != sorted(order)
            self.assertGreater(mixed, 5)
            for c in cells:
                mine = [a for a in p["asks"] if (a["version"], a["group"]) == c]
                self.assertEqual(sorted(a["unit"] for a in mine), sorted(units))
                counts = {n: sum(1 for a in mine if a["options"]["config_set"] == n) for n in ("w1", "w2", "w3")}
                self.assertEqual(set(counts.values()), {8}, (k, c))
            self.assertEqual(plan(k)["asks"], p["asks"])  # made twice: the same plan
            firsts.append(p)
        self.assertNotEqual([a["options"]["config_set"] for a in firsts[0]["asks"]],
                            [a["options"]["config_set"] for a in firsts[1]["asks"]])
        # another seed, another plan
        first = firsts[0]
        self.reload(seed='"another-seed"')
        self.assertNotEqual(plan(1)["asks"], first["asks"])
        # five sets: the items take the sets in turn, 4 or 5 items in each set, still one set per item
        quiet(swap.setup_dirs, self.env, 5)
        state = swap.load_state(self.env)
        p = plan(1, sets=["w1", "w2", "w3", "w4", "w5"])
        set_of = {}
        for a in p["asks"]:
            set_of.setdefault(a["unit"], set()).add(a["options"]["config_set"])
        self.assertEqual({len(x) for x in set_of.values()}, {1})
        counts = [sum(1 for x in set_of.values() if x == {n}) for n in ("w1", "w2", "w3", "w4", "w5")]
        self.assertEqual((sum(counts), max(counts) - min(counts) <= 1), (24, True), counts)
        self.assertEqual(plan(1, sets=["w1", "w2", "w3", "w4", "w5"])["asks"], p["asks"])

    def test_item_list(self):
        """The ids may come with or without "item:". An id the item file does not have, or one listed twice,
        is refused."""
        units, info = swap.item_units(self.env)
        self.assertTrue(all(u.startswith("item:") for u in units))
        self.assertEqual(info["prefix_added"], 24)
        f = self.tmp / "items.json"
        for ids, err in ((["item:mmlupro-574", "mmlupro-1261"], None), (["mmlupro-574", "mmlupro-574"], swap.SwapError),
                         (["no-such-item"], items_mod.ItemsError)):
            f.write_text(json.dumps({"items": ids}))
            self.env.item_list = f
            if err is None:
                self.assertEqual(swap.item_units(self.env)[0], ["item:mmlupro-574", "item:mmlupro-1261"])
            else:
                with self.assertRaises(err):
                    swap.item_units(self.env)

    def test_group_settings(self):
        """scored_groups and stage1_passes: what is taken, and what is refused."""
        self.reload(scored_groups='["sw_w", "sw_o", "sw_n"]', stage1_passes=2)
        self.assertEqual((self.env.scored_groups, self.env.stage1_passes), (("sw_n", "sw_o", "sw_w"), 2))
        for key, value in (("scored_groups", '["sw_o", "sw_o"]'), ("scored_groups", "[]"),
                           ("scored_groups", '["sw_x"]'), ("stage1_passes", 4), ("stage1_passes", 0),
                           ("another_key", 1)):
            self.write_settings(**{key: value})
            with self.assertRaises(swap.SwapError, msg=key):
                swap.load_env(str(self.data / "设置.toml"))
        self.write_settings()
        env = swap.load_env(str(self.data / "设置.toml"))
        self.assertEqual((env.scored_groups, env.stage1_passes), (("sw_o", "sw_w"), None))
        g = "\n".join(x for x in (self.data / "设置.toml").read_text().splitlines() if not x.startswith("parallel"))
        (self.data / "设置.toml").write_text(g + "\n")
        self.assertEqual(swap.load_env(str(self.data / "设置.toml")).parallel, 2)  # the default


# ---------------------------------------------------------------------------------- probe checks

class ProbeJudgeTests(Base):
    """The four steps' checks on transcripts made up here."""

    def setUp(self):
        super().setUp()
        self.root = self.tmp / "made-up"
        root = self.tmp / "exp" / "s"
        self.folders = {OLD: root / "oz31", NEW: root / "oz64"}
        self.state = {"config_root": str(root), "codes": {OLD: "oz31", NEW: "oz64"},
                      "sets": {"w1": {OLD: "oz12", NEW: "oz47"}, "w2": {OLD: "oz23", NEW: "oz58"},
                               "w3": {OLD: "oz39", NEW: "oz81"}},
                      "set_roots": {n: str(root) for n in ("w1", "w2", "w3")}}

    def step1(self, tweaks=None, how="chars", name="P1"):
        tweaks = tweaks or {}
        rd = self.root / name
        rows = [("sw_n", None), *[("sw_o", s) for s in swap.STRUCTURES], ("sw_n", None)]
        views = []
        for k, (g, s) in enumerate(rows, 1):
            key = "sw_n2" if k == 6 else (s or "sw_n1")
            rec = self.fake_probe(rd, ask_id=f"a{k}", order=k, group=g, version=OLD, structure=s,
                                  config_dir=self.folders[OLD], tweak=tweaks.get(key), how=how)
            views.append(swap.request_view(rec, rd))
        return views

    def step2(self, tweaks=None, structure="join2", name="P2"):
        tweaks = tweaks or {}
        rd = self.root / name
        rows = [(OLD, "sw_w"), (NEW, "sw_n"), (NEW, "sw_o"), (NEW, "sw_w"), (NEW, "sw_n")]
        views = []
        for k, (v, g) in enumerate(rows, 1):
            key = f"{v} {g}" + (" 2" if k == 5 else "")
            rec = self.fake_probe(rd, ask_id=f"b{k}", order=k, group=g, version=v,
                                  structure=None if g == "sw_n" else structure, config_dir=self.folders[v],
                                  tweak=tweaks.get(key))
            views.append(swap.request_view(rec, rd))
        return views

    def step3(self, tweaks=None, structure="join2", name="P3", own_path_for=None):
        """sw_o then sw_w of 2.1.317 for every set, in its probe folder, filled with the set's path (or, for
        the set own_path_for, wrongly with the probe folder's own path). Returns (ask, view) pairs."""
        tweaks = tweaks or {}
        rd = self.root / name
        pairs, k = [], 0
        for n in ("w1", "w2", "w3"):
            for g in ("sw_o", "sw_w"):
                k += 1
                path = self.folders[NEW] if n == own_path_for else configdirs.config_dir(self.state, OLD, n)
                rec = self.fake_probe(rd, ask_id=f"c{k}", order=k, group=g, version=NEW, structure=structure,
                                      config_dir=self.folders[NEW], tweak=tweaks.get(f"{n} {g}"), fill_set=n,
                                      fill_path=path)
                pairs.append(({"ask_id": f"c{k}", "version": NEW, "group": g, "fill_set": n}, swap.request_view(rec, rd)))
        return pairs

    def test_step1(self):
        r = swap.judge_step1(self.step1())
        self.assertTrue(r["ok"], r.get("why"))
        self.assertEqual(r["decided"], "join2")
        self.assertEqual(r["passed"], ["join2"])
        self.assertEqual({s: x["minus_sw_n"] for s, x in r["structures"].items()},
                         {"join0": -2, "join1": -1, "join2": 0, "marker": 2})
        self.assertEqual({s: x["system_blocks"] for s, x in r["structures"].items()},
                         {"join0": 2, "join1": 2, "join2": 2, "marker": 3})
        self.assertEqual(r["structures"]["join2"]["sw_n_system_blocks"], 3)
        self.assertEqual({(x["cache_read_input_tokens"], x["cache_creation_input_tokens"])
                          for x in r["structures"].values()}, {(0, 0)})
        # counted in words, join1, join2 and marker read the same: join2 is taken, being first
        r = swap.judge_step1(self.step1(how="words", name="W"))
        self.assertEqual((r["ok"], r["decided"], r["passed"]), (True, "join2", ["join2", "marker", "join1"]))
        # in words with join2 off by one token: marker is taken
        r = swap.judge_step1(self.step1({"join2": {"tokens": 1}}, how="words", name="W2"))
        self.assertEqual((r["ok"], r["decided"], r["passed"]), (True, "marker", ["marker", "join1"]))
        # each change on its own makes join2 fail, and with it the step
        for what, tw in (("tokens", {"tokens": 1}), ("intro", {"intro": "You are a Claude agent, built on Anthropic's "
                                                                        "Claude Agent SDK."}),
                         ("tools", {"extra_tool": True}), ("system role message", {"blob": True})):
            r = swap.judge_step1(self.step1({"join2": tw}, name=f"T-{what}"))
            j = r["structures"]["join2"]
            self.assertFalse(j["ok"], what)
            self.assertFalse(r["ok"], what)
            self.assertIsNone(r["decided"])
            self.assertEqual((j["tokens_same"], j["first_block_same"], j["others_differ_in"]),
                             {"tokens": (False, True, []), "intro": (True, False, []),
                              "tools": (True, True, ["tools"]),
                              "system role message": (True, True, ["extra_messages"])}[what], what)
            self.assertIn("no structure passed", r["why"])
        # the two sw_n differ: the step stops although join2 would pass
        r = swap.judge_step1(self.step1({"sw_n2": {"tokens": 1}}, name="N"))
        self.assertFalse(r["ok"])
        self.assertTrue(r["structures"]["join2"]["ok"])
        self.assertIn("do not agree", r["why"])

    def test_step2(self):
        texts = self.texts()
        s1 = self.step1()
        r = swap.judge_step2(s1, self.step2(), "join2", texts, self.author)
        self.assertTrue(r["ok"], r.get("why"))
        self.assertEqual(r["6"]["sw_w_minus_sw_o"][OLD], r["6"]["sw_w_minus_sw_o"][NEW])
        self.assertEqual(r["6"]["sw_w_minus_sw_o"][OLD], len(swap.SENTENCES[NEW]) - len(swap.SENTENCES[OLD]))
        # each change on its own fails its own check, and only that one (model and effort are sent parameters
        # too, so they also fail the comparison of everything sent besides the system blocks)
        cases = {"tokens": ({f"{NEW} sw_w": {"tokens": 1}}, ["6_input_tokens"]),
                 "first block": ({f"{NEW} sw_o": {"intro": "You are a Claude agent, built on Anthropic's Claude Agent "
                                                          "SDK."}}, ["3_first_block"]),
                 "tools": ({f"{OLD} sw_w": {"extra_tool": True}}, ["5_other_parts"]),
                 "system role message": ({f"{NEW} sw_o": {"blob": True}}, ["5_other_parts"]),
                 "one character of the whole prompt": ({f"{NEW} sw_w": {"last_char": True}}, ["4_whole_prompt_sent"]),
                 "the two sw_n": ({f"{NEW} sw_n 2": {"tokens": 1}}, ["2_new_sw_n_agree"]),
                 "effort": ({f"{NEW} sw_o": {"effort": "medium"}}, ["1_answered_model_effort", "5_other_parts"]),
                 "model": ({f"{OLD} sw_w": {"model": "claude-fable-5-2"}}, ["1_answered_model_effort", "5_other_parts"])}
        for k, (what, (tw, failed)) in enumerate(cases.items()):
            r = swap.judge_step2(s1, self.step2(tw, name=f"Q{k}"), "join2", texts, self.author)
            self.assertFalse(r["ok"], what)
            self.assertEqual([c for c, x in r["checks"].items() if not x], failed, what)
        x = swap.judge_step2(s1, self.step2({f"{NEW} sw_w": {"last_char": True}}, name="Q9"), "join2", texts,
                             self.author)["4"][f"{NEW} sw_w"]
        self.assertEqual((x["argv_value_is_the_programs_whole_prompt"], x["rebuilt_equals_whole_prompt_two_newlines_author"],
                          x["blocks_as_expected"]), (True, False, False))
        self.assertIn("first difference", x["first_difference"])
        # with marker: the blocks are cut and put back at the marker line
        s1m = self.step1(how="chars", name="M1")
        s2m = self.step2(structure="marker", name="M2")
        r = swap.judge_step2(s1m, s2m, "marker", texts, self.author)
        self.assertTrue(r["checks"]["4_whole_prompt_sent"])
        self.assertEqual(r["4"][f"{NEW} sw_w"]["blocks_after_the_first"], 2)

    def test_step3(self):
        texts = self.texts()
        s2 = self.step2()
        r = swap.judge_step3(s2, self.step3(), "join2", texts, self.author, self.state)
        self.assertTrue(r["ok"], r)
        self.assertEqual(sorted(r["sets"]), ["w1", "w2", "w3"])
        for n, x in r["sets"].items():
            self.assertEqual(x["filled_config_dir"], str(configdirs.config_dir(self.state, OLD, n)))
            self.assertEqual(sorted(x["first_request_input_tokens"]), ["sw_o", "sw_w"])
            self.assertEqual(x["compared_with"], "b2")  # step 2's first sw_n in 2.1.317's probe folder
            self.assertEqual(x["sw_w_minus_sw_o"], x["step2_sw_w_minus_sw_o"])
        # each change on its own fails its own check in the one set it is in. An input token number one
        # off is not one of step 3's checks (step 4 compares it), so that set still passes
        cases = {"tokens": ({"w2 sw_w": {"tokens": 1}}, []),
                 "first block": ({"w2 sw_o": {"intro": "You are a Claude agent, built on Anthropic's Claude Agent "
                                                      "SDK."}}, ["sw_o 3_first_block"]),
                 "tools": ({"w2 sw_w": {"extra_tool": True}}, ["sw_w 5_other_parts"]),
                 "system role message": ({"w2 sw_o": {"blob": True}}, ["sw_o 5_other_parts"]),
                 "one character of the whole prompt": ({"w2 sw_w": {"last_char": True}}, ["sw_w 4_whole_prompt_sent"]),
                 "no answer": ({"w2 sw_o": {"no_answer": True}}, ["sw_o 1_answered_model_effort"]),
                 "effort": ({"w2 sw_w": {"effort": "medium"}}, ["sw_w 1_answered_model_effort", "sw_w 5_other_parts"])}
        for k, (what, (tw, failed)) in enumerate(cases.items()):
            r = swap.judge_step3(s2, self.step3(tw, name=f"R{k}"), "join2", texts, self.author, self.state)
            got = [f"{g} {c}" for g, x in r["sets"]["w2"]["probes"].items() for c, ok in x["checks"].items() if not ok]
            self.assertEqual(got, failed, what)
            self.assertEqual(r["ok"], not failed, what)
            self.assertTrue(r["sets"]["w1"]["ok"] and r["sets"]["w3"]["ok"], what)
        # filled with the probe folder's own path instead of the set's: the whole prompt check fails
        r = swap.judge_step3(s2, self.step3(name="R-own", own_path_for="w3"), "join2", texts, self.author, self.state)
        self.assertEqual((r["ok"], r["sets"]["w3"]["ok"]), (False, False))
        self.assertFalse(r["sets"]["w3"]["probes"]["sw_o"]["checks"]["4_whole_prompt_sent"])
        # a set with a probe not recorded is incomplete, and is not judged
        pairs = self.step3(name="R-missing")
        pairs[3] = (pairs[3][0], None)
        r = swap.judge_step3(s2, pairs, "join2", texts, self.author, self.state)
        self.assertTrue(r["sets"]["w2"].get("incomplete"))

    def test_step4(self):
        rd = self.root / "P4"
        step3 = {"w1": {"ok": True, "first_request_input_tokens": {"sw_o": 900, "sw_w": 1000}}}
        k = 0

        def pair_of(v, tweak=None, sw_w_tokens=None):
            nonlocal k
            out = []
            for i, g in enumerate(("sw_n", swap.OWN_GROUP[v])):
                k += 1
                a = {"ask_id": f"d{k}", "version": v, "group": g, "options": {"config_set": "w1"}}
                rec = self.fake_probe(rd, ask_id=a["ask_id"], order=k, group=g, version=v,
                                      structure=None if g == "sw_n" else "join2", config_dir=self.folders[v],
                                      tweak=tweak if i == 1 else None, kept=False, fill_set="w1",
                                      fill_path=configdirs.config_dir(self.state, OLD, "w1"))
                out.append((a, rec))
            return out

        # 2.1.316: sw_n and sw_o with equal tokens pass. One token off, no answer, or the wrong order fail
        for tweak, ok in ((None, True), ({"tokens": 1}, False), ({"no_answer": True}, False)):
            pairs = pair_of(OLD, tweak)
            self.assertEqual(swap.judge_step4(pairs, step3)["ok"], ok, tweak)
            self.assertFalse(swap.judge_step4(list(reversed(pairs)), step3)["ok"])
        # 2.1.317: sw_w's tokens are compared with step 3's sw_w of the same set
        pairs = pair_of(NEW)
        own = swap.extract.first_request_input_tokens(pairs[1][1])
        for s3_tokens, ok in ((own, True), (own + 1, False)):
            s3 = {"w1": {"ok": True, "first_request_input_tokens": {"sw_o": 1, "sw_w": s3_tokens}}}
            r = swap.judge_step4(pairs, s3)
            self.assertEqual((r["ok"], r["step3_sw_w_tokens"]), (ok, s3_tokens))
        self.assertFalse(swap.judge_step4(pairs, {})["ok"])  # no step 3 for the set
        self.assertFalse(swap.judge_step4(pairs, {"w1": {"ok": False, "first_request_input_tokens": {"sw_w": own}}})["ok"])
        self.assertFalse(swap.judge_step4(pair_of(NEW, {"no_answer": True}),
                                          {"w1": {"ok": True, "first_request_input_tokens": {"sw_w": own}}})["ok"])


# ----------------------------------------------------------------------------------------------- send

class SendTests(Base):
    def test_probes_then_trial(self):
        out = self.prepare()
        calls = self.calls()
        kept = [c for c in calls if c["kept"]]
        self.assertEqual(len(kept), 6 + 5 + 2 * self.sets)
        self.assertEqual(len(calls), 6 + 5 + 2 * self.sets + 2 * 2 * self.sets)
        state = swap.load_state(self.env)
        probe_dirs = {str(configdirs.config_dir(state, v)) for v in swap.VERSIONS}
        self.assertEqual({c["cfg"] for c in kept}, probe_dirs)  # transcripts only in the probe folders
        self.assertFalse({c["cfg"] for c in calls if not c["kept"]} & probe_dirs)
        self.assertEqual({c["cfg"] for c in kept[11:]}, {str(configdirs.config_dir(state, NEW))})  # step 3
        check = json.loads(self.env.probe_check_file.read_text())
        self.assertEqual(check["step1"]["decided"], "join2")
        self.assertEqual({s: x["minus_sw_n"] for s, x in check["step1"]["structures"].items()},
                         {"join0": -2, "join1": -1, "join2": 0, "marker": 2})
        self.assertTrue(check["step2"]["ok"])
        self.assertEqual((check["sets_missing"], check["folders_missing"], check["all_ok"]), ([], [], True))
        self.assertEqual(sorted(check["step3"]), ["w1", "w2", "w3"])
        for n, r in check["step3"].items():
            self.assertTrue(r["ok"], r)
            self.assertEqual(r["filled_config_dir"], str(configdirs.config_dir(state, OLD, n)))
            self.assertTrue(all(isinstance(t, int) for t in r["first_request_input_tokens"].values()))
        self.assertEqual(len(check["step4"]), 6)
        self.assertTrue(all(r["ok"] for r in check["step4"].values()))
        for key, r in check["step4"].items():
            if r["version"] == NEW:
                self.assertEqual(r["first_request_input_tokens"][1], r["step3_sw_w_tokens"])
        self.assertIn("all four probe steps have passed", out)
        # running probes again sends nothing
        n0 = len(self.calls())
        rc, out = quiet(swap.run_probes, self.env, self.args())
        self.assertEqual((rc, len(self.calls())), (0, n0), out)
        # a small batch: 2 items in the four cells. The first call stops after 5 asks, the second does the rest
        rc, out = quiet(swap.cmd_send, self.env, self.args(trial=2, stop_after=5))
        self.assertEqual(rc, 2, out)
        self.assertEqual(len(self.calls()) - n0, 5)
        rc, out = quiet(swap.cmd_send, self.env, self.args(trial=2))
        self.assertEqual(rc, 0, out)
        rc, out = quiet(swap.cmd_send, self.env, self.args(trial=2))  # complete: nothing is sent again
        self.assertEqual(rc, 0, out)
        self.assertEqual(len(self.calls()) - n0, 8)
        rep = self.runcheck_ok("SWS")
        self.assertEqual((rep["records"], len(rep["calls"])), (8, 2))
        self.assertEqual(self.violations(), [])
        texts = self.texts()
        wholes: dict = {}
        records = grade.load_records(self.env.run_dir("SWS"))
        self.assertEqual({r["group"] for r in records}, {"sw_o", "sw_w"})
        for r in records:
            self.assertEqual(r["mode"], "stock_blocked")
            sw = r["swap"]
            self.assertEqual((sw["group"], sw["structure"], sw["config_dir"]), (r["group"], "join2", r["config_dir"]))
            self.assertEqual(r["config_dir"], str(configdirs.config_dir(state, r["version"], sw["set"])))
            self.assertEqual((r["options"]["config_set"], sw["fill_set"], sw["fill"]), (sw["set"], sw["set"], "set"))
            self.assertEqual(sw["folder"], f"{sw['set']}/{r['version']}")
            self.assertEqual(sw["filled_config_dir"], str(configdirs.config_dir(state, OLD, sw["set"])))
            self.assertEqual(r["argv"].index("--append-system-prompt") + 1, r["argv"].index(self.author))
            whole = swap.whole_prompt(texts, r["group"], "join2", sw["filled_config_dir"])
            self.assertEqual(r["argv"][-2:], ["--system-prompt", whole])
            self.assertEqual((sw["whole_sha256"], sw["whole_chars"]), (sha(whole), len(whole)))
            self.assertEqual(r["parallel"], self.parallel)
            wholes.setdefault((r["unit"], r["group"]), set()).add((sw["set"], sw["whole_sha256"]))
        self.assertEqual({len(x) for x in wholes.values()}, {1})  # one item, one way: one set, one whole prompt
        everything = "\n".join(p.read_bytes().decode("utf-8", "replace") for p in self.env.data.rglob("*") if p.is_file())
        self.assertNotIn(TOKEN, everything)
        rc, out = quiet(swap.cmd_status, self.env, self.args())
        self.assertIn("send may go: True", out)
        self.assertNotIn("<answer>", out)

    def test_another_structure_taken_and_the_settings_follow(self):
        """If the server joined blocks with nothing between them, only join0 would give sw_n's input tokens:
        step 1 takes it. The settings name join2, so probes stops before step 2 and says what to write. With
        join0 in the settings, step 1 is not sent again and the other three steps pass."""
        quiet(swap.cmd_setup_dirs, self.env, self.args())
        self.ctl("server_join", "")
        rc, out = quiet(swap.run_probes, self.env, self.args())
        self.assertEqual(rc, 1, out)
        self.assertIn('structure = "join0"', out)
        self.assertEqual(len(self.calls()), 6)
        check = json.loads(self.env.probe_check_file.read_text())
        self.assertEqual((check["step1"]["decided"], check["step1"]["passed"], check["steps_1_and_2_ok"]),
                         ("join0", ["join0"], False))
        with self.assertRaises(swap.SwapError) as e:
            quiet(swap.cmd_send, self.env, self.args(trial=1))
        self.assertIn("structure", str(e.exception))
        self.reload(structure='"join0"')
        rc, out = quiet(swap.run_probes, self.env, self.args())
        self.assertEqual(rc, 0, out)
        self.assertEqual(len(self.calls()), 6 + 5 + 6 + 12)
        check = json.loads(self.env.probe_check_file.read_text())
        self.assertEqual((check["step2"]["structure"], check["all_ok"]), ("join0", True))

    def test_step1_fails_and_is_sent_again(self):
        """No structure gives sw_n's input tokens when the server is taken to join blocks with three
        newlines: step 1 stops and nothing more is sent. probes again sends step 1 once more."""
        quiet(swap.cmd_setup_dirs, self.env, self.args())
        self.ctl("server_join", "\n\n\n")
        rc, out = quiet(swap.run_probes, self.env, self.args())
        self.assertEqual(rc, 1, out)
        self.assertIn("no structure passed", out)
        self.assertEqual(len(self.calls()), 6)
        self.ctl("server_join")
        rc, out = quiet(swap.run_probes, self.env, self.args())
        self.assertEqual(rc, 0, out)
        self.assertEqual(len(self.calls()), 6 + 6 + 5 + 6 + 12)
        self.assertEqual(sorted(p.name for p in self.env.plans.glob("SWP1_*")), ["SWP1_1.json", "SWP1_2.json"])

    def test_one_folder_never_two_asks_one_set_two_versions_at_once(self):
        quiet(swap.setup_dirs, self.env)
        texts = self.texts()
        self.ctl("sleep", "0.5")
        rows = [{"version": v, "mode": "stock_blocked", "unit": swap.PROBE_UNIT, "warmup": True,
                 "options": {"config_set": "w1"}, "label": "x"} for v in (OLD, OLD, NEW)]
        p = swap.explicit_plan(self.env, "SWX_1", rows, ["sw_n"] * 3, [None] * 3, texts, purpose="test")
        out = swap.send_once(self.env, p, texts, parallel=5)
        self.assertFalse(out["aborted"], out)
        spans = sorted(self.spans(self.calls()))
        self.assertEqual(len(spans), 3)
        old_spans = [x for x in spans if x[3] == OLD]
        self.assertEqual(old_spans[0][2], old_spans[1][2])
        self.assertLessEqual(old_spans[0][1], old_spans[1][0])  # one folder: one after the other
        new_span = next(x for x in spans if x[3] == NEW)
        self.assertTrue(old_spans[1][0] < new_span[1] and new_span[0] < old_spans[1][1])  # two folders of w1 at once
        self.assertEqual(self.violations(), [])

    def test_full_send_two_passes_then_grade(self):
        """Two passes on the 24 items (192 asks), 2 at once in 6 folders, one item trying a tool. Then the
        records go through runcheck and grade.py unchanged."""
        self.reload(passes=2)
        self.prepare()
        units, _ = swap.item_units(self.env)
        self.ctl("tool_shas", self.env.inputs().unit(units[0]).text_sha256)
        self.ctl("sleep", "0.05")
        n0 = len(self.calls())
        t0 = time.time()
        rc, out = quiet(swap.cmd_send, self.env, self.args())
        self.assertEqual(rc, 0, out[-2000:])
        took = time.time() - t0
        self.assertEqual(self.violations(), [])
        records = []
        for n in ("SW1", "SW2"):
            self.runcheck_ok(n)
            records += grade.load_records(self.env.run_dir(n))
        self.assertEqual(len(records), 192)
        self.assertFalse((self.env.plans / "SW1r.json").exists())
        calls = self.calls()[n0:]
        spans = self.spans(calls)
        most = max(sum(1 for s, e, _, _ in spans if s <= t < e) for t, _, _, _ in spans)
        self.assertEqual(most, self.parallel)
        state = swap.load_state(self.env)
        pair = {str(configdirs.config_dir(state, v, n)): n for n in ("w1", "w2", "w3") for v in swap.VERSIONS}
        together = sum(1 for a in spans for b in spans if a is not b and a[2] != b[2] and pair[a[2]] == pair[b[2]]
                       and a[0] < b[1] and b[0] < a[1])
        set_of: dict = {}
        for r in records:
            self.assertEqual(r["config_dir"], r["swap"]["config_dir"])
            self.assertEqual(pair[r["config_dir"]], r["options"]["config_set"])
            self.assertEqual(r["swap"]["filled_config_dir"], str(configdirs.config_dir(state, OLD, r["swap"]["set"])))
            set_of.setdefault((r["pass"], r["unit"]), set()).add(r["swap"]["set"])
        self.assertEqual({len(x) for x in set_of.values()}, {1})  # one item in one pass: one set
        for k in (1, 2):
            for v in swap.VERSIONS:
                for g in ("sw_o", "sw_w"):
                    mine = [r for r in records if r["pass"] == k and r["version"] == v and r["group"] == g]
                    self.assertEqual(len(mine), 24)
                    self.assertEqual({sum(1 for r in mine if r["options"]["config_set"] == n) for n in ("w1", "w2", "w3")},
                                     {8})
        author_checks, claudecode = grade.import_author_graders(self.env.settings.author_repo)
        rows = grade.grade_records(records, self.env.inputs(), author_checks, claudecode)
        self.assertEqual({r["outcome"] for r in rows}, {"scored"})
        self.assertEqual({r["group"] for r in rows}, {"sw_o", "sw_w"})
        tried = [r for r in rows if r.get("tool_calls")]
        self.assertEqual(len(tried), 8)  # 1 item x 4 cells x 2 passes, refused by the hook, still scored
        self.assertTrue(all(r["config_dir"] for r in rows))
        print(f"\n  full send: 192 asks in {took:.0f} s, at most {most} at once, {together} pairs of overlapping asks "
              "in the two folders of one set")

    def test_send_some_passes_only(self):
        """send --passes A-B sends passes A to B and their resends only. A pass already complete is not sent
        again. A wrong range is refused before anything else."""
        self.prepare()
        self.small_pass_plans(3, 4)  # 12 asks per pass
        n0 = len(self.calls())
        rc, out = quiet(swap.cmd_send, self.env, self.args(passes="2-3"))
        self.assertEqual(rc, 0, out[-2000:])
        self.assertIn("note: passes before 2 that are not complete: [1]", out)
        self.assertEqual(len(self.calls()) - n0, 24)
        have = {n: len(grade.load_records(self.env.run_dir(n))) if (self.env.run_dir(n) / "asks").is_dir() else 0
                for n in ("SW1", "SW2", "SW3", "SW4")}
        self.assertEqual(have, {"SW1": 0, "SW2": 12, "SW3": 12, "SW4": 0})
        rc, out = quiet(swap.cmd_send, self.env, self.args(passes="2"))
        self.assertEqual((rc, len(self.calls()) - n0), (0, 24), out)
        rc, out = quiet(swap.cmd_send, self.env, self.args(passes="1-4"))
        self.assertEqual((rc, len(self.calls()) - n0), (0, 48), out)
        for n in ("SW1", "SW2", "SW3", "SW4"):
            self.runcheck_ok(n)
        for bad in ("0-2", "3-2", "5", "1-5", "a", "2-"):
            with self.assertRaises(swap.SwapError, msg=bad):
                swap.cmd_send(self.env, self.args(passes=bad))
        self.assertEqual(len(self.calls()) - n0, 48)

    def test_stop_at_the_line_from_the_settings(self):
        self.assertEqual(self.env.weekly_line, LINE)
        self.assertEqual(swap.load_env(str(REAL_SETTINGS)).weekly_line, LINE)
        self.prepare()
        n0 = len(self.calls())
        self.ctl("util", f"{LINE - 0.01:.4f}")
        self.ctl("util_after", f"{n0 + 7} {LINE}")
        self.ctl("sleep", "0.2")
        rc, out = quiet(swap.cmd_send, self.env, self.args(trial=6))
        self.assertEqual(rc, 2, out)
        self.assertIn("small batch SWS: line", out)
        self.assertIn(f"reached the plan's line {LINE}", out)
        calls = self.calls()[n0:]
        # Nothing was started after the runner saw the reading, by its own events in the order it wrote them. The
        # stand-in's own clock is not used, because a process started just before shows a later start.
        events = [json.loads(x) for x in (self.env.run_dir("SWS") / "events.jsonl").read_text().splitlines()]
        k = next(i for i, e in enumerate(events) if e["event"] == "weekly_line_reached")
        self.assertEqual([e for e in events[k:] if e["event"] == "ask_start"], [])
        self.assertEqual(sum(1 for e in events if e["event"] == "ask_start"), len(calls))
        self.assertLessEqual(len(calls), 7 + self.parallel)
        sent_before = len(calls)
        for fn in (swap.cmd_send, swap.run_probes):  # before the weekly reset: refused, nothing sent
            with self.assertRaises(swap.SwapError) as e:
                quiet(fn, self.env, self.args(trial=6))
            self.assertIn("--after-reset", str(e.exception))
        self.assertEqual(len(self.calls()) - n0, sent_before)
        self.ctl("util_after")
        self.ctl("util", "0.02")
        rc, out = quiet(swap.cmd_send, self.env, self.args(trial=6, after_reset=True))
        self.assertEqual(rc, 0, out)
        self.assertEqual(len(self.calls()) - n0, 24)
        self.runcheck_ok("SWS")
        self.assertEqual(self.violations(), [])

    def test_outage_waits_then_resends(self):
        """Eight failed asks in a row: the formal waits and a probe. The asks that never reached the model are
        asked once more after the pass. Nothing else is sent twice."""
        self.prepare()
        self.small_pass_plans(3, 3)  # 12 asks per pass
        n0 = len(self.calls())
        self.ctl("fail", "1")
        rc, out = quiet(swap.cmd_send, self.env, self.args())
        self.assertEqual(rc, 0, out[-2000:])
        self.assertEqual(self.slept, [5 * 60])
        calls = self.calls()[n0:]
        # 8 failed asks (one at a time: the call's first ask runs alone until one answers), 1 probe, the 4 left
        # of pass 1, the 8 resent, then passes 2 and 3
        self.assertEqual(len(calls), 8 + 1 + 4 + 8 + 12 + 12)
        resend = plan_mod.load(self.env.plans / "SW1r.json")
        self.assertEqual(len(resend["asks"]), 8)
        self.assertTrue(all(a["resend_of"]["plan"] == "SW1" for a in resend["asks"]))
        self.assertTrue(all(a["options"]["config_set"] and a["fill_set"] == a["options"]["config_set"]
                            for a in resend["asks"]))
        failed = [a["resend_of"]["ask_id"] for a in resend["asks"]]
        self.runcheck_ok("SW1", failed_without_output=failed)
        for n in ("SW1r", "SW2", "SW3"):
            self.runcheck_ok(n)
        state = swap.load_state(self.env)
        for r in grade.load_records(self.env.run_dir("SW1r")):
            self.assertEqual(r["swap"]["filled_config_dir"], str(configdirs.config_dir(state, OLD, r["swap"]["set"])))
        health = sorted(p.name for p in self.env.settings.raw_dir.glob("SWH_*"))
        self.assertEqual(health, ["SWH_001"])
        rec = grade.load_records(self.env.run_dir("SWH_001"))[0]
        self.assertEqual((rec["mode"], rec["effort"], rec["unit"], rec["status"], rec["version"], rec["swap"]),
                         ("author", "low", "probe:author-ok", "done", NEW, None))
        self.assertEqual(rec["config_dir"], str(configdirs.config_dir(state, NEW)))
        st = json.loads(self.env.state_file.read_text())
        self.assertTrue(st.get("resend2_none") and st.get("resend3_none"))
        self.assertEqual(self.violations(), [])

    def test_usage_limit(self):
        self.prepare()
        self.ctl("limit", "1")
        self.ctl("util", "0.92")  # at or above 0.90, below the line
        rc, out = quiet(swap.cmd_send, self.env, self.args(trial=2))
        self.assertEqual(rc, 2, out)
        self.assertIn("usage_limit", out)
        self.ctl("util", "0.30")  # the same message with a low reading is not believed: it stops for a person
        with self.assertRaises(swap.SwapError) as e:
            quiet(swap.cmd_send, self.env, self.args(trial=2))
        self.assertIn("usage-limit", str(e.exception))


# --------------------------------------------------------------------------------------------- guards

class GuardTests(Base):
    def test_folders_like_the_formal_ones(self):
        rep, _ = quiet(swap.setup_dirs, self.env)
        state = swap.load_state(self.env)
        main = json.loads(self.formal_state.read_text())
        self.assertEqual((state["user_id"], state["machine_id"]), (main["user_id"], main["machine_id"]))
        paths = [r["folder"] for r in rep["folders"]]
        self.assertEqual(len(paths), 2 + 2 * self.sets)
        self.assertEqual(len(set(paths)), len(paths))
        self.assertEqual({len(p) for p in paths}, {len(str(Path(main["config_root"]) / "oz55"))})
        for p in paths:
            name = Path(p).name
            self.assertTrue(name.startswith("oz") and name[2:] not in ("16", "17"), name)
            self.assertEqual(Path(p).parent, self.tmp / "exp" / "s")
            self.assertEqual(oct(os.stat(p).st_mode & 0o777), "0o700")
            self.assertEqual(json.loads((Path(p) / ".claude.json").read_text()), {"userID": "a" * 64, "machineID": "b" * 64})
        self.assertEqual(sorted(state["codes"]), sorted(swap.VERSIONS))
        self.assertEqual(swap.worker_sets(state), ["w1", "w2", "w3"])
        self.assertTrue(all(sorted(state["sets"][n]) == sorted(swap.VERSIONS) for n in ("w1", "w2", "w3")))
        self.assertEqual(set(state["set_remote_flags"].values()), {"off"})
        before = self.env.settings.config_dirs_file.read_text()
        quiet(swap.setup_dirs, self.env)
        self.assertEqual(self.env.settings.config_dirs_file.read_text(), before)
        quiet(swap.setup_dirs, self.env, 4)
        after = swap.load_state(self.env)
        self.assertEqual({k: after["sets"][k] for k in ("w1", "w2", "w3")}, {k: state["sets"][k] for k in ("w1", "w2", "w3")})
        self.assertEqual(after["codes"], state["codes"])
        self.assertIn("w4", after["sets"])

    def test_probes_and_send_refuse_and_say_why(self):
        quiet(swap.cmd_setup_dirs, self.env, self.args())
        # send before any probe
        with self.assertRaises(swap.SwapError) as e:
            quiet(swap.cmd_send, self.env, self.args(trial=1))
        self.assertIn("run probes first", str(e.exception))
        self.assertEqual(self.calls(), [])
        # another program sending: both refuse. --alongside-other-sends lets this guard pass
        self.env.find_other_sends = lambda template: ["pid 1: python -B driver.py --settings x"]
        for fn in (swap.run_probes, swap.cmd_send):
            with self.assertRaises(swap.SwapError) as e:
                quiet(fn, self.env, self.args(trial=1))
            self.assertIn("another program is sending", str(e.exception))
        swap.guards(self.env, self.args(alongside_other_sends=True), send=False)
        self.env.find_other_sends = lambda template: []
        # this group's last weekly reading at the line
        f = self.env.settings.raw_dir / "SWS" / "events.jsonl"
        f.parent.mkdir(parents=True)
        f.write_text(json.dumps({"time": "2099-01-01T00:00:00.000+00:00", "event": "ask", "ask_id": "x",
                                 "weekly_utilization": LINE}) + "\n")
        for fn in (swap.run_probes, swap.cmd_send):
            with self.assertRaises(swap.SwapError) as e:
                quiet(fn, self.env, self.args(trial=1))
            self.assertIn("--after-reset", str(e.exception))
        swap.guards(self.env, self.args(after_reset=True), send=False)
        shutil.rmtree(f.parent)
        self.assertEqual(self.calls(), [])
        # allow_send = false
        self.reload(allow_send="false")
        for fn in (swap.run_probes, swap.cmd_send):
            with self.assertRaises(swap.SwapError) as e:
                quiet(fn, self.env, self.args(trial=1))
            self.assertIn("allow_send = false", str(e.exception))
        self.reload()
        # after the probes: send may go
        rc, out = quiet(swap.run_probes, self.env, self.args())
        self.assertEqual(rc, 0, out)
        n0 = len(self.calls())
        swap.guards(self.env, self.args(), send=True)
        # other texts than the ones the probes were sent with
        rows, _ = swap.read_source(swap.SOURCE)
        rs = json.loads(json.dumps(rows))
        p = swap.pick_source_rows(rs)
        for v in swap.VERSIONS:
            p[v]["system"][1] = p[v]["system"][1].replace("Harness", "Harnesz")
        src = self.tmp / "other.jsonl"
        src.write_text("".join(json.dumps(r) + "\n" for r in rs))
        swap.extract_all(self.env.texts_dir, self.author, source=src, replace=True)
        with self.assertRaises(swap.SwapError) as e:
            swap.guards(self.env, self.args(), send=True)
        self.assertIn("step 1 has not passed", str(e.exception))
        swap.extract_all(self.env.texts_dir, self.author, replace=True)  # the texts as they were: the probes count again
        swap.guards(self.env, self.args(), send=True)
        # another structure in the settings
        self.reload(structure='"join1"')
        with self.assertRaises(swap.SwapError) as e:
            swap.guards(self.env, self.args(), send=True)
        self.assertIn("the settings name join1", str(e.exception))
        self.reload()
        swap.guards(self.env, self.args(), send=True)
        # a set more: no step 3 for it, and its two folders have no warm-up yet
        quiet(swap.setup_dirs, self.env, 4)
        self.reload(sets=4)
        with self.assertRaises(swap.SwapError) as e:
            swap.guards(self.env, self.args(), send=True)
        self.assertIn("sets without step 3 passed", str(e.exception))
        self.assertIn("['w4']", str(e.exception))
        # step 3 for w4 passed (sent here by hand), the warm-ups not yet
        texts, state = self.texts(), swap.load_state(self.env)
        fp = swap.current_fingerprint(self.env, texts)["fingerprint"]
        s1 = swap.step1_state(self.env, texts, fp)
        s2 = swap.step2_state(self.env, texts, fp, s1)
        p3 = swap.step3_plan(self.env, texts, ["w4"], s2.plan["name"])
        self.assertEqual(quiet(swap._send_step, self.env, p3, texts, 1, self.args())[0], "complete")
        with self.assertRaises(swap.SwapError) as e:
            swap.guards(self.env, self.args(), send=True)
        self.assertIn(f"['w4/{OLD}', 'w4/{NEW}']", str(e.exception))
        rc, out = quiet(swap.run_probes, self.env, self.args())  # only the two new folders are warmed up
        self.assertEqual(rc, 0, out)
        self.assertEqual(len(self.calls()) - n0, 2 + 4)
        swap.guards(self.env, self.args(), send=True)

    def test_other_sends_seen_by_ps(self):
        """Command lines that read like 再验少想's driver.py or 全部发.sh are seen, and this process is not."""
        self.assertEqual(swap._vis("全部发.sh"), "M-eM^EM-(M-iM^CM-(M-eM^OM^Q.sh")
        ps = [subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)", "driver.py", "--settings", "x"]),
              subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)", "全部发.sh"])]
        try:
            time.sleep(0.3)
            hits = swap.other_sends(self.env.settings.binary_template)
            for p in ps:
                self.assertTrue(any(h.startswith(f"pid {p.pid}:") for h in hits), hits)
            self.assertFalse(any(h.startswith(f"pid {os.getpid()}:") for h in hits))
            self.env.find_other_sends = swap.other_sends
            with self.assertRaises(swap.SwapError) as e:
                swap.guards(self.env, self.args(), send=False)
            self.assertIn("another program is sending", str(e.exception))
        finally:
            for p in ps:
                p.kill()
                p.wait()

    def test_real_settings_refuse_to_send(self):
        env = swap.load_env(str(REAL_SETTINGS))
        self.assertFalse(env.settings.allow_send)
        self.assertEqual((env.weekly_line, env.parallel, env.sets, env.structure, env.passes, env.seed),
                         (0.95, 2, 3, "join2", 12, "swap-20261114"))
        self.assertEqual((env.scored_groups, env.stage1_passes), (("sw_o", "sw_w"), 6))
        self.assertEqual(REAL["group"]["scored_groups"], ["sw_o", "sw_w"])
        self.assertEqual(env.item_list, swap.PROJECT / "程序" / "再验少想" / "items_think_more_24.json")
        self.assertEqual(env.settings.config_root, Path("/Users/Shared/kq7/s"))
        d = swap.PROJECT / "本机数据" / "对调两句话组"
        self.assertEqual((env.settings.config_dirs_file, env.settings.raw_dir, env.settings.lock_dir),
                         (d / "配置文件夹.json", d / "原始记录", d / "locks"))
        recheck = tomllib.loads((swap.PROJECT / "本机数据" / "再验少想" / "设置.toml").read_text(encoding="utf-8"))
        for part in ("env", "login", "scan"):
            self.assertEqual(REAL[part], recheck[part], part)
        own = {"config_dirs_file", "raw_dir", "lock_dir", "config_root", "raw_mirror_dir"}
        self.assertEqual({k: v for k, v in REAL["paths"].items() if k not in own},
                         {k: v for k, v in recheck["paths"].items() if k not in own})
        for fn in (swap.cmd_send, swap.run_probes):
            with self.assertRaises(swap.SwapError) as e:
                fn(env, self.args())
            self.assertIn("allow_send = false", str(e.exception))

    def test_compare_with_the_real_settings(self):
        """The print-only side by side command with the real settings: sw_n differs from main's ask only in
        the config folder. sw_o and sw_w also in the one pair added at the end. The pair
        --append-system-prompt <the author's text> stays in place. One item takes one set on both versions,
        and the two versions' whole prompts of one way are the same."""
        env = swap.load_env(str(REAL_SETTINGS))
        out_file = self.tmp / "compare.json"
        rc, text = quiet(swap.cmd_compare, env, self.args(out=str(out_file)))
        self.assertEqual(rc, 0)
        doc = json.loads(out_file.read_text())
        self.assertEqual([d["version"] for d in doc["versions"]], list(swap.VERSIONS))
        self.assertTrue(doc["same_set_same_whole_prompts"])
        for d in doc["versions"]:
            self.assertEqual(d["differ_by_way"], d["expected"], d["version"])
            self.assertTrue(d["append_pair_unchanged"])
            n = d["main_argv_items"]
            rows = {w: (m, v) for w, m, v in d["rows"]}
            self.assertEqual(rows[f"命令 第{n}项"][0], "（没有这一项）")
            self.assertEqual(rows[f"命令 第{n}项"][1]["sw_o"], "--system-prompt")
            self.assertEqual(rows[f"命令 第{n}项"][1]["sw_n"], "（没有这一项）")
        self.assertNotIn("注意：", text)
        self.assertNotIn(self.author, text)
        self.assertNotIn(TOKEN, text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
