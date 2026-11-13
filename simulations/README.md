# Simulations

These programs make up data and run the rule on it. None of them asks a model anything. Every number in PREREGISTRATION.md that comes from a simulation comes from one of the outputs kept here.

The file names, comments and output keys are in Chinese, because these were working files. The tables below say what each one is and what the keys mean.

## The files

| File | What it is | Used in PREREGISTRATION.md |
|---|---|---|
| `模拟五_看了两遍再定开不开第三遍.py` | Simulation 5. The whole procedure on made-up data: two passes, the rule for a third, the final test, for accuracy and thinking together. It calls `../ccversions/judge.py` and doesn't rewrite any of the arithmetic. Scenarios with no difference get 10 times as many datasets as the others | sections 4, 6 and 7 |
| `输出五_看了两遍再定开不开第三遍.txt` | Its output, final round: 400 datasets per scenario (4,000 with no difference), 1,000 shuffles each, 9 processes | same |
| `输出五_第一版_变低只看位置.txt` | The output of the first round, when "points to a drop" looked at the shape alone. It came from an earlier state of simulation 5 and of `judge.py`, before the step check was added. That earlier state is not kept | "about 4 times in 10", section 4 |
| `检查_变低开始得很早.py` | The check of early drops: a drop after only 4 or 5 versions, either lasting to the newest version or a run of 13 or 6 versions. Same made-up data and procedure as simulation 5, accuracy only, so only the accuracy scan can open the third pass here | sections 5 and 7 |
| `输出_检查_变低开始得很早.txt` | Its output: 300 datasets per scenario, 1,000 shuffles, 9 processes | same |
| `模拟二_垫底版本加跑.py` | Simulation 2, for an earlier rule that re-ran the three lowest versions (later dropped). Its last three output lines, with no difference at all, give the gap between the best and worst of 39 versions after one, two and three passes | about 15 and 12 points, section 7 |
| `输出二_垫底版本加跑_第一批.txt` | Its output | same |
| `模拟三_点名一刀和任意一段.py` | Simulation 3, for an earlier rule with a cut named in advance at 2.1.303 beside the scan, each at a 2% line | about 3.7 points, section 11 |
| `输出三_两遍.txt` | Its output for two passes: 300 datasets per scenario (900 with no difference), 600 shuffles | same |
| `模拟四_去掉点名一刀_任意一段的线放到4%.py` | Simulation 4, the scan alone at lines of 2%, 4% and 5%, from before the third pass rule. Kept as a record | none now |
| `输出四_两遍.txt`, `输出四_三遍.txt` | Its output for two and three passes, same sizes as simulation 3 | none now |
| `模拟一_几种判法对比.py` | Simulation 1, which compared early forms of the rule. Simulations 3 and 4 load it for its data and its scan. Its own output is not kept here | none |
| `思考量_试跑和作者的数.py` | Not a simulation. It reads LiveNerf's `results/daily.csv` and the raw records of trial layers 3, 4, 5 and 7, and works out the thinking and output numbers | 1.27, 0.30, the thinking ratios in section 12, about 8% |
| `输出_思考量_试跑和作者的数.txt` | Its output | same |

## How to run them again

Python 3.10 or later with numpy. Simulation 2 also needs scipy. Each program reads LiveNerf's `data/standard_panel.json`, so it needs a copy of [LiveNerf](https://github.com/ninjahawk/livenerf), named in `LIVENERF_REPO`. The outputs here used LiveNerf at commit `3febff63` (9 November 2026). From this folder:

```
export LIVENERF_REPO=/path/to/livenerf
python3 -I 模拟五_看了两遍再定开不开第三遍.py 400 1000 9
python3 -I 检查_变低开始得很早.py 300 1000 9
python3 -I 模拟二_垫底版本加跑.py
python3 -I 模拟三_点名一刀和任意一段.py 2 300 600
python3 -I 模拟四_去掉点名一刀_任意一段的线放到4%.py 2 300 600
python3 -I 模拟四_去掉点名一刀_任意一段的线放到4%.py 3 300 600
```

The arguments of simulation 5 are datasets per scenario, shuffles per dataset, processes, and optionally a word that picks the scenarios whose names contain it. With the arguments above it took about 55 minutes on 9 processes. A quick try: `python3 -I 模拟五_看了两遍再定开不开第三遍.py 2 20 2 没有差别`. Simulation 3 and 4 take passes, datasets and shuffles. Simulation 2 takes no arguments and runs 4,000 datasets per case, so it is slow.

The seeds are fixed in each program. Simulation 5 splits the work by the number of processes, and the split sets the seeds, so use the same number to compare with the output here.

`思考量_试跑和作者的数.py` can't be run from this repo. Besides `LIVENERF_REPO` it needs `CCV_RAW_RECORDS`, the folder of the trial records, and those stay offline because they hold the model's answers to GPQA questions. Its output is kept as it came.

## Lines changed from the working copies

The programs here are the working copies, with only the paths changed so that they run from this folder:

- `模拟五_看了两遍再定开不开第三遍.py`, line 25: the folder that holds `ccversions/` is now `..`. It was the program folder of the project. Line 29: the panel file is now found through `LIVENERF_REPO`. It was a fixed path on the test machine.
- `模拟一_几种判法对比.py`, lines 2 and 3, and `模拟二_垫底版本加跑.py`, lines 2 and 4: `os` is imported, and the LiveNerf folder comes from `LIVENERF_REPO`.
- `思考量_试跑和作者的数.py`, lines 15 and 16: `daily.csv` is found through `LIVENERF_REPO`, and the trial records through `CCV_RAW_RECORDS`. Line 6, in the docstring, now names `CCV_RAW_RECORDS` in place of the local folder.

Nothing else was changed. Comments still use the working paths: the header of simulation 5, for example, calls the rule `程序/ccversions/judge.py`, which is `../ccversions/judge.py` here. Comments that mention sections of 判断标准 mean the Chinese working copy of the rule. The README at the top of this repo gives its section numbers in PREREGISTRATION.md. `检查_变低开始得很早.py` is new, written on the evening of 11 November for the check in section 5. The outputs are copied as they came.

## What the Chinese in the outputs means

Each output line of the simulations is one scenario. The values are shares of the datasets, unless the key says otherwise.

### Simulation 5 and its first round

| Key | Meaning |
|---|---|
| `情景` | scenario |
| `造了几份` | datasets made |
| `两遍_答对率过线` | two passes only: an accuracy difference is declared (all three conditions of section 5) |
| `三遍_答对率过线` | three passes always: an accuracy difference is declared |
| `两遍_思考量过线`, `三遍_思考量过线` | the same for thinking |
| `开线X_开了第三遍` | with an opening line of X: the third pass opened |
| `开线X_答对率说有差别` | with an opening line of X, the whole procedure: an accuracy difference is declared |
| `开线X_思考量说有差别` | the same for thinking |
| `开线X_两样里至少一样说有差别` | at least one of the two is declared |
| `开线X_答对率说变低` | an accuracy difference is declared and meets the bar for "lower" (in the first round, the shape alone) |
| `开线X_思考量说变少` | a thinking difference is declared and meets the bar for "thinks less" |
| `每份打乱 N 次，用时 S 秒` | N shuffles per dataset, S seconds in all |

| Scenario | Meaning |
|---|---|
| `没有差别` | no difference |
| `没有差别_答对和思考有关联0.5` | no difference, with right answers and long thinking linked within an ask (correlation 0.5) |
| `没有差别_第三遍只跑了一半` | no difference, third pass stopped half way |
| `没有差别_第三遍只跑了四分之一` | no difference, third pass stopped a quarter of the way |
| `答对率_从第22个版本起整段变低N个点` | accuracy N points lower from version 22 on (the last 18) |
| `答对率_中间13个版本变低N个点` | accuracy N points lower in versions 19 to 31 |
| `答对率_最后6个版本变低N个点` | accuracy N points lower in the last 6 versions |
| `答对率_连着3个版本变低N个点` | accuracy N points lower in versions 25 to 27 |
| `答对率_单个版本变低N个点` | accuracy N points lower in version 26 alone |
| `答对率_从第22个版本起整段变高N个点` | accuracy N points higher from version 22 on |
| `思考量_从第22个版本起整段变少N%` | thinking N% less from version 22 on |
| `思考量_单个版本变少N%` | thinking N% less in version 26 alone |

### The check of early drops

| Key or scenario | Meaning |
|---|---|
| `前面K个版本_之后一直到最新都低N个点` | K versions as usual, then every version to the newest N points lower |
| `前面K个版本_接着13个版本低N个点` | K versions as usual, then 13 versions N points lower, then the rest as usual |
| `前面K个版本_接着6个版本低N个点` | the same with 6 versions |
| `开了第三遍` | the third pass opened |
| `说有差别` | an accuracy difference is declared |
| `说变低` | it is declared and meets the bar for "lower" |
| `说有差别的里面说变低的` | of the declared ones, the share that meets the bar |
| `每份打乱 N 次` | N shuffles per dataset |

### Simulation 2

| Key | Meaning |
|---|---|
| `真差几个点` | the true drop of one version (the 21st), in points |
| `追几个` | how many of the lowest versions are re-run |
| `做法` | `full`: every version gets a third pass and the lowest get extra passes. `target`: only the lowest are re-run, against 6 reference versions |
| `嫌疑版本新跑几遍` | new passes for each of the lowest versions |
| `进了垫底名单` | the truly lower version was among the lowest after two passes |
| `被验证为差` | it was then confirmed lower |
| `把没问题的版本错判成差` | versions with no difference wrongly confirmed lower, per dataset |
| `两遍里垫底版本比平均低(点,中位)` | how far the lowest version sits below the mean after two passes, in points, median over datasets |
| `两遍里最高最低相差(点,中位)` | the gap between the highest and the lowest version after two passes, in points, median |
| `没有差别时 遍数` | with no difference at all: the number of passes |
| `最高减最低 中位` | the gap between the highest and the lowest version, in points, median |
| `最高减最低 95%的情况不超过` | the gap that 95% of the datasets stay under |
| `垫底比平均低 中位` | how far the lowest version sits below the mean, in points, median |
| `垫底比平均低 95%不超过` | the distance that 95% of the datasets stay under |

### Simulations 3 and 4

| Key | Meaning |
|---|---|
| `情景` | scenario |
| `差几个点` | the true drop, in points |
| `遍数` | passes |
| `N` | datasets |
| `点名一刀@2%` | the cut named in advance (from 2.1.303 on) alone, at a 2% line |
| `任意一段@L` | the scan over every run of consecutive versions, at a line of L |
| `任意一刀@2%` | only cuts of the form "from version X on", at 2% |
| `单个版本@2%` | only single versions, at 2% |
| `点名或任意一段` | the named cut or the scan, each at 2% |
| `任意一段@L且方向一样且至少3点` | the scan at a line of L, plus the same sign in every pass and at least 3 points |

| Scenario | Meaning |
|---|---|
| `没有差别` | no difference |
| `从2.1.303起整段变低` | lower from 2.1.303 on (the last 18 versions) |
| `从2.1.300起整段变低` | lower from 2.1.300 on (the last 21) |
| `2.1.300到2.1.312这13个变低` | the 13 versions 2.1.300 to 2.1.312 lower |
| `连着3个版本变低` | versions 25 to 27 lower |
| `最后6个版本变低` | the last 6 versions lower |
| `单个版本变低` | version 26 alone lower |

### The thinking numbers

The output is plain text. Its labels:

| Text | Meaning |
|---|---|
| `作者每天的数（Opus 5.5，2.1.280，high，78 道题）` | LiveNerf's daily numbers, with the dates covered |
| `11 月 3 日以前`, `11 月 3 日和以后` | before 3 November, 3 November and after |
| `N 天` | N days |
| `每天输出量中间值的平均` | mean of the daily median output tokens |
| `最低`, `最高`, `标准差` | lowest, highest, standard deviation |
| `答对率平均` | mean accuracy |
| `试跑的真题记录` | trial records on real items. Each line names the trial plan (`L3` is trial layer 3) and the version |
| `N 次` | N asks |
| `输出量中间值`, `平均` | median and mean output tokens |
| `思考量中间值`, `平均` | median and mean thinking tokens |
| `一点没想的 N 次` | N asks with zero thinking tokens |
| `同一道题 B 比 A：N 道，思考量是 R 倍（lo 到 hi），对数差的标准差 S` | item by item over N items, B thought R times as much as A (95% interval lo to hi). S is the standard deviation of the log difference |
| `照作者那样问，2.1.280，low 比 high` | LiveNerf's harness on 2.1.280, effort low against high |
| `输出量是 R 倍` | output tokens, as a ratio |
| `能看出多大的差别（粗算）` | a rough estimate of the thinking difference that could be seen, made before simulation 5 and replaced by it |
| `整段约少 X%，单个版本约少 Y%` | about X% less over a long run, about Y% less in one version |
| `factor 取 4.1` | the factor of the rough estimate, set so that the same rough method matched simulation 4's accuracy numbers |

## After a third pass has opened (added 13 November 2026)

Folder `after_third_pass/`. This is item 12 of the change log entry "13 November 2026: extra numbers and wordings" in PREREGISTRATION.md. It was run and added here before the final report and the interim files of the registered run were opened.

| File | What it is |
|---|---|
| `count_after_third_pass.py` | Makes simulation 5's datasets again for the four scenarios with no difference (same seeds, 4,000 datasets each, 1,000 shuffles) and counts how often a difference is declared among the datasets in which the third pass opened, split by the test that opened it. It calls simulation 5 and `../ccversions/judge.py` unchanged. Its docstring says how it is run |
| `output_after_third_pass.txt` | Its output. Part 1 recounts the 112 shares that the registered output of simulation 5 gives for these scenarios. All 112 are the same to the four decimals printed there. Part 2 holds the new tables |
| `output_after_third_pass.json` | The same counts, for programs |
| `output_after_third_pass_datasets.csv` | One line per made-up dataset (16,000), so that any count can be redone |

The scenario names in the output are simulation 5's: `没有差别` (no difference, third pass sent in full), `没有差别_答对和思考有关联0.5` (the same, with right answers and long thinking linked inside an ask), `没有差别_第三遍只跑了一半` and `没有差别_第三遍只跑了四分之一` (the third pass stops after a half or a quarter).
