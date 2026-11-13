# Comparisons added on 12 November 2026

Code for the two secondary comparisons in the change log entry "12 November 2026, evening" of `PREREGISTRATION.md`: time of day (`time_of_day.py`) and Desktop against `main` on 2.1.321 (`desktop_vs_cli.py`).

It was written and committed here before the final report of the registered run was opened, and before any answer of the run or of the Desktop group had been graded or looked at by us. So far it has run only on made-up data and on the rehearsal, which doesn't count.

| File | What it is |
|---|---|
| `common.py` | The fixed numbers of the rule, US working hours, the three wordings |
| `time_of_day.py` | Inside US working hours against outside, `main` only. The docstring lists every number it computes |
| `desktop_vs_cli.py` | The Desktop group against `main` on 2.1.321, 77 items. Grades the Desktop records with `grade.py` unchanged |
| `fake_data.py`, `test_two_comparisons.py` | 20 tests on made-up data: a planted difference is found at its size, and data with no difference get no verdict |

## Choices the rule left open

These were fixed here, before any result.

- p = (1 + shuffles at least as large as the real one) / (1 + shuffles), so p is never 0.
- A cell's share inside US working hours is taken over the asks of that cell that have a value for the measure.
- Accuracy is computed both ways (errors and voids left out, and counted as wrong, section 3). The weaker of the two wordings stands, and "otherwise" if the two point in opposite directions.
- For thinking, "larger than the largest difference between two pass levels" is compared in logs.
- The sign check for time of day uses the inside hours of pass 1 and of pass 2. If the end of pass 3 runs into US working hours, its own difference is reported beside them.
- A pass or a Desktop round in which fewer than half the items count is left out of the sign check.
- 14:00:00 UTC is inside and 01:00:00 UTC is outside.
- The hourly table takes out item and pass levels from a fit without the inside term, so it doesn't depend on where the day is cut.
- The `main` side of the Desktop comparison is 2.1.321's asks in the cells that count.
- A Desktop record that didn't run 2.1.321 is left out and listed.
- A third Desktop round that has some asks but fewer than 77 stops the program unless a flag is given.

## Running it

The folder sits beside `ccversions/`. `desktop_vs_cli.py` and the tests also need the runner modules (`settings.py`, `items.py`) and the script that made the Desktop records, which are published with the results. `time_of_day.py` runs with what is here when it is given `--graded` and `--versions-file`.

## The group that replays the Desktop app's system prompt (added 12 November 2026, night)

`desktop_prompt.py` computes the six comparisons of the change log entry "12 November 2026, night: a group that replays the Desktop app's system prompt". `test_desktop_prompt.py` holds 30 tests on made-up records.

It was committed here before the group's first scored ask, before the final report of the registered run was opened, and before any answer of the run, of the Desktop group or of this group had been graded or looked at by us. It has run on made-up records only. The program refuses to run until the third Desktop round is in or 00:10 UTC on 13 November 2026 has passed.

Choices the rule left open, fixed here before any result:

- For b minus a and d minus e, the sign check takes pass k of one arm against pass k of the other. The two arms were sent in the same batch.
- For e minus `main`, the check against the line for "clear" takes each pass of e against the mean of `main`'s passes, as the Desktop comparison does.
- The warning on the two comparisons that cross the batches is added when accuracy (both ways of counting) or thinking reaches "clear" in e minus `main`. "Points one way" adds no warning.
- Accuracy is computed both ways, as above. In "otherwise", X is the larger of the two.
- A pass in which fewer than half the items of the comparison count on both sides is left out of the sign check. With no pass in the check, a result can't be "clear".
- If one arm has fewer passes on an item than the other, each side is averaged over the passes it has.
- The `main` side is 2.1.321's asks in the cells that count, on all 78 items.
- The comparison with the Desktop group leaves out the one question the app can't deliver, on both sides. That leaves 77 items.
- A pass is complete when it has all 78 items.
- Records that are warm-ups, unscored, no items, of another group or of another version are left out and listed. A resent ask takes the place of the ask it was sent for. The small batch and the probes are not read.
- If b minus a comes out clear, the two arms differ in the text only. What this run can't tell apart is which of the two added sections did it, or the extra length alone. The test that would: one arm for each section alone, and one arm with unrelated text of the same length.
- If d minus e comes out clear, the arms differ in the whole system prompt. What this run can't tell apart is which part of the Desktop text did it, or its length. The test that would: start from the command line program's own prompt and add the Desktop sections one at a time, one arm each.

The tests also need the script that sends this group, which is published with the results.

## Group `api` on three passes (added 13 November 2026)

`api_three_passes.py` gives the comparison of group `api` with group `author` on 2.1.322 once more, with the pass added on 13 November 2026 (change log entry "13 November 2026: a third pass for group `api`"). It was committed here while that pass was being sent and before the final report was opened.

- It uses `analyze.paired`, the function the registered report uses for this line: item by item, each side averaged over its passes, `api` minus `author`, and a 95 per cent range from 10,000 redraws of the items.
- It reports three figures: passes 1 and 2 (this must equal the figure of the registered report), pass 3 alone, and the three passes together. Each has accuracy counted both ways, thinking tokens and output tokens.
- It attaches no wording. Section 9 has none for this line.
- The records of the added pass are graded with `grade.py` unchanged.
- It does not run until the registered run has graded all its passes and the added pass has 78 asks on each side.
- `test_api_three_passes.py` has 8 tests on made-up data. They do not cover the grading step.

