"""Turn one raw record (what Claude Code printed) into plain fields. Pure functions, no I/O.

Claude Code prints one JSON object with --output-format json, and one JSON event per line with
stream-json. Both end in a result object with the same fields (result, is_error, num_turns,
stop_reason, usage, modelUsage, permission_denials, ...). stream-json also carries a system/init
event listing the tools, MCP servers, slash commands, Skills, plugins and agents of that session
(checklist A3, A6, C14), the assistant messages (tool calls, checklist C4), and events such as
rate_limit_event or a model fallback (C9, E1).

Mode "api" (trial layer 6) records the raw server-sent event stream of the Messages API instead
(format "api-sse"). parse() puts that stream back together into the one message it carried and gives a
result object with the same fields as Claude Code's (result: the text blocks joined; num_turns: 1, as one
request is one turn; stop_reason, usage, and modelUsage keyed by the model the API says answered), so
the grading and the run check read both kinds of record the same way. api_cost() prices one reply with
the official per-token prices.

Mode stock_blocked (trial layer 7) keeps the tools in the request and refuses every call with a hook.
tool_activity() reads a stream-json output for what the model tried: how many rounds ended in tool calls,
each call's tool name, and what became of it (refused by the hook, refused by the permission check, not
run for another reason Claude Code states, rejected before it ran, no result, or ran). fields() adds
those counts to the fields of a stock_blocked record only, so the fields of every other mode stay exactly
as they were. first_request_input_tokens() reads the input tokens of the first request alone (the usage
on the first assistant message), which is what one compares between two ways of asking when the
version's session file has no request lines (trial layer 7, question one).
"""

import json

from . import modes as modes_mod

MODEL = "claude-opus-5-5"
API_FORMAT = "api-sse"  # modes.API_OUTPUT_FORMAT

# USD per million tokens, from https://platform.claude.com/docs/en/about-claude/pricing (read 2026-11-10):
# base input, 5-minute cache writes, 1-hour cache writes, cache hits and refreshes, output. The same page
# says US-only inference (inference_geo "us") multiplies every category by 1.1, and the thinking page says
# thinking tokens are billed as output tokens (they are part of usage.output_tokens).
API_PRICES_SOURCE = "https://platform.claude.com/docs/en/about-claude/pricing, read 2026-11-10"
API_PRICES = {
    "claude-opus-5-5": {"input": 4.0, "cache_write_5m": 5.0, "cache_write_1h": 8.0, "cache_read": 0.20, "output": 20.0},
    "claude-fable-5-2": {"input": 8.0, "cache_write_5m": 10.0, "cache_write_1h": 16.0, "cache_read": 0.20,
                         "output": 40.0},
    # the models Claude Code falls back to after a refusal (checklist C9), in case a reply names one
    "claude-opus-5": {"input": 5.0, "cache_write_5m": 6.25, "cache_write_1h": 10.0, "cache_read": 0.50, "output": 25.0},
    "claude-opus-4-8": {"input": 5.0, "cache_write_5m": 6.25, "cache_write_1h": 10.0, "cache_read": 0.50,
                        "output": 25.0},
}
US_ONLY_MULTIPLIER = 1.1
INIT_FIELDS = ("cwd", "tools", "mcp_servers", "model", "permissionMode", "slash_commands", "apiKeySource", "betas",
               "claude_code_version", "output_style", "agents", "skills", "plugins", "plugin_errors",
               "memory_paths", "scratchpad_path", "analytics_disabled", "product_feedback_disabled", "capabilities")


def output_format(argv: list) -> str:
    if "--output-format" in argv:
        return argv[argv.index("--output-format") + 1]
    return "text"


def is_api(record: dict) -> bool:
    return record.get("transport") == "api"


def record_format(record: dict) -> str:
    """The format of a record's stdout: "api-sse" for mode api, else the --output-format of its argv."""
    return API_FORMAT if is_api(record) else output_format(record.get("argv") or [])


def sse_events(raw: str) -> tuple[list[dict], int]:
    """The JSON events of a server-sent event stream ("event:" and "data:" lines, a blank line ends one
    event). A reply that is plain JSON (an HTTP error body) gives that one object."""
    events, bad, data = [], 0, []

    def flush():
        nonlocal bad
        if not data:
            return
        try:
            obj = json.loads("\n".join(data))
            if isinstance(obj, dict):
                events.append(obj)
        except json.JSONDecodeError:
            bad += 1
        data.clear()

    saw_data = False
    for line in raw.splitlines():
        if line.startswith("data:"):
            saw_data = True
            data.append(line[5:].lstrip(" "))
        elif line.strip() == "":
            flush()
    flush()
    if not saw_data and raw.strip():
        try:
            obj = json.loads(raw)
            if isinstance(obj, dict):
                events.append(obj)
        except json.JSONDecodeError:
            bad += 1
    return events, bad


def assemble_message(events: list[dict]) -> dict:
    """One streamed Messages API reply put back together: the message (content blocks with their text,
    thinking and signature; stop_reason; usage, where message_delta's counts replace message_start's), and
    whether message_stop came, and the error event or error body if there was one."""
    msg, complete, error = None, False, None
    for e in events:
        t = e.get("type")
        if t == "message_start":
            msg = json.loads(json.dumps(e.get("message") or {}))
            msg["content"] = []
            msg.setdefault("usage", {})
        elif t == "content_block_start" and msg is not None:
            i = e.get("index", len(msg["content"]))
            while len(msg["content"]) <= i:
                msg["content"].append(None)
            msg["content"][i] = json.loads(json.dumps(e.get("content_block") or {}))
        elif t == "content_block_delta" and msg is not None:
            i = e.get("index", 0)
            block = msg["content"][i] if i < len(msg["content"]) else None
            d = e.get("delta") or {}
            if block is None:
                continue
            kind = d.get("type")
            if kind == "text_delta":
                block["text"] = (block.get("text") or "") + (d.get("text") or "")
            elif kind == "thinking_delta":
                block["thinking"] = (block.get("thinking") or "") + (d.get("thinking") or "")
            elif kind == "signature_delta":
                block["signature"] = (block.get("signature") or "") + (d.get("signature") or "")
            elif kind == "input_json_delta":
                block["partial_json"] = (block.get("partial_json") or "") + (d.get("partial_json") or "")
            elif kind == "citations_delta":
                block.setdefault("citations", []).append(d.get("citation"))
        elif t == "message_delta" and msg is not None:
            d = e.get("delta") or {}
            for k in ("stop_reason", "stop_sequence", "stop_details", "container"):
                if k in d:
                    msg[k] = d[k]
            for k, v in (e.get("usage") or {}).items():
                if v is not None:
                    msg["usage"][k] = v
        elif t == "message_stop":
            complete = True
        elif t == "error":
            error = e.get("error") or e
    if msg is not None:
        msg["content"] = [b for b in msg["content"] if b is not None]
    return {"message": msg, "complete": complete, "error": error}


def _parse_api(stdout: str) -> dict:
    events, bad = sse_events(stdout)
    got = assemble_message(events)
    msg = got["message"]
    kinds = {}
    for e in events:
        k = str(e.get("type"))
        kinds[k] = kinds.get(k, 0) + 1
    result = None
    if msg is not None:
        failed = (not got["complete"]) or got["error"] is not None
        text = "".join(b.get("text") or "" for b in msg["content"] if b.get("type") == "text")
        model = msg.get("model")
        result = {"type": "result", "subtype": "error" if failed else "success", "is_error": failed,
                  "result": text, "num_turns": 1, "stop_reason": msg.get("stop_reason"), "terminal_reason": None,
                  "usage": msg.get("usage") or {}, "modelUsage": {model: {}} if model else {},
                  "permission_denials": []}
    tool_uses = [b.get("name") for b in (msg or {}).get("content") or [] if b.get("type") == "tool_use"]
    return {"events": len(events), "bad_lines": bad, "event_kinds": kinds, "result": result, "init": None,
            "tool_uses": tool_uses, "assistant_messages": 1 if msg is not None else 0, "rate_limit_events": [],
            "fallback_events": [], "api_message": msg, "api_complete": got["complete"], "api_error": got["error"]}


def api_cost(usage: dict | None, model: str | None) -> dict:
    """What one reply costs at the official API prices (API_PRICES). usd is None when it cannot be priced.
    cache writes are split by the usage's cache_creation object; a reply that has cache writes but no split
    is priced as 1-hour writes (the copied request asks for ttl 1h) and says so in problems."""
    usage = usage or {}
    out = {"usd": None, "model": model, "parts_usd": {}, "problems": [], "prices_per_mtok": None,
           "source": API_PRICES_SOURCE, "multiplier": 1.0}
    prices = API_PRICES.get(model or "")
    if prices is None:
        out["problems"].append(f"no price for model {model!r}")
        return out
    out["prices_per_mtok"] = prices
    created = usage.get("cache_creation_input_tokens") or 0
    split = usage.get("cache_creation") or {}
    w5 = split.get("ephemeral_5m_input_tokens")
    w1 = split.get("ephemeral_1h_input_tokens")
    if w5 is None and w1 is None:
        w5, w1 = 0, created
        if created:
            out["problems"].append("cache writes without a 5m/1h split: priced as 1-hour writes")
    w5, w1 = w5 or 0, w1 or 0
    if w5 + w1 != created:
        out["problems"].append(f"cache_creation split {w5}+{w1} differs from cache_creation_input_tokens {created}")
    counts = {"input": usage.get("input_tokens") or 0, "cache_write_5m": w5, "cache_write_1h": w1,
              "cache_read": usage.get("cache_read_input_tokens") or 0, "output": usage.get("output_tokens") or 0}
    geo = usage.get("inference_geo")
    if geo == "us":
        out["multiplier"] = US_ONLY_MULTIPLIER
    elif geo not in (None, "global"):
        out["problems"].append(f"inference_geo {geo!r}: no price rule known; priced as global")
    if usage.get("speed") not in (None, "standard"):
        out["problems"].append(f"speed {usage.get('speed')!r}: priced at standard prices, which is too low")
    parts = {k: counts[k] * prices[k] / 1_000_000 * out["multiplier"] for k in counts}
    out["tokens"] = counts
    out["parts_usd"] = {k: round(v, 6) for k, v in parts.items()}
    out["usd"] = round(sum(parts.values()), 6)
    return out


def parse(stdout: str, fmt: str) -> dict:
    if fmt == API_FORMAT:
        return _parse_api(stdout)
    events, bad_lines = [], 0
    if fmt == "json":
        try:
            obj = json.loads(stdout)
            events = [obj] if isinstance(obj, dict) else []
        except json.JSONDecodeError:
            bad_lines = 1 if stdout.strip() else 0
    else:
        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                bad_lines += 1
                continue
            if isinstance(obj, dict):
                events.append(obj)
    result = next((e for e in reversed(events) if e.get("type") == "result"), None)
    if result is None and fmt == "json" and events and "result" in events[0]:
        result = events[0]
    init = next((e for e in events if e.get("type") == "system" and e.get("subtype") == "init"), None)
    tool_uses, assistant_messages = [], 0
    for e in events:
        if e.get("type") == "assistant":
            assistant_messages += 1
            for block in ((e.get("message") or {}).get("content") or []):
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    tool_uses.append(block.get("name"))
    kinds = {}
    for e in events:
        k = f"{e.get('type')}/{e.get('subtype')}" if e.get("subtype") else str(e.get("type"))
        kinds[k] = kinds.get(k, 0) + 1
    return {
        "events": len(events),
        "bad_lines": bad_lines,
        "event_kinds": kinds,
        "result": result,
        "init": {k: init.get(k) for k in INIT_FIELDS if k in init} if init else None,
        "tool_uses": tool_uses,
        "assistant_messages": assistant_messages,
        "rate_limit_events": [e for e in events if e.get("type") == "rate_limit_event"],
        "fallback_events": [e for e in events if e.get("type") == "system" and "fallback" in str(e.get("subtype"))],
    }


def _fraction(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def rate_limit_reading(rate_limit_events: list) -> dict:
    """The usage reading in the rate_limit_event lines of one ask (checklist E1, E2).

    Seen once, from the user's terminal copy (2.1.284, 2026-11-10):
        {"type": "rate_limit_event", "rate_limit_info": {"status": "allowed", "rateLimitType": "seven_day",
         "overageStatus": "rejected", ..., "unifiedWindows": {"seven_day": {"utilization": 0.01, ...}}}, ...}
    utilization is the used share of the window, 0.01 meaning 1 per cent. The 2.1.280 code can also
    put five_hour and seven_day_overage_included windows under unifiedWindows. A version's print mode
    queues one such line whenever its rate-limit state is updated, so an ask may carry several; the
    last one that has a reading counts. --output-format json prints only the final result, so asks in
    that format (mode "author") carry none, and every field here is then None: not an error.
    is_using_overage is the event's isUsingOverage (checklist E3: true would mean the ask was billed as
    extra usage), the last one given; None when no event has it.
    """
    weekly = five_hour = status = overage = None
    for e in rate_limit_events:
        info = e.get("rate_limit_info") or {}
        windows = info.get("unifiedWindows") or {}
        w = _fraction((windows.get("seven_day") or {}).get("utilization"))
        if w is None and info.get("rateLimitType") == "seven_day":
            w = _fraction(info.get("utilization"))
        f = _fraction((windows.get("five_hour") or {}).get("utilization"))
        if f is None and info.get("rateLimitType") == "five_hour":
            f = _fraction(info.get("utilization"))
        weekly = w if w is not None else weekly
        five_hour = f if f is not None else five_hour
        status = info.get("status", status)
        if "isUsingOverage" in info:
            overage = info["isUsingOverage"]
    return {"rate_limit_event_count": len(rate_limit_events), "weekly_utilization": weekly,
            "five_hour_utilization": five_hour, "rate_limit_status": status, "is_using_overage": overage}


def billing_problems(api_key_source, is_using_overage) -> list[str]:
    """Checklist A10, E3: reasons to think an ask was not paid from the subscription. A field the output
    does not have (None, as with --output-format json) says nothing and is not a problem."""
    out = []
    if is_using_overage is True:
        out.append("isUsingOverage is true")
    if api_key_source not in (None, "", "none"):
        out.append(f"apiKeySource is {api_key_source!r}, not 'none'")
    return out


def requested_model(record: dict) -> str:
    """The model the ask named (its --model value, or the model of a mode-api request); MODEL for a record
    without one."""
    if is_api(record):
        return ((record.get("request_body") or {}).get("model")) or record.get("model") or MODEL
    argv = record.get("argv") or []
    if "--model" in argv and argv.index("--model") + 1 < len(argv):
        return argv[argv.index("--model") + 1]
    return MODEL


def _stream_events(stdout: str) -> list[dict]:
    out = []
    for line in (stdout or "").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            out.append(obj)
    return out


def _content_text(content) -> str:
    """The text of a tool result's content (a string, or blocks that hold text or nested content)."""
    if isinstance(content, str):
        return content
    parts = []
    for b in content or []:
        if isinstance(b, str):
            parts.append(b)
        elif isinstance(b, dict):
            if isinstance(b.get("text"), str):
                parts.append(b["text"])
            elif isinstance(b.get("content"), (str, list)):
                parts.append(_content_text(b["content"]))
    return "\n".join(parts)


# What became of one tool call, safest first. Only "ran" means the call was carried out on this machine.
TOOL_OUTCOMES = ("blocked_by_hook", "denied_by_permission", "not_run", "rejected_before_run", "no_result", "ran")
# Claude Code's own words for a call it rejected before running it (a deferred tool called without its
# schema, a bad input): the hooks page says validation rejections come back as tool_use_error results and
# happen before hooks run.
REJECTED_MARKERS = ("<tool_use_error>", "InputValidationError")


def blocks_tools(record: dict) -> bool:
    mode = modes_mod.MODES.get(record.get("mode") or "")
    return bool(mode and mode.blocks_tools)


def tool_activity(stdout: str, fmt: str, block_message: str = modes_mod.BLOCK_MESSAGE) -> dict | None:
    """What the model tried with tools in one stream-json output (None for another format).

    A call is a tool_use block of a top-level assistant message (parent_tool_use_id empty). A round is one
    such message with at least one call; Claude Code counts a round and the answer after it as two turns
    (trial layer 1, the refused `touch`: one call, num_turns 2). Each call's outcome comes from the
    tool_result with its id: the hook's sentence in it -> blocked_by_hook; the id among the permission
    denials -> denied_by_permission; a tool_result_meta entry with a non_execution_kind -> not_run;
    an error naming a tool_use_error or InputValidationError -> rejected_before_run; no result -> no_result;
    anything else -> ran. Events of a subagent (parent_tool_use_id set) are counted, not read: a subagent
    only runs when a call to the Agent tool was carried out."""
    if fmt != "stream-json":
        return None
    events = _stream_events(stdout)
    calls, rounds, results, meta, denied = [], [], {}, {}, set()
    subagent_events = hook_events = 0
    for i, e in enumerate(events):
        t = e.get("type")
        nested = e.get("parent_tool_use_id") not in (None, "")
        if t == "assistant":
            if nested:
                subagent_events += 1
                continue
            msg = e.get("message") or {}
            uses = [b for b in msg.get("content") or [] if isinstance(b, dict) and b.get("type") == "tool_use"]
            if uses:
                key = msg.get("id") or f"event-{i}"
                if key not in rounds:
                    rounds.append(key)
            for b in uses:
                calls.append({"id": b.get("id"), "name": b.get("name"),
                              "input_head": json.dumps(b.get("input"), ensure_ascii=False)[:200]})
        elif t == "user":
            if nested:
                subagent_events += 1
                continue
            content = (e.get("message") or {}).get("content")
            for b in content if isinstance(content, list) else []:
                if isinstance(b, dict) and b.get("type") == "tool_result":
                    results[b.get("tool_use_id")] = {"is_error": bool(b.get("is_error")),
                                                     "text": _content_text(b.get("content"))}
            for m in e.get("tool_result_meta") or []:
                if isinstance(m, dict):
                    meta[m.get("id")] = m
        elif t == "system":
            if e.get("subtype") == "permission_denied":
                denied.add(e.get("tool_use_id"))
            if "hook" in str(e.get("subtype") or ""):
                hook_events += 1
        elif t == "result":
            for d in e.get("permission_denials") or []:
                if isinstance(d, dict):
                    denied.add(d.get("tool_use_id"))
    outcomes = {k: 0 for k in TOOL_OUTCOMES}
    for c in calls:
        r, m = results.get(c["id"]), meta.get(c["id"]) or {}
        if r is None:
            out = "no_result"
        elif block_message in r["text"]:
            out = "blocked_by_hook"
        elif c["id"] in denied:
            out = "denied_by_permission"
        elif m.get("non_execution_kind"):
            out = "not_run"
        elif r["is_error"] and any(x in r["text"] for x in REJECTED_MARKERS):
            out = "rejected_before_run"
        else:
            out = "ran"
        c["outcome"] = out
        c["non_execution_kind"] = m.get("non_execution_kind")
        c["result_head"] = (r or {}).get("text", "")[:200]
        outcomes[out] += 1
    return {"tool_rounds": len(rounds), "call_count": len(calls), "names": [c["name"] for c in calls],
            "outcomes": outcomes, "blocked_by_hook": outcomes["blocked_by_hook"],
            "not_blocked_by_hook": len(calls) - outcomes["blocked_by_hook"], "ran": outcomes["ran"],
            "subagent_events": subagent_events, "hook_events": hook_events, "calls": calls}


def first_request_input_tokens(record: dict) -> int | None:
    """The input tokens of the ask's first request alone: input, cache writes and cache reads on the usage
    of the first top-level assistant message (stream-json; trial layer 1 saw one such usage per request).
    None for a json output, which has only the totals."""
    fmt = record_format(record)
    if fmt == API_FORMAT:
        usage = (parse(record.get("stdout") or "", fmt)["api_message"] or {}).get("usage")
    elif fmt == "stream-json":
        first = next((e for e in _stream_events(record.get("stdout") or "") if e.get("type") == "assistant"
                      and e.get("parent_tool_use_id") in (None, "")), None)
        usage = ((first or {}).get("message") or {}).get("usage")
    else:
        usage = None
    if not usage:
        return None
    return sum(usage.get(k) or 0 for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"))


def canary_hits(record: dict) -> int | None:
    """How often a probe's canary word came back (trial layer 7; None when the probe has no canary)."""
    c = record.get("canary")
    if not isinstance(c, dict):
        return None
    return sum(v for k, v in c.items() if k.startswith("hits_") and isinstance(v, int))


def _blocked_fields(record: dict) -> dict:
    """The extra fields of a stock_blocked record (trial layer 7)."""
    ta = tool_activity(record.get("stdout") or "", record_format(record)) or {}
    return {
        "tool_rounds": ta.get("tool_rounds"),
        "tool_calls": ta.get("call_count"),
        "tools_tried": ta.get("names"),
        "tool_outcomes": ta.get("outcomes"),
        "tools_not_blocked_by_hook": ta.get("not_blocked_by_hook"),
        "tools_ran": ta.get("ran"),
        "subagent_events": ta.get("subagent_events"),
        "canary_hits": canary_hits(record),
    }


def fields(record: dict) -> dict:
    """The plain fields of one ask (no question text, no answer text)."""
    fmt = record_format(record)
    parsed = parse(record.get("stdout") or "", fmt)
    res = parsed["result"] or {}
    usage = res.get("usage") or {}
    model_usage = res.get("modelUsage") or {}
    context = sum(usage.get(k) or 0 for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"))
    api_part = {}
    if fmt == API_FORMAT:  # only mode api records get these, so the rows of other records stay as they were
        err = parsed.get("api_error") or {}
        api_part = {
            "transport": "api",
            "api_http_status": record.get("http_status"),
            "api_complete": parsed.get("api_complete"),
            "api_error_type": err.get("type") if isinstance(err, dict) else None,
            "api_cost_usd": record.get("api_cost_usd"),
            "request_digest_cc": record.get("request_digest_cc"),
            "beta_set": record.get("beta_set"),
        }
    return {
        "output_format": fmt,
        "parsed_events": parsed["events"],
        "bad_lines": parsed["bad_lines"],
        "event_kinds": parsed["event_kinds"],
        "has_result": parsed["result"] is not None,
        "is_error": res.get("is_error"),
        "subtype": res.get("subtype"),
        "num_turns": res.get("num_turns"),
        "stop_reason": res.get("stop_reason"),
        "terminal_reason": res.get("terminal_reason"),
        "result_chars": len(res.get("result") or "") if isinstance(res.get("result"), str) else None,
        "duration_ms": res.get("duration_ms"),
        "duration_api_ms": res.get("duration_api_ms"),
        "ttft_ms": res.get("ttft_ms"),
        "total_cost_usd": res.get("total_cost_usd"),
        "input_tokens": usage.get("input_tokens"),
        "output_tokens": usage.get("output_tokens"),
        "cache_creation_input_tokens": usage.get("cache_creation_input_tokens"),
        "cache_read_input_tokens": usage.get("cache_read_input_tokens"),
        "context_tokens": context,
        "thinking_tokens": (usage.get("output_tokens_details") or {}).get("thinking_tokens"),
        "service_tier": usage.get("service_tier"),
        "inference_geo": usage.get("inference_geo"),
        "speed": usage.get("speed"),
        "served_models": list(model_usage),
        "cost_basis": {m: (u or {}).get("costBasis") for m, u in model_usage.items()},
        "canonical_model": {m: (u or {}).get("canonicalModel") for m, u in model_usage.items()},
        "permission_denials": len(res.get("permission_denials") or []),
        "tool_uses": parsed["tool_uses"],
        "assistant_messages": parsed["assistant_messages"],
        "rate_limit_events": parsed["rate_limit_events"],
        **rate_limit_reading(parsed["rate_limit_events"]),
        "api_key_source": (parsed["init"] or {}).get("apiKeySource"),
        "fallback_events": len(parsed["fallback_events"]),
        "server_tool_requests": server_tool_requests(parsed["result"]) if fmt != API_FORMAT else None,
        "first_request_input_tokens": first_request_input_tokens(record),
        "requested_model": requested_model(record),
        "init": parsed["init"],
        **api_part,
        # only stock_blocked records get these, so the rows of other records stay as they were
        **(_blocked_fields(record) if blocks_tools(record) else {}),
    }


def server_tool_requests(result: dict | None) -> int:
    """How many server-side tool requests (web search, web fetch) the result line counts. These run on
    Anthropic's side, so the hook of mode stock_blocked never sees them; 0 in every trial record."""
    usage = (result or {}).get("usage") or {}
    counts = usage.get("server_tool_use") or {}
    total = sum(v for v in counts.values() if isinstance(v, (int, float)) and not isinstance(v, bool))
    for u in ((result or {}).get("modelUsage") or {}).values():
        total = max(total, (u or {}).get("webSearchRequests") or 0)
    return int(total)


def ask_failed(record: dict) -> bool:
    """No answer came back: the runner's status is not "done", or Claude Code exited non-zero, printed no
    result or reported an error. A refusal is an answer of the model and does not count here."""
    if record.get("status") != "done":
        return True
    if is_api(record):
        return False
    res = parse(record.get("stdout") or "", record_format(record))["result"]
    if res is None:
        return True
    if res.get("stop_reason") == "refusal":
        return False
    return record.get("returncode") != 0 or bool(res.get("is_error"))


def never_reached_model(record: dict) -> bool:
    """The ask may be asked once more (design file 判断标准.md, section 1): it failed and nothing shows
    that the model worked on it. A timeout never counts (it may depend on the version), nor does a
    minimum-version stop, a refusal, or any ask whose output counts output tokens."""
    status = record.get("status")
    if status in ("timeout", "min_version", "done_but_dirty", "not_subscription", "runner_error"):
        return False
    if is_api(record):
        if status in ("network_error", "rate_limited"):
            return True
        return status == "http_error" and not (record.get("api_usage") or {}).get("output_tokens")
    if status in ("launch_error", "usage_limit"):
        return True
    if not ask_failed(record):
        return False
    res = parse(record.get("stdout") or "", record_format(record))["result"] or {}
    usage = res.get("usage") or {}
    worked = (usage.get("output_tokens") or 0) > 0 or any(
        ((u or {}).get("outputTokens") or 0) > 0 for u in (res.get("modelUsage") or {}).values())
    return not worked


def result_text(record: dict) -> str | None:
    """The final answer text Claude Code returned (the `result` field), which is all the author grades.
    For mode api: the text blocks of the API's reply, joined."""
    res = parse(record.get("stdout") or "", record_format(record))["result"] or {}
    value = res.get("result")
    return value if isinstance(value, str) else None


def looks_like_usage_limit(stdout: str, stderr: str, argv: list) -> bool:
    """A guess until layer 1 shows the real text: a rate_limit_event whose own status is "rejected"
    (overageStatus "rejected" only means extra usage is off, and is ignored), or a failed result, or a
    failed process, that talks about a usage or rate limit. A normal answer that mentions limits never
    counts."""
    parsed = parse(stdout, output_format(argv))
    if any((e.get("rate_limit_info") or {}).get("status") == "rejected" for e in parsed["rate_limit_events"]):
        return True
    res = parsed["result"]
    words = ("usage limit", "rate limit", "hit your limit", "limit reached", "weekly limit", "5-hour limit")
    if res is not None:
        if not res.get("is_error"):
            return False
        text = json.dumps(res).lower()
    else:
        text = stderr.lower()
    return any(w in text for w in words)
