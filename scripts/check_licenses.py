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
    # "AGPLv3" and "AGPLv3+" are common setup.py values, so the version suffix is part of the token.
    (re.compile(r"(?<![a-z])agpl[v0-9.+-]*(?![a-z])|\bgnu affero\b", re.IGNORECASE), "AGPL"),
    (re.compile(r"(?<![a-z])sspl[v0-9.+-]*(?![a-z])|server side public license", re.IGNORECASE), "SSPL"),
    # Both the prose form and the SPDX form, which uses a hyphen: "Apache-2.0 WITH Commons-Clause".
    (re.compile(r"\bcommons[ -]clause\b", re.IGNORECASE), "Commons Clause"),
    # GPL in any form, but never LGPL: the negative lookbehind keeps "LGPL-2.1" and "LGPLv3" out.
    (re.compile(r"(?<![a-z])gpl[v0-9.+-]*(?![a-z])|\bgnu general public license\b", re.IGNORECASE), "GPL"),
)


def blocked_reason(license_text: str) -> str | None:
    """The blocked family this license string belongs to, or None when it is permissive."""
    for pattern, name in _BLOCKED:
        if pattern.search(license_text or ""):
            return name
    return None


def _or_branches(expression: str) -> list[str]:
    """Top-level OR branches of an SPDX expression, with parentheses kept intact. Splitting only at
    depth zero keeps "(MIT OR Apache-2.0) AND GPL-3.0-only" as one branch, which is what AND means."""
    branches, depth, start = [], 0, 0
    i = 0
    while i < len(expression):
        char = expression[i]
        if char == "(":
            depth += 1
        elif char == ")":
            depth = max(0, depth - 1)
        elif depth == 0 and expression[i : i + 4].upper() == " OR " :
            branches.append(expression[start:i])
            start = i + 4
            i += 3
        i += 1
    branches.append(expression[start:])
    return [b.strip() for b in branches if b.strip()]


def expression_reason(expression: str) -> str | None:
    """An SPDX License-Expression is blocked only when every top-level OR branch is blocked: an OR is
    a choice, so a distribution offering "MIT OR GPL-2.0-or-later" may be taken as MIT."""
    reasons = [blocked_reason(branch) for branch in _or_branches(expression)]
    if not reasons or any(reason is None for reason in reasons):
        return None
    return reasons[0]


def offenders() -> list[str]:
    """Every installed distribution whose declared license is blocked."""
    found: list[str] = []
    for dist in importlib.metadata.distributions():
        name = dist.metadata.get("Name", "unknown")
        classifiers = " ".join(c for c in (dist.metadata.get_all("Classifier") or []) if "License" in c)
        expression = dist.metadata.get("License-Expression") or ""
        # Some wheels paste the whole licence body into the legacy License field. Scanning all of it
        # flags a permissive package whose bundled notices merely mention a copyleft licence (pandas
        # does), and discarding it misses a pasted GPL text entirely. A licence body names itself in
        # its opening line, so the first 200 characters are the part that identifies it. An SPDX
        # expression is not prose and is read as an expression instead.
        declared = expression or (dist.metadata.get("License") or "")
        reason = blocked_reason(classifiers) or (expression_reason(expression) if expression else blocked_reason(declared[:200]))
        if reason:
            found.append(f"{name}: {reason} (classifiers={classifiers!r} license={declared[:200]!r})")
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
