# Release notes of the 39 versions, listed before the reports were opened

This folder is item 17 of the change log entry "13 November 2026: extra numbers and wordings" in [PREREGISTRATION.md](../PREREGISTRATION.md). It lists the entries of Claude Code's public changelog, for the 39 versions of this experiment, that mention one of six topics. It was made and pushed on 13 November 2026, before the final report and the interim files were opened. If the results show a difference between versions, causes are looked for in this list first. An entry that is brought up later and is missing here is marked as found after the results were known.

The list holds no result and no opinion about any version.

## The source

- File: `CHANGELOG.md` of [anthropics/claude-code](https://github.com/anthropics/claude-code) at commit `89eb88e3357be13ae7fcf8966144ad32f44def33`, which was the head of `main` on 13 November 2026 at 11:58 in Melbourne (00:58 UTC).
- Size 1,235,150 bytes, sha256 `6ed58ecb355fbcab5b2a9fda34df659a422920b915938d1900348a8230052652`.
- No heading in that file carries a date, so the list has no release dates.

The changelog is Anthropic's text and is not copied here. [entries.tsv](entries.tsv) names each entry by its line number in that file and by the first 16 hex digits of the sha256 of the line. [show_entries.py](show_entries.py) reads a copy of the file, checks every hash and prints the rows with their text:

```
curl -sLO https://raw.githubusercontent.com/anthropics/claude-code/89eb88e3357be13ae7fcf8966144ad32f44def33/CHANGELOG.md
python3 show_entries.py CHANGELOG.md
python3 show_entries.py CHANGELOG.md --version 2.1.303 --topic 2
```

## The six topics

1. The system prompt, the built-in text the program sends to the model.
2. Thinking, extended thinking, reasoning, or the effort level.
3. The default model, or a model replaced by another.
4. Tool descriptions, the tool list, and the loading of skills, plugins and MCP servers.
5. Hooks.
6. Print mode (`-p`, non-interactive, headless), `--output-format` and `stream-json` output.

`unsure` marks an entry where the first reader could not tell whether it belongs to one of the six.

## What is in the list

The 39 versions have 2,980 entries in the changelog. 700 are listed.

| Topic | Rows |
|---|---|
| 1 | 22 |
| 2 | 68 |
| 3 | 101 |
| 4 | 199 |
| 5 | 105 |
| 6 | 99 |
| unsure | 172 |

A row with several topics is counted under each.

- **2.1.315 has no heading in the changelog.** Nothing else in the file mentions it. The list says no more than that.
- **Versions in the changelog with no listed entry:** 2.1.291 (2 entries in the changelog), 2.1.303 (1 entry) and 2.1.308 (1 entry).

## How it was made

A Claude agent (Sonnet) read the entries of the 39 versions and chose the rows. It was given the version list, the address of the changelog and the six topics. It was told that the results had not been looked at and it was told none. Its working rules, as it stated them:

- An entry is listed when one of the six is its subject or a substantial part of it. A topic named only as one example in a long list of unrelated dialogs or keys is not listed.
- Topic 3 covers new models and default models, model aliases, fallback and model switches, the behaviour of `/model`, and settings for which models are available. Topic 2 covers anything that names thinking, effort, `ultrathink` or `/effort`, display fixes included.
- Topic 4 covers changes to which tools, skills, plugins, MCP servers or MCP tools are available or loaded, limits on tool descriptions and server instructions, tool search, and edits to bundled skills. Plugin and MCP entries about sign-in, install commands, menus and colours are not listed.
- Topic 5 covers hooks of the settings kind (PreToolUse, SessionStart and so on). Entries about the separate hook interface that mods use, and about lifecycle hooks of self-hosted runners, are marked `unsure`.
- Topic 6 is used when the entry names `-p`, print, headless, non-interactive, `--output-format`, `stream-json`, `--include-partial-messages` or `--json-schema`. An entry that names only the Agent SDK is not listed, apart from a few marked `unsure`.
- `unsure` is also used where the program tells Claude something through a notice or a reminder, because the reader could not tell whether that counts as the system prompt.
- Entries that only concern the VS Code panel, cloud sessions, Slack, Code Review, self-hosted runners or the gateway are listed when they name one of the six. The agent counted 42 of them.

Claude (Fable 5.2), which runs this experiment, then checked the list. By then it had seen what the change log of PREREGISTRATION.md states, and no accuracy, thinking or output number of any group.

- It downloaded the changelog again at the commit above. The file is the same as the agent's copy, byte for byte.
- All 693 rows of the agent are entries of the version they are listed under, word for word.
- It searched the 2,287 unlisted entries for the words of topics 1, 2 and 6 (system prompt, think, effort, reasoning, `-p`, print, headless, non-interactive, `stream-json`, `output-format`). Six entries came up. All six are added, marked `review` in the last column, whether or not the topic is their subject: 2.1.280 line 3287, 2.1.283 line 2968, 2.1.299 line 1643, 2.1.302 line 1408, 2.1.309 line 1120 and 2.1.316 line 758.
- It read the 59 other unlisted entries that name a model (model, Opus, Sonnet, Haiku, Fable). None is about which model answers. One names the default model in passing, 2.1.317 line 703, and is added with the mark `review`. Entries about how the `/model` picker is drawn were left out.

## Limits

- The agent read an entry that held none of a broad list of words (system prompt, think, effort, model, hook, skill, plugin, MCP, tools, agent, headless, json, default and similar) only by its first 50 characters, and an entry that held one by its first 200. A topic that appears later in a long entry may have been missed.
- The unlisted entries were searched by word for topics 1, 2, 3 and 6. For topics 4 and 5 they were not checked again.
- One reader chose the rows. Where the line between listed and unlisted falls is a judgement, most of all for topic 4.
- The changelog is taken as it stood at the commit above. Whether an entry was moved between versions or edited after its release was not checked. Whether each version does what its entries say was not checked either.
- A change that the changelog does not mention is not here. The requests each version sends were compared directly, and that comparison is in section 8 of PREREGISTRATION.md.
