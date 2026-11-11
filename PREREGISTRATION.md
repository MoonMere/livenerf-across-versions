# Preregistration: LiveNerf across Claude Code versions

This file fixes how the results of this experiment will be read. It was committed and pushed before the first real question was sent, so the git timestamp shows that it came first. Once the run has started, nothing above the change log at the bottom is edited. Any change goes into that log with the sentence it changes, the date, and which results had been seen by then.

The same rule exists as code. `ccversions/judge.py` holds the arithmetic and `ccversions/analyze.py` reads the graded answers and writes the report. Simulation 5, behind most of the numbers in this file, calls `judge.py` directly, so its numbers come from the code that will judge the real data.

## 1. The question

[LiveNerf](https://github.com/ninjahawk/livenerf) asks Claude Opus 5.5 the same 78 questions every day through one pinned Claude Code version (2.1.280) and watches the model over time. This experiment holds the time fixed, a few days in November 2026, and changes the Claude Code version instead. The model, the effort setting and the questions stay the same.

There are two questions, and each has its own test:

1. **Accuracy.** Does the share of correct answers differ between versions?
2. **Thinking.** Does the number of thinking tokens differ between versions?

Thinking less and answering worse are separate findings, and they are reported separately.

## 2. What gets sent

### Versions

Every Claude Code version released from 2.1.280 up to 11 November 2026: 39 versions, 2.1.280 to 2.1.322. Versions 2.1.297, 2.1.298, 2.1.313 and 2.1.320 were never released. The list is frozen there. A version released later is not added.

Each binary comes from the official download location, and its sha256 must match the official manifest. Auto update is off and the binaries are read only.

### Questions

LiveNerf's frozen panel of 78 questions: 59 from MMLU-Pro, 12 from GPQA Diamond, 3 from AIME and 4 from other maths competitions. The question file is built with LiveNerf's own code and matches LiveNerf's sha256. One step differs from running LiveNerf's code today: the AIME 2026 dataset on Hugging Face was uploaded again on 19 October 2026 and no longer matches the hash pinned in LiveNerf's code, so the items come from the revision of 15 May 2026, which does match. The GPQA authors ask that their questions not be republished, so question text never appears in anything published here.

### One ask in the main comparison

Every ask is a new `claude -p` process with the question on stdin. With the version's own binary in place of `claude`:

```
claude -p --model claude-opus-5-5 --output-format stream-json --verbose \
  --append-system-prompt "<LiveNerf's system prompt>" \
  --strict-mcp-config --mcp-config '{"mcpServers":{}}' \
  --settings '<the hook below>' \
  --no-session-persistence --permission-mode default --effort high
```

The model receives:

- The version's own system prompt, tool list, tool descriptions and Skill list, exactly as that version ships them.
- LiveNerf's system prompt, two sentences long (`prompts/system_v1.txt` in the LiveNerf repo), appended after it.
- The question as the user message.

The `--settings` value adds one PreToolUse hook that matches every tool:

```json
{"hooks":{"PreToolUse":[{"matcher":"*","hooks":[{"type":"command","command":"/bin/cat >/dev/null; echo 'Tool use is disabled in this session. No tool call will run.' >&2; exit 2"}]}]}}
```

Every tool call the model makes is refused before it runs. The refusal comes back to the model as the result of the call, and it shows the hook's command as well as its message. In the trials a refused Read call came back as:

```
PreToolUse:Read hook error: [/bin/cat >/dev/null; echo 'Tool use is disabled in this session. No tool call will run.' >&2; exit 2]: Tool use is disabled in this session. No tool call will run.
```

In trial layer 7, the first request with this hook matched the first request without it in all 51 pairs compared: word for word in 6 pairs (with dates and session IDs masked), and by input size in the other 45. Every version was in at least one pair. So the model receives what the version would send for a user with no setup of their own. The one difference from a real user is that a real user's tools work. Tools stay unusable here so that the model can't read files or run commands on the test machine. The code calls this mode `stock_blocked`.

Everything else is held fixed:

- Remote feature flags are not fetched (`DISABLE_TELEMETRY=1` and `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1`), so each version runs on the defaults inside its own binary. Flags fetched now would be the server's flags of November 2026, whatever the version's release date.
- Each version has its own config folder. It is empty apart from a device ID that is the same in every folder.
- The working folder is one fixed empty folder, outside any home folder and outside any git repo.
- The environment is built from a fixed list of variable names, the same for every version. Nothing comes from anyone's own Claude Code setup: no `CLAUDE.md`, settings, hooks, Skills, plugins, MCP servers or memory.
- Every Claude Code ask uses the same subscription account.
- At most two asks run at the same time, and never two in the same config folder.
- The timeout is 900 seconds for every version, LiveNerf's number.

### The groups beside the main comparison

| Group | Versions | How it asks | Passes 1 and 2 | Pass 3, if opened | What it is for |
|---|---|---|---|---|---|
| `main` | all 39 | as above | once per pass | once | the comparison itself |
| `flags_on` | 2.1.280, 2.1.299, 2.1.308, 2.1.322 | as `main`, with today's remote flags fetched | once per pass | no | does fetching the flags change anything |
| `author` | 2.1.280, 2.1.322 | LiveNerf's own harness: LiveNerf's two sentences replace the system prompt, no tools, LiveNerf's flags and environment variables, output as `stream-json` | once per pass | no | checks the setup against LiveNerf's published numbers |
| `notools` | 2.1.280, 2.1.322 | the version's own system prompt with LiveNerf's sentences appended, tools, Skills and MCP switched off | once per pass | no | the step between `author` and `main` |
| `effort_medium`, `effort_low`, `effort_xhigh`, `effort_max` | 2.1.322 | as `main`, at that effort | once per pass | `effort_low` twice, the others no | a yardstick for the size of a difference |
| `fable` | 2.1.322 | as `main`, with `--model claude-fable-5-2` | once per pass | no | Fable 5.2 against Opus 5.5 |
| `api` | 2.1.322 | no Claude Code: the whole request that `author` sends on 2.1.322, copied and sent straight to the Messages API | once per pass | no | through Claude Code against straight to the API |

The `api` request differs from the copied one in two places. It leaves out the opening line that introduces Claude Code as the Agent SDK, because with that line in, the account's API credits could not be used. And it sends 10 beta headers, all listed in Anthropic's documentation. Version 2.1.322 sends 15. Five that the documentation doesn't list are dropped. One more that it doesn't list, `per-turn-control-2026-07-01`, is replaced by `mid-conversation-output-config-2026-07-01`, which the documentation names as the one a per-message `output_config` needs.

Whether to add a group that runs through the Claude Desktop app is decided after the main results are in.

### Order

One pass means every arm (one version in one group) answers each of the 78 questions once. With 39 versions that is 3,042 asks in `main` and 1,092 in the groups, 4,134 in all.

Each pass shuffles the 78 questions and cuts them into 26 blocks of 3. Every block holds every version of every group, and the order inside a block is shuffled as well. Wherever the run pauses or stops, every version has had the same share of the clock. The shuffles are seeded with the string `registered-run-20261111` plus the pass and block number. The groups run inside the same blocks as `main`.

### What stops the run

`formal.py` drives the whole run and follows the rules in this file without waiting for a person.

- **The weekly usage line.** See section 4.
- **A usage limit from Claude,** with the weekly reading at 90% or more. The analysis runs on what is there.
- **8 asks in a row with no answer** (an outage). It waits, sends a cheap probe from time to time, and carries on once a probe is answered. After 6 hours of one outage it stops. An outage that comes after asks were going through again is a new one.
- **Anything else** stops the run and reports why: a tool call that ran, a web search done on Anthropic's side during a `stock_blocked` ask, a working folder that is not empty after an ask, an ask that was not billed to the subscription, a failed check before a pass, a block or an ask, an `api` ask that could not reach the server or was answered with a 4xx status, an `api` answer whose cost can't be worked out, API spending in one pass reaching 25 US dollars, an error inside the runner itself, or what reads like a usage limit message while the weekly reading is below 90%, where a real limit is unlikely.

The first two end the run: starting again only writes the analysis again. After any other stop, the rules are these, fixed now because by then some results will have been seen:

- Asks that have a record are neither deleted nor sent again. Each is judged by section 3.
- Once the cause is found, the same command carries on with the asks not yet sent. Questions, groups, seeds, grading and the rule in this file stay as they are.
- If the run can't go on without changing the code that sends the asks, the change and the results seen by then go into the change log below first.
- If it can't go on at all, the analysis uses what is there, and the conclusions say where it stopped and why.

## 3. Which answers count

Each ask goes through these checks in order. The first that matches decides.

| Order | What happened | Recorded as | Counts |
|---|---|---|---|
| 1 | No clean answer came back: timeout (900 s), launch failure, network failure, usage limit, Claude Code exited with an error or printed no result, a refusal that Claude Code reports as an error, the version refused to start because the server's minimum version is newer, the working folder was not empty afterwards, the ask was not billed to the subscription, or (`api` only) an error status, an error inside the stream or a stream cut short | error | no |
| 2 | (`stock_blocked` only) a tool call actually ran, or a subagent sent events | void, `tool_ran`. The run stops | no |
| 3 | The result line counts a web search or web fetch done on Anthropic's side. These never pass through the hook, so the hook can't refuse them. None was seen in the trials or the rehearsal | void, `server_tool`. In `stock_blocked` the run stops | no |
| 4 | A model other than the one asked for (`claude-opus-5-5`, or `claude-fable-5-2` in group `fable`) appears in the usage | void, `fallback` | no |
| 5 | (`stock_blocked`) the number of turns is neither 1 nor 1 plus the rounds of refused tool calls. In the other modes, it is not 1. A continuation after the answer hit the output cap lands here | void, `retried` | no |
| 6 | A refusal that comes back as a normal answer | void, `refusal` | no |
| 7 | (`api` only) the answer stopped at `max_tokens` | void, `max_tokens` | no |
| 8 | (`author` and `api` only) more input tokens than LiveNerf allows: the number of characters in the system prompt and the question, plus 2,500 | void, `context` | no |
| 9 | anything else | graded: LiveNerf's `extract_answer` on the final answer text, then its choice, integer or rational grader against the key. Right is 1, wrong is 0 | yes |

Rows 4, 5, 6 and 8 and the grading follow LiveNerf's own harness, and the graders are imported from LiveNerf's code unchanged. Row 1 holds LiveNerf's failure cases plus a few checks of this setup. Rows 2 and 3 and the turn count in row 5 are this experiment's additions. Row 7 exists because an API request that hits the output cap has no second turn for row 5 to catch.

- **No retries.** An ask that fails is recorded and left. One exception: an ask that never reached the model (launch failure, network failure, sent back by a usage limit, or a failure whose output shows no output tokens) is sent once more at the end of its pass, marked as resent. The resent ask takes the place of the original. A timeout is never resent, because how long an answer takes may depend on the version. Nor is an ask the server refused for its version. An ask that the runner itself declines to start, because a check just before it failed, leaves no record. It is sent as usual once the cause is fixed, and it doesn't count as resent.
- **A version the server refuses.** Anthropic can make old versions refuse to start by raising a minimum version. If any `main` ask of a version comes back that way, the version is out of the comparison as a whole, in every pass. The other versions are compared as usual, every count in this file that depends on 39 uses the number left, and the error limits in section 4 are counted over them. Its answered asks stay in the public table. This has not happened in the trials or the rehearsal.
- **Errors and voids are published.** A table (`errors_and_voids.csv`) gives, for each version and pass, how many errors and voids there were and why. The table of versions (`per_version.csv`) flags any version with more than 5% in a pass (4 or more of 78). 5% is LiveNerf's number.
- **Two ways of counting.** Every accuracy result is computed twice: once with errors and voids left out, once with them counted as wrong. Where the two disagree, both numbers are reported, and only what holds in both is claimed. Thinking is counted only the first way, because a failed ask has no thinking count.
- **Which item counts in a pass.** An item counts in a pass once all 39 versions in `main` have a record for it, whatever its outcome. An unfinished pass is counted item by item this way. So every counted item has all 39 versions, and a stop part way through can't favour some versions.
- **Trials and the rehearsal don't count.** Section 12 lists what they showed.

## 4. How many passes, and which ones decide

1. Two passes first. The groups run in both, inside the same stream.
2. After two passes, the program writes an interim report: the accuracy test (section 5, errors and voids left out) and the thinking test (section 6), each on the two passes.
3. A third pass opens when both of these hold:
   - At least one of the two tests points to a drop (defined below) with p < 0.10. This line is looser than the 0.05 used for conclusions, and it only decides whether to spend more quota.
   - Errors plus voids over the first two passes are at most 5% of the `main` asks in the items that count (section 3), and at most 10% for each version over the two passes together. This check counts failed asks only.
4. The third pass: every version answers all 78 questions once more and `effort_low` answers them twice more, all in one stream. With 39 versions that is 3,198 asks. The other groups don't run again.
5. If step 3 doesn't hold, there is no third pass and the conclusions use two passes. If too many errors and voids were the reason, the conclusions say so.
6. The program makes this call on its own, by the fixed rule: `judge.opens_third_pass` for the drop and the line, `analyze.third_pass_decision` for the error limits.

### Points to a drop

The test in section 5 reports the most marked segment of versions. Two shapes count as pointing to a drop:

- the segment is lower than the rest, and there are older versions before it. The drop starts where the segment starts.
- the segment is higher than the rest, and there are newer versions after it. The drop comes right after the segment.

The shape alone is not enough. The step itself has to hold up. A low segment is compared with the versions before it alone, and a high segment with the versions after it alone. The distance between them is measured in standard errors:

```
sd   = sqrt(sum of squared residuals / (number of values - number of item and pass cells))
step = (mean residual of that side - mean residual of the segment) / (sd * sqrt(1 / n_segment + 1 / n_side))
```

For a high segment the sign of `step` is flipped. Residuals are defined in section 5. There are two bars. To open a third pass, `step` must be at least 2.0. To be called "lower" in the conclusions, it must be at least 3.0 (section 5). The bars differ because the two mistakes cost different things: a third pass opened for nothing costs quota, and a rise announced as a drop is a wrong headline.

The reason for the step check: when later versions really are higher overall and the first two or three versions happen to score high, the most marked segment can come out as "versions 3 to 21 are low", which by position alone reads as a drop in the middle. In a round of simulation 5 that judged by position alone, a true rise of 4 to 5 points over the last 18 versions was announced as a drop in the middle about 4 times in 10. With the bar at 3 standard errors it is 2 or 3 times in 100 (2.3% to 2.8%).

The remaining shape, a segment from some version to the newest that is higher than everything before it, says only that something rose. It doesn't open a third pass. The third pass is there for a curve that is high early and lower later. A curve that is flat, or goes up and down but ends about where it started, isn't worth the extra quota.

### Usage lines

The run is limited by the weekly quota of the account it uses. The reading is the share of that quota used, as reported with the latest ask.

- Passes 1 and 2 stop when the reading reaches 70%. Once a third pass is open, the line moves to 95%: a drop that the first two passes point to gets its third pass even when the quota left covers only part of it.
- If passes 1 and 2 reach 70% before they finish, the rule in step 3 runs on the data so far. If it opens the third pass, the line moves to 95%, the rest of passes 1 and 2 runs, then pass 3. If it doesn't, the run stops and the conclusions use what is there. The simulations did not check this case on its own. Going by the rehearsal's costs, two passes should use about a quarter to a third of the weekly quota, so this case is unlikely.
- If the third pass reaches 95% part way, everything it finished counts.
- Nothing waits for the quota to reset. Asks sent a week later would no longer share the clock with the rest.

### One rule for two passes or three

The same test runs on all passes pooled, whether there are two or three. If two passes cleared the line, a third was opened, and the three pooled don't clear it, the conclusion is "not confirmed by the third pass".

### Does looking at two passes first spoil the line?

It doesn't, as long as the rule is fixed before the run and the whole procedure is checked as one piece. Simulation 5 does exactly that. It makes 39 versions that are truly identical, runs two passes, opens the third by the rule above, adds it when opened, then tests as in sections 5 and 6, and counts how often a difference is called.

| When the versions are truly identical | Third pass opened | Accuracy difference called | Thinking difference called | At least one called |
|---|---|---|---|---|
| third pass finished | 18.6% | 2.7% | 1.9% | 4.5% |
| same, with right answers and long thinking linked within an ask | 16.5% | 2.8% | 1.8% | 4.5% |
| third pass stopped half way by the usage line | 16.7% | 3.1% | 2.3% | 5.4% |
| third pass stopped a quarter of the way | 17.6% | 4.3% | 3.0% | 7.1% |

Each row comes from 4,000 simulated datasets, each shuffled 1,000 times, so the figures can be off by a few tenths of a point. Accuracy and thinking each stay within 5%. That is lower than the roughly 5% from testing two passes alone, because most chance hits at two passes are washed out by the third.

The opening line was tried at 10%, 15%, 20% and 25%, and 10% was chosen. At 10%, identical versions open a third pass by chance 16.5% to 18.6% of the time, and a true drop of 4 points from version 22 on opens it 8 times in 10. At 25%, the chance openings rise to about 4 in 10, and an accuracy difference is called 3.5% of the time instead of 2.7%.

## 5. The accuracy test: any run of consecutive versions

The versions are sorted by version number, which is also their release order.

**Take out item difficulty.** In each cell (one item in one pass) there are 39 results, one per version. Average the ones that count and subtract that average from each of them. These are the residuals. A segment's score is the mean residual over all its values. With complete data, the difference between two segments' scores equals the difference in their accuracy. With gaps, a version that lost a few easy items isn't dragged down by it.

**Every segment.** A segment is any run of consecutive versions, from a single version up to all versions but one. That gives 779 segments for 39 versions. "From version X to the newest", "version X alone" and "versions X to Y" are all segments. No version is named in advance, and the data decide where the cut falls.

For each segment:

```
diff = score inside - score outside
z    = diff * sqrt(n_in * n_out / (n_in + n_out))
```

`n_in` and `n_out` are the numbers of values that count inside and outside. Segments of different lengths carry different amounts of luck, which is why diff is scaled to z. The statistic is the largest |z| over all 779 segments.

**Shuffle.** If the versions don't differ, it is luck which version each result in a cell landed on. So the 39 results of each cell (missing ones included) are dealt to the 39 versions at random, each cell on its own, and the largest |z| is taken again. This is done 10,000 times with seed 20261111.

```
p = (1 + number of shuffles whose largest |z| >= the real largest |z|) / (1 + 10,000)
```

The line is p < 0.05. Each shuffle also takes the largest of 779, so choosing the most marked segment is already paid for in the line.

**What is reported.** The segment with the largest |z|, and in a table the other segments whose |z| is above the 95th percentile of the shuffled maxima (up to 50). A segment that starts at the first version and the segment right after it are one cut seen from two sides, with the same |z| and opposite signs. It is reported as "from version X on". Three more numbers go with it: the versions before the segment, the segment, and the versions after it, each as its mean residual against all versions. They show whether the segment is a dip in the middle or a step down that lasts.

**A difference is declared when all three hold:**

1. p < 0.05.
2. |diff| is at least 3 points. LiveNerf uses the same minimum.
3. In each pass alone, the same segment's diff has the same sign as the pooled diff. A pass where fewer than half the items count is left out of this check, and its data still count in the pooled numbers.

When the versions truly don't differ, the whole procedure, third pass rule included, calls an accuracy difference 2.7% to 4.3% of the time (section 4).

For a declared difference, the report gives its size in points and a range: the 78 items are redrawn with replacement 10,000 times (seed 20261111), diff is recomputed each time, and the middle 95% is the range.

Following section 3, the test runs twice, once with errors and voids left out and once with them counted as wrong. An accuracy difference is declared only when both runs declare it with the same sign.

**Saying "lower" takes one more step.** The report says "from version X on, accuracy is lower" or "versions X to Y are lower" only when a difference is declared, the segment has one of the two shapes of section 4, and its `step` is at least 3.0. A declared difference that doesn't point to a drop is written up as which segment is higher than which, without the word "lower". This extra bar costs true drops almost nothing: in simulation 5, nearly every true drop that was declared also met it. The exception is a run of low versions that starts very early, with only four or five versions before it, and ends before the newest version. Simulation 5 has no such case. A separate check on made-up data (`simulations/检查_变低开始得很早.py`) found that about 7 to 9 in 10 of those declared runs meet the bar. The rest are written up as which versions are higher than which. A drop that starts as early and lasts to the newest version met the bar nearly every time it was declared.

## 6. The thinking test

A post on X on 7 November 2026 said thinking at effort high had dropped sharply since 3 November. So thinking gets its own test.

**What is measured.** For each ask, the thinking tokens Claude Code reports in its `result` line, `usage.output_tokens_details.thinking_tokens`. All 39 versions reported it in the trials. The thinking text itself comes back empty. Only the count is there.

**Which asks count.** The same asks that count for accuracy.

**Method.** Each ask's value is `ln(thinking tokens + 1)`. From there it is the same as section 5: residuals within each cell, all 779 segments, the largest |z|, 10,000 shuffles with seed 20261111, line p < 0.05. A single version is one of the 779 segments, so single versions are covered by the same scan.

**A thinking difference is declared when all three hold:**

1. p < 0.05.
2. The size is at least 10%: `|exp(diff) - 1| >= 0.10`, where diff is the mean log inside minus the mean log outside. 10% was chosen because LiveNerf's daily median output tokens vary from day to day with a standard deviation of about 8%.
3. The same sign in every pass, with the same rule for unfinished passes as section 5.

"Thinks less" is said only when a difference is declared, the segment has one of the two shapes of section 4, and its `step` is at least 3.0.

This line is thinking's own 5%, separate from the accuracy line. When neither question has a real difference, the whole procedure calls a thinking difference 1.8% to 3.0% of the time, and at least one of the two 4.5% to 7.1% of the time (section 4). The conclusions say so.

**Reported without a verdict:** each version's geometric mean and median thinking, how many of each version's asks had zero thinking, and the thinking of the four effort groups as a multiple of high, as a yardstick.

**What this can see** (simulation 5, the difference found 8 times in 10):

| True situation | Two passes only | Two passes, third when the rule opens it | Three passes always |
|---|---|---|---|
| thinking lower from version 22 on (the last 18 versions) | about 11% less | about 11% less | about 11% less |
| one version alone (version 26) thinks less | about 27% less | about 26% less | 25% less or under |

The first row reads about 11% in all three columns, and a third pass doesn't shrink it, because of the 10% minimum. When the true difference is right around 10%, the measured one often falls below 10%, and more data don't help it clear the minimum.

The simulated data were made as "each ask's log thinking is the item's level plus random noise of fixed size". The size comes from trial layer 5, where 2.1.280 and 2.1.322 each answered the 78 items once: the standard deviation of the log difference for the same item was 1.27.

For scale: in the trials, 2.1.280 in LiveNerf's own harness thought 0.30 times as much at effort low as at high (item by item, 78 items each, 95% interval 0.20 to 0.45). A version whose thinking fell close to the low level would show up in two passes even on its own. Accuracy can't do that: in LiveNerf's validation, low scored only about 8 points below high, and a single version needs about 16 points to show in two passes.

**Not checked.** Real thinking counts include zeros, which the simulated data don't. In the rehearsal, medium and low thought for zero tokens on the multiple choice item. The 1.27 comes from one way of asking (`notools`), two versions, one pass each. None of this moves the real line, which comes from shuffling the real data.

## 7. What size of difference this can see

Simulation 5 again, for accuracy. Each figure is the true difference that the test finds 8 times in 10.

| True situation | Two passes only | Two passes, third when the rule opens it | Three passes always |
|---|---|---|---|
| lower from version 22 on (the last 18 versions) | about 4.5 points | about 4.2 | about 3.6 |
| 13 versions in a row lower, in the middle (versions 19 to 31) | about 4.7 | about 4.5 | under 4 |
| the last 6 versions lower | about 6.2 | about 5.8 | about 5.4 |
| 3 versions in a row lower (versions 25 to 27) | about 8.8 | about 8.2 | about 7.3 |
| one version alone lower (version 26) | about 16 | about 15 | about 13 |

- The middle column is what this run gets when the rule is followed and the quota covers the whole third pass. A third pass stopped part way lands between the middle column and "two passes only". "Three passes always" runs the third pass whatever the first two show. It is there for comparison, and the registered run follows the middle column.
- Each situation used 400 simulated datasets, so "8 times in 10" can be off by two or three points. The figures are read between two neighbouring steps of the output and can be off by a few tenths of a point.
- The simulated data use LiveNerf's results for each item: for each item, (correct + 1) / 10 from its 8 confirmation samples. One version answering the 78 items once then varies by about 4.9 points, which matches the 4.87 points LiveNerf measured over 47 days.
- Where the drop starts matters. From version 22 on, both sides of the cut hold many versions. A drop that starts near either end leaves few versions on one side and needs to be larger: "the last 6 versions" above is one case. In the separate check of section 5, a drop of 5 points from version 5 or 6 on was declared only 4 to 5 times in 10.
- When all versions are truly identical and each answers twice, the best and worst of the 39 usually differ by about 15 points, and by about 12 with three passes (simulation 2). Single versions scattering up and down on a chart is normal, and no conclusion is drawn from it.

So this run can find a drop of four or five points from a version near the middle on, eight or nine points over a few versions in a row, and about fifteen points in one version alone.

The real line comes from shuffling the real data. These figures only show how sensitive the method is.

## 8. Secondary numbers

These are computed and reported, marked as secondary, and never used to say something got worse. The ones that are scanned use the method of section 5 with 2,000 shuffles and no minimum size.

- **Before and after 2.1.303.** Accuracy of 2.1.303 and the 17 versions after it, accuracy of the 21 versions before it, and the difference after item difficulty is taken out. A post on X about [anthropics/claude-code#105112](https://github.com/anthropics/claude-code/issues/105112) pointed at 2.1.303, which is where this experiment started. These numbers are reported only, because no version has a sound reason to be named in advance. The post was its writer's own guess, and the author of #105112 wrote that 2.1.303 ran both before and after the change the issue reports.
- **Output tokens** (log), which hold thinking and the written answer together.
- **Length of the written answer**: output tokens minus thinking tokens (log).
- **Tool attempts**: the share of asks where the model tried a tool, and how many rounds it tried.
- **Errors and voids**, as a share.
- **Time per ask** (log).
- **Accuracy over time**: all versions together, block by block, in the order the blocks ran.
- **Tried a tool or not**: accuracy and thinking each scanned separately for asks where the model tried a tool and asks where it didn't.
- **Versions that send the same thing.** Neighbouring versions whose first request had the same size on every item are probably sending the same content, and they are grouped. This uses pass 1 and needs at least half the items to compare. The report lists the groups, tests whether versions inside a group differ (shuffling only inside the group, 2,000 times), and scans again with each group as one unit. Numbers only. One known difference does not show in the size: with remote flags not fetched, 2.1.300 and 2.1.301 send one extra request parameter, `safeguards`, that the other versions don't. This was seen in the trials with tools switched off and was not checked again in `stock_blocked`. Every version's own numbers are reported as well, so whether these two differ from the rest of their group can still be seen.

The table of right and wrong answers for every item, and every version's accuracy in every pass, are published so that anyone can redo the analysis.

## 9. The groups

| Group | Compared with | How | What it can tell |
|---|---|---|---|
| `flags_on` (4 versions) | the same 4 versions in `main` | item by item, the 4 versions together | whether fetching today's remote flags makes a difference. With the 4 together, about 7 points would show |
| `author` (2 versions) | LiveNerf's published daily numbers, and the same 2 versions in `main` | against LiveNerf: do accuracy and the median output tokens over the 78 answers fall inside LiveNerf's daily range? LiveNerf's numbers are split into before 3 November and from 3 November on. Only 2.1.280 can be compared this way, because LiveNerf runs only 2.1.280. Against `main`: item by item | whether the setup is built right, how much Claude Code's own system prompt and tool descriptions change things, and whether output length on 2.1.280 at high now matches LiveNerf's numbers from before 3 November |
| `notools` (2.1.280, 2.1.322) | `author` and `main` on the same versions | the three ways of asking as three steps, item by item | when the gap is large, which step it comes from. When it is a few points, the steps can't be told apart |
| the four effort groups (2.1.322) | 2.1.322 at high in `main`, and the mean of all 39 versions at high | item by item, accuracy and thinking, with a range | a yardstick: how much one effort step moves accuracy and thinking, to put any version difference in scale. For `effort_xhigh` and `effort_max` also: if neither scores higher than high, the report says these 78 items are at their ceiling for accuracy. LiveNerf measured one step down (medium against high) at -4.2 ± 3.9 points |
| `fable` (2.1.322) | Opus 5.5 in `main` on 2.1.322 | item by item | how far apart the two models are on these 78 items |
| `api` (2.1.322) | `author` on 2.1.322 | item by item | whether going through Claude Code differs from calling the API directly |

Item by item means: for each item, each side's mean over its answers, then the difference for each item, averaged over the items both sides have. Ranges redraw the items 10,000 times with seed 20261111. Thinking and output comparisons are given as ratios. Each group has few answers, so group results are given as a difference and a range only, and the report says that the groups are small.

## 10. How results will be written

- **A difference is declared.** Say which segment or version, how many points, the range, and the figure for each pass. Beside it, give the effort groups' differences so the size has something to compare against.
- "Lower" and "thinks less" appear only when a difference is declared and it meets the bar for saying "lower" (section 5). Otherwise the report says which segment is higher than which.
- **Two passes cleared the line, a third was opened, and three pooled don't.** Give the figure from two passes and the figure from three, and say "not confirmed by the third pass".
- **Nothing declared.** Say "this method saw no change larger than X across a run of versions, and none larger than Y in a single version", with X and Y from section 7. Never write "no nerf".
- When nothing is declared, no extra passes are run and no more quota is spent on it. The public page says what was done, that no difference was seen, the smallest difference the method could see, and gives the data.
- **Before any drop is reported publicly, two checks.** First, a separate Claude agent that has not seen the analysis code redoes the analysis from this file alone, and the two sets of numbers must match. Second, compare what the version where the drop starts sends to the model with what the version before it sends: the size of the first request, and for 2.1.300 and later the saved request text. If the content didn't change and the score fell, treat it first as a fault in the measurement and look for it.
- **Every conclusion carries three limits.** The questions are LiveNerf's 78 multiple choice and maths questions, and coding work is outside them. The model sees the tool descriptions and can't use any tool, while a real user's tools work. What is measured is Opus 5.5 as served in these days of November 2026, sent through 39 versions of Claude Code. What the server did on each version's release day can't be measured.
- This experiment can't separate "this version's prompt is different" from "the server treats this version differently". Both count as the version.
- If a difference moves together with the share of asks that tried a tool, the report says it may be linked to the blocked tools and gives the split numbers from section 8.
- **Thinking gets its own paragraph.** For a declared difference: which segment or version thinks more or less, by what per cent, the range, the figure for each pass, the effort groups' thinking as a multiple of high, and the accuracy difference of the same segment or version. Say "thinks less" or "thinks more", never "got dumber". If nothing is declared: "this method saw no change in thinking larger than X", with X from section 6.

**Figures.** One point per version: its accuracy over all passes pooled. A line through each point: the middle 95% when the 78 items are redrawn 10,000 times. Behind the points, a grey band: where versions land by luck alone when all 39 are identical. Over 10,000 shuffles, take the highest and the lowest version each time. The top of the band is the 97.5th percentile of the highest, and the bottom is the 2.5th percentile of the lowest. If all 39 points sit inside the band, no version stands out on its own.

A second figure does the same for thinking, with each version's geometric mean. The two figures sit one above the other with the versions lined up.

## 11. The strongest objections, and the answers

- **Too strict.** One version alone has to drop about fifteen points to show. Users may feel a drop of a few points, and this rule would say "not seen". The answer: the report says exactly what size the method could see, and the right and wrong table for every item is public.
- **Wrong kind of questions.** Most complaints are about long coding tasks, and 78 multiple choice and maths questions may not show them. This can't be fixed here, so it is stated as a limit.
- **Not naming a version costs sensitivity.** Naming 2.1.303 in advance would find about 3.7 points in two passes (simulation 3, run with an older and stricter line), against about 4.5 without naming. The answer: no version has a sound reason to be named (section 8), so the data decide the cut, and nobody can say the cut was chosen to fit.
- **Taking the largest of 779 segments is choosing after the fact.** The answer: every shuffle also takes the largest, so the choice is already in the line.
- **Deciding on a third pass after seeing two gives the result a second chance.** The answer: the rule was fixed and published before the run, the final test pools every pass against the same line, and a result that clears the line at two passes and misses it at three is written up as not confirmed. The simulation checked the whole procedure as one: with identical versions, an accuracy difference is called 2.7% to 4.3% of the time (section 4).
- **Opening the third pass only for drops is hunting for nerfs.** The answer: the line for calling a difference is the same in both directions. The only lean is in where extra quota goes. A rise is reported too, with two passes behind it, so it needs to be larger to show (section 7, "two passes only").
- **The blocked tools may affect versions differently.** The answer: section 8 splits asks that tried a tool from those that didn't, and `notools` serves as a control with no tool descriptions at all.

## 12. What was seen before registration

No question of the registered run had been sent when this file was committed. These earlier runs were seen. None of them counts in the results.

| Run | Versions | How asked | Items | What was seen |
|---|---|---|---|---|
| trial layers 1 and 2, and the first part of layer 7 | 2 versions, then all 39 | probes only | none | what each version sends, input sizes, whether every tool call is refused |
| trial layer 3 | 2.1.280 | `author`, effort low | 78 | 39 right |
| trial layer 4 | 2.1.280 | `author`, effort high | 78 | 54 right (69.2%), median output 608 tokens |
| trial layer 5 | 2.1.280, 2.1.322 | `notools`, high | 78 each | 43 right, and 46 right of 77 scored (1 void). Item by item, 2.1.322 thought 0.87 times as much as 2.1.280 (95% interval 0.66 to 1.15) |
| trial layer 6 | 2.1.322 | Fable 5.2 asked as in `notools`, and `api` | 10 each | Fable 5.2: 9 right of 10. API: all 10 answered, 8 right |
| trial layer 7 | 2.1.280, 2.1.322 | `stock_blocked`, high | 12 each | 17 right of 24. Item by item, 2.1.322 thought 1.50 times as much as 2.1.280 (95% interval 0.97 to 2.32) |
| rehearsal, 11 November | all 39 and every group | as registered | 3 (one MMLU-Pro, one GPQA, one AIME) | right or wrong and thinking for every version and group on those 3 items, 159 asks |

While this rule was being written, the only data seen were the simulations and the runs above.

## 13. Where the numbers come from

| Number | Source |
|---|---|
| 900 s timeout, 3 point minimum, 5% error flag | LiveNerf |
| -4.2 ± 3.9 points for medium against high, about 8 points for low against high | LiveNerf's instrument validation |
| about 8% daily spread of median output tokens, 4.87 points daily spread of accuracy | LiveNerf's `results/daily.csv`, up to 9 November 2026 |
| each item's chance of a right answer in the simulations | LiveNerf's `data/standard_panel.json` |
| false call rates, power for accuracy and thinking, the opening line | simulation 5 (`simulations/`), which calls `judge.py` |
| how often early drops are declared and meet the bar for "lower" (sections 5 and 7) | the check of early drops (`simulations/`), which calls `judge.py` |
| about 15 and 12 points between best and worst identical versions | simulation 2 (`simulations/`) |
| about 3.7 points with 2.1.303 named in advance | simulation 3 (`simulations/`), run under an older line |
| about 7 points for `flags_on` | a rough calculation from the 4.9 point spread of one version answering the 78 items once |
| 51 pairs of matching first requests, the text a refused call returns | trial layer 7 |
| 1.27 standard deviation of log thinking, 0.30 low against high, the thinking ratios in section 12 | trial layers 3, 4, 5 and 7, from the thinking script in `simulations/` |
| about a quarter to a third of the weekly quota for two passes | costs measured in the rehearsal and trial layers 5 and 7 |
| 70% and 95% usage lines, 10% minimum for thinking, 2 and 3 standard errors for the step, 10% opening line | choices made for this experiment |

## Change log

Nothing yet.
