# 检查：变低开始得很早、前面只有四五个版本可比时，「说有差别」的里面有多少也够得上「说变低」。
# 模拟五没有放这种情景。不发任何提问。2026-11-11 傍晚写的，正式开跑之前。
#
# 造数据的办法跟模拟五一样（每道题的答对机会取自 LiveNerf 作者公开的试答结果，对的次数加 1，除以 10），
# 整套做法也一样：跑两遍，照 judge.opens_third_pass 决定开不开第三遍，最后照 judge.judge 下结论。
# 算法直接调用 ../ccversions/judge.py。
#
# 用法：LIVENERF_REPO=<LiveNerf 仓库> python3 -I 这个文件 每种情景造几份 每份打乱几次 [几个进程]
import json
import os
import sys
from multiprocessing import Pool
from statistics import NormalDist

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.dont_write_bytecode = True
from ccversions import judge  # noqa: E402

PANEL = os.path.join(os.environ["LIVENERF_REPO"], "data", "standard_panel.json")
V, I, R = 39, 78, 3


def item_chances() -> np.ndarray:
    d = json.load(open(PANEL))
    return np.array([(f["calibration"][i]["confirm_passes"] + 1) / (f["calibration"][i]["confirm_samples"] + 2)
                     for f in d["families"].values() for i in f["ids"]], float)


def shifted(p: np.ndarray, points: float) -> np.ndarray:
    logit = np.log(p / (1 - p))
    lo, hi = 0.0, 10.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if np.abs(p - 1 / (1 + np.exp(-(logit - mid)))).mean() < points / 100:
            lo = mid
        else:
            hi = mid
    return 1 / (1 + np.exp(-(logit - (lo + hi) / 2)))


def scenarios():
    sc = []
    for before in (4, 5):
        sc += [(f"前面{before}个版本_之后一直到最新都低{x}个点", before, V - before, x) for x in (4, 5)]
        sc += [(f"前面{before}个版本_接着13个版本低{x}个点", before, 13, x) for x in (5, 6)]
        sc += [(f"前面{before}个版本_接着6个版本低{x}个点", before, 6, x) for x in (7, 8)]
    return sc


def tally(task):
    si, (name, before, length, points), n, shuffles = task
    p0 = item_chances()
    rng = np.random.default_rng([judge.SEED, 6, si])
    chance = np.repeat(p0[:, None], V, axis=1)
    chance[:, before:before + length] = shifted(p0, points)[:, None]
    cut = np.array([[NormalDist().inv_cdf(min(max(x, 1e-9), 1 - 1e-9)) for x in row] for row in chance])
    declared = named = opened = 0
    for _ in range(n):
        val = (rng.standard_normal((I, R, V)) < cut[:, None, :]).astype(float)
        resid, mask = judge.residuals(val)
        sh = judge.shuffled_pass_sums(resid, mask, shuffles, rng)
        two = judge.judge(val, passes=[0, 1], min_effect=judge.MIN_DIFF_ACCURACY, shuffled=sh)
        third = judge.opens_third_pass([two])
        res = judge.judge(val, passes=[0, 1, 2], min_effect=judge.MIN_DIFF_ACCURACY, shuffled=sh) if third else two
        opened += third
        declared += res["declared"]
        named += res["declared"] and res["drop_named"]
    return {"情景": name, "造了几份": n, "开了第三遍": round(opened / n, 4), "说有差别": round(declared / n, 4),
            "说变低": round(named / n, 4), "说有差别的里面说变低的": round(named / declared, 4) if declared else None}


def main():
    n, shuffles = int(sys.argv[1]), int(sys.argv[2])
    procs = int(sys.argv[3]) if len(sys.argv) > 3 else 8
    tasks = [(si, sc, n, shuffles) for si, sc in enumerate(scenarios())]
    with Pool(procs) as pool:
        for row in pool.imap(tally, tasks):
            print(json.dumps(row, ensure_ascii=False), flush=True)
    print("每份打乱", shuffles, "次")


if __name__ == "__main__":
    main()
