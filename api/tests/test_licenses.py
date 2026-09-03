"""The license guard is what stands between a copyleft dependency and an Apache-2.0 submission, so its
matcher is tested rather than trusted (the CI job used to hand a real violation to a weaker fallback)."""
from __future__ import annotations

import pytest

from scripts.check_licenses import blocked_reason


@pytest.mark.parametrize(
    "value",
    [
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "GPL-3.0",
        "GPL-2.0-only",
        "GPL",
        "GPLv2",
        "AGPL-3.0",
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
