# The two groups sent after the reports were opened

Everything here belongs to the change log entry "13 November 2026, evening: two groups sent after the reports were opened" in [PREREGISTRATION.md](../PREREGISTRATION.md). The asks of these groups were decided after the results of the registered run were seen.

| File | What it is |
|---|---|
| `arms_xhigh.json`, `arms_high.json` | the two groups, in the format of `inputs/formal_arms.json` |
| `run_x.json`, `run_h.json` | seed, block size, usage line and asks at once for each group |
| `versions_20261113.json` | the registered version list with 2.1.323 added |
| `items_think_more_24.json` | the 24 questions that `high_recheck` asks, with the rule that picked them |
| `items_think_less_19.json` | the 19 questions of the second kind, reported as a set by `xhigh_recheck` |
| `probes_RP1.json` | the 26 unscored probes sent before the first scored ask |
| `driver.py` | sends passes of one group through the steps of the registered driver |
| `gate.py`, `test_gate.py` | the rule that says whether stage 2 of `high_recheck` is sent, and its tests on made-up rows |
| `send_all.sh` | the order of the night: `xhigh_recheck`, stage 1 of `high_recheck`, the rule, stage 2 if it is sent (copied from the script that ran, where its name and comments are in Chinese and its paths are local) |
| `analysis.py`, `test_analysis.py` | the three tests and the reported numbers, and tests on made-up rows |
| `rescore.py`, `test_rescore.py`, `rescore_keys_20261113.json` | accuracy scored two more ways (on the sound questions only, and with corrected keys), the lists it follows, and tests on made-up rows. No declared test |

`driver.py`, `gate.py`, `analysis.py` and `rescore.py` import the registered sender from `../ccversions/`. They need the local settings file and the records of the asks, which are not published, so here only the tests run:

```
cd recheck && python -B -m unittest test_gate test_analysis test_rescore
```

The tests need Python 3.10 or later with numpy.
