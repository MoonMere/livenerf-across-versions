"""The ways an ask can be run, and how each Claude Code way turns into argv and environment.

Five ways start one version's Claude Code (MODES):

    author          the LiveNerf author's harness: his two sentences replace the built-in system prompt,
                    no tools, his flags and his four environment variables, JSON output
    stock_notools   the version's own system prompt with the author's two sentences appended; tools,
                    the built-in Skill list and MCP switched off (the mode for the 39-version batch)
    stock           the version's own system prompt with the two sentences appended, everything else
                    as shipped; tools stay, so the permission mode is pinned and only probes may be sent
    stock_blocked   (trial layer 7) mode stock plus one flag, --settings with BLOCK_SETTINGS: a PreToolUse
                    hook that matches every tool and exits 2, so the model gets the same first request as
                    in mode stock (tool list and tool descriptions included) but every tool call it makes
                    is refused before it runs and the refusal is handed back to it as the tool's error.
                    Like stock it pins the permission mode. Unlike stock it may send items: trial layer 7
                    sent 197 probes on all 39 versions, every one of the 99 tool calls was refused by the
                    hook and none ran, and 2026-11-11 the main conversation narrowed plan rule 10 (tools
                    kept: probes only) to the modes without the block, i.e. stock
    low_effort      stock_notools one effort step lower than the plan's effort (positive control)

One way starts no Claude Code at all (API_MODE, since trial layer 6; checklist G1):

    api             the runner itself calls the Messages API with a copy of the whole request one version
                    sent in mode author (api.py builds it from a template file). The ask's "version" is
                    the version whose request was copied. No argv, no environment, no config folder.

ALL_MODES holds all six. Desktop runs are not part of this program.
"""

import json
from dataclasses import dataclass, field

MODEL = "claude-opus-5-5"  # checklist B6: always explicit
FABLE = "claude-fable-5-2"
# The only models an ask may name. Every ask uses MODEL unless a plan names the other one: a probe-only
# plan for one ask (trial layer 2: Fable 5.2 probes on 2.1.321, 2.1.322 and one older version), or,
# since trial layer 6, a shuffled plan for all its asks, items included (the Fable 5.2 comparison).
MODEL_CHOICES = (MODEL, FABLE)
# The oldest version that knows a model. An item may name a model only on versions from this one on:
# 2.1.319 sent a Fable ask with another system prompt and output cap (trial layer 2, section 9), and the
# official page says Fable 5.2 needs Claude Code 2.1.321 or later. Probes may still try older versions.
MODEL_FIRST_VERSION = {MODEL: None, FABLE: "2.1.321"}


def version_tuple(version: str) -> tuple:
    return tuple(int(x) for x in str(version).split("."))


def version_knows_model(version: str, model: str) -> bool:
    first = MODEL_FIRST_VERSION.get(model)
    return first is None or version_tuple(version) >= version_tuple(first)
EFFORT_LADDER = ("low", "medium", "high", "xhigh", "max")
EMPTY_MCP = '{"mcpServers":{}}'
# The author's value. Only mode "author" passes it (checklist B4): the meaning of --setting-sources
# changed in 2.1.314, so the modes that compare versions leave it out. A probe-only plan may add it
# back to another mode, to compare with and without.
SETTING_SOURCES = "project"
SETTING_SOURCES_RE = r"(user|project|local)(,(user|project|local))*"
# Permission modes a probe-only plan may pin instead of the mode's own (checklist C4: is "manual" the
# same as "default"?). Both are accepted by all 39 versions (layer 0, report 03b).
PERMISSION_MODE_CHOICES = ("default", "manual")
TIMEOUT_SECONDS = 900  # the author's per-call timeout (claudecode.py line 118), the same for every version
MAX_PARALLEL = 2  # checklist C11

# The author's HERMETIC_ENV (livenerf/providers/claudecode.py lines 70-75). DISABLE_AUTOUPDATER is
# already in every ask's base environment, so only the other three are mode-specific.
AUTHOR_ENV = {
    "CLAUDE_CODE_DISABLE_CLAUDE_MDS": "1",
    "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1",
    "CLAUDE_CODE_DISABLE_ADVISOR_TOOL": "1",
}

# Mode stock_blocked (trial layer 7). The official hooks page (code.claude.com/docs/en/hooks, read
# 2026-11-11) says: a PreToolUse hook runs before a tool call executes and can block it; "*" matches every
# tool (every tool name but EndConversation, which none of the measured versions offers); a hook that
# exits 2 blocks the call and Claude sees its stderr as the denial reason; a hook that exits with any other
# code, fails to start or times out does NOT block (fail-open; the onFailure field that would change that
# needs 2.1.295, so it is not used: every version gets the same settings, and older versions skip a
# settings file holding a field they do not know, changelog 2.1.281). In shell form the command runs with
# `sh -c` on macOS. So the command is kept to what cannot fail: read the hook input to its end (so the
# writer never meets a closed pipe), print one fixed sentence to stderr, exit 2. It names no path, so
# nothing about this machine reaches the model through it. All 39 versions list `--settings
# <file-or-json>` in their help (layer 0 help outputs); the JSON string form needs no file.
BLOCK_MESSAGE = "Tool use is disabled in this session. No tool call will run."
BLOCK_HOOK_COMMAND = "/bin/cat >/dev/null; echo '" + BLOCK_MESSAGE + "' >&2; exit 2"
BLOCK_SETTINGS = {"hooks": {"PreToolUse": [{"matcher": "*",
                                            "hooks": [{"type": "command", "command": BLOCK_HOOK_COMMAND}]}]}}
BLOCK_SETTINGS_JSON = json.dumps(BLOCK_SETTINGS, separators=(",", ":"))


@dataclass(frozen=True)
class Mode:
    name: str
    replace_system_prompt: bool  # --system-prompt (replace) or --append-system-prompt
    tools_off: bool  # --tools "" and --disable-slash-commands
    output_format: str  # json or stream-json
    permission_mode: str | None  # pinned whenever tools stay (checklist C4)
    env: dict = field(default_factory=dict)
    effort_step: int = 0  # 0, or -1 for one step lower
    items_allowed: bool = True  # False: probes only (plan rule 10)
    setting_sources: str | None = None  # --setting-sources value, or None for no such flag
    transport: str = "cli"  # "cli": start the version's Claude Code; "api": call the Messages API
    settings_json: str | None = None  # a --settings value (trial layer 7: the hook that refuses every tool)

    @property
    def blocks_tools(self) -> bool:
        """True for a mode whose tools stay in the request but are refused before they run (stock_blocked)."""
        return self.settings_json == BLOCK_SETTINGS_JSON


MODES = {
    "author": Mode("author", replace_system_prompt=True, tools_off=True, output_format="json",
                   permission_mode=None, env=dict(AUTHOR_ENV), setting_sources=SETTING_SOURCES),
    "stock_notools": Mode("stock_notools", replace_system_prompt=False, tools_off=True,
                          output_format="stream-json", permission_mode=None),
    "stock": Mode("stock", replace_system_prompt=False, tools_off=False, output_format="stream-json",
                  permission_mode="default", items_allowed=False),
    "stock_blocked": Mode("stock_blocked", replace_system_prompt=False, tools_off=False,
                          output_format="stream-json", permission_mode="default",
                          settings_json=BLOCK_SETTINGS_JSON),  # items allowed since trial layer 7, part two
    "low_effort": Mode("low_effort", replace_system_prompt=False, tools_off=True, output_format="stream-json",
                       permission_mode=None, effort_step=-1),
}

OUTPUT_FORMATS = ("json", "stream-json")

# Mode "api": the request of mode author, copied and sent by the runner itself (api.py). Its output is
# the raw server-sent event stream of the Messages API, recorded as it came.
API_OUTPUT_FORMAT = "api-sse"
API_MODE = Mode("api", replace_system_prompt=True, tools_off=True, output_format=API_OUTPUT_FORMAT,
                permission_mode=None, transport="api")
ALL_MODES = {**MODES, "api": API_MODE}


class ModeError(RuntimeError):
    pass


def effort_for(mode: Mode, plan_effort: str) -> str:
    if plan_effort not in EFFORT_LADDER:
        raise ModeError(f"effort {plan_effort!r} is not one of {EFFORT_LADDER}")
    i = EFFORT_LADDER.index(plan_effort) + mode.effort_step
    if i < 0:
        raise ModeError(f"mode {mode.name} needs an effort below {plan_effort!r}, and there is none")
    return EFFORT_LADDER[i]


FROM_MODE = "from-mode"  # build_argv default: take the value the mode itself sets


def build_argv(binary: str, mode: Mode, system_prompt: str, effort: str, *, keep_transcript: bool = False,
               output_format: str | None = None, setting_sources: str | None = FROM_MODE,
               permission_mode: str | None = FROM_MODE, model: str = MODEL) -> list[str]:
    """argv for one ask. The user message goes to stdin, as in the author's harness.

    For mode "author" with no overrides this is exactly the author's _command() (verified by
    `ccversions verify-author`), with his binary path replaced by the version's binary.
    setting_sources, permission_mode and model are overrides for probe-only plans; None leaves the
    setting-sources or permission-mode flag out. The model is always passed, and only MODEL_CHOICES.
    """
    if mode.transport != "cli":
        raise ModeError(f"mode {mode.name} starts no Claude Code and has no argv")
    fmt = output_format or mode.output_format
    if fmt not in OUTPUT_FORMATS:
        raise ModeError(f"output format {fmt!r} is not one of {OUTPUT_FORMATS}")
    if model not in MODEL_CHOICES:
        raise ModeError(f"model {model!r} is not one of {MODEL_CHOICES}")
    sources = mode.setting_sources if setting_sources == FROM_MODE else setting_sources
    perm = mode.permission_mode if permission_mode == FROM_MODE else permission_mode
    argv = [binary, "-p", "--model", model, "--output-format", fmt]
    if fmt == "stream-json":
        argv += ["--verbose"]  # stream-json needs it in print mode
    argv += ["--system-prompt" if mode.replace_system_prompt else "--append-system-prompt", system_prompt]
    if mode.tools_off:
        argv += ["--tools", ""]
    argv += ["--strict-mcp-config", "--mcp-config", EMPTY_MCP]
    if mode.settings_json:
        argv += ["--settings", mode.settings_json]
    if mode.tools_off:
        argv += ["--disable-slash-commands"]
    if not keep_transcript:
        argv += ["--no-session-persistence"]
    if sources:
        argv += ["--setting-sources", sources]
    if perm:
        argv += ["--permission-mode", perm]
    argv += ["--effort", effort]
    return argv


def flags_used() -> list[dict]:
    """Every Claude Code flag the runner can pass, with the modes that pass it (for the record)."""
    rows = [
        ("-p", "all", "print mode: one prompt, one answer, then exit"),
        ("--model " + MODEL, "all, unless a plan names another model", "checklist B6"),
        ("--model " + FABLE, "probe-only plans that name it for an ask; shuffled plans that name it (items only "
         "on versions from " + MODEL_FIRST_VERSION[FABLE] + " on)",
         "trial layer 2: Fable 5.2 probes; trial layer 6: the Fable 5.2 comparison"),
        ("--output-format json", "author (and plans that set it)", "checklist C14"),
        ("--output-format stream-json", "stock_notools, stock, stock_blocked, low_effort (and author when a plan "
         "sets it)", "checklist C14; trial layer 3: author items in stream-json carry the usage reading (E1, E2, E3)"),
        ("--verbose", "whenever the output format is stream-json", "stream-json needs it with -p"),
        ("--system-prompt <author's two sentences>", "author", "replaces the built-in system prompt"),
        ("--append-system-prompt <author's two sentences>", "stock_notools, stock, stock_blocked, low_effort",
         "checklist C13"),
        ('--tools ""', "author, stock_notools, low_effort", "no tools"),
        ("--strict-mcp-config", "all", "checklist A6"),
        ("--mcp-config '" + EMPTY_MCP + "'", "all", "checklist A6"),
        ("--settings '" + BLOCK_SETTINGS_JSON + "'", "stock_blocked",
         "trial layer 7: one PreToolUse hook for every tool that exits 2, so tools are described but never run"),
        ("--disable-slash-commands", "author, stock_notools, low_effort", "no Skills or slash commands"),
        ("--no-session-persistence", "all, unless a probe keeps its transcript", "checklist C5, B7"),
        ("--setting-sources " + SETTING_SOURCES, "author (other modes only in probe-only plans that add it back)",
         "the author's value; checklist B4"),
        ("--permission-mode default", "stock, stock_blocked", "checklist C4"),
        ("--permission-mode manual", "only probe-only plans that pin it", "checklist C4: compare with default"),
        ("--effort <level>", "all", "checklist C3: always explicit"),
        ("--version", "send mode, before each block", "checklist B2; never in a dry run"),
        ("(none)", "api", "mode api starts no Claude Code; it sends the copied request itself (api.py)"),
    ]
    return [{"flag": f, "modes": m, "why": w} for f, m, w in rows]
