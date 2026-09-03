# Pre-submission sweeps

Task 5.11. Run over every tracked file before any judge-facing surface changes, and again in the
freeze window. The commands live here so the run is repeatable, and the deliberate exceptions are
named rather than silently allowed.

Each scan below names its characters by code point, because a document that contained the
characters it forbids would fail the em-dash gate that CI runs on this repository. That is the
same reason `docs/claims-audit.md` describes the forbidden vendor names without repeating them.

## Commands

```bash
bash scripts/no_em_dash.sh                       # the dash gate CI runs

# em dash (U+2014), en dash (U+2013), curly quotes (U+2018, U+2019, U+201C, U+201D)
uv run python - <<'PY'
import re, subprocess
files = subprocess.run(["git", "ls-files", "*.md", "*.py"], capture_output=True, text=True).stdout.split()
bad = re.compile("[\\u2014\\u2013\\u2018\\u2019\\u201c\\u201d]")  # dashes and curly quotes, by code point
for f in files:
    if f.startswith("rules/sources/"):
        continue          # verbatim third-party text; changing its punctuation breaks quote verification
    for i, line in enumerate(open(f, encoding="utf-8", errors="ignore"), 1):
        if bad.search(line):
            print(f"{f}:{i}: {line.strip()[:100]}")
PY

git ls-files '*.md' | grep -v '^rules/sources/' | xargs grep -niwE \
  'leverage|robust|comprehensive|seamless|powerful|sophisticated|cutting-edge|revolutionary|effortlessly|streamline|delve|elevate|empower|intuitive|unlock|ecosystem'
git grep -hoiE '[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}' -- . ':!uv.lock'            # addresses
git grep -nE '\(?[0-9]{3}\)?[-. ][0-9]{3}[-. ][0-9]{4}' -- . ':!uv.lock' ':!bench'  # phone shapes
git ls-files | grep -iE '\.(pdf|env|jks|keystore|p8|p12|mov|mp4)$|^private/|sources-cache'
uv run python scripts/check_links.py                                               # every link answers
```

## Result, 2026-09-03

| Sweep | Result |
|---|---|
| Dashes | none in any tracked file outside `rules/sources/`, which holds verbatim third-party text |
| Curly quotes | one, deliberate: `api/tests/test_quotes.py` feeds a curly apostrophe to the normalizer to prove it is straightened |
| AI-tone blocklist | no hit in any tracked document |
| Addresses | two, both Google service accounts named in the deploy setup: they are infrastructure identifiers, not people |
| Phone shapes | none |
| Private material | no PDF, no `.env`, no keystore, no `private/`, no fetch cache is tracked |
| Third-party names | the task table no longer carries a teammate's account handle; team membership lives on Devpost and the repository's own collaborator list |
| Links | every URL and repository path in README and JUDGE answers; see `docs/links-check.md` |
