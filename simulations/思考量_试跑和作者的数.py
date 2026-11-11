"""判断标准「五之二」和第十一节里那些数的出处。只读文件，不发任何提问。

用法：python3 -I 思考量_试跑和作者的数.py
读两处：
  1. LiveNerf 作者公开的 results/daily.csv（每天 78 道题输出量的中间值）
  2. 环境变量 CCV_RAW_RECORDS 指的文件夹里试跑第 3、4、5、7 层的真题记录（每次提问的输出量和思考量）
"""
import csv
import glob
import json
import math
import os
import statistics as st

AUTHOR = os.path.join(os.environ["LIVENERF_REPO"], "results", "daily.csv")
RAW = os.environ["CCV_RAW_RECORDS"]


def author_part():
    rows = list(csv.DictReader(open(AUTHOR)))
    sel = sorted((r for r in rows if r["arm"] == "measured" and r["family"] == "all"), key=lambda r: r["date_utc"])
    pre = [r for r in sel if r["date_utc"] < "2026-11-03"]
    post = [r for r in sel if r["date_utc"] >= "2026-11-03"]
    print("一、作者每天的数（Opus 5.5，2.1.280，high，78 道题）", sel[0]["date_utc"], "到", sel[-1]["date_utc"])
    for name, g in (("11 月 3 日以前", pre), ("11 月 3 日和以后", post)):
        t = [float(r["output_tokens_median"]) for r in g]
        s = [float(r["score"]) for r in g]
        print(f"  {name}：{len(g)} 天，每天输出量中间值的平均 {st.mean(t):.0f}，最低 {min(t):.0f}，最高 {max(t):.0f}，"
              f"标准差 {st.pstdev(t):.0f}，答对率平均 {st.mean(s) * 100:.1f}%")


def load(plan):
    out = []
    for f in glob.glob(os.path.join(RAW, plan, "asks", "*.json")):
        d = json.load(open(f))
        if not str(d.get("unit", "")).startswith("item:"):
            continue
        res = None
        for line in (d.get("stdout") or "").splitlines():
            try:
                ev = json.loads(line)
            except Exception:
                continue
            if ev.get("type") == "result":
                res = ev
        if not res:
            continue
        u = res.get("usage") or {}
        out.append({"version": d["version"], "unit": d["unit"], "out": u.get("output_tokens"),
                    "think": (u.get("output_tokens_details") or {}).get("thinking_tokens")})
    return out


def paired(a_rows, b_rows, key):
    ma = {r["unit"]: r for r in a_rows}
    mb = {r["unit"]: r for r in b_rows}
    common = sorted(set(ma) & set(mb))
    lr = [math.log((mb[u][key] + 1) / (ma[u][key] + 1)) for u in common]
    m = st.mean(lr)
    se = st.stdev(lr) / math.sqrt(len(lr))
    return len(common), math.exp(m), math.exp(m - 1.96 * se), math.exp(m + 1.96 * se), st.stdev(lr)


def pilot_part():
    print("二、试跑的真题记录")
    plans = ["L3-01_author_items_2_1_280", "L4-01_author_items_2_1_280_high",
             "L5-01_stock_notools_items_280_322_high", "L7-05_blocked_items_280_322_high"]
    data = {p: load(p) for p in plans}
    for p in plans:
        byv = {}
        for r in data[p]:
            byv.setdefault(r["version"], []).append(r)
        for v, g in sorted(byv.items()):
            outs = [r["out"] for r in g]
            th = [r["think"] for r in g]
            print(f"  {p} {v}：{len(g)} 次，输出量中间值 {st.median(outs):.0f}，平均 {st.mean(outs):.0f}，"
                  f"思考量中间值 {st.median(th):.0f}，平均 {st.mean(th):.0f}，一点没想的 {sum(1 for t in th if t == 0)} 次")
        if len(byv) == 2:
            a, b = sorted(byv)
            n, r, lo, hi, sd = paired(byv[a], byv[b], "think")
            print(f"    同一道题 {b} 比 {a}：{n} 道，思考量是 {r:.2f} 倍（{lo:.2f} 到 {hi:.2f}），对数差的标准差 {sd:.2f}")
    n, r, lo, hi, sd = paired(data[plans[1]], data[plans[0]], "think")
    print(f"  照作者那样问，2.1.280，low 比 high：{n} 道，思考量是 {r:.2f} 倍（{lo:.2f} 到 {hi:.2f}）")
    n, r, lo, hi, sd = paired(data[plans[1]], data[plans[0]], "out")
    print(f"    输出量是 {r:.2f} 倍（{lo:.2f} 到 {hi:.2f}）")


def rough_power(sd_pair=1.27, items=78, versions=39, factor=4.1):
    print("三、能看出多大的差别（粗算）。factor 取 4.1，是拿同样的算法去凑答对率模拟四的数得来的")
    s = sd_pair / math.sqrt(2)
    for passes in (2, 3):
        k = versions // 2
        se_seg = s * math.sqrt(1 / (items * k * passes) + 1 / (items * (versions - k) * passes))
        se_one = s * math.sqrt(1 / (items * passes) + 1 / (items * (versions - 1) * passes))
        print(f"  {passes} 遍：整段约少 {100 * (1 - math.exp(-factor * se_seg)):.0f}%，单个版本约少 {100 * (1 - math.exp(-factor * se_one)):.0f}%")


if __name__ == "__main__":
    author_part()
    pilot_part()
    rough_power()
