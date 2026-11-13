#!/bin/bash
# 2026-11-13 夜里加的两组，照登记的先后发：
#   开到 xhigh 的一组第 1 到 5 遍 → high 那一组第 1 到 12 遍（第一段）→ gate.py 照规则定发不发第二段
#   → 规则说发，就发 high 那一组第 13 到 24 遍（第二段）。
# 每一步都只调 driver.py 和 gate.py，它们的说明在各自文件开头。哪一步没有正常结束，后面的都不发。
# 用法：nohup caffeinate -i -s bash 全部发.sh &   屏幕输出和每一步的结束码都记在 本机数据/再验少想/全部发.log
set -u
BASE="/Users/scott/Documents/Claude/LiveNerf实验"
S="$BASE/本机数据/再验少想/设置.toml"
PY="$BASE/本机数据/python环境/bin/python"
LOG="$BASE/本机数据/再验少想/全部发.log"
cd "$BASE/程序/再验少想" || exit 9
say() { echo "$(date -u +%FT%TZ) CHAIN $*" >> "$LOG"; }

say "start pid $$"
"$PY" -B driver.py --settings "$S" --config run_x.json --first 1 --last 5 >> "$LOG" 2>&1; rc=$?
say "xhigh_recheck passes 1-5 ended, exit $rc"
if [ $rc -ne 0 ]; then say "end: stopped after xhigh_recheck"; exit $rc; fi

"$PY" -B driver.py --settings "$S" --config run_h.json --first 1 --last 12 >> "$LOG" 2>&1; rc=$?
say "high_recheck passes 1-12 ended, exit $rc"
if [ $rc -ne 0 ]; then say "end: stopped in stage 1 of high_recheck"; exit $rc; fi

"$PY" -B gate.py --settings "$S" --config run_h.json --out "$BASE/本机数据/再验少想/h/gate.json" >> "$LOG" 2>&1; rc=$?
say "gate ended, exit $rc (0: stage 2 is sent, 1: stage 2 is not sent, 2: no decision)"
if [ $rc -eq 0 ]; then
  "$PY" -B driver.py --settings "$S" --config run_h.json --first 13 --last 24 >> "$LOG" 2>&1; rc=$?
  say "high_recheck passes 13-24 ended, exit $rc"
fi
say "end"
exit 0
