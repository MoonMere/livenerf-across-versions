# 模拟五：整套「先跑两遍，照两遍的数决定开不开第三遍」的做法，看错的机会有多大、能看出多大的差别。
# 不发任何提问。2026-11-11 下午写的，正式开跑之前。
#
# 算法不在这份文件里重写：直接调用跑结果时用的那份程序 程序/ccversions/judge.py，
# 所以这里算出来的数，就是正式算结果时那套代码的数。
#
# 用法：python3 -I 这个文件 每种情景造几份数据 每份打乱几次 [几个进程] [只跑名字里带这几个字的情景]
#
# 造数据的办法跟模拟一到模拟四一样：每道题的答对机会取自 LiveNerf 作者公开的试答结果
# （对的次数加 1，除以 10），一个版本答一遍，答对率上下晃约 4.9 个百分点。
# 思考量：每次提问的对数思考量是题目的水平加一个随机晃动，晃动的标准差 0.90
# （试跑第 5 层两个版本同一道题的对数差标准差 1.27，除以根号 2）。
# 同一次提问里答对不答对和想得多不多可以有关联，用「关联」这个参数调，0 是没有关联。
import json
import math
import os
import sys
import time
from multiprocessing import Pool
from statistics import NormalDist

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.dont_write_bytecode = True
from ccversions import judge  # noqa: E402

PANEL = os.path.join(os.environ["LIVENERF_REPO"], "data", "standard_panel.json")
V, I, R = 39, 78, 3
THINK_SD = 0.90
OPEN_LINES = (0.10, 0.15, 0.20, 0.25)


def item_chances() -> np.ndarray:
    d = json.load(open(PANEL))
    k = []
    for fam in d["families"].values():
        for iid in fam["ids"]:
            c = fam["calibration"][iid]
            k.append((c["confirm_passes"] + 1) / (c["confirm_samples"] + 2))
    return np.array(k, float)


def shifted(p: np.ndarray, points: float) -> np.ndarray:
    """The chances after a drop of `points` percentage points on average (a rise when negative)."""
    if points == 0:
        return p.copy()
    logit = np.log(p / (1 - p))
    lo, hi = 0.0, 10.0
    sign = 1.0 if points > 0 else -1.0
    for _ in range(60):
        mid = (lo + hi) / 2
        change = np.abs(p - 1 / (1 + np.exp(-(logit - sign * mid)))).mean()
        if change < abs(points) / 100:
            lo = mid
        else:
            hi = mid
    return 1 / (1 + np.exp(-(logit - sign * (lo + hi) / 2)))


def one_dataset(rng, p0, affected, points, think_change, rho, shuffles, third_share):
    chance = np.repeat(p0[:, None], V, axis=1)
    if points:
        ps = shifted(p0, points)
        for v in affected:
            chance[:, v] = ps
    cut = np.array([[NormalDist().inv_cdf(min(max(x, 1e-9), 1 - 1e-9)) for x in row] for row in chance])
    g = rng.standard_normal((I, R, V))
    acc = (g < cut[:, None, :]).astype(float)
    think = THINK_SD * (rho * g + math.sqrt(1 - rho * rho) * rng.standard_normal((I, R, V)))
    if think_change:
        think[:, :, affected] += math.log(1 + think_change)
    if third_share < 1:  # the third pass stopped early: only the first share of its cells exist
        keep = int(round(I * third_share))
        order = rng.permutation(I)
        acc[order[keep:], 2, :] = np.nan
        think[order[keep:], 2, :] = np.nan
    out = {}
    for name, val, min_effect, effect in (("acc", acc, judge.MIN_DIFF_ACCURACY, "diff"),
                                          ("think", think, judge.MIN_RATIO_THINKING, "ratio")):
        resid, mask = judge.residuals(val)
        sh = judge.shuffled_pass_sums(resid, mask, shuffles, rng)
        two = judge.judge(val, passes=[0, 1], min_effect=min_effect, effect=effect, shuffled=sh)
        three = judge.judge(val, passes=[0, 1, 2], min_effect=min_effect, effect=effect, shuffled=sh)
        out[name] = (two, three)
    return out


def tally(task):
    name, affected, points, think_change, rho, third_share, n, shuffles, seed = task
    p0 = item_chances()
    rng = np.random.default_rng(seed)
    keys = ["两遍_答对率过线", "三遍_答对率过线", "两遍_思考量过线", "三遍_思考量过线"]
    for a in OPEN_LINES:
        keys += [f"开线{a}_开了第三遍", f"开线{a}_答对率说有差别", f"开线{a}_思考量说有差别",
                 f"开线{a}_两样里至少一样说有差别", f"开线{a}_答对率说变低", f"开线{a}_思考量说变少"]
    c = dict.fromkeys(keys, 0)
    for _ in range(n):
        res = one_dataset(rng, p0, affected, points, think_change, rho, shuffles, third_share)
        a2, a3 = res["acc"]
        t2, t3 = res["think"]
        c["两遍_答对率过线"] += a2["declared"]
        c["三遍_答对率过线"] += a3["declared"]
        c["两遍_思考量过线"] += t2["declared"]
        c["三遍_思考量过线"] += t3["declared"]
        for a in OPEN_LINES:
            opened = judge.opens_third_pass([a2, t2], a)
            fa, ft = (a3, t3) if opened else (a2, t2)
            c[f"开线{a}_开了第三遍"] += opened
            c[f"开线{a}_答对率说有差别"] += fa["declared"]
            c[f"开线{a}_思考量说有差别"] += ft["declared"]
            c[f"开线{a}_两样里至少一样说有差别"] += fa["declared"] or ft["declared"]
            c[f"开线{a}_答对率说变低"] += fa["declared"] and fa["drop_named"]
            c[f"开线{a}_思考量说变少"] += ft["declared"] and ft["drop_named"]
    return name, n, c


def scenarios():
    tail = list(range(21, 39))
    mid = list(range(18, 31))
    last6 = list(range(33, 39))
    three = [24, 25, 26]
    sc = [("没有差别", [], 0, 0.0)]
    sc += [(f"答对率_从第22个版本起整段变低{x}个点", tail, x, 0.0) for x in (3, 4, 5)]
    sc += [(f"答对率_中间13个版本变低{x}个点", mid, x, 0.0) for x in (4, 5, 6)]
    sc += [(f"答对率_最后6个版本变低{x}个点", last6, x, 0.0) for x in (5, 6, 7, 8)]
    sc += [(f"答对率_连着3个版本变低{x}个点", three, x, 0.0) for x in (7, 8, 9, 10)]
    sc += [(f"答对率_单个版本变低{x}个点", [25], x, 0.0) for x in (12, 15, 18)]
    sc += [(f"答对率_从第22个版本起整段变高{x}个点", tail, -x, 0.0) for x in (4, 5)]
    sc += [(f"思考量_从第22个版本起整段变少{int(x * 100)}%", tail, 0, -x) for x in (0.08, 0.10, 0.12, 0.15)]
    sc += [(f"思考量_单个版本变少{int(x * 100)}%", [25], 0, -x) for x in (0.25, 0.30, 0.40)]
    return sc


def main():
    n = int(sys.argv[1])
    shuffles = int(sys.argv[2])
    procs = int(sys.argv[3]) if len(sys.argv) > 3 else 8
    only = sys.argv[4] if len(sys.argv) > 4 else ""
    tasks = []
    t0 = time.time()
    for si, (name, affected, points, think_change) in enumerate(scenarios()):
        variants = [(name, 0.0, 1.0)]
        if name == "没有差别":
            variants = [("没有差别", 0.0, 1.0), ("没有差别_答对和思考有关联0.5", 0.5, 1.0),
                        ("没有差别_第三遍只跑了一半", 0.0, 0.5), ("没有差别_第三遍只跑了四分之一", 0.0, 0.25)]
        for vi, (vname, rho, share) in enumerate(variants):
            if only and only not in vname:
                continue
            total = n * 10 if vname.startswith("没有差别") else n
            chunks = max(1, min(procs * 2, total // 25))
            for ci in range(chunks):
                size = total // chunks + (1 if ci < total % chunks else 0)
                tasks.append((vname, affected, points, think_change, rho, share, size, shuffles,
                              [judge.SEED, 5, si, vi, ci]))
    sums, counts, order = {}, {}, []
    with Pool(procs) as pool:
        for name, k, c in pool.imap_unordered(tally, tasks):
            if name not in sums:
                sums[name], counts[name] = dict.fromkeys(c, 0), 0
                order.append(name)
            counts[name] += k
            for key, v in c.items():
                sums[name][key] += v
    names = [v for v in dict.fromkeys(t[0] for t in tasks)]
    for name in names:
        print(json.dumps({"情景": name, "造了几份": counts[name],
                          **{k: round(v / counts[name], 4) for k, v in sums[name].items()}}, ensure_ascii=False))
    print("每份打乱", shuffles, "次，用时", round(time.time() - t0), "秒")


if __name__ == "__main__":
    main()
