"""ccversions: run the LiveNerf panel against many Claude Code versions, one fresh ask at a time.

The question texts and the graders come from the LiveNerf author's code (ninjahawk/livenerf, MIT).
This package only builds the asks, launches them (or prints them, in a dry run), keeps the raw
records and grades them afterwards with the author's graders.

Nothing in this package hard-codes a path, an account or a login on the machine it runs on. All of
that lives in a local settings file (see settings.example.toml), passed with --settings or the
CCV_SETTINGS environment variable.
"""

import sys

# Importing the LiveNerf author's modules must never leave __pycache__ folders inside the author's
# repository, which is treated as read-only.
sys.dont_write_bytecode = True

PACKAGE_VERSION = "0.1.0"
