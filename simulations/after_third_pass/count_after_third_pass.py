"""After a third pass has opened: how often identical versions still end in a declared difference.

Item 12 of the change log entry "13 November 2026: extra numbers and wordings, fixed before the
reports are opened" in PREREGISTRATION.md promises this number and says it is counted with
simulation 5.

Simulation 5 counts, over every made-up dataset of a scenario, how often the whole procedure declares
a difference. This program makes the same datasets (same scenarios, same number of datasets, same
shuffles, same seeds) and counts the same outcomes over the datasets in which the third pass opened.
It also splits those datasets by the test that opened the third pass: accuracy alone, thinking alone,
or both.

Only the four scenarios with no difference between versions are run.

The arithmetic is all in the two registered files, and neither is changed. The made-up data and the
tests come from simulation 5 (`scenarios`, `item_chances`, `one_dataset`), and the opening rule and
the seed come from `ccversions/judge.py`, which simulation 5 loads (`opens_third_pass`, `OPEN_ALPHA`,
`SEED`). Two small pieces of simulation 5's `main()` are copied here, because they sit inside that
function: the list of the four scenarios with no difference, and the way a scenario is cut into
chunks. The check below shows whether the copy is exact.

Why the same datasets need care: simulation 5 cuts each scenario into chunks, and the chunk index is
part of each chunk's seed. How many chunks there are depends on the number of processes simulation 5
was given, which was 9 for the registered output. This program cuts the chunks as simulation 5 would
with that number (--seed-processes) and runs them on as many worker processes as it is told
(--workers). The two numbers are separate, so a smaller machine makes the same datasets.

The check: before the new tables, this program recounts every share that the registered output of
simulation 5 gives for these four scenarios (opening lines 0.10, 0.15, 0.20 and 0.25, two passes,
three passes, the whole procedure) and compares each with the registered figure at the four decimals
printed there. The new numbers stand on those datasets only when every share is the same.

The 95% ranges are Clopper-Pearson intervals for a share of datasets. They show how far a share could
move with another set of made-up datasets of the same size. They say nothing about how close the
made-up data are to the real run.

Usage:

    export LIVENERF_REPO=/path/to/livenerf     # the outputs of simulation 5 used commit 3febff63
    python3 -B -I count_after_third_pass.py \\
        --sim5 path/to/模拟五_看了两遍再定开不开第三遍.py \\
        --registered path/to/输出五_看了两遍再定开不开第三遍.txt \\
        --workers 4

The other defaults are those of the registered output: 400 datasets per scenario (simulation 5 makes
ten times as many, 4,000, for each scenario with no difference), 1,000 shuffles per dataset, and 9
processes for the seeds.

Outputs, named by --out-prefix (default: next to this file):
    <prefix>.txt            the tables, for reading
    <prefix>.json           the same counts, for programs
    <prefix>_datasets.csv   one line per made-up dataset, so that any count here can be redone
"""

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import os
import platform
import sys
import time

# Keep the folders of simulation 5 and judge.py free of cache files.
sys.dont_write_bytecode = True
# One core per worker process.
for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS",
             "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_var, "1")

from multiprocessing import Pool  # noqa: E402

import numpy as np  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

# Copied from simulation 5's main(): the scenario with no difference and its four variants
# (name, correlation between right answers and thinking within an ask, share of the third pass run).
NULL_SCENARIO = "没有差别"
NULL_VARIANTS = [("没有差别", 0.0, 1.0), ("没有差别_答对和思考有关联0.5", 0.5, 1.0),
                 ("没有差别_第三遍只跑了一半", 0.0, 0.5), ("没有差别_第三遍只跑了四分之一", 0.0, 0.25)]
# Copied from simulation 5's main(): scenarios whose names start with this get ten times the datasets.
NULL_FACTOR = 10

ENGLISH = {
    "没有差别": "no difference, third pass finished",
    "没有差别_答对和思考有关联0.5": "no difference, right answers and long thinking linked within an ask "
                                   "(correlation 0.5), third pass finished",
    "没有差别_第三遍只跑了一半": "no difference, third pass stopped half way",
    "没有差别_第三遍只跑了四分之一": "no difference, third pass stopped a quarter of the way",
}

TESTS = ("acc", "think")
PASS_SETS = ("two", "three")
FIELDS = ("p", "has_drop", "declared", "drop_named", "best_start", "best_end", "diff")

GROUPS = [
    ("all", "every dataset (the whole procedure, as in section 4)"),
    ("opened", "third pass opened (by either test)"),
    ("opened_acc_only", "third pass opened by the accuracy test alone"),
    ("opened_think_only", "third pass opened by the thinking test alone"),
    ("opened_both", "third pass opened, both tests met the opening rule"),
    ("not_opened", "third pass not opened"),
]
OUTCOMES = [
    ("acc_declared", "accuracy difference declared"),
    ("think_declared", "thinking difference declared"),
    ("either_declared", "at least one of the two declared"),
    ("acc_lower", "accuracy declared and called lower"),
    ("think_less", "thinking declared and called less"),
]


def load_sim5(path):
    spec = importlib.util.spec_from_file_location("simulation5", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["simulation5"] = module
    spec.loader.exec_module(module)
    return module


_SIM5 = None


def _init_worker(sim5_path):
    global _SIM5
    _SIM5 = load_sim5(sim5_path)


def run_chunk(task):
    """One chunk, made the way simulation 5's tally() makes it: a generator from the chunk's seed, then
    one_dataset() called on it once per dataset, in order. tally() draws nothing else from the generator,
    so the datasets here are the datasets there. Returns one record per dataset."""
    sim5 = _SIM5
    (vname, affected, points, think_change, rho, share, n, shuffles, seed), chunk = task
    p0 = sim5.item_chances()
    rng = np.random.default_rng(seed)
    rows = []
    for j in range(n):
        res = sim5.one_dataset(rng, p0, affected, points, think_change, rho, shuffles, share)
        row = {"scenario": vname, "chunk": chunk, "dataset": j}
        for test in TESTS:
            for label, r in zip(PASS_SETS, res[test]):
                for f in FIELDS:
                    row[f"{test}_{label}_{f}"] = r[f]
        rows.append(row)
    return vname, chunk, rows


def build_tasks(sim5, n, shuffles, seed_processes):
    """The chunks of the four scenarios with no difference, cut as simulation 5's main() cuts them when
    it is given `seed_processes` processes."""
    judge = sim5.judge
    tasks = []
    for si, (name, affected, points, think_change) in enumerate(sim5.scenarios()):
        if name != NULL_SCENARIO:
            continue
        for vi, (vname, rho, share) in enumerate(NULL_VARIANTS):
            total = n * NULL_FACTOR
            chunks = max(1, min(seed_processes * 2, total // 25))
            for ci in range(chunks):
                size = total // chunks + (1 if ci < total % chunks else 0)
                tasks.append(((vname, affected, points, think_change, rho, share, size, shuffles,
                               [judge.SEED, 5, si, vi, ci]), ci))
    return tasks


def result_of(row, test, label):
    return {f: row[f"{test}_{label}_{f}"] for f in FIELDS}


def recount_registered(rows, judge, open_lines):
    """The shares of simulation 5's output, counted with the formulas of its tally()."""
    keys = ["两遍_答对率过线", "三遍_答对率过线", "两遍_思考量过线", "三遍_思考量过线"]
    for a in open_lines:
        keys += [f"开线{a}_开了第三遍", f"开线{a}_答对率说有差别", f"开线{a}_思考量说有差别",
                 f"开线{a}_两样里至少一样说有差别", f"开线{a}_答对率说变低", f"开线{a}_思考量说变少"]
    c = dict.fromkeys(keys, 0)
    for row in rows:
        a2, a3 = result_of(row, "acc", "two"), result_of(row, "acc", "three")
        t2, t3 = result_of(row, "think", "two"), result_of(row, "think", "three")
        c["两遍_答对率过线"] += a2["declared"]
        c["三遍_答对率过线"] += a3["declared"]
        c["两遍_思考量过线"] += t2["declared"]
        c["三遍_思考量过线"] += t3["declared"]
        for a in open_lines:
            opened = judge.opens_third_pass([a2, t2], a)
            fa, ft = (a3, t3) if opened else (a2, t2)
            c[f"开线{a}_开了第三遍"] += opened
            c[f"开线{a}_答对率说有差别"] += fa["declared"]
            c[f"开线{a}_思考量说有差别"] += ft["declared"]
            c[f"开线{a}_两样里至少一样说有差别"] += fa["declared"] or ft["declared"]
            c[f"开线{a}_答对率说变低"] += fa["declared"] and fa["drop_named"]
            c[f"开线{a}_思考量说变少"] += ft["declared"] and ft["drop_named"]
    return {k: int(v) for k, v in c.items()}


def count_groups(rows, judge, line):
    """At the registered opening line: for each group of datasets, how many there are and how many end in
    each outcome. The final result is the three-pass test when the third pass opened and the two-pass
    test when it did not, as in simulation 5."""
    counts = {g: dict(n=0, **{o: 0 for o, _ in OUTCOMES}) for g, _ in GROUPS}
    for row in rows:
        a2, a3 = result_of(row, "acc", "two"), result_of(row, "acc", "three")
        t2, t3 = result_of(row, "think", "two"), result_of(row, "think", "three")
        by_acc = bool(judge.opens_third_pass([a2], line))
        by_think = bool(judge.opens_third_pass([t2], line))
        opened = bool(judge.opens_third_pass([a2, t2], line))
        if opened != (by_acc or by_think):
            raise RuntimeError("the split by test does not add up to the opening rule")
        fa, ft = (a3, t3) if opened else (a2, t2)
        out = {
            "acc_declared": bool(fa["declared"]),
            "think_declared": bool(ft["declared"]),
            "either_declared": bool(fa["declared"] or ft["declared"]),
            "acc_lower": bool(fa["declared"] and fa["drop_named"]),
            "think_less": bool(ft["declared"] and ft["drop_named"]),
        }
        groups = ["all"]
        if opened:
            groups.append("opened")
            groups.append("opened_both" if by_acc and by_think else
                          "opened_acc_only" if by_acc else "opened_think_only")
        else:
            groups.append("not_opened")
        for g in groups:
            counts[g]["n"] += 1
            for o, _ in OUTCOMES:
                counts[g][o] += out[o]
    return counts


def _binom_cdf(k, n, p):
    """P(X <= k) for X ~ Binomial(n, p)."""
    if k < 0:
        return 0.0
    if k >= n:
        return 1.0
    if p <= 0.0:
        return 1.0
    if p >= 1.0:
        return 0.0
    lp, lq = math.log(p), math.log1p(-p)
    lgn = math.lgamma(n + 1)
    terms = [lgn - math.lgamma(i + 1) - math.lgamma(n - i + 1) + i * lp + (n - i) * lq for i in range(k + 1)]
    top = max(terms)
    return min(1.0, math.exp(top) * sum(math.exp(t - top) for t in terms))


def _solve(f, target, rising):
    """The p in (0, 1) where f crosses target, by halving the interval. f rises with p when rising is
    True and falls with p otherwise."""
    lo, hi = 0.0, 1.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if (f(mid) < target) == rising:
            lo = mid
        else:
            hi = mid
        if hi - lo < 1e-13:
            break
    return (lo + hi) / 2


def clopper_pearson(k, n, level=0.95):
    if n == 0:
        return None, None
    tail = (1 - level) / 2
    # lower end: P(X >= k) = tail, which rises with p. Upper end: P(X <= k) = tail, which falls with p.
    lower = 0.0 if k == 0 else _solve(lambda p: 1 - _binom_cdf(k - 1, n, p), tail, rising=True)
    upper = 1.0 if k == n else _solve(lambda p: _binom_cdf(k, n, p), tail, rising=False)
    return lower, upper


def read_registered(path):
    lines = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line.startswith("{"):
                d = json.loads(line)
                lines[d["情景"]] = d
    return lines


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def pct(x):
    return "n/a" if x is None else f"{100 * x:.2f}%"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--sim5", required=True, help="simulation 5, 模拟五_看了两遍再定开不开第三遍.py")
    ap.add_argument("--registered", required=True,
                    help="the registered output of simulation 5, 输出五_看了两遍再定开不开第三遍.txt")
    ap.add_argument("--datasets-per-scenario", type=int, default=400,
                    help="simulation 5's first argument (scenarios with no difference get ten times this)")
    ap.add_argument("--shuffles", type=int, default=1000, help="simulation 5's second argument")
    ap.add_argument("--seed-processes", type=int, default=9,
                    help="simulation 5's third argument, which sets the chunks and so the seeds")
    ap.add_argument("--workers", type=int, default=4, help="worker processes actually used")
    ap.add_argument("--out-prefix", default=os.path.join(HERE, "output_after_third_pass"))
    args = ap.parse_args()

    t0 = time.time()
    sim5 = load_sim5(os.path.abspath(args.sim5))
    judge = sim5.judge
    line = judge.OPEN_ALPHA
    tasks = build_tasks(sim5, args.datasets_per_scenario, args.shuffles, args.seed_processes)
    print(f"{len(tasks)} chunks on {args.workers} workers, opening line {line}", file=sys.stderr, flush=True)

    rows_by = {}
    with Pool(args.workers, initializer=_init_worker, initargs=(os.path.abspath(args.sim5),)) as pool:
        for done, (vname, chunk, rows) in enumerate(pool.imap_unordered(run_chunk, tasks), 1):
            rows_by[(vname, chunk)] = rows
            print(f"[{time.time() - t0:7.0f} s] chunk {done}/{len(tasks)} done: {vname}, chunk {chunk}, "
                  f"{len(rows)} datasets", file=sys.stderr, flush=True)
    elapsed = time.time() - t0

    registered = read_registered(args.registered)
    result = {"provenance": {}, "check": {}, "groups": {}}
    prov = result["provenance"]
    prov["finished_utc"] = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
    prov["python"] = platform.python_version()
    prov["numpy"] = np.__version__
    prov["datasets_per_scenario_argument"] = args.datasets_per_scenario
    prov["shuffles_per_dataset"] = args.shuffles
    prov["seed_processes"] = args.seed_processes
    prov["workers"] = args.workers
    prov["opening_line"] = line
    prov["seconds"] = round(elapsed)
    prov["sha256"] = {
        os.path.basename(args.sim5): sha256(args.sim5),
        "ccversions/judge.py": sha256(judge.__file__),
        "LiveNerf data/standard_panel.json": sha256(sim5.PANEL),
        os.path.basename(args.registered): sha256(args.registered),
    }

    all_rows = []
    all_match = True
    for vname, _, _ in NULL_VARIANTS:
        chunks = sorted(c for (v, c) in rows_by if v == vname)
        rows = [r for c in chunks for r in rows_by[(vname, c)]]
        all_rows += rows
        n = len(rows)
        mine = recount_registered(rows, judge, sim5.OPEN_LINES)
        reg = registered.get(vname)
        check = {"datasets": n, "registered_datasets": None if reg is None else reg["造了几份"], "shares": {}}
        ok = reg is not None and reg["造了几份"] == n
        for key, k in mine.items():
            share = round(k / n, 4)
            reg_share = None if reg is None else reg.get(key)
            same = reg_share is not None and share == reg_share
            ok = ok and same
            check["shares"][key] = {"count": k, "share": share, "registered": reg_share, "same": same}
        if reg is not None:
            for key in reg:
                if key not in ("情景", "造了几份") and key not in mine:
                    ok = False
                    check["shares"][key] = {"count": None, "share": None, "registered": reg[key], "same": False}
        check["all_same"] = ok
        all_match = all_match and ok
        result["check"][vname] = check

        g = count_groups(rows, judge, line)
        out = {}
        for gname, _ in GROUPS:
            m = g[gname]["n"]
            out[gname] = {"datasets": m, "share_of_all": g[gname]["n"] / n if n else None, "outcomes": {}}
            for o, _ in OUTCOMES:
                k = g[gname][o]
                lo, hi = clopper_pearson(k, m)
                out[gname]["outcomes"][o] = {"count": k, "of": m, "share": k / m if m else None,
                                             "range95": [lo, hi]}
        result["groups"][vname] = out
    result["check_all_same"] = all_match

    prefix = args.out_prefix
    with open(prefix + ".json", "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=1)

    cols = ["scenario", "chunk", "dataset"] + [f"{t}_{s}_{f}" for t in TESTS for s in PASS_SETS for f in FIELDS]
    with open(prefix + "_datasets.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in all_rows:
            w.writerow({k: (int(v) if isinstance(v, (bool, np.bool_)) else v) for k, v in r.items()})

    L = []
    L.append("After a third pass has opened: identical versions, simulation 5's datasets")
    L.append("")
    L.append(f"Finished {prov['finished_utc']} UTC after {prov['seconds']} seconds on {args.workers} worker "
             f"processes. Python {prov['python']}, numpy {prov['numpy']}.")
    L.append(f"Datasets per scenario argument {args.datasets_per_scenario} (x{NULL_FACTOR} for these scenarios), "
             f"{args.shuffles} shuffles per dataset, chunks and seeds as with {args.seed_processes} processes.")
    L.append(f"Opening line for the tables: {line} (judge.OPEN_ALPHA).")
    L.append("SHA-256 of the files used:")
    for name, h in prov["sha256"].items():
        L.append(f"  {h}  {name}")
    L.append("")
    L.append("1. Check against the registered output of simulation 5")
    L.append("")
    L.append("Each share below is recounted from this program's datasets with the formulas of simulation 5's")
    L.append("tally() and compared with the registered line at the four decimals printed there.")
    L.append("")
    for vname, _, _ in NULL_VARIANTS:
        c = result["check"][vname]
        same = sum(1 for v in c["shares"].values() if v["same"])
        L.append(f"{vname} ({ENGLISH[vname]}): datasets {c['datasets']} here, {c['registered_datasets']} "
                 f"registered. {same} of {len(c['shares'])} shares the same."
                 + ("" if c["all_same"] else " NOT ALL THE SAME."))
        for key, v in c["shares"].items():
            mark = "same" if v["same"] else "DIFFERENT"
            L.append(f"    {key:<24} here {v['count']}/{c['datasets']} = {v['share']}   registered {v['registered']}"
                     f"   {mark}")
        L.append("")
    L.append("Every share the same: " + ("yes" if all_match else "NO"))
    L.append("")
    L.append(f"2. Shares at the registered opening line {line}")
    L.append("")
    L.append("The final result is the test on three passes when the third pass opened and on two passes when")
    L.append("it did not. \"Opened by the accuracy test\" means that the accuracy test on two passes points to a")
    L.append("drop (has_drop) with p below the line. Ranges are 95% Clopper-Pearson intervals.")
    for vname, _, _ in NULL_VARIANTS:
        L.append("")
        L.append(f"{vname} ({ENGLISH[vname]})")
        out = result["groups"][vname]
        for gname, gtext in GROUPS:
            gg = out[gname]
            L.append(f"  {gtext}: {gg['datasets']} datasets ({pct(gg['share_of_all'])} of all)")
            for o, otext in OUTCOMES:
                v = gg["outcomes"][o]
                lo, hi = v["range95"]
                L.append(f"      {otext:<36} {pct(v['share']):>7}   {v['count']:>4} of {v['of']:<5}"
                         f"   95% range {pct(lo)} to {pct(hi)}")
    text = "\n".join(L) + "\n"
    with open(prefix + ".txt", "w", encoding="utf-8") as fh:
        fh.write(text)
    print(text)
    if not all_match:
        sys.exit(1)


if __name__ == "__main__":
    main()
