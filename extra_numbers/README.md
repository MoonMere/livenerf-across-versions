# Extra numbers: the code, committed before the reports were opened

Code for items 1 to 8, 13 to 15 and 18 of the change log entry "13 November 2026: extra numbers and wordings, fixed before the reports are opened" of [PREREGISTRATION.md](../PREREGISTRATION.md). Items 9 to 12, 16 and 17 are done elsewhere.

A Claude agent (Opus) wrote it on 13 November 2026. The agent was told not to open any data of the run. It was given the names and types of the fields of a record, without a single value. Claude (Fable 5.2), which runs this experiment, then read the program against the entry and ran the tests. The folder was committed here before the final report and the interim files of the registered run were opened. So far the program has run on made-up data only.

| File | What it is |
|---|---|
| `extra_numbers.py` | The program. Its docstring says what each item computes and in which function |
| `fake_data.py`, `test_extra_numbers.py` | 39 tests on 11 made-up datasets. For every item at least one number is counted again by plain Python loops over the rows and compared |

## What it takes from the registered program

Which differences are declared, and on which segment, is read from the registered program's two reports (the final one, and the interim one after passes 1 and 2). This program never decides that again. Before anything else it rebuilds each scan from the graded rows with the registered functions and compares the segment, the difference, z, the support for a drop and the three parts with the reports. If one of them differs it stops and writes nothing.

## Choices the entry left open

These were fixed here, before any result.

1. "Less than half" (items 1 and 2), "halves" (item 5) and "less than a third" (item 14) are compared on the scale the scan works on: shares for accuracy, logs for thinking. For thinking, comparing per cents can give another answer when the difference is large.
2. Item 1 (a): the difference in the share of asks that tried a tool is computed as the scan computes a difference, after the mean of each cell (one item in one pass) is taken out. The raw shares of the two sides are given beside it.
3. Item 1, "less than half the declared difference or has the other sign": the difference in (b) divided by the declared difference is below 0.5. A negative quotient is the other sign and counts. The declared difference is the registered scan's own.
4. Item 2, "read": a choice answer is read when it is one letter A to Z after the trimming LiveNerf's grader does (spaces and round brackets). A letter the item doesn't offer counts as read, and the grader marks it wrong. An integer answer is read when it is an integer after spaces and commas are removed, as in the grader. A rational answer is read when LiveNerf's `rational()` returns a number.
5. Item 2, "scans that share as section 8 scans its numbers": 2,000 shuffles and no minimum size, as the registered program does for section 8.
6. Item 2, "over the read answers alone": errors, voids and unread answers are all left out. The result is compared with the declared difference counted with errors and voids left out.
7. Item 3, "the ratio of the totals": each side's total is divided by its number of asks first, so that the number of versions on each side doesn't enter.
8. Item 3, "the ratio over the asks with thinking above zero": computed as the scan computes a difference, after the mean of each cell is taken out, and written as a ratio. The ratio of the medians uses the raw medians of the two sides.
9. Item 3, the per cent written as a change in the geometric mean: the entry gives no sentence. The program writes "Inside S the geometric mean of thinking tokens plus one is X% lower than in the other versions, after the difficulty of each item is taken out", or "higher".
10. Item 4, "for each of the two tests": three scans are measured, accuracy both ways and thinking.
11. Item 5, "halves the difference": the item is named when half or less of the difference is left without it, the other sign included. It is named by its identifier in the item file, which holds nothing of the question.
12. Item 6, "the middle 95%": the 2.5 and 97.5 per cent points of the version index over the draws, each a version that occurred, with no interpolation. The span is marked for the summary only when that test has a declared difference. It is computed and reported either way.
13. Item 7, "both segments with both sizes": each segment's difference under both ways of counting, four numbers. This is done for the final report and for the interim report.
14. Item 8, "while the scan declares nothing": accuracy and thinking are each taken on their own. The other reading is that neither test declares anything. Accuracy is counted with errors and voids left out, as in the registered line of section 8.
15. Item 13, "met all three conditions": the interim report's own declared line. For accuracy that needs both ways of counting to declare with the same sign. "Only had p < 0.05": at least one way of counting had p < 0.05 and the test was not declared.
16. Item 15, "a drop is declared from a version": only differences the registered program calls "lower". For a low segment the drop starts at its first version. For a high segment it starts at the version after it. The other reading covers low segments only.
17. Item 15's fixed sentence says "From X on it is lower". When a low segment ends before the newest version, the program gives the fixed sentence and, beside it, one adapted to that segment and marked as adapted. The condition that the checks of section 10 find no fault lies outside this program, and the output says so.
18. Item 15, "the scan over groups": for accuracy it is the registered report's own, recomputed here and compared. For thinking the registered program has none, and this program computes it the same way.
19. Item 18, "the sum over the messages of the ask": top-level assistant messages only, each counted once by its id at the largest output count any of its lines carries. Only scored asks in cells that count are compared.
20. When the two ways of counting declare a difference on two different segments, items 1, 2, 5 and 15 are computed for both segments.

## Not checked on the real data

- Whether one reply is split over several lines of a record, and whether those lines carry the same output count, was not looked at. The program counts the asks where they differ. If each line carried only its own part, the sum would come out too small and item 18 would fall under "other" for nearly every ask. That is checked first if it happens.
- Records of `main` are taken to be stream-json. The path for another format is not covered by the tests.
- Item 6's choice of segment was compared with a segment by segment computation on 4 redraws only. Item 15's scan over groups for thinking was not checked another way.

## Running it

The folder sits beside `ccversions/`. The tests need LiveNerf's repository for its `rational()` parser:

```
CCV_AUTHOR_REPO=<LiveNerf repository> python -B -m unittest test_extra_numbers
```

On the real data:

```
python -B extra_numbers.py --author-repo DIR --graded FILE ... --raw-dir DIR ... \
    --final-report FILE --interim-report FILE --items FILE --out DIR
```

The default paths in the program are the folder layout of the machine the run was made on. The program prints whether a difference is declared, so it is run only after the reports are opened. It writes `extra_numbers.json` and `extra_numbers.md`, with no answer text, no question text and no key.
