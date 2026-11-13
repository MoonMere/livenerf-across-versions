"""Print the release-note entries listed in entries.tsv, with their text.

entries.tsv names each entry by its line number in Claude Code's CHANGELOG.md
at one commit, and carries no text of the changelog. This script reads a copy
of that file, checks it against the hashes, and prints the rows in full.

    curl -sLO https://raw.githubusercontent.com/anthropics/claude-code/89eb88e3357be13ae7fcf8966144ad32f44def33/CHANGELOG.md
    python3 show_entries.py CHANGELOG.md
    python3 show_entries.py CHANGELOG.md --version 2.1.303 --topic 2
"""

import argparse
import hashlib
import pathlib
import sys

FILE_SHA256 = "6ed58ecb355fbcab5b2a9fda34df659a422920b915938d1900348a8230052652"
TOPICS = {
    "1": "system prompt",
    "2": "thinking or effort",
    "3": "default model, or a model replaced by another",
    "4": "tool descriptions, tool list, skills, plugins, MCP loading",
    "5": "hooks",
    "6": "print mode (-p), headless, --output-format, stream-json",
    "unsure": "the first reader could not tell",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("changelog", help="path to CHANGELOG.md at the commit named above")
    parser.add_argument("--version", help="only this Claude Code version, for example 2.1.303")
    parser.add_argument("--topic", help="only this topic: 1 to 6, or unsure")
    args = parser.parse_args()

    raw = pathlib.Path(args.changelog).read_bytes()
    if hashlib.sha256(raw).hexdigest() != FILE_SHA256:
        print("This is not the file the table was made from (sha256 differs).", file=sys.stderr)
        print("Line numbers may be off. Each row is still checked on its own hash.", file=sys.stderr)
    lines = raw.decode("utf-8").split("\n")

    table = pathlib.Path(__file__).with_name("entries.tsv").read_text(encoding="utf-8")
    bad = 0
    shown = 0
    for row in table.splitlines()[1:]:
        version, line, topics, digest, added_in = row.split("\t")
        number = int(line)
        text = lines[number - 1] if number <= len(lines) else ""
        if hashlib.sha256(text.encode("utf-8")).hexdigest()[:16] != digest:
            bad += 1
            print(f"{version} line {line}: the text does not match the hash", file=sys.stderr)
            continue
        tags = [t.strip() for t in topics.split(",")]
        if args.version and version != args.version:
            continue
        if args.topic and args.topic not in tags:
            continue
        shown += 1
        names = ", ".join(TOPICS[t] for t in tags)
        note = "" if added_in == "first_pass" else "  [added in review]"
        print(f"{version}  line {line}  [{names}]{note}")
        print(f"    {text[2:]}")
    print(f"{shown} rows shown, {bad} rows failed their hash", file=sys.stderr)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
