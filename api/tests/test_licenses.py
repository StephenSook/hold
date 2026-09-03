"""The license guard is what stands between a copyleft dependency and an Apache-2.0 submission, so its
matcher is tested rather than trusted (the CI job used to hand a real violation to a weaker fallback)."""
from __future__ import annotations

import pytest

from scripts.check_licenses import blocked_reason, expression_reason


@pytest.mark.parametrize(
    "value",
    [
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "GPL-3.0",
        "GPL-2.0-only",
        "GPL",
        "GPLv2",
        "AGPL-3.0",
        "AGPLv3",  # a common setup.py value; the word boundary used to break on the v
        "AGPLv3+",
        "agplv3",
        "Apache-2.0 WITH Commons-Clause",  # the SPDX spelling, hyphenated
        "LicenseRef-Commons-Clause",
        "GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007 " + "x" * 400,  # a pasted licence body
        "License :: OSI Approved :: GNU Affero General Public License v3",
        "SSPL-1.0",
        "Commons Clause",
    ],
)
def test_copyleft_and_source_available_licenses_are_blocked(value: str) -> None:
    assert blocked_reason(value), value


@pytest.mark.parametrize(
    "value",
    [
        "License :: OSI Approved :: MIT License",
        "Apache-2.0",
        "BSD-3-Clause",
        "ISC",
        "Python Software Foundation License",
        "Mozilla Public License 2.0 (MPL 2.0)",
        "LGPL-2.1",  # allowed on purpose: dynamically imported, and nothing here carries it
        "",
    ],
)
def test_permissive_licenses_pass(value: str) -> None:
    assert blocked_reason(value) is None, value


def test_the_installed_environment_is_clean() -> None:
    from scripts.check_licenses import offenders

    assert offenders() == []


@pytest.mark.parametrize(
    ("expression", "blocked"),
    [
        ("MIT OR GPL-2.0-or-later", False),  # a real PyPI declaration; the MIT branch may be taken
        ("GPL-2.0-only OR LGPL-2.1-only", False),  # LGPL is allowed here, so the choice clears
        ("Apache-2.0 OR MIT", False),
        ("AGPL-3.0-only OR SSPL-1.0", True),  # every branch blocked, so the choice is no escape
        ("GPL-3.0-only", True),
        ("Apache-2.0 AND GPL-3.0-only", True),  # AND is not a choice
        ("Apache-2.0 WITH Commons-Clause", True),
        ("(MIT OR Apache-2.0) AND GPL-3.0-only", True),  # the OR is inside the parentheses
        ("MIT OR (GPL-3.0-only AND SSPL-1.0)", False),
    ],
)
def test_spdx_expressions_treat_or_as_a_choice(expression: str, blocked: bool) -> None:
    assert (expression_reason(expression) is not None) is blocked, expression
