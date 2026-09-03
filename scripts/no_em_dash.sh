#!/usr/bin/env bash
# Gate: fail if any em-dash character (U+2014) appears in any tracked or untracked
# (non-ignored) file. Resolves the file set via git ls-files per CI rule 3.
# Uses Python for the grep to avoid platform differences with grep -P.
set -euo pipefail

# rules/sources/ holds verbatim third-party snapshots (statutes, forms, rate sheets); their
# punctuation is the publisher's and is exempt. Everything we write ourselves is checked.
FILES=$(git ls-files --cached --others --exclude-standard | grep -v '^rules/sources/')

if [ -z "$FILES" ]; then
  echo "no_em_dash: no files to check"
  exit 0
fi

FOUND=$(echo "$FILES" | python3 -c "
import sys, os
found = []
for path in sys.stdin.read().splitlines():
    if not os.path.isfile(path):
        continue
    try:
        with open(path, 'rb') as f:
            if b'\xe2\x80\x94' in f.read():
                found.append(path)
    except OSError:
        pass
print('\n'.join(found))
")

if [ -n "$FOUND" ]; then
  echo "ERROR: em-dash found in the following files:"
  echo "$FOUND"
  echo "Replace with: colon (elaboration), comma/parens (aside), period (clause break), hyphen (range)."
  exit 1
fi

echo "no_em_dash: clean"
