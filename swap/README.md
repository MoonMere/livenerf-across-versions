# The group that swaps the two sentences

Everything here belongs to the change log entry "14 November 2026: the two sentences that changed at 2.1.317 are swapped between 2.1.316 and 2.1.317" in [PREREGISTRATION.md](../PREREGISTRATION.md). The asks of this group were decided after the results of the registered run were seen.

| File | What it is |
|---|---|
| `swap.py`, `test_swap.py` | makes the texts for `--system-prompt`, makes the config folders, sends the probes and the passes, and its tests with a stand-in for Claude Code |
| `texts_sha256.json` | the lengths and hashes of the three pieces of text the system prompts are built from, and where they were taken from. The texts are parts of Claude Code's own system prompt and are not published |
| `settings_group.toml` | the part of the settings file that shapes the group: questions, passes, stage 1, ways, sets, way of joining, seed, asks at once, usage line. The paths of this computer are left out |
| `analysis.py`, `test_analysis.py` | the two tests, the decision after stage 1 and the reported numbers, and tests on made-up rows |

The questions are those of [`../recheck/items_think_more_24.json`](../recheck/items_think_more_24.json).

`swap.py` and `analysis.py` import the registered sender from `../ccversions/`. They need the local settings file and the records of the asks, which are not published, so here only the tests of `analysis.py` run, and seven of its 52 go through the local settings module and fail here. The tests of `swap.py` also need the three texts and the local settings:

```
cd swap && python -B -m unittest test_analysis
```

The tests need Python 3.10 or later with numpy.
