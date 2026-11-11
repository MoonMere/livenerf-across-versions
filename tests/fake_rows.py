"""Made-up graded rows shaped like the registered run, for testing analyze.py. No model is asked.

make_rows() gives two (or three) passes of 39 versions on 78 items plus the small groups. A drop can be
hidden in it: from one version on, every later version is `drop_points` percentage points less often
right, and thinks `think_drop` (a share) less.
"""

import math
import random

VERSIONS = [f"2.1.{n}" for n in range(280, 323) if n not in (297, 298, 313, 320)]
FAMILIES = ["mmlupro"] * 59 + ["gpqa"] * 12 + ["aime"] * 3 + ["comps"] * 4
SMALL = [("flags_on", ["2.1.280", "2.1.299", "2.1.308", "2.1.322"], "stock_blocked", "high", 0, 1.0),
         ("author", ["2.1.280", "2.1.322"], "author", "high", 0.03, 1.2),
         ("notools", ["2.1.280", "2.1.322"], "stock_notools", "high", 0.0, 1.0),
         ("effort_medium", ["2.1.322"], "stock_blocked", "medium", -0.04, 0.6),
         ("effort_low", ["2.1.322"], "stock_blocked", "low", -0.08, 0.3),
         ("effort_xhigh", ["2.1.322"], "stock_blocked", "xhigh", 0.01, 1.6),
         ("effort_max", ["2.1.322"], "stock_blocked", "max", 0.01, 2.2),
         ("fable", ["2.1.322"], "stock_blocked", "high", 0.15, 1.0),
         ("api", ["2.1.322"], "api", "high", 0.03, 1.2)]


def make_rows(seed: int = 1, *, passes: int = 2, drop_from: str | None = None, drop_points: float = 0.0,
              think_drop: float = 0.0, error_share: float = 0.01, skip_last_blocks: int = 0,
              block_units: int = 3) -> list[dict]:
    rng = random.Random(seed)
    chance = [min(0.95, max(0.1, rng.gauss(0.6, 0.25))) for _ in range(78)]
    level = [rng.gauss(6.0, 1.3) for _ in range(78)]
    units = [f"item:{FAMILIES[i]}-{i:02d}" for i in range(78)]
    cut = VERSIONS.index(drop_from) if drop_from else None
    rows = []
    for p in range(1, passes + 1):
        order_units = list(range(78))
        rng.shuffle(order_units)
        blocks = [order_units[b:b + block_units] for b in range(0, 78, block_units)]
        if p == passes and skip_last_blocks:
            blocks = blocks[:-skip_last_blocks]
        order = 0
        for bi, chunk in enumerate(blocks):
            for i in chunk:
                arms = [("main", v, "stock_blocked", "high", 0.0, 1.0) for v in VERSIONS]
                for g, vs, mode, effort, d_acc, f_think in SMALL:
                    if p <= 2 or g == "effort_low":
                        arms += [(g, v, mode, effort, d_acc, f_think) for v in vs]
                rng.shuffle(arms)
                for g, v, mode, effort, d_acc, f_think in arms:
                    order += 1
                    low = g == "main" and cut is not None and VERSIONS.index(v) >= cut
                    pr = chance[i] + d_acc - (drop_points / 100 if low else 0.0)
                    think = level[i] + rng.gauss(0, 0.9) + math.log(f_think) + (math.log(1 - think_drop) if low else 0.0)
                    tried = rng.random() < 0.15
                    bad = rng.random() < error_share
                    tokens = int(max(0.0, math.exp(think) - 1))
                    rows.append({
                        "plan": f"F{p}", "ask_id": f"p{p}b{bi:03d}o{order:05d}", "group": g, "pass": p, "block": bi,
                        "order": order, "version": v, "mode": mode, "effort": effort, "unit": units[i],
                        "family": FAMILIES[i], "repeat": 1, "warmup": False, "scored": True, "resend_of": None,
                        "outcome": "error" if bad else "scored", "reason": "failed" if bad else None,
                        "score": None if bad else float(rng.random() < pr),
                        "thinking_tokens": None if bad else tokens,
                        "output_tokens": None if bad else tokens + rng.randint(150, 700),
                        "tool_calls": None if mode != "stock_blocked" else int(tried), "tool_rounds": int(tried),
                        "num_turns": 1 + int(tried), "elapsed_seconds": round(5 + tokens / 60 + rng.random(), 3),
                        "started_at": f"2026-11-1{p}T{bi % 24:02d}:{order % 60:02d}:00.000+00:00",
                        "first_request_input_tokens": 15000 + 30 * (VERSIONS.index(v) // 3) + i,
                        "context_tokens": 15100 + i, "requested_model": "claude-opus-5-5", "remote_flags": "off",
                        "inference_geo": "global",
                    })
    return rows
