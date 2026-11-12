# Two comparisons added on 12 November 2026

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
