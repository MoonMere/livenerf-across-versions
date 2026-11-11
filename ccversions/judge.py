"""The decision rule of the experiment, as arithmetic (design file 判断标准.md, sections 2, 3 and 5-2).

Everything here works on one array `val[item, pass, version]`: the value of one ask (1 or 0 for a scored
answer, or the log of its thinking tokens), NaN where the ask has no value (an error, a void answer, or
not asked). Versions are in release order. Nothing here reads a file or knows what a record is; analyze.py
builds the arrays, and the simulations in 设计/判断标准_模拟/ call the same functions on made-up data, so
the numbers in the design file are numbers of this very code.

The scan (section 3, "any run of consecutive versions"):

  1. Take out the item's difficulty: inside each cell (one item in one pass) subtract the mean of the
     cell's values from each value. A segment's score is the mean of these residuals over its versions.
  2. For every run of consecutive versions but the whole list (V * (V + 1) / 2 - 1 of them, 779 for 39):
     diff = score inside - score outside, and z = diff * sqrt(n_in * n_out / (n_in + n_out)), n being the
     number of values. The statistic is the largest |z|.
  3. Shuffle: inside each cell, deal the V results (missing ones included) to the V versions at random,
     and take the largest |z| again. p = (1 + shuffles at least as large) / (1 + shuffles).

A difference is declared when p < alpha, the difference is at least a minimum size, and every pass taken
alone has the same sign on that segment (passes with less than half their cells are left out of the sign
check, their data still counts in the pooled numbers).

Whether a third pass is opened after two (section 2): the best segment of the two-pass scan points to a
drop (its shape, see has_drop, and the step itself, see drop_support) and p is below the opening line.
"""

import numpy as np

SEED = 20261111
SHUFFLES = 10_000
ALPHA = 0.05            # the line of a declared difference (accuracy and thinking each have their own)
OPEN_ALPHA = 0.10       # the lower line that opens a third pass after two (set from simulation 5: with
                        # no difference at all, a third pass opens in about 18 to 20 runs out of 100)
MIN_DIFF_ACCURACY = 0.03    # 3 percentage points (the LiveNerf author's number)
MIN_RATIO_THINKING = 0.10   # 10 per cent more or less thinking
MIN_PASS_SHARE_FOR_SIGN = 0.5
MIN_DROP_SUPPORT = 2.0      # to open a third pass: standard errors between the segment and the versions
                            # on the side of the drop
MIN_DROP_SUPPORT_NAMED = 3.0  # to call a declared difference a drop in the conclusions


def segments(n_versions: int) -> tuple[np.ndarray, np.ndarray]:
    """Start and end index (inclusive) of every run of consecutive versions except the whole list."""
    starts, ends = [], []
    for a in range(n_versions):
        for b in range(a, n_versions):
            if not (a == 0 and b == n_versions - 1):
                starts.append(a)
                ends.append(b)
    return np.array(starts), np.array(ends)


def residuals(val: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """val[item, pass, version] -> (residual with 0 where missing, mask of the values that count)."""
    mask = ~np.isnan(val)
    n = mask.sum(axis=-1, keepdims=True)
    total = np.where(mask, val, 0.0).sum(axis=-1, keepdims=True)
    mean = np.divide(total, n, out=np.zeros_like(total, dtype=float), where=n > 0)
    return np.where(mask, val - mean, 0.0), mask


def scan(sums: np.ndarray, counts: np.ndarray, starts: np.ndarray, ends: np.ndarray):
    """sums[..., V], counts[..., V]: per version, the sum of residuals and how many values.
    Returns diff[..., S] and z[..., S] for every segment (0 where a side is empty)."""
    lead = np.zeros(sums.shape[:-1] + (1,))
    cs = np.concatenate([lead, np.cumsum(sums, axis=-1)], axis=-1)
    cn = np.concatenate([lead, np.cumsum(counts, axis=-1)], axis=-1)
    s_in = cs[..., ends + 1] - cs[..., starts]
    n_in = cn[..., ends + 1] - cn[..., starts]
    s_out = cs[..., -1:] - s_in
    n_out = cn[..., -1:] - n_in
    ok = (n_in > 0) & (n_out > 0)
    safe_in = np.where(ok, n_in, 1.0)
    safe_out = np.where(ok, n_out, 1.0)
    diff = np.where(ok, s_in / safe_in - s_out / safe_out, 0.0)
    z = diff * np.sqrt(np.where(ok, n_in * n_out / (safe_in + safe_out), 0.0))
    return diff, z


def pass_sums(resid: np.ndarray, mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """[..., item, pass, version] -> per pass and version: sums[..., pass, V], counts[..., pass, V]."""
    return resid.sum(axis=-3), mask.sum(axis=-3).astype(float)


def shuffled_pass_sums(resid: np.ndarray, mask: np.ndarray, n: int, rng: np.random.Generator):
    """n shuffles of the cells. Returns sums[n, pass, V], counts[n, pass, V]."""
    if mask.all():
        big = np.broadcast_to(resid, (n,) + resid.shape).copy()
        shuffled = rng.permuted(big, axis=-1)
        return shuffled.sum(axis=1), np.broadcast_to(mask.sum(axis=0).astype(float), (n,) + mask.shape[1:]).copy()
    order = np.argsort(rng.random((n,) + resid.shape), axis=-1)
    r = np.take_along_axis(np.broadcast_to(resid, (n,) + resid.shape), order, axis=-1)
    m = np.take_along_axis(np.broadcast_to(mask, (n,) + mask.shape), order, axis=-1)
    return r.sum(axis=1), m.sum(axis=1).astype(float)


def has_drop(start: int, end: int, diff: float, n_versions: int) -> bool:
    """Does this segment say that something got lower from some version on?

    A segment lower than the rest that does not start at the first version: the drop is where it starts.
    A segment higher than the rest that does not end at the last version: the drop is right after it.
    The two other shapes (low at the very start, high at the very end) only say that something rose.

    This is the shape only. judge() also asks that the step itself is there (drop_support): the segment
    against the versions before it (a low segment) or after it (a high one), taken alone, at least
    MIN_DROP_SUPPORT standard errors apart to open a third pass ("has_drop"), and at least
    MIN_DROP_SUPPORT_NAMED to be called a drop in the conclusions ("drop_named"). Without it a rise
    from some version on reads as a drop whenever the first two or three versions happen to score high
    and are left out of the low segment: with a real rise of 5 points from version 22 on, the shape
    alone says "drop" in about half the runs, 2 standard errors in about a quarter, 3 in 3 to 5 of 100
    (counted over all made-up runs, whether or not the difference passed the line; in simulation 5's
    first round, which used the shape alone, 36 per cent of the runs both passed the line and were
    called a drop).
    The two lines differ because the two mistakes cost different things: a third pass opened for nothing
    costs usage, a rise announced as a drop is a wrong headline.
    """
    if diff < 0:
        return start > 0
    if diff > 0:
        return end < n_versions - 1
    return False


def drop_support(resid: np.ndarray, mask: np.ndarray, start: int, end: int, diff: float) -> float | None:
    """How many standard errors the segment lies below the versions before it (a low segment), or above
    the versions after it (a high segment). None where that side has no version. The standard error
    comes from the spread of all residuals that count (one degree of freedom less per cell)."""
    n_versions = resid.shape[-1]
    lo, hi = (0, start) if diff < 0 else (end + 1, n_versions)
    if hi <= lo:
        return None
    n_all = float(mask.sum())
    cells = float(mask.any(axis=-1).sum())
    if n_all - cells <= 0:
        return None
    sd = float(np.sqrt((resid ** 2).sum() / (n_all - cells)))
    n_seg, n_side = float(mask[..., start:end + 1].sum()), float(mask[..., lo:hi].sum())
    if sd == 0 or n_seg == 0 or n_side == 0:
        return None
    gap = resid[..., lo:hi].sum() / n_side - resid[..., start:end + 1].sum() / n_seg
    if diff > 0:
        gap = -gap
    return float(gap / (sd * np.sqrt(1 / n_seg + 1 / n_side)))


def judge(val: np.ndarray, *, passes: list[int] | None = None, min_effect: float, effect: str = "diff",
          shuffles: int = SHUFFLES, seed: int = SEED, alpha: float = ALPHA,
          shuffled: tuple | None = None, keep_null: bool = False) -> dict:
    """The scan on the given passes (indexes into axis 1; default all).

    effect "diff": the size is |diff| (accuracy, in shares). effect "ratio": the size is |exp(diff) - 1|
    (thinking, val being logs). shuffled: (sums[n, pass, V], counts[n, pass, V]) made before, so that
    two-pass and three-pass scans of a simulation share their shuffles.
    """
    n_items, n_passes, n_versions = val.shape
    passes = list(range(n_passes)) if passes is None else list(passes)
    starts, ends = segments(n_versions)
    resid, mask = residuals(val)
    sums, counts = pass_sums(resid, mask)
    diff, z = scan(sums[passes].sum(axis=0), counts[passes].sum(axis=0), starts, ends)
    best = int(np.abs(z).argmax())
    observed = float(np.abs(z[best]))
    if starts[best] == 0:
        # A run that starts at the first version and the run after it are the same split seen from two
        # sides (same |z|, opposite sign). It is reported as "from version X on".
        best = int(np.where((starts == ends[best] + 1) & (ends == n_versions - 1))[0][0])
    if shuffled is None:
        rng = np.random.default_rng(seed)
        parts, done = [], 0
        while done < shuffles:
            n = min(500, shuffles - done)
            s, c = shuffled_pass_sums(resid, mask, n, rng)
            _, zs = scan(s[:, passes].sum(axis=1), c[:, passes].sum(axis=1), starts, ends)
            parts.append(np.abs(zs).max(axis=-1))
            done += n
        null = np.concatenate(parts)
    else:
        s, c = shuffled
        _, zs = scan(s[:, passes].sum(axis=1), c[:, passes].sum(axis=1), starts, ends)
        null = np.abs(zs).max(axis=-1)
    p = float((1 + (null >= observed - 1e-12).sum()) / (1 + len(null)))
    d = float(diff[best])
    size = abs(d) if effect == "diff" else abs(float(np.exp(d)) - 1.0)
    # every pass alone: the sign on the best segment
    cells_per_pass = (mask.any(axis=-1)).sum(axis=0)  # cells of each pass that hold any value
    per_pass, signs_ok = [], True
    for r in passes:
        dr, _ = scan(sums[r], counts[r], starts, ends)
        share = float(cells_per_pass[r]) / n_items
        counted = share >= MIN_PASS_SHARE_FOR_SIGN
        per_pass.append({"pass_index": int(r), "diff": float(dr[best]), "share_of_cells": share,
                         "counts_for_sign": counted})
        if counted and np.sign(dr[best]) != np.sign(d):
            signs_ok = False
    out = {
        "passes": [int(r) for r in passes], "segments": int(len(starts)), "shuffles": int(len(null)),
        "best_start": int(starts[best]), "best_end": int(ends[best]), "diff": d, "z": observed, "p": p,
        "size": size, "per_pass": per_pass, "same_sign_every_pass": signs_ok,
        "passes_line": p < alpha, "big_enough": size >= min_effect,
        "declared": bool(p < alpha and size >= min_effect and signs_ok),
        "null_95": float(np.quantile(null, 0.95)),
    }
    shape = has_drop(int(starts[best]), int(ends[best]), d, n_versions)
    support = drop_support(resid[:, passes, :], mask[:, passes, :], int(starts[best]), int(ends[best]), d)
    out["drop_shape"], out["drop_support"] = shape, support
    out["has_drop"] = bool(shape and support is not None and support >= MIN_DROP_SUPPORT)
    out["drop_named"] = bool(shape and support is not None and support >= MIN_DROP_SUPPORT_NAMED)
    # The versions before the segment, the segment, and the versions after it, each on its own (mean
    # residual; None where there is no version). A reader sees from these three numbers whether the
    # segment is a dip, a step down, or the low side of a step up.
    tot_s, tot_n = sums[passes].sum(axis=0), counts[passes].sum(axis=0)
    a, b = int(starts[best]), int(ends[best])

    def part(lo, hi):
        n = float(tot_n[lo:hi].sum())
        return None if hi <= lo or n == 0 else float(tot_s[lo:hi].sum() / n)

    out["three_parts"] = {"before": part(0, a), "segment": part(a, b + 1), "after": part(b + 1, n_versions),
                          "versions_before": a, "versions_in_segment": b - a + 1,
                          "versions_after": n_versions - 1 - b}
    if keep_null:
        out["null"] = null
    # the other segments above the line, for the table
    line = float(np.quantile(null, 1 - alpha))
    over = np.where(np.abs(z) > line)[0]
    out["segments_over_line"] = [{"start": int(starts[j]), "end": int(ends[j]), "diff": float(diff[j]),
                                  "z": float(abs(z[j]))} for j in over[np.argsort(-np.abs(z[over]))][:50]]
    return out


def opens_third_pass(two_pass_results: list[dict], open_alpha: float = OPEN_ALPHA) -> bool:
    """Section 2: after two passes, any of the scans (accuracy, thinking) points to a drop and is below
    the opening line."""
    return any(r["has_drop"] and r["p"] < open_alpha for r in two_pass_results)


def bootstrap_range(val: np.ndarray, start: int, end: int, *, effect: str = "diff", draws: int = 10_000,
                    seed: int = SEED) -> tuple[float, float]:
    """The middle 95 per cent of the segment's difference when the items are redrawn with replacement."""
    resid, mask = residuals(val)
    s_item = resid.sum(axis=1)   # [item, V]
    n_item = mask.sum(axis=1).astype(float)
    rng = np.random.default_rng(seed)
    n_items = val.shape[0]
    out = []
    for lo in range(0, draws, 1000):
        k = min(1000, draws - lo)
        pick = rng.integers(0, n_items, size=(k, n_items))
        s = s_item[pick].sum(axis=1)  # [k, V]
        n = n_item[pick].sum(axis=1)
        s_in, n_in = s[:, start:end + 1].sum(axis=1), n[:, start:end + 1].sum(axis=1)
        s_out, n_out = s.sum(axis=1) - s_in, n.sum(axis=1) - n_in
        out.append(s_in / np.maximum(n_in, 1) - s_out / np.maximum(n_out, 1))
    d = np.concatenate(out)
    if effect == "ratio":
        d = np.exp(d) - 1.0
    return float(np.quantile(d, 0.025)), float(np.quantile(d, 0.975))
