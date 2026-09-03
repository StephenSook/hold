#!/usr/bin/env python
"""
License guard (task 5.4). HOLD ships Apache-2.0, so no dependency may carry a copyleft or
source-available license. CI runs this bare: `uv run python scripts/check_licenses.py`.

Blocked: AGPL, GPL (any version, including a bare "GPL"), SSPL, Commons Clause.
Allowed on purpose: LGPL. These are dynamically imported Python libraries, not statically linked,
so the LGPL's relinking obligation does not reach this project's own code. No dependency carries
it today either way; the allowance is stated so the guard and the policy agree rather than one
claiming to block what the other permits.

api/tests/test_licenses.py proves each family above is caught or cleared.
"""
from __future__ import annotations

import importlib.metadata
import re
import sys

_BLOCKED: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bagpl\b|\bgnu affero\b", re.IGNORECASE), "AGPL"),
    (re.compile(r"\bsspl\b|server side public license", re.IGNORECASE), "SSPL"),
    (re.compile(r"\bcommons clause\b", re.IGNORECASE), "Commons Clause"),
    # GPL in any form, but never LGPL: the negative lookbehind keeps "LGPL-2.1" out.
    (re.compile(r"(?<![a-z])gpl\b|(?<![a-z])gplv?[0-9]|\bgnu general public license\b", re.IGNORECASE), "GPL"),
)


def blocked_reason(license_text: str) -> str | None:
    """The blocked family this license string belongs to, or None when it is permissive."""
    for pattern, name in _BLOCKED:
        if pattern.search(license_text or ""):
            return name
    return None


def offenders() -> list[str]:
    """Every installed distribution whose declared license is blocked."""
    found: list[str] = []
    for dist in importlib.metadata.distributions():
        name = dist.metadata.get("Name", "unknown")
        classifiers = " ".join(c for c in (dist.metadata.get_all("Classifier") or []) if "License" in c)
        short = dist.metadata.get("License-Expression") or dist.metadata.get("License") or ""
        if len(short) > 200:  # some wheels paste the whole license body into this field
            short = ""
        reason = blocked_reason(f"{classifiers} {short}")
        if reason:
            found.append(f"{name}: {reason} (classifiers={classifiers!r} license={short!r})")
    return sorted(found)


def main() -> int:
    found = offenders()
    if found:
        print("LICENSE FAILURES:")
        for line in found:
            print(f"  {line}")
        return 1
    count = sum(1 for _ in importlib.metadata.distributions())
    print(f"license-guard: {count} packages, none carrying AGPL, GPL, SSPL or Commons Clause")
    return 0


if __name__ == "__main__":
    sys.exit(main())
