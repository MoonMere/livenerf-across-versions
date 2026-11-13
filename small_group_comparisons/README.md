# Three small groups against `main`: the code, committed before the reports were opened

Code for what the change log of [PREREGISTRATION.md](../PREREGISTRATION.md) asks for under "How it is compared" in the entry "13 November 2026: a group without LiveNerf's two sentences, and a third pass for `flags_on` and for `author` on 2.1.280", and for items 9 and 16 of the entry "13 November 2026: extra numbers and wordings, fixed before the reports are opened".

- `nosent`: main's ask without LiveNerf's two sentences, on 2.1.280 and 2.1.322, three passes (plans NS1, NS2, NS3, and their resend plans NS1r, NS2r, NS3r).
- `flags_on`: four versions with the remote flags fetched. Passes 1 and 2 are in the registered run, pass 3 is plan S3.
- `author` on 2.1.280. Passes 1 and 2 are in the registered run, pass 3 is plan S3.

None of these numbers carries a verdict, and none enters the two tests of sections 5 and 6.

A Claude agent (Opus) wrote it on 13 November 2026. The agent was told not to open any data of the run. It was given the names and types of the fields of a record, without a single value. Claude (Fable 5.2), which runs this experiment, then read the program against the entries and ran the tests. The folder was committed here before the final report and the interim files of the registered run were opened. So far the program has run on made-up data only.

| File | What it is |
|---|---|
| `small_group_comparisons.py` | The program. Its docstring says what each number is and in which function it is computed |
| `fake_data.py`, `test_small_group_comparisons.py` | 40 tests on made-up data. Every number is worked out a second time by plain Python loops over the made-up asks and compared |

The folder names in the program's default paths are those of the machine that ran the experiment. Each has an option.

## The command for the real run

Run it from this folder, with the project's Python, after the registered run has its final report:

```
OMP_NUM_THREADS=3 OPENBLAS_NUM_THREADS=3 VECLIB_MAXIMUM_THREADS=3 \
  ../../本机数据/python环境/bin/python -B small_group_comparisons.py --livenerf-daily DAILY_CSV
```

`DAILY_CSV` is a copy of LiveNerf's `results/daily.csv` downloaded after the last ask of `author` on 2.1.280 (plan S3, 13 November 2026). The option has no default, so that an old copy is never used by accident. The program prints `not run: ...` and exits with code 2 when it stops. Nothing is written then.

## What it reads

Each of these has an option. The defaults are relative to the project folder that holds `程序/`.

| what | default | option |
|---|---|---|
| graded rows of the registered run | `本机数据/正式跑/graded/F1/graded.jsonl`, and F1r, F2, F2r, F3, F3r where they exist | `--graded FILE` (repeat) |
| the registered final report | `本机数据/正式跑/final/report.json` | `--final-report FILE` |
| the registered settings (LiveNerf's repository and the item file, used to grade the added plans) | `本机数据/本机设置.toml` | `--settings FILE` |
| raw records of plan S3 (and S3r if there is one) | `本机数据/小组第三遍/原始记录/S3/asks/` | `--s3-raw-root DIR` (the folder above `S3/`) |
| raw records of NS1 to NS3 and NS1r to NS3r | `本机数据/去掉两句话组/原始记录/NS1/asks/` and the others | `--nosent-raw-root DIR` |
| raw records of plan A3 (author on 2.1.322, pass 3), optional | `本机数据/API第三遍/原始记录/A3/asks/` | `--a3-raw-root DIR` |
| the report of `后加的两个对比/desktop_prompt.py`, optional | `本机数据/后加的两个对比/desktop_prompt/report.json` | `--desktop-prompt-report FILE` |
| LiveNerf's daily numbers | none | `--livenerf-daily FILE` |

From the item file it uses each item's id, family, grader and key, through `ccversions.items.load`, exactly as `formal.py` grades. Keys are used only by LiveNerf's graders, never written.

## What it writes

In `--out` (default `本机数据/小组对比/`): `small_group_comparisons.json` for programs and `small_group_comparisons.md` for people. Every block says which entry of the change log asks for it, and which point or item. Neither file holds an answer, a question, a key or an item name. Both are searched for paths and e-mail addresses (`grade.PUBLIC_BAD`) before they are kept. No graded rows are written, because a graded row holds the answer.

## What is computed, and in which function

| block in the outputs | asked for by | function |
|---|---|---|
| `nosent_against_main` | nosent entry, "How it is compared", point 1 | `nosent_against_main` |
| `nosent_gap` | the same, point 2 | `nosent_gap` |
| `nosent_unread` | the same, point 3, with item 2 of the extra numbers entry | `nosent_unread` |
| `flags_on_against_main` | the same, point 5, with section 9 | `flags_on_against_main` |
| `author_against_main` | the same, point 5, with section 9 | `author_against_main` |
| `author_against_livenerf_range` | the same, point 5, with section 9 | `author_against_livenerf_range` |
| `a_day_apart` | the nosent entry's "Limits", point 1 | `a_day_apart` |
| `item_9` | extra numbers entry, item 9 | `item_9_same_day` |
| `item_16` | extra numbers entry, item 16 | `item_16_flags_on` |

The program's opening text says in detail what each number is.

## Before any number: the check against the final report

`analyze.small_groups` is run on the graded rows read here. Its entries for `flags_on` and `author` (passes 1 and 2) must equal the final report's, every number, ranges included. The version list, the versions the server refused and the passes of main must be the same too. If anything differs, the program stops and names each number that differs.

## Resends

A resent ask takes the place of the ask it was sent for, through `analyze.apply_resends`, the registered function. In the registered run this is done on all its rows at once. For each added plan it is done on the plan and its resend plan together. The output's `resend_fields` block says, for the registered run and for each added plan, whether the records carry the fields this needs and how many resends there were.

## When a plan is not finished, or not sent

| state | what it means | what the program does |
|---|---|---|
| complete | every ask of the plan's arms has a row, and every ask that never reached the model has a resend | computes |
| partly sent | some asks have no record, or an ask never reached the model and has no resend yet | S3 or NS1 to NS3: stops. With `--allow-partial` it computes on what is there and writes a WARNING at the top of both outputs. Every figure says which passes and how many asks it used. |
| not sent | the plan's folder has no records | the same as partly sent |
| problem | a resend that points to no ask that was read, a resend whose group, version, item or pass differs from its ask, two rows for one ask, a record without one of the fields plan, ask_id, pass, group, version, unit, scored, warmup, resend_of, or a row whose pass is not its plan's | stops always |

A3 and the desktop-prompt report are optional. When either is missing, its comparison says "not computed" and why, and the rest is computed.

## Where the registration can be read two ways

These are the readings this program follows.

1. "The figure on two passes" for `flags_on` and `author` is the figure of the registered report's kind: their passes 1 and 2 against all three passes of main.
2. `author` against main is given on 2.1.280 alone, as point 5 names it. The registered report pools 2.1.280 and 2.1.322.
3. "For the two together" pools each side over both versions, item by item, as `analyze.small_groups` pools the versions of a group.
4. "Inside LiveNerf's daily range" means between the lowest and the highest daily value of the period, both ends included. It is given for each pass (78 answers, as one day of LiveNerf) and for the passes pooled.
5. Item 9's "the same UTC day": when the asks of one pass were sent on two UTC days, LiveNerf's figure is the mean of those days' figures, each weighted by this group's scored asks on that day. Each day is also given on its own.
6. Item 9's "if they differ": LiveNerf's figure lies outside the range of this group's figure.
7. Item 16's "between versions that flags_on covers": at least one of flags_on's four versions is inside the declared segment and at least one is outside.
8. Item 16's "flags_on shows it": flags_on's own difference between its versions inside and outside the segment, item by item over three passes, has the declared sign and a range that leaves out zero, in both ways of counting for accuracy. Two passes and main on the same four versions are given beside it.
9. The nosent entry's "Limits" asks for two comparisons beside the nosent result: arm e of the desktop-prompt group against main on 2.1.321, and pass 3 of `author` on 2.1.322 against its passes 1 and 2. The first is copied from the desktop-prompt report. The second is computed here from plan A3.

## Self-tests

```
OMP_NUM_THREADS=3 ../../本机数据/python环境/bin/python -B test_small_group_comparisons.py
```

They use only made-up data (`fake_data.py`): made-up graded rows of the registered run, a final report made from them by the registered `analyze.analyze`, raw records of S3, NS1 to NS3 and A3 graded by `grade.py` with stand-ins for LiveNerf's graders, and a made-up `daily.csv`. Every number is worked out a second time from the list of made-up asks with plain Python, without `grade.py`, `analyze.py` or this program. Some are also checked against `analyze.small_groups`.

The made-up data include a world with no difference, a world with a planted difference of known size (twelve items out of 78 wrong, and twice the thinking), answers no grader can read, a void, resends, a plan cut in half, a plan not sent, an ask not resent yet, a resend that points to nothing, a final report that does not match, and the three wordings of item 16.

If the environment variable `LIVENERF_REPO` names a copy of LiveNerf's repository, two more tests run: the stand-ins are compared with LiveNerf's own graders on every made-up answer, and the grader is built from a made-up settings file the way the real run builds it. In this repository the second of these and the test that compares the program's constants with the files that sent the asks are skipped, because they need files that are not published here (`ccversions/items.py`, `ccversions/settings.py` and the senders of the added plans).

## What cannot be checked before the real run

- Whether the records of S3 and of NS1 to NS3 carry pass 3 and passes 1 to 3. The program checks this and stops if not.
- Whether the real final report's `small_groups` entries are matched by the rows read here. The program checks this and stops if not.
- The fields of the real nosent records. They are written by the registered sender, so they should be the fields of a main record. The program checks them.
