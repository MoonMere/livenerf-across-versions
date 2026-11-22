# The small trial on 200 questions the panel never used

Everything here belongs to the change log entry "22 November 2026: a small trial on 200 questions the panel never used, on one version" in [PREREGISTRATION.md](../PREREGISTRATION.md). The asks of this trial were decided after the results of the registered run and of the groups added later were seen. No ask of it enters a comparison between versions.

| File | What it is |
|---|---|
| `question_ids.txt` | the MMLU-Pro `question_id` of the 200 questions, in the order they were taken (LiveNerf's shuffled order) |
| `arms_old.json`, `arms_new.json` | the two groups, in the format of `inputs/formal_arms.json`: `small_trial_old` asks the 78 panel questions, `small_trial_new` asks the 200 |
| `run_old.json`, `run_new.json` | questions, seed, block size, usage line, asks at once and the cap on asks for each group |
| `versions_20261122.json` | the version list of the trial: 2.1.316, and 2.1.322 for the outage probe only |
| `probes_SP1.json` | the one unscored probe sent before the first scored ask |
| `driver.py`, `test_driver.py` | sends the passes of one group through the steps of the registered driver, one ask at a time, with the cap of 1,150 asks, and its tests with a stand-in for Claude Code |
| `old_pass_check.py`, `test_old_pass_check.py` | the four conditions of the panel pass, and tests on made-up rows |
| `new_passes_numbers.py`, `test_new_passes_numbers.py` | the numbers read from the 200 questions and the two decisions, and tests on made-up rows |

The files, other than this one and `question_ids.txt`, were copied unchanged from the program folder of the test machine. Where a file speaks of "the rules" and their sections, or names a path in Chinese, it means the working rules of the trial, a file in Chinese that is not published. Its sha256 is in the entry. `work_dir` in the two run files is a relative path to a folder on the test machine.

`driver.py` and `test_driver.py` import the registered sender from `../ccversions/` and its test stand-in from `../tests/`. Parts of both are not published, so they do not run here. The two programs for the numbers need the graded answers, the readers' tables with the table that maps their codes to question ids, the designing session's table and the table of mid November, which are not published either, so here only their tests run:

```
cd small_trial && python -B -m unittest test_old_pass_check test_new_passes_numbers
```

The tests were run with Python 3.12 and numpy.

## Readings the programs follow where the entry is silent

All of these were fixed before the first ask.

**Sending**

- LiveNerf's function builds only the first 2,000 questions of its shuffled order. Its constant `MMLU_PRO_SUBSET` was set to 12,032 in memory before the call. LiveNerf's file was not edited.
- The cap. Before a plan is sent, the asks already recorded for the trial are counted: both groups, asks sent again, the probe and outage probes. If these and the asks of the plan that are not yet recorded would pass 1,150, the plan is not started and the script stops for a person to decide. Before each outage probe the same count is taken with one ask added. So the trial can stop some asks short of 1,150 and never passes it. The one exception is in the entry: if the panel pass has to be sent again, the cap is raised to 1,228 first. A plan is never cut short to fit.
- The probe, the panel pass and the five passes are three commands, run one after the other.

**The panel pass (`old_pass_check.py`)**

- A scored answer is an ask whose outcome is `scored` under the registered grading. An ask that never reached the model and was sent again counts by the ask that was sent again. A void ask counts as no scored answer, and so does a question with no record. The question without a scored answer has no ask that can count in conditions 2 to 4.
- Before the four conditions, the program checks that the rows it was given are one pass of the 78 questions: the table of mid November has 78 questions, no question has two asks, and no ask is of a question outside the table. If this fails, the program says the pass does not come out alike. The check guards against a wrong input file.
- "Without thinking" is a scored ask with a thinking token count of 0.
- The 63 questions of condition 3 are those whose share of asks without thinking over the versions up to 2.1.316 is 0 in the table.
- The median of condition 4 is the median thinking token count over all asks of the question on those versions, with an ask without thinking counted as 0. A question whose median is 0 has no ratio. It is left out of condition 4 and named in the report. The bounds 0.75 and 1.33 are inside the range that passes.

**The 200 questions (`new_passes_numbers.py`)**

- An ask counts when its outcome is `scored` and it carries a thinking token count. An ask sent again takes the place of the ask it was sent for.
- For a question with n scored asks, n below 5, the estimate is k(n − k)/(n(n − 1)), which is k(5 − k)/20 at n = 5 and is unbiased as well. A question with one scored ask is left out of M. The counts of k = 0 to 5 are over the questions with five scored asks, and the other questions are listed by their number of scored asks.
- The 90% range of M: the questions are drawn again with replacement 2,000 times with the seed 20261122, and the 5th and 95th percentiles are taken.
- The row of the decision is the row of M itself. 0.005 is in the first row and 0.002 is in the second.
- The median of thinking tokens and the spread of ln(thinking tokens) of a question use its asks that thought. The spread is the sample standard deviation and needs two such asks. A question that never thought has neither figure.
- "Thinking asks did not all match the key" means that at least one ask that thought did not match. A question that never thought is not in that list.
- The rules ask for the questions the model cannot bring to the key. They are counted two ways: questions never right, and questions right in fewer than half of their scored asks. For each, the median thinking of those questions is set beside that of the other questions, as the median of the questions' medians.
- The shares of the reading (questions the readers objected to, and of those the ones with a flaw that can be stated plainly) are computed once, over the 200.
- The share with a plain flaw is taken over the objected questions that the designing session read. The session's label 真毛病 (a real flaw) counts as a plain flaw. Its other label, 说不准 (cannot say), counts as read with no plain flaw. For this the program is run with `--main-reads-column 主对话的判断 --main-reads-yes 真毛病`. Its defaults are a column `clear_flaw` and the labels `yes` and `是`.
- A reader's answer differs from the key when the letters are not the same. An answer that names two letters differs even when one of them is the key.
- The pool left after the reading is given two ways: 2,037 times the share the readers did not object to, and 1,837 times that share, the pool without the 200 of this trial. "More than half" means strictly more.
- Seconds per ask are over the asks of the five passes, whatever their outcome, with an ask sent again in the place of the ask it was sent for. The change in the weekly usage reading is between the first and the last of those asks by start time. If the weekly quota is reset in between, the change comes out negative.
