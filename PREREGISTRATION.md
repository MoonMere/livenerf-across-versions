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

### 12 November 2026: a Claude Desktop group is added

The sentence this changes is in section 2: "Whether to add a group that runs through the Claude Desktop app is decided after the main results are in." Soren Hou decided on 12 November 2026 that the group is run and that the decision does not wait for the results. This entry was committed and pushed before the first Desktop question was sent.

**What had been seen by then.** Pass 1 was complete and pass 2 was about seven tenths sent. Of the real asks, only these had been looked at: how many were sent, whether each was done or timed out, how long they took, what they cost and the usage reading. No answer had been graded. No accuracy or thinking number had been computed or looked at.

**What the group is.**

- The 78 questions, each asked twice (two rounds), one new Desktop session for each ask. Model `claude-opus-5-5`, effort high, permission mode default.
- The Desktop app starts the Claude Code it ships with. On 12 November that was 2.1.321, one of the 39 versions. The version is read from every session's own file. If it changes part way, the asks of each version are reported apart.
- The sessions run in an empty folder. Its settings keep out the user's own instruction files, memory and personal skills, and refuse every tool call with the same hook and the same sentence as `main`. Trial sessions on 12 November showed all of this working.
- The questions are sent with the Desktop app's own tool for starting a session from another session, by the Claude session that looks after the run. Sessions are started one at a time and each is archived before the next one starts. A trial showed that a session started while another one is open gets one more line that lists the other sessions.
- An ask counts only if the question the model received is the question's text byte for byte. An ask whose text differs is discarded and asked again. After that, section 3 decides which answers count, as for `main`. The timeout is 900 seconds from the question.
- The order of the questions in each round is drawn from a fixed seed.

**How it differs from `main` on the same version, besides going through the app.**

- The app wraps the question. The first message reads "Background (from the session that started this one):", then LiveNerf's two sentences, then "Task:", then the question, then one line that names a shared notes folder. In `main` LiveNerf's two sentences are appended to the system prompt and the question is the whole message.
- The system prompt has a section telling the model that it was started from another session.
- Plugins, extensions and connectors installed in the app stay visible to the model, with the skills they bring. Their tools are refused like any other tool. The folder's settings can't take them out.
- Whether the app's sessions fetch today's remote flags was not checked. `main` does not fetch them. (Looked at later: see "things that had been left unchecked" below.)
- The sessions are asked one after another in one stretch of a few hours, on the same account, while the registered run is still going.

**How it is compared.** With `main` on the version the sessions report, item by item as section 9 defines it, for accuracy and for thinking, as a difference and a range, with the note that the group is small. It is reported beside the main comparison. It takes no part in the tests of sections 5 and 6 or in the decision about pass 3.

**Code.** The code that sends the registered run is unchanged and the run was not stopped. The Desktop records are made by a separate script that reads each session's file and writes a record in the registered format, so the registered grading code reads it unchanged. The record's `stdout` field is rebuilt from the session file and the record says so. The script is published with the results.

### 12 November 2026, later: the Desktop group starts again with 77 questions

The first try was stopped after 68 asks and none of them count. No Desktop answer had been graded. The session files showed two problems:

- Most asks had gone out at effort low or medium. A session started with the app's tool gets at most the effort of the session that starts it, and that session's effort had been lowered part way.
- The tool replaces every "@" in a question with a full-width "＠". One question has SMILES strings, so it can't be delivered unchanged.

From here on an ask counts only if its session file shows effort high. The group has 77 questions, and the comparison with `main` uses the same 77. The questions are sent by a separate Claude session that stays at effort high.

### 12 November 2026, evening: a third Desktop round, and a comparison by time of day

Both were decided while pass 3 was being sent. This entry was pushed before pass 3 ended and before the third Desktop round was sent.

**What had been seen by then.** From the registered run: how many asks were sent, whether each was done or timed out, how long they took, what they cost, the usage reading, and the line the run logs after pass 2. That line says whether pass 3 opens and gives a yes or no for whether each of the two tests had declared a difference on two passes. No segment, version, accuracy or thinking number had been looked at, and the interim files had not been opened. From the Desktop group: each ask's duration and output token count, and that 20 asks tried a tool and were refused. No Desktop answer had been graded.

**US working hours** means Monday to Friday, 9 am US Eastern to 5 pm US Pacific. In November that is 14:00 UTC to 01:00 UTC the next day. An ask is inside or outside by the time it was sent.

**A third Desktop round.** The group is compared with `main` on 2.1.321, which now has three passes. Both Desktop rounds were sent between 04:24 and 05:38 UTC on 12 November, outside US working hours. Counting every group, 63% of the asks of pass 1 and 49% of pass 2 were sent inside them, and most or all of pass 3 is expected to fall outside. So the group gets a third round of the same 77 questions, sent inside US working hours on Thursday 12 November US time, the same way as the first two, with its order drawn from the same seed. With it, a third of the Desktop asks are inside those hours, against a bit over a third of the registered run's. If the round has not started by 00:10 UTC on 13 November, or the app no longer starts 2.1.321, the group stays at two rounds. The final report of the registered run stays unopened until the round is in or that time has passed.

**Time of day.** Soren Hou noticed that the passes cover different hours of the day. A pass takes about ten hours and each pass asks the items in a new random order. So every item was answered by all 39 versions at two or three different times of day. The run was not designed for this. It is added to the secondary numbers of section 8, for `main` only.

- For each item and pass: the mean over the 39 versions (accuracy, and `ln(thinking tokens + 1)`), and the share of those asks sent inside US working hours.
- A least squares fit of that mean on item, pass and share inside gives the difference inside minus outside, with item difficulty and whole-pass differences taken out. The range redraws the items 10,000 times. The p value shuffles the items' places within each pass 10,000 times, which is the randomisation the run itself used. Seed 20261111.
- The same fit with a separate difference for each pass gives two parts: the inside hours of pass 1 (the US morning and early afternoon) and of pass 2 (the US afternoon and evening).
- Published without a verdict: the mean for each hour of the day in UTC, after item and pass are taken out, so the day can be cut another way.

The code for this is committed to this repository before the final report is opened. It is in `added_comparisons/`.

**How these two comparisons are worded.** Soren Hou's point was that a large difference by time of day, or between Desktop and `main`, deserves more than a bare number. For these two comparisons only, three wordings are fixed here.

- **Clear.** All of: p < 0.01. A size of at least 3 points for accuracy or 10% for thinking. The same sign in each part taken alone, where the parts are the two above for time of day, and each Desktop round against the mean of `main` for Desktop. For time of day, also larger than the largest difference between the levels of two passes in the same fit. For Desktop, p comes from flipping the sign of each item's difference 10,000 times. A clear difference goes into the summary of the results in plain words, followed by the causes this run can't tell apart and the test that would tell them apart.
- **Points one way.** p < 0.05 and the size, short of clear. Reported with its range and those words.
- **Otherwise.** "No difference larger than X was seen", with X from the range.

Two limits go beside any time of day result. In passes 1 and 2, all the asks inside US working hours were sent on one US working day, Wednesday 11 November. And that day was a US federal holiday. If the end of pass 3 runs past 14:00 UTC on 12 November, those asks are inside the hours of a second day, and the result gives the days as they were. A clear result is written as a difference between these hours on these days.

### 12 November 2026, night: a group that replays the Desktop app's system prompt

Decided while pass 3 was being sent. Soren Hou agreed to add the group. The design below is by the Claude session that looks after the run. This entry was pushed before the first scored ask of the group.

**Why.** A separate look at Soren Hou's own Claude Code session files found two things. The Desktop app saves, at the start of every session it opens, a copy of the system prompt it gave the model. And that text changes while the Claude Code version stays the same. The largest change was on 14 October 2026 (UTC), when the text grew from 17,564 to 30,726 characters on 2.1.295. The registered run compares versions of the command line program, so a change of this kind is outside what it can see. The Desktop group uses the app on one day, so it sees one text only.

**What had been seen by then.** Everything listed in the entry above, and also these. From the registered run: the first event of each ask, which lists the skills, plugins and MCP servers that were loaded. From the Desktop group: the system prompt each session saved, the beta list of each request, and whether a session file holds the word `userEmail`. From Soren Hou's everyday Desktop sessions: the saved system prompts, by heading, length and hash, and three of the texts in full. No answer had been read or graded. No accuracy or thinking number of this experiment had been computed or looked at, and the interim files had not been opened. A separate analysis of his everyday session files counts thinking by day. Its numbers had been read and were not checked. They are no part of this experiment.

**Added on 12 November 2026 at 23:45 AEDT, before the first ask of this group.** The registered run ended at 12:42 UTC. Two more things had been seen by then. One is the line the run logs after pass 3. It gives a yes or no for whether each of the two tests declared a difference on three passes. The other is the input token count of the first request of each `main` ask on 2.1.321, which the checks below compare with arm e. The final report and the interim files had not been opened, and no answer of the registered run had been read or graded.

**What the group is.** The 78 questions, asked three times with each of five system prompts: 1,170 asks. All of them use the command line binary of 2.1.321, the same file as `main`.

| Arm | System prompt | Where it comes from |
|---|---|---|
| `dsp_a` | the Desktop text before the change | saved by a Desktop session opened on 14 October 2026 at 12:34 UTC, on 2.1.295. 17,564 characters |
| `dsp_b` | the Desktop text after the change | saved by a session opened on 14 October 2026 at 23:38 UTC, on 2.1.295. 30,726 characters. Every paragraph of the earlier text is in it word for word. It adds 13,154 characters: a section on starting other sessions, and a section on the task list and wrapping up |
| `dsp_c` | the Desktop text of 12 November | saved by a session opened on 12 November 2026 at 07:12 UTC, on 2.1.321. 33,146 characters |
| `dsp_d` | the Desktop text of the Desktop group | the text that all 154 sessions of the Desktop group saved. 33,330 characters. It has one section more than `dsp_c`, which tells the model that it was started from another session |
| `dsp_e` | 2.1.321's own system prompt | unchanged, as in `main` |

- The lengths in the table are those of the saved copy. It is a list of text items, measured here joined by single newlines. One item is only the marker `__SYSTEM_PROMPT_DYNAMIC_BOUNDARY__`.
- As sent: the marker item is dropped, as 2.1.321 itself drops it before sending, and the other items are joined by an empty line into one text. In arms a, b and c the `# Memory` section (2,086 characters) is taken out. It names the user's memory folder, and the Desktop group's text has no such section. As sent, the four texts have 15,453, 28,615, 31,034 and 33,303 characters.
- Arms a to d pass `--system-prompt` with the saved text, an empty line, and LiveNerf's two sentences. This replaces the version's own system prompt. Arm e appends LiveNerf's two sentences to the version's own system prompt, as `main` does.
- Everything else is as in `main`: the model, effort high, tools visible and refused by the same hook, remote flags not fetched, the same fixed list of environment variables, the same login, output as `stream-json`. Three things differ from `main`. The config folders are new empty folders, one for each ask that runs at the same time, prepared the way the registered run prepares its folders. 5 asks run at a time, where `main` runs 2. And the asks are sent on another day.
- A round is ordered the way the registered run orders a pass. The 78 questions are shuffled and cut into 26 blocks of 3. The 15 asks of a block (3 questions, 5 arms) go out in a shuffled order. Seed 20261111. So the arms share the same hours.
- Section 3 decides which answers count. The run stops after 8 failed asks in a row, as the registered run does, and when the weekly usage reading reaches 0.99. If it stops part way, the asks that are in still count, and the report says how many rounds each arm got.
- The sha256 of each text as sent is in `desktop_prompt/PROMPTS_SHA256.txt`.

**Checks before the first scored ask.** One unscored ask for each arm, with its session file kept. For arms a to d, the system prompt in the request must hold the saved text byte for byte, followed by LiveNerf's two sentences. Anything the program puts around it is recorded and published. For arm e, the command and the names of the environment variables must match `main` on 2.1.321 except for the config folder. Then two questions for each arm, unscored, to check that the records are written as they should be. If a check fails, the group is not run.

**Result of the checks, 12 November 2026 at 23:49 AEDT, before the first scored ask.** 25 unscored asks were sent. In arms a to d the request holds the system prompt in two blocks. The first is one line that the program adds itself: `You are a Claude agent, built on Anthropic's Claude Agent SDK.` The second is the saved text, an empty line and LiveNerf's two sentences, byte for byte, with nothing before or after. In arm e the first block is `You are Claude Code, Anthropic's official CLI for Claude, running within the Claude Agent SDK.`, and the first request has the same input token count as `main` on 2.1.321 for the same question. All five arms sent the same model, effort high and the same 12 tools. All 10 asks of the small batch were done, with 5 running at a time. The checks passed and the group is run. The first line is the same in arms a to d, so it does not touch b minus a, c minus b or d minus c. It is one more difference inside d minus e, and between arm d and the real app, whose first line begins `You are Claude Code`.

**How it is compared.** Item by item, as section 9 defines it, for accuracy and for thinking. p comes from flipping the sign of each item's difference 10,000 times, seed 20261111.

| Comparison | What it asks | How it is worded |
|---|---|---|
| b minus a | whether the two sections added on 14 October changed anything. This is the main one | the three wordings of the entry above |
| d minus e | whether swapping the command line program's own system prompt for the Desktop app's saved text changes anything | the three wordings of the entry above |
| c minus b | the changes between 14 October and 12 November | difference and range |
| d minus c | the section about being started from another session | difference and range |
| e minus `main` on 2.1.321 | the same way of asking, on another day, in other folders, sent by another script | difference and range. If this one comes out clear by the lines of the entry above, a warning goes beside every comparison that crosses the two batches |
| the Desktop group minus d, on its 77 questions | what the real app adds beyond the saved text | difference and range |

For the three wordings, the parts that must have the same sign are the three rounds.

**What size this can see.** One version answering the 78 items once varies by about 4.9 points (section 7). Two arms with three rounds each then differ by about 4 points by chance alone. A true difference of about 11 points would be found 8 times in 10 at p < 0.05. This figure is worked out from the 4.9 and was not simulated. Thinking is a continuous number and is more sensitive. How much more was not estimated.

**Limits.**

- The items are single questions with single answers. The two sections added on 14 October are about work in many steps: keeping a task list and starting other sessions. Finding no difference on these items would say nothing about that kind of work.
- How the app splits the saved items into the blocks of a request was not looked at. Here they go out as one text.
- The saved text is only part of what the app sends. The opening line, a long section of safety rules for browsing, the instructions of MCP servers, a block with the account's email address and git status, and the tool descriptions are missing from it. Arms a to d test the saved text, sent through the command line program.
- All four texts come from one person's computer.
- The group was added part way, after the things listed above had been seen.

**Code.** The asks are sent by a separate script that uses the registered sender's modules unchanged. It is published with the results. The code for the comparisons is committed to this repository before the final report is opened.

### 12 November 2026, night: things that had been left unchecked

The project's own notes were read through for places where something was written down as not checked and nobody went back to it. Nine of them could bear on a conclusion. They were gone through before the final report was opened. No ask was sent for this and no answer was read.

For the Desktop comparison:

- **The binary.** The app's copy of 2.1.321 and the command line copy have the same size and different sha256. With the code signatures removed, the two files differ in two places only: the header at the start of the file, and a property list embedded in the command line copy. Every other byte is the same. So the Desktop group runs the same program as `main` on 2.1.321. Section 2's sentence about sha256 covers the 39 command line binaries.
- **Remote flags.** This replaces the line "Whether the app's sessions fetch today's remote flags was not checked." In the trials, 2.1.321 sent three beta names with remote flags fetched that it leaves out without them. None of the three is in any of the 257 requests recorded in the Desktop group's folder. In 256 of them the beta list is the list `main` sends plus one name. The other request belongs to a trial session. Whether the app fetched the flags can't be seen in the records. What can be seen is that these three were off.
- **Environment variables.** The variables the app's sessions run with were not recorded for rounds 1 and 2. Their names are recorded at round 3.
- **Login.** The app uses its own login and the registered run uses a token. One thing that follows from this was found. 229 of the 230 session files in the Desktop group's folder hold the word `userEmail`, the name of a block that shows the model the account's email address. In the trials with the token login the model saw no email address. That was looked at on 2.1.280 and 2.1.322 only. This is one more difference between the Desktop group and `main`.
- **The system prompt.** The text the Desktop group's sessions saved has 33,330 characters. The system prompt that 2.1.321 sent in the trials, with tools switched off and remote flags not fetched, had 5,922 characters with LiveNerf's two sentences. The two share the headings `# Harness`, `# Environment` and `# Context management`. The group in the entry above measures what this difference does.

For the main comparison:

- **Skills, plugins and MCP servers.** Section 2 says that nothing comes from anyone's own setup. The trials had looked at two versions. The first event of each ask has now been read for all 39 versions: 3 trial asks for each version, every ask of passes 1 and 2, and the 2,283 asks of pass 3 that were in by then. No MCP server was loaded in any of them, every plugin was built into the program, and no skill of the user's own was there. The program's own lists differ by version: no plugin in 2.1.280, one from 2.1.281, two from 2.1.286 and three from 2.1.317, with 16 skills up to 2.1.285 and 17 from 2.1.286. In `flags_on` the fetched flags add one built-in plugin and two skills.
- **Fallback on the oldest versions.** On 2.1.280 to 2.1.284 the usage block may fail to show that the safety classifier moved an ask to another model. Such an answer would then be graded as an Opus 5.5 answer where a later version would void it. LiveNerf saw 9 such asks in 3,666. The report gives the number of voided asks for every version, so that a gap in these five can be seen.
- **Effort on versions before 2.1.300.** These 18 versions keep no record of the request. The effort is the one the program reports. If one of them lowered the effort without saying so, this run can't see it.
- **LiveNerf's two sentences on versions before 2.1.300.** `--append-system-prompt` is in the help text of all 39 versions and none of them rejects it. That the two sentences reach the model was seen in the requests of the 21 versions from 2.1.300 on. For the 18 before, it had not been checked directly. After pass 3 one unscored ask goes to each of the 18 to check it, and the report says what it showed.

### 13 November 2026: a third pass for group `api`

Decided on 13 November 2026 at about 10:25 in Melbourne (12 November, 23:25 UTC). This entry was pushed before the first ask of this pass.

**Why.** Soren Hou asked whether the API group should have three passes like the two other ways of reaching the model, the command line program and the Desktop app. Of all the comparisons in section 9, `api` against `author` on 2.1.322 has the fewest asks when both sides are counted: 78 questions on two passes on each side. Its API asks are paid from API credits and take nothing from the weekly usage of the subscription.

**What had been seen by then.** Everything listed in the entries above, and also these. The line the run logs after pass 3, which gives a yes or no for whether each of the two tests declared a difference on three passes. The answers to the 19 unscored asks that checked LiveNerf's two sentences on the versions before 2.1.300. For every ask of the desktop-prompt group: whether it was done, the model, the input token count of the first request and whether a tool ran. The names of the environment variables of three sessions of Desktop round 3. Of group `api` in passes 1 and 2: whether each ask was done, its HTTP status and its cost. No answer of the registered run, the Desktop group or the desktop-prompt group had been read or graded. The final report and the interim files had not been opened.

**What is added.** 156 asks: the 78 questions once more for group `api`, and once more for group `author` on 2.1.322, the group it is compared with. Both groups are specified as in section 2. The two go out in one plan made by the registered sender with the registered seed: 26 blocks of three questions, the six asks of a block in shuffled order, two at a time. In passes 1 and 2 the two groups were also mixed in one sequence, so in every pass they share the same hours. A dry run showed that each of the 156 asks is the same as the pass 2 ask of the same group and question: command, question, config folder, names of the environment variables, API request template and beta list.

**How it is compared.** As in section 9: item by item, each side averaged over its passes. The report of the registered run gives the figure on two passes. The figure on three passes is given beside it and marked as added.

**Limits.**

- Pass 3 of these two groups is sent on 13 November in Melbourne, and passes 1 and 2 on 11 and 12 November. The two groups are sent together, so the comparison between them does not depend on the day.
- In pass 3 the two groups are sent on their own. In passes 1 and 2 they sat among the asks of the 39 versions.
- `author` on 2.1.280 gets no third pass. Its comparison with LiveNerf's published figures stays on two passes.
- The other small groups stay on two passes: `flags_on`, `notools`, the effort groups other than `effort_low`, and `fable`. A third pass narrows a range by one fifth at most, by formula. The subscription's weekly usage stood at 86%, and one more pass of these groups was estimated to take 5 to 7 points of it.

### 13 November 2026: extra numbers and wordings, fixed before the reports are opened

Written on 13 November 2026 at about 11:51 in Melbourne (00:51 UTC). This entry was pushed before the final report and the interim files were opened.

Nothing in this entry changes whether a difference is declared, whether it is called "lower", or any number the registered program computes. It adds numbers to report beside those and fixes how some cases are worded, so that these choices are made before the results are known. No ask is sent because of this entry.

**Why.** Before opening the reports, two Claude agents were asked to look for what could go wrong. The first read only this repository and wrote down what a critic could show two weeks after publication. The second wrote the analysis again from sections 3 to 6 of this file, without seeing the code, and compared its program with the registered one on made-up data.

**What had been seen by then.** Everything listed in the entries above, and also these.

- Of the added pass of `api` and `author`: that each of the 156 asks was done, its status and its cost.
- Of Desktop round 3: for each ask whether it was done and whether a tool call was refused, and the saved system prompt, which differs from rounds 1 and 2 only in the identifier of the session that started the sessions.
- Of the graded rows of the registered run, through a script that loads identifiers and marks only: how many rows each cell has, the `warmup` and `scored` marks, whether a row is a resend, the version reported at the start of each ask and the form of each timestamp. The 39 versions of `main` have exactly one row in every cell of the three passes. No row carries the `warmup` mark, none lacks the `scored` mark and none is a resend. The only cells with two rows are the 78 of `effort_low` in pass 3, which section 4 asks twice. Every ask reports the version it was sent to. Every timestamp carries its time zone. The version list is in release order.
- LiveNerf's public page on 13 November: its accuracy for Opus 5.5 in five segments of ten days and for Fable 5.2 on four days.
- The line the run logs after pass 3, as listed above.

No answer has been read. No accuracy, thinking or output number of any group has been looked at, and the final report and the interim files have not been opened.

**A correction to two entries above.** The entries of 12 November (night) and 13 November say that no answer of the registered run "had been read or graded". The registered program grades every answer on its own when it writes the interim and the final report, so by then the program had graded them. What those entries mean is that no person and no Claude agent had read an answer, a score or a report, apart from the yes or no line they name. The README said until today that no question of the run had been sent. It now gives the present state.

**The rewrite from the text.** On 15 made-up datasets (4 with no difference between versions, 11 with one built in, among them missing records, resends, voids, zero thinking, an unfinished last pass and a version the server refuses), the rewrite and the registered program agreed on every number that does not come from random draws: which segment, its size, z, the figure for each pass, the shape and `step`, whether a difference is declared, whether it is called "lower", whether the third pass opens, and each version's accuracy and thinking. They agreed to at least six decimal places. The numbers that come from random draws (p, the ranges, the grey band) agreed within the error of the draws, because the two programs draw in a different order.

Three sentences of this file can be read two ways. The registered program's reading stands, and it is stated here:

- Section 3, `errors_and_voids.csv`: the program counts errors and voids in the cells that count (section 3, "Which item counts in a pass").
- Section 3, the flag for more than 5% in a pass: the program takes 5% of the items that count in that pass, so "4 or more of 78" holds for a finished pass.
- Sections 3 and 5, two ways of counting: the program declares an accuracy difference when both runs declare one and the two diffs have the same sign. It does not check that both runs name the same segment. See item 7 below.

**The check of section 10, made exact.** Section 10 asks that before any drop is reported, an agent that has not seen the code redoes the analysis and the two sets of numbers match. This is now done for every declared difference, a drop or otherwise. The program used is the rewrite as it stood before its author opened the registered code. It is run on the real data by an agent that has not seen the code, and it is published with the results. "Match" means: every number that does not come from random draws is the same after rounding to the digits reported. A p value matches when the two differ by at most four standard errors of a p estimated from 10,000 shuffles, which is `4 * sqrt(p * (1 - p) / 10000)`. A range matches when each end differs by at most 0.5 points for accuracy or 2 percentage points for thinking. The registered p is the one from `judge.py`. If the two programs fall on different sides of a line, the report gives both and says so. Where this file and the registered code differ, the code whose hashes are in `RUNNER_SHA256.txt` decides, and the report lists the difference.

**Numbers added to the report.** None of them has a verdict of its own. Ranges redraw the 78 items 10,000 times with seed 20261111 unless another number is given.

1. **Blocked tools.** In `main` every tool call is refused, and a refused call gives the model one more round. A real user's tools run. For each declared difference the report gives (a) the share of asks that tried a tool inside the segment and outside it, with the difference and its range, and (b) the same segment's difference over the asks that did not try a tool, with its range. In section 10, "moves together with the share of asks that tried a tool" now means: the range in (a) leaves out zero, and the difference in (b) is less than half the declared difference or has the other sign. When that holds, the sentence that states the difference also says that it may come from the blocked tools. Which asks tried a tool is itself an effect of the version, so (b) compares different asks on each side. It is a check and no more than that.
2. **Answers that could not be read.** LiveNerf's graders read only the last `<answer>` block, and a choice item is right only when the block holds the letter and nothing else beyond spaces and round brackets. An answer counts as read when there is such a block and it has the form the grader of that item accepts: one letter, an integer, or a rational number. This does not use the key. The report gives each version's share of scored asks that were not read, scans that share as section 8 scans its numbers, and for each declared accuracy difference gives the same segment's difference over the read answers alone. If more than half of a declared accuracy difference is gone when only read answers are counted, the summary says that the format of the answers changed, in place of saying that the answers got worse. The answers themselves stay unpublished because they would give away the questions.
3. **Zero thinking.** The thinking test averages `ln(thinking tokens + 1)`, so a few asks with zero thinking move the per cent far more than they move the total. For each declared thinking difference the report gives the share of asks with zero thinking inside and outside the segment, the ratio over the asks with thinking above zero, the ratio of the medians and the ratio of the totals. The per cent from section 6 is written as a change in the geometric mean.
4. **A size the choice of segment did not see.** For each of the two tests, the segment that the scan of passes 1 and 2 ranks first is measured on pass 3 alone, with its range. This is reported whether or not anything is declared. The interim report written after pass 2 is published in full.
5. **One item or one family.** For each declared difference: the difference with each item left out in turn (the smallest and the largest are reported, and the item is named when leaving it out halves the difference), and the difference within each family of items (MMLU-Pro, GPQA, AIME, competition maths).
6. **Where the segment starts and ends.** The items are redrawn 2,000 times and the scan is run again on each draw, without shuffles. The report gives, for the segment ranked first, the middle 95% of its first version and of its last version. When either covers more than one version, the summary gives that span in place of a single version.
7. **Two ways of counting that name different segments.** The report gives both segments with both sizes and says that they differ. If both runs declare a difference and the program's line says no because the signs differ, or yes while the segments differ, the summary says exactly that. It does not write "no difference was seen" for the first case, and it does not give one segment alone for the second.
8. **Before and after 2.1.303** (section 8). The difference gets a range, and the same cut is reported for thinking, as a ratio with a range. It stays secondary. If its range leaves out zero while the scan declares nothing, the report gives both and the reason they can differ: the scan pays for choosing among 779 segments, and a cut named beforehand does not. This cut was named by a post, which is why section 8 does not let it decide.
9. **`author` on 2.1.280 against LiveNerf on the same days.** Beside the comparison of section 9 (inside LiveNerf's daily range), the report gives this group's accuracy in each pass minus LiveNerf's published accuracy for the same UTC day, with the range of this group's figure. If they differ, the report says by how much and adds that comparisons between versions are made inside one account and do not depend on it.
10. **How many added comparisons there are.** The comparisons added after the run began that carry one of the three wordings are eight: time of day (accuracy, thinking), the Desktop group against `main` (accuracy, thinking), and b minus a and d minus e of the desktop-prompt group (accuracy, thinking each). If nothing differs, the chance that at least one of eight independent results reaches "points one way" is about 1 in 3, and "clear" about 8 in 100. They are not fully independent, so these are rough. Only a "clear" result goes into the summary. A result that "points one way" is given in its own section with this count beside it.
11. **A fourth limit beside every conclusion** (section 10 lists three). In `main` the remote flags are not fetched, and a real session fetches them. Group `flags_on` shows what fetching them changes on four versions, and it can see about 7 points.
12. **After a third pass has opened.** The "less than 5%" of section 4 holds for the whole procedure, counted before the run. This run opened a third pass. How often identical versions end in a declared difference once a third pass has opened is counted with simulation 5 and given beside the 5% in the results.
13. **"Not confirmed by the third pass"** (sections 4 and 10). For each test the report gives the figure on passes 1 and 2 and the figure on all three, whatever they show. The phrase is used when the test on two passes met all three conditions for a declared difference and the test on three passes does not. If two passes only had p < 0.05, the report says that in those words.
14. **A segment that is higher than both sides.** The three mean residuals (before, segment, after) are always given. When a declared segment is higher than the rest and the versions before and after it differ from each other by less than a third of the segment's difference, the summary adds that the versions before and after the segment are at about the same level.
15. **A boundary where nothing was sent differently.** For each declared difference the report says whether each end of the segment falls between two versions of one group of section 8 ("versions that send the same thing"). If it does, the report names the nearest version at which the request did change and gives the scan over groups beside it. If a drop is declared from a version that sends the same request as the version before it, and the checks of section 10 find no fault, the sentence is: "From X on it is lower. X sends the same request as the version before it. This experiment cannot tell whether the server treats X differently or the cut fell here by luck."
16. **`flags_on` against `main`.** Three wordings. If `main` shows a declared difference between versions that `flags_on` covers and `flags_on` shows it too, the report says so. If `flags_on` does not show it, the report says that the difference was seen with the flags not fetched and was not seen with them fetched, and that four versions can only see about 7 points. If no declared difference falls between versions that `flags_on` covers, the report says that this group cannot speak to it.
17. **Release notes.** A table of the entries in Claude Code's public changelog for the 39 versions that mention the system prompt, thinking or effort, the default model, tool descriptions, hooks or print mode is added to this repository before the reports are opened. Causes for a declared difference are looked for in that table first, and an entry found later is marked as found after the results were known.
18. **How thinking is counted.** The thinking count comes from the result line of each ask. The report says, for each version, whether the output tokens of the result line equal the sum over the messages of the ask, for asks that tried a tool and asks that did not. The ratio of thinking between `api` and `author` on 2.1.322, which section 9 already computes, shows whether the client's count agrees with the server's on that version.

Also published with the results: the commit of LiveNerf's repository whose graders were used, and the hashes of the 39 program files.

**Limits.**

- The thresholds in items 1, 2, 5 and 14 (a half, a third) were chosen here without a simulation.
- These numbers are computed after the reports are opened, by code written after this entry. The code is published with the results.
- The first agent's report was written from this repository and public pages only. Its statements about LiveNerf's graders were checked against LiveNerf's code. Its rough figure for item 12 (about one in four for accuracy) was not checked and is replaced by the count from simulation 5.

### 13 November 2026: a group without LiveNerf's two sentences, and a third pass for `flags_on` and for `author` on 2.1.280

Decided on 13 November 2026 at 11:46 in Melbourne (00:46 UTC). This entry was pushed before the first ask of these groups, probes included, and before the final report and the interim files were opened.

**Why.** Every ask of this experiment carries LiveNerf's two sentences. They tell the model that the task is graded automatically and exactly, ask it to work carefully and to follow the output format. A real user's session has no such sentences. Soren Hou asked what they say and whether a small test without them was worth adding. If one version's own system prompt asks for shorter or quicker work and another's does not, "work carefully" may cover that up, and the versions would look more alike here than they are in use. No group so far can show this.

He also said that the weekly usage of the subscription should no longer limit what is added, because he can reset it, and asked that each small group be judged on whether a third pass is worth it. Two were judged worth it. `flags_on` is the group closest to a real session, and it is what answers "real sessions fetch the remote flags and yours did not". `author` on 2.1.280 is the one figure that is compared with LiveNerf's own, and with it both versions of `author` have three passes. The others stay on two passes: `notools` explains where a gap comes from and is only needed if there is one, the effort groups other than `effort_low` are yardsticks and `effort_low` has four passes, and `fable` is compared across a gap that LiveNerf's own page puts above 20 points.

This replaces two sentences in the limits of the entry "a third pass for group `api`" above: "`author` on 2.1.280 gets no third pass" and the one that keeps `flags_on` on two passes.

**What had been seen by then.** Everything listed in the entry above, "extra numbers and wordings". No number of any group had been looked at. The yes or no line of the two tests on three passes had been seen (12 November). The first agent named in the entry above advised against sending any more scored asks for that reason: a reader may take it as adding data after seeing the outcome. The asks added here enter neither of the two tests, and they are marked as added wherever they are reported.

**What is added.** 858 asks.

1. **Group `nosent`: 468 asks.** The 78 questions on 2.1.280 and on 2.1.322, three passes. Each ask is the `main` ask of that version with one thing taken out: the `--append-system-prompt` argument and the two sentences that follow it. Everything else is `main`'s: the config folder `main` used for that version, the tools described and every call refused, model, effort high, remote flags not fetched, environment, working folder, timeout. Each question ends with its own instruction for the answer format, so the graders work unchanged. `modes.py` is under the run's fingerprint and is not edited. A script outside the fingerprinted modules builds each ask with `ccversions.run` and removes the pair. Each pass is cut into blocks of three questions, a block asks both versions, the order inside a block is shuffled with seed 20261111, and two asks run at a time. Before the first scored ask, a command prints `main`'s command beside this group's for both versions, and one unscored probe per version checks what was sent. The outcome of these checks is added to this entry before the first scored ask.
2. **A third pass for `flags_on` (four versions, 312 asks) and for `author` on 2.1.280 (78 asks).** Both groups are specified as in section 2. They go out in one plan made by the registered sender with the registered seed: 26 blocks of three questions, the asks of a block in shuffled order, two at a time. A dry run showed that each of the 390 asks is the same as the pass 2 ask of the same group, version and question: command, question, config folder, working folder, timeout and the names of the environment variables.

**How it is compared.**

- `nosent` against `main` on the same version, using the three passes `main` already has: item by item as section 9 defines it, accuracy as a difference, thinking and output as ratios, each with a range. Given for 2.1.280, for 2.1.322 and for the two together.
- Whether the two sentences change the gap between the two versions: (`nosent` on 2.1.322 minus `nosent` on 2.1.280) beside (`main` on 2.1.322 minus `main` on 2.1.280), and the difference between these two with a range.
- For both sides, the share of answers that could not be read (item 2 of the entry above) and the accuracy over the read answers alone. The two sentences also ask the model to follow the output format, so without them more answers may miss the form the graders accept.
- Difference and range only. None of this carries a verdict or one of the three wordings.
- `flags_on` and `author` on 2.1.280: as in section 9, on three passes. The figure on two passes is given beside it, and the figure on three is marked as added.

**What size this can see.** One version answering the 78 items once varies by about 4.9 points (section 7). With three passes on each side, two ways of asking one version differ by about 4 points by chance alone, and a true difference of about 11 points would be found 8 times in 10 at p < 0.05. With the two versions together it is about 8 points. These figures are worked out from the 4.9 and were not simulated. A third pass narrows a range of the small groups by about one tenth.

**Limits.**

- `nosent` is sent on 13 November, and the passes of `main` it is compared with were sent on 11 and 12 November. No `main` asks are sent beside it. Soren Hou decided this: the day and the hour are a minor comparison in this experiment, and one more pass of `main` on two versions would leave those two with more passes than the other 37. Two comparisons that already exist show what a day's gap does to the same way of asking: arm e of the desktop-prompt group against `main` on 2.1.321, and pass 3 of `author` on 2.1.322 (13 November) against its passes 1 and 2. They are reported beside the `nosent` result.
- `nosent` covers two versions. It says nothing about the other 37.
- The remote flags that `flags_on` fetches on 13 November may differ from those of 11 and 12 November.
- In pass 3 these groups are sent on their own. In passes 1 and 2 `flags_on` and `author` sat among the asks of the 39 versions.
- The stop line for these asks is a weekly usage reading of 0.99. If it is reached, the asks go on after Soren Hou resets the usage of the account, and the report gives the hours of the gap. Section 4's rule that nothing waits for a reset was written for the registered run.
- These asks were added after the yes or no line had been seen, as stated above.

### 13 November 2026, afternoon: `nosent` is sent another way, and the checks before its first scored ask

Written on 13 November 2026 at about 13:40 in Melbourne (02:40 UTC). This entry was pushed before the first scored ask of group `nosent` and before the final report and the interim files were opened.

**What had been seen by then.** Everything listed in the entries above, and also these. Of the third pass of `flags_on` and of `author` on 2.1.280: that all 390 asks came back done, and the fields that say how each was sent. Of the eight probes below: the command, the system prompt each one sent or stored, and the input token count of its first request. No answer has been read, the probes' answers included. No accuracy, thinking or output number of any group has been looked at, and the final report and the interim files have not been opened.

**The sentence this changes.** In the entry above: "Each ask is the `main` ask of that version with one thing taken out: the `--append-system-prompt` argument and the two sentences that follow it." The script was written that way first, and the checks that entry asks for were run on it.

- The command printed beside `main`'s differed in that pair alone, on both versions. The commands recorded for the 468 `main` asks on these two versions were this group's commands once the pair was taken out.
- Four unscored probes: on each version one sent this group's way and one sent `main`'s way beside it, to compare. The entry above named one per version. The second one was added so that the two could be compared word for word.
- On 2.1.322 the request can be read as it was sent. Without the pair, LiveNerf's two sentences were gone, and the first line of the system prompt had changed as well. Sent `main`'s way it reads `You are Claude Code, Anthropic's official CLI for Claude, running within the Claude Agent SDK.` Without the pair it read `You are a Claude agent, built on Anthropic's Claude Agent SDK.` Nothing else differed.
- On 2.1.280 only a copy of the system prompt that the program stores can be read, and that copy has no first line. The two copies differed in LiveNerf's two sentences alone.
- On both versions the first request had 62 fewer input tokens than `main`'s.

So leaving the pair out changes two things, and this group is meant to change one.

**How it is sent now.** `--append-system-prompt` stays in the command, and the text after it is one space character (U+0020). Everything else is as the entry above says. The Claude session that looks after the run decided this before any scored ask of the group. Four new probes of the same design were sent:

- On 2.1.322 the first line is the same in both probes and LiveNerf's two sentences are gone. The system prompt as sent is `main`'s with the two sentences removed, except that it ends with an empty line and one space.
- On 2.1.280 the stored copies show the same.
- On both versions the first request has 51 fewer input tokens than `main`'s. On 2.1.280 the first line can't be read, so that it stayed the same rests on this number: it is the number of 2.1.322, where the first line was read, and it was 62 on both versions when the first line had changed.

The eight probes are unscored. The group uses `main`'s config folders for the two versions. A listing of both folders before the first probe and after the last shows no file added or removed. The files whose content changed are files that every ask rewrites.

Before the rest goes out, the first block of six asks is sent, and the input token count of each first request is compared with `main`'s for the same version and question. If the gap is not the one the probes showed, the group stops there and this log says what was found. An ask that never reached the model is sent once more at the end of its pass, as section 3 says. The sha256 of the script that sends the group is `dfad1b2f200f659a2f85171ba4edfb965e1a5dcc5e3e9e644af44208acf35282`. It is published with the results.

**A correction to "What size this can see" in the entry above.** The figures there, about 11 points on one version and about 8 with the two together, are for `nosent` against `main`. The second comparison, whether the two sentences change the gap between the two versions, takes four sets of answers, and its figure is about 16 points. It is worked out the same way and was not simulated. "A third pass narrows a range of the small groups by about one tenth" is about the range of a group's difference from `main`, which already has three passes.

**Item 12 of "extra numbers", counted.** Simulation 5's made-up datasets were made again with the same seeds, and each dataset's path was kept (`simulations/after_third_pass/`). The recount gives the same 112 shares as the registered output. With 39 identical versions and the third pass sent in full, 742 of 4,000 datasets opened a third pass.

| Third pass opened by | Datasets | Accuracy difference declared | Thinking difference declared |
|---|---|---|---|
| either test | 742 | 94 (12.7%, 95% range 10.4% to 15.3%) | 70 (9.4%, 7.4% to 11.8%) |
| the accuracy test alone | 345 | 69 (20.0%) | 4 (1.2%) |
| the thinking test alone | 357 | 10 (2.8%) | 58 (16.2%) |
| both | 40 | 15 | 8 |

Over all 4,000 datasets the shares are 2.7% and 1.9%, as in section 4. Which row fits this run is known once the interim report is opened, and the results give that row beside the "less than 5%". These counts replace the rough "about one in four" named in the limits of the entry "extra numbers and wordings". Their limits are simulation 5's: 1,000 shuffles for each dataset, no errors or voids, no asks with zero thinking. The output also covers the three other scenarios of section 4.

**Code for the extra numbers.** The program for items 1 to 8, 13 to 15 and 18 of that entry is in `extra_numbers/`, committed with this entry. It has run on made-up data only. Its README lists 20 places where the entry could be read two ways and the reading that was fixed, before any result.

### 13 November 2026, afternoon: the code for the three small groups, the readings it follows, and one sentence of section 2

Written on 13 November 2026 at about 14:45 in Melbourne (03:45 UTC). This entry was pushed before the final report and the interim files were opened. No accuracy, thinking, output or cost number of any group had been looked at.

**The scored asks of `nosent`.** All 468 were sent on 13 November 2026 between 02:42 and 03:40 UTC, the first block of six first. The check named in the entry above was run on those six and then on all 468: the first request of every ask had 51 fewer input tokens than `main`'s for the same version and question. Every ask came back done, so no ask was sent again. The stop line was not reached. A listing of the two config folders after the last ask shows no file added or removed since before the first probe, and the files whose content changed are the same ones as after the probes. Of these asks, what has been seen is whether each came back done, the fields that say how it was sent, and that input token count. No answer has been read.

**The code.** [`small_group_comparisons/`](small_group_comparisons/) computes what the entry "a group without LiveNerf's two sentences, and a third pass for `flags_on` and for `author` on 2.1.280" asks for under "How it is compared", and items 9 and 16 of the entry "extra numbers and wordings". A Claude agent (Opus) wrote it without opening any data of the run. Claude (Fable 5.2) read the program against the two entries and ran its 40 tests on made-up data. In this repository two of the tests are skipped, because they need files that are not published here. Before the program computes anything, it rebuilds the registered report's numbers for `flags_on` and `author` on passes 1 and 2 from the graded rows, and it stops if one of them differs.

**Readings fixed here.** In these places the two entries can be read two ways. The program follows the readings below. They were fixed before any result.

1. "The figure on two passes" for `flags_on` and `author` is the registered report's kind of figure: their passes 1 and 2 against all three passes of `main`.
2. `author` against `main` is given on 2.1.280 alone, as the entry names it. The registered report pools 2.1.280 and 2.1.322.
3. `nosent` "for the two together" pools each side over both versions, item by item, as the registered program pools the versions of a group.
4. "Inside LiveNerf's daily range" (section 9) means between the lowest and the highest daily value of the period, both ends included. It is given for each pass and for the passes pooled.
5. Item 9, "the same UTC day": when the asks of one pass were sent on two UTC days, LiveNerf's figure is the mean of those days' figures, each weighted by this group's scored asks on that day. Each day is also given on its own.
6. Item 9, "if they differ": LiveNerf's figure lies outside the range of this group's figure.
7. Item 16, "between versions that `flags_on` covers": at least one of the four versions of `flags_on` is inside the declared segment and at least one is outside.
8. Item 16, "`flags_on` shows it too": the difference of `flags_on` between its versions inside the segment and its versions outside, item by item over its three passes, has the declared sign and a range that leaves out zero. For accuracy this must hold in both ways of counting. The figure on two passes and that of `main` on the same four versions are given beside it.

**What the program adds.** The limits of the `nosent` entry ask for two comparisons beside its result. One of them, pass 3 of `author` on 2.1.322 against its passes 1 and 2, is computed here item by item. The other is copied from the report of the desktop-prompt comparison. For item 9 and for the comparison with LiveNerf's daily range, accuracy is also given with errors and voids counted as wrong, as section 3 asks. For each added plan the program gives the first ask, the last ask and the longest wait between two asks.

**One sentence of section 2.** Section 2 says: "So the model receives what the version would send for a user with no setup of their own." The check behind that sentence compared asks sent with `claude -p`, the way every ask of this experiment is sent: one command, one answer, and the program exits. Whether a session in the terminal's chat interface sends the same system prompt and the same tool list was not compared. The sentence holds for `claude -p`.

**No fourth pass.** On 13 November a fourth pass of the 39 versions was considered, to be sent if a drop is declared, and it is not added. The registered procedure already takes a second look: a third pass opens only when two passes point to a drop, and all three are then tested together. Its error rate was measured as one piece before the run (section 4). Any ask sent after the reports are opened will be reported as decided after the results were seen.

**Analyses thought of after the reports are opened.** The results will be handed to a new Claude conversation, which is asked to start from the question of section 1 and from the data. It may run analyses that this file does not list. Each one will be marked as thought of after the results were known. Every analysis that is tried will be listed, whether or not it shows anything. None of them changes whether a difference is declared, or any number the registered program computes. Three directions were noted before the reports were opened and may be looked at, with no method fixed: what one ask costs at API prices for each version (the record of each ask holds the figure Claude Code reports and its token counts), whether, on the same item, the answers with less thinking are wrong more often, and for each version the share of items that get the same answer in every pass.

### 13 November 2026, evening: two groups sent after the reports were opened

Written on 13 November 2026 at about 19:35 in Melbourne (08:35 UTC) and pushed before any ask of these two groups was sent, probes included. The reports of the registered run were opened on the afternoon of 13 November. Everything in this entry was decided after their results were seen, and every result of these groups will carry that mark, as the entry before this one says. No number of the registered run and none of its decisions changes.

**What had been seen.** The registered program declared a difference in thinking: a run of versions that starts at 2.1.317 and ends at 2.1.322, the last version, thinks less. It declared no difference in accuracy. The full results are not published yet. They will be published whatever these groups show. After the reports were opened, a Claude conversation (Fable 5.2) ran analyses that the registration does not list. Four things it saw led to this entry.

1. Effort xhigh was asked on 2.1.322 alone (group `effort_xhigh`). The registered run cannot say whether the versions differ at xhigh.
2. Take one question and all of its scored asks in `main`. On 24 of the 78 questions the asks with more thinking were right more often. On 19 the asks with less thinking were right more often. The rule is under "The 24 questions". In the total over the 78 questions the two kinds pull against each other. On the first kind, 2.1.317 to 2.1.322 thought about a fifth less than the five versions before them. That was noticed after the fact, in data that had already been looked at.
3. On those 24 questions the accuracy of 2.1.317 to 2.1.322 was a little lower than that of the five versions before them, and the range ran from clearly lower to clearly higher. The data in hand cannot settle it.
4. Versions differ from each other a little more than chance alone gives, with no pattern by release. A shuffle that deals single asks to versions at random takes that spread for noise between asks. When it compares two sets of five versions it declares a difference too often: 14% to 34% of the time in a simulation of the accuracy comparison below, with a spread of 1.5 to 3 points between versions. So the tests below take the version as the unit.

**Group `xhigh_recheck`: 4,290 asks.** The 78 questions at effort xhigh on eleven versions, five passes. The versions are 2.1.311, 2.1.312, 2.1.314, 2.1.315 and 2.1.316 (the five before the declared run), 2.1.317, 2.1.318, 2.1.319, 2.1.321 and 2.1.322 (the declared run), and 2.1.323, which was released on 12 November 2026 UTC and is treated as written under "2.1.323". Each ask is the `main` ask of that version and question with `--effort xhigh` in place of `--effort high`: the version's own system prompt and tool descriptions, every tool call refused before it runs, remote flags not fetched, the config folder `main` used for that version, the same environment, working folder and timeout. A dry run of pass 1 showed that each of the 780 asks on the ten versions differs from `main`'s pass 3 ask of the same version and question in that one argument of the command. Config folder, working folder, timeout, question text and binary are the same.

**Group `high_recheck`: 3,168 asks, and 3,168 more if the rule below says so.** The 24 questions of the first kind at effort high on the same eleven versions, in two stages of twelve passes each. Each ask is the `main` ask of that version and question. A dry run of pass 1 showed that each of the 240 asks on the ten versions is the same as `main`'s pass 3 ask of the same version and question in command, config folder, working folder, timeout, question text and binary.

**The 24 questions.** For each of the 78 questions, over its scored asks in `main` (three passes of 39 versions, up to 117 asks), r is the correlation between ln(thinking tokens + 1) and right (1) or wrong (0), and t = r × sqrt(n − 2) / sqrt(1 − r²). A question is of the first kind when t is above 2.6 and of the second kind when t is below −2.6. Eleven questions were always right or always wrong and have no t. The first kind has these 24:

`comps-cmimc_2025-34`, `gpqa-recWxGU8Q4YReJ1tb`, `gpqa-reckl6PkaEMWM50yZ`, `gpqa-rectlyG9pCAAuWhoB`, `mmlupro-10150`, `mmlupro-11746`, `mmlupro-11896`, `mmlupro-1261`, `mmlupro-1508`, `mmlupro-1580`, `mmlupro-3000`, `mmlupro-3268`, `mmlupro-4659`, `mmlupro-5039`, `mmlupro-5040`, `mmlupro-574`, `mmlupro-6329`, `mmlupro-6415`, `mmlupro-6465`, `mmlupro-6728`, `mmlupro-8743`, `mmlupro-9761`, `mmlupro-9836`, `mmlupro-9873`.

Twenty are MMLU-Pro questions, three are GPQA and one is competition maths. The list was fixed from the registered run's data before any ask of this entry and is in `recheck/items_think_more_24.json`. The asks of the ten versions helped pick the questions, so the registered run's own figures on these questions flatter the difference. New asks do not have that fault. If the ten versions were alike, new asks would show no difference on any list of questions fixed beforehand.

**How they are sent.** By the registered sender, with the plans it makes. Each pass shuffles its questions and cuts them into blocks of three. Every block holds each of the eleven versions on each of its three questions, and the order inside a block is shuffled. The seeds are `recheck-xhigh-20261113` and `recheck-high-20261113`, plus the pass and block number. An ask that never reached the model is asked once more at the end of its pass, an outage is waited out as in the registered run, and the timeout is 900 seconds. Two things differ from the registered run. Five asks run at a time, where the registered run had two. The sender still never runs two asks of one version at once, so no config folder has two asks at a time. And the usage line is 99% of the weekly quota. The order is: the five passes of `xhigh_recheck`, then passes 1 to 12 of `high_recheck`, then the decision about stage 2, then passes 13 to 24 if they are sent. `recheck/driver.py` strings the passes together. It calls the steps of the registered driver and adds no way of asking.

**Fingerprint.** These asks carry the fingerprint `73a9622e733e2ed8`. The registered run has `5faa105aaa83a3e9`. The eleven modules under the fingerprint, the question file, the probe file and the settings that shape an ask are byte for byte those of the registered run. Two parts differ: the version list (`recheck/versions_20261113.json`, the registered list with 2.1.323 added) and the table of config folders (one folder added for 2.1.323, and a set of folders for the probes below).

**2.1.323.** It was the newest release when this was written, and the registered list ends at 2.1.322. Its binary was downloaded from the official address on 13 November 2026 and checked the way the 39 were. The signature of its manifest is good and was made by the official key. The binary's sha256, `5432918d904a9b6afef7bb79d20df24d76052eabc1f41bceb84091d21f8889a7`, and its size, 344,369,984 bytes, are those of the manifest. Its config folder was made like the others and holds the same two device IDs. It is asked in the same blocks as the ten. It takes no part in any test or in the decision about stage 2. Nobody here knows yet what it changed, and if it had changed back, counting it with the later five would blur the comparison. It gets a row of its own beside the ten, and the system prompt it sends is compared with that of 2.1.322 word for word. If one of the checks below fails for it, it is left out and the ten go ahead.

**Probes before the first scored ask.** 26 unscored asks, sent into config folders made for them, with the session file kept so that the request can be read. Each is one sentence: `Reply with <answer>OK</answer>.`, or in one case a request to run a shell command. For each of the eleven versions: the `main` ask at high and at xhigh. For 2.1.323 also: two asks in a fresh folder with tools switched off, the ask with tools left on, and the ask that tells the model to run a shell command. The checks are these. Every probe comes back done, answered by `claude-opus-5-5` alone, on the subscription. The request of each version holds the effort that was asked for. For 2.1.323: the first and the second ask in a fresh folder have the same number of input tokens, the ask with every tool call refused has the same number of input tokens in its first request as the ask with tools on, the shell command is refused before it runs, and the list of beta names in its request is compared with that of 2.1.322 to see that the remote flags were not fetched. If one of the ten does not send xhigh as asked, `xhigh_recheck` is not sent as written here and this entry is changed first. The outcome of the checks is added to this entry before the first scored ask.

**Outcome of the probes.** Added on 13 November 2026 at about 19:40 in Melbourne (08:40 UTC), before the first scored ask. The 26 probes were sent between 08:35 and 08:37 UTC. All came back done, answered by `claude-opus-5-5` alone, on the subscription, with no billing problem. Every version kept a session file that holds the request, and every request holds the effort that was asked for: high in the eleven asks at high, xhigh in the eleven at xhigh. For 2.1.323: the first and the second ask in a fresh folder both had 2,259 input tokens. The ask with every tool call refused and the ask with tools on both had 16,386 input tokens in the first request. The shell command was refused by the hook before it ran, and the word in the file it was told to print did not come back. Its request names the same 16 betas as that of 2.1.322, and none of the three names that fetching the remote flags added in the trial. So 2.1.323 is asked with the ten. What 2.1.323 sends differs from what 2.1.322 sends in two places. One is the path of the config folder inside the system prompt, which differs between any two versions. The other is the description of four tools (Agent, Skill, ToolSearch, Workflow), where "`<system-reminder>` messages" became "messages from the system": 12 input tokens fewer in all. The sentences of the system prompt that changed at 2.1.317 are the same in 2.1.323 as in 2.1.322. Between 2.1.316 and 2.1.317 these probes show what the trial showed: two sentences of the system prompt changed and no tool description did.

**The three tests.** Each compares the later five versions with the earlier five and takes the version as the unit. For each of the ten versions, take each question's mean over that version's scored asks, then the mean of those over the questions. That gives ten values. T is the mean of the later five minus the mean of the earlier five. There are 252 ways to split ten values into five and five. p is the share of the 252 whose difference is at least as far from zero as T, the true split included. A difference is declared when p is 0.05 or less. The smallest p this test can give is 2 in 252.

1. Thinking at xhigh. The value of an ask is ln(thinking tokens + 1). The asks are those of `xhigh_recheck`: all 78 questions, five passes.
2. Thinking at high on the 24 questions. The same value on stage 1 of `high_recheck` (passes 1 to 12), whether or not stage 2 is sent. Stage 2 is sent by a rule on accuracy, and on these questions accuracy goes with thinking, so a thinking test on both stages would lean on that decision.
3. Accuracy at high on the 24 questions. The value of an ask is 1 when it is right and 0 when it is wrong. The asks are those of both stages of `high_recheck`. This test is run only if stage 2 is sent.

For thinking, exp(T) − 1 is reported as the change in the geometric mean. For accuracy, T × 100 is reported in points. Each comes with the range from redrawing the questions 10,000 times. Which asks are scored follows section 3, as for `main`. The three tests are run at 0.05 each with no correction, and the exact p of each is given.

**The rule for stage 2.** When passes 1 to 12 of `high_recheck` and their resends are complete, `recheck/gate.py` grades them and computes D1: the T of test 3 on stage 1 alone, in points. Stage 2 is sent when D1 is −1.0 or lower. If D1 is above −1.0, stage 2 is not sent, test 3 is not run, and the report says that no lower accuracy was seen on these questions and gives D1 with its range. Test 3 is run once, at the end, on all asks. Leaving stage 2 out can only take away chances to declare, so the rule cannot lift the error rate above that of a test that always sends both stages. In a simulation made before this entry, with no true difference, stage 2 was left out 71% to 75% of the time and a difference was declared 2% of the time. With a true drop of 3.5 points, stage 2 was wrongly left out 4% to 8% of the time. The program prints D1, the ten version figures and the decision. As a trial of the program, `main`'s own asks on these questions were run through it and gave D1 = −3.3 on three asks per question and version. That figure is no result, because those asks helped pick the questions. No other decision about sending depends on a result. The numbers of `xhigh_recheck` are opened when its five passes are complete, and those of stage 1 when the decision has been made.

**What each test can see.** Computed before the first ask, by simulation from the asks of the registered run. Test 1: a true cut of 10% at xhigh is declared about nine times in ten (97% when the spread within a question is that of the 156 xhigh asks in hand, 86% when it is as wide as at high), a cut of 8% about 88% of the time, a cut of 5% about half the time. Test 2: a cut of the size seen in `main` on these questions is declared 92% to 99% of the time, and a cut half that size about 58% of the time. Test 3, on 24 asks per question and version: a true drop of 3.5 points is declared 57% to 83% of the time, a drop of 4.5 points 79% to 96%, a drop of 6 points 96% to 100%. The lower figure of each pair holds when versions differ from each other by 1.5 points beyond chance, the higher when they do not differ. Five versions a side set these limits, and more asks would lift them little. On these 24 questions accuracy on 2.1.322 was 17%, 27%, 40%, 54% and 87% at effort low, medium, high, xhigh and max. By that yardstick a cut of a fifth to a quarter in thinking would cost 3.5 to 4.5 points.

**Wordings.**

- Test 1 declared with T below zero: "At effort xhigh, 2.1.317 to 2.1.322 think less than 2.1.311 to 2.1.316", with the per cent and its range. Not declared: "At effort xhigh no difference in thinking was seen between 2.1.317 to 2.1.322 and 2.1.311 to 2.1.316", with the estimate, its range, and the sentence that a cut of 10% would have been seen about nine times in ten and a cut of 5% about half the time.
- Test 2 declared with T below zero: "On the questions where more thinking goes with more right answers, 2.1.317 to 2.1.322 think less than 2.1.311 to 2.1.316", with the per cent and its range, and the sentence that this was first seen after the fact in the registered run and was then tested on new asks by a rule fixed beforehand. Not declared: "The cut in thinking seen after the fact on these questions was not confirmed on new asks", with the estimate and its range.
- Test 3 declared with T below zero: "On these questions 2.1.317 to 2.1.322 are right less often than 2.1.311 to 2.1.316", with the points and their range. Not declared: "No lower accuracy was declared on these questions", with the estimate, its range, and the sentence that a drop of 3.5 points would have been seen six to eight times in ten.
- A test declared with T above zero is reported in the same words with the direction turned around.
- Every sentence about these groups says that their asks were decided after the registered results were seen.

**Also reported, whatever it shows, with no declaration.** For both groups, a row for each of the eleven versions: the geometric mean of thinking, the share of asks with zero thinking, thinking over the asks with thinking above zero, accuracy, the share of asks that tried a tool, and the counts of errors and voids. Beside each test, the p of a shuffle that deals the asks of each question and pass to the ten versions at random 10,000 times, with the warning of point 4 above. For `xhigh_recheck`: the accuracy of the later five against the earlier five on all 78 questions, and thinking and accuracy on the 24 questions, on the 19 of the second kind and on the other 35. For `high_recheck`: thinking on both stages when stage 2 is sent, and each question's own difference. Beside the new figures, the `main` figures of the same versions on the same questions.

**If a group is cut short.** If the usage line or an outage ends a group early, the asks sent so far count. In a pass that was cut short, a question counts only where all ten versions have a record of it, as section 3 says for `main` ("Which item counts in a pass"). If stage 1 of `high_recheck` is cut short, the rule makes no decision about stage 2, test 2 is run on what is there, and the report says so.

**What was left out.** The 19 questions of the second kind are not asked again at high. They had been planned as a contrast for test 3 and would have cost 4,560 asks. If test 3 declares a drop, the only contrast for it is the registered run's figure on those 19, which has a wide range. LiveNerf's own way of asking is not added here. A search for the cause (one version, with only the sentences of its system prompt that changed at 2.1.317 swapped) is not part of this entry. It will get an entry of its own before its first ask.

**Limits.** These asks were decided after the results were seen: which versions, which questions, which effort. Test 2 turns something noticed after the fact into a test on new asks, and that is all it does. Five versions a side can only see large differences. The 24 questions come from the same 78 and most are of one family. As in `main`, every tool call is refused, the remote flags are not fetched, and each ask is a single `claude -p` call. All asks come from one account in one night. Five asks at a time is more than `main` had.

**Code.** [`recheck/`](recheck/) holds the two group files, the two run settings, the version list, the list of the 24 questions, `driver.py`, `gate.py` and its tests on made-up rows. The program for the three tests and the reported numbers is added to that folder before any thinking count or answer of these groups is looked at, and the time of its commit shows that.

**The program for the tests.** Added on 13 November 2026 at 19:45 in Melbourne (08:45 UTC), while pass 1 of `xhigh_recheck` was being sent. `recheck/analysis.py` computes the three tests and the reported numbers. Of the scored asks, what had been seen by then: how many had come back and that each was done, the usage reading, and how long the blocks took. No thinking count, answer or score had been looked at. The program has run on made-up rows (`recheck/test_analysis.py`) and, as a trial, on the registered run's own asks of the ten versions, where it gives the figures already known from that run. In these places the entry can be read two ways, and the program follows the readings below.

1. A question for which one of the ten versions has no scored ask is left out for all ten, and the report names it.
2. The rule for a pass that was cut short is applied to every pass: a question counts in a pass only where all ten versions have a record of it. In a complete pass that leaves out nothing.
3. The range of T: T is computed again as the mean over the questions of each question's difference (the later five's mean minus the earlier five's mean), the questions are redrawn with replacement 10,000 times with seed 20261111, and the range is the middle 95%.
4. The shuffle of asks given beside each test deals the ten values of each question and pass, missing ones included, to the ten versions at random 10,000 times with seed 20261111. Its p is (the number of shuffles at least as far from zero as T, plus 1) divided by 10,001.
5. "Thinking over the asks with thinking above zero" is, for each version, the mean of ln(thinking tokens + 1) over those asks within each question, then over the questions that have such an ask.
6. The row of 2.1.323 covers the questions the ten versions have. Beside its figures the report gives the means of the two sets of five and its rank among the eleven. No sentence is fixed for it.
7. The 19 questions of the second kind are listed in `recheck/items_think_less_19.json`. "The other 35" are the questions in neither list.
8. Every comparison that is not one of the three tests is given with its T, range and p and carries no declaration.
