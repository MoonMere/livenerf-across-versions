# LiveNerf across Claude Code versions

Same model, same 78 questions, 39 versions of Claude Code. Does the version change how well Claude Opus 5.5 answers, or how much it thinks?

**Status:** the rule for reading the results is registered in [PREREGISTRATION.md](PREREGISTRATION.md), before the run. No question of the run has been sent yet. The results will go here when it ends, whatever they show.

## Why

[LiveNerf](https://github.com/ninjahawk/livenerf) asks Claude Opus 5.5 the same 78 questions every day to see whether the model gets worse after launch. It pins Claude Code at 2.1.280 on purpose: a new Claude Code release changes what the model is sent, and LiveNerf wants to watch the model alone.

Some reports of Claude getting worse point at Claude Code itself. A post on X about [anthropics/claude-code#105112](https://github.com/anthropics/claude-code/issues/105112), for example, named version 2.1.303. A benchmark pinned at 2.1.280 can't see that kind of change. So this experiment turns LiveNerf around. It holds the time fixed, a few days in November 2026, and changes the Claude Code version.

## What runs

- **Versions.** Every Claude Code release from 2.1.280 up to 11 November 2026: 39 versions, 2.1.280 to 2.1.322.
- **Model and effort.** `claude-opus-5-5` with `--effort high` on every ask of the main comparison, as in LiveNerf.
- **Questions.** LiveNerf's 78 (MMLU-Pro, GPQA Diamond, AIME and other maths competitions), graded by LiveNerf's own graders, imported unchanged.
- **What the model sees.** Whatever that version sends by default: its own system prompt, tool list and tool descriptions, with LiveNerf's two sentences added at the end of the system prompt. A PreToolUse hook refuses every tool call before it runs, so the model sees the tools and can't use them. Remote feature flags are not fetched, and nothing from anyone's own Claude Code setup gets in.
- **Order.** Two passes over all 78 questions. Each pass is cut into blocks of 3 questions, and every version answers in every block, so all versions share the clock evenly. A third pass opens only when the first two point to a drop, by a rule fixed in advance.
- **Small groups beside the main run.** LiveNerf's own harness on two versions, the same two versions with tools switched off, today's remote flags on four versions, four other effort levels as a yardstick, Fable 5.2 against Opus 5.5, and the same request sent straight to the API.

## How a difference gets called

Sort the versions by release. Every run of consecutive versions, from a single version up to all but one, is a candidate: 779 of them. The scan takes out each question's difficulty, finds the run that stands out most, and checks it against 10,000 shuffles that deal each question's results to the versions at random. Every shuffle also takes its most extreme run, so picking the best one is already paid for in the line.

A difference is called when that run clears the 95% line, is at least 3 points (10% for thinking), and points the same way in every pass. No version is named in advance. The data decide where the cut falls.

What it can see, 8 times in 10, with two passes (a third pass sharpens this a little):

| True change | Accuracy | Thinking |
|---|---|---|
| from version 22 of 39 on | about 4.5 points | about 11% |
| 3 versions in a row | about 9 points | not simulated |
| one version alone | about 16 points | about 27% |

A drop that starts near the first or the last version needs to be larger. When all versions are truly the same, the whole procedure calls a difference less than 5% of the time for each of the two questions. A smaller change than the table shows will be reported as not seen at that size, with these numbers next to it.

The full rule, with every number and where it comes from, is in [PREREGISTRATION.md](PREREGISTRATION.md).

## Next to LiveNerf

| | LiveNerf | This experiment |
|---|---|---|
| What changes | the day, since launch | the Claude Code version |
| Claude Code | 2.1.280, pinned | 2.1.280 to 2.1.322 |
| System prompt | LiveNerf's two sentences replace Claude Code's | Claude Code's own, with LiveNerf's two sentences added |
| Tools | none | described to the model, every call refused |
| Decision rule | windows of 10 days against the first 10 days, a 99% interval in two windows in a row | a scan over every run of consecutive versions, a 95% line from shuffling |
| Machine | Windows | macOS |

Both use the same 78 questions, the same graders, effort high, a timeout of 900 seconds, a minimum difference of 3 points and a flag at 5% errors. The `author` group runs LiveNerf's harness on 2.1.280 and is compared with LiveNerf's published numbers, as a check that the setup is built right. The machines and accounts differ, so that check can only be rough.

## Who made this

Claude Fable 5.2 designed and built most of this experiment, working in Claude Code. That covers the runner, the rule and its simulations, the analysis code, the trial runs and a full rehearsal. Claude Opus and Sonnet subagents did part of the practical work, such as downloading and checking the 39 versions, writing the first version of the runner and drafting the English of these pages.

Soren Hou started the project and steered it. He asked for the experiment and made the calls that shaped it: effort high to match LiveNerf, every version from 2.1.280 to the newest on 11 November 2026, no version picked out in advance as the suspect, and a third pass only when the first two point to a drop. It was his question that added the second test, for thinking tokens. He followed each step through plain explanations and approved it or pushed back. Checking the code and the rule line by line was Claude's work.

Claude Fable 5.2 is an Anthropic model, and this experiment measures an Anthropic product. The rule was fixed and published before any data, the graders are LiveNerf's, and the data will be public, so the work can be checked without trusting whoever did it. This is an independent project.

## In this repo

```
PREREGISTRATION.md         the rule for reading the results, fixed before the run
RUNNER_SHA256.txt          sha256 of every file of the program that sends the questions, and of the four input files it reads
LICENSE                    MIT
ccversions/judge.py        the rule as arithmetic: the scan, the shuffles, the third pass rule, the ranges
ccversions/analyze.py      reads the graded answers and writes the report, tables and figures
ccversions/grade.py        which answers count (section 3 of PREREGISTRATION.md), imported by analyze.py
ccversions/extract.py      reads one ask's fields out of Claude Code's output, imported by grade.py
ccversions/modes.py        the ways of asking, imported by extract.py
ccversions/__init__.py     makes the folder a package
inputs/formal_arms.json    the groups: versions, way of asking, passes
inputs/formal_run.json     the run settings: seed, block size, asks at once, usage lines
tests/                     tests of judge.py and analyze.py on made-up answers, and of the server tool rule
simulations/               the simulations behind the numbers in PREREGISTRATION.md, with their outputs
```

The files in `ccversions/` and `inputs/` are copied byte for byte from the program that will run, so their sha256 match the lines in `RUNNER_SHA256.txt`. The tests are copied unchanged as well. `work_dir` in `formal_run.json` is a relative path, in Chinese, to a folder on the test machine outside this repo. It is left as it is so that the file's sha256 still matches.

To run the tests (Python 3.10 or later with numpy), from this folder:

```
python -B -m unittest discover -s tests
```

`simulations/README.md` says what each simulation is and how to run it again.

Comments in the code mention "the design file" and its sections. That is the Chinese working copy of this rule, and its sections are numbered differently. Its sections 1, 2, 3, 4, 5, "5-2", 6, 7 and 8 are sections 3, 4, 5, 7, 8, 6, 9, 10 and 11 of PREREGISTRATION.md, and the part of its section 2 on a run that stops is "What stops the run" in section 2 here. "Checklist" in comments means a list of controls kept in working notes offline. The trial layers are listed in section 12 of PREREGISTRATION.md.

The program that sends the questions is published together with the results, and its files will be added then. `RUNNER_SHA256.txt` gives the sha256 of each of them now, before the run, so anyone can check later that the published program is the one that ran.

After the run, this repo gets the report, a table with one row per ask, each version's accuracy in every pass, and the figures. Question text and raw answers stay offline, because the GPQA authors ask that their questions not be republished.

## Limits

- The questions are multiple choice and maths. Most complaints are about long coding work, which these 78 questions leave out.
- The model sees the tools and can't use them. A real user's tools work.
- It measures Opus 5.5 as served on a few days in November 2026, through each version. What the server did when each version came out can't be measured now.
- It can't tell "this version's prompt is different" apart from "the server treats this version differently". Both count as the version.

## Thanks

To [LiveNerf](https://github.com/ninjahawk/livenerf), for the questions, the graders and the published daily data that this experiment is built on.
