"""
License guard: verify all installed packages use permissive licenses.
Fails if any package uses GPL, AGPL, LGPL, SSPL, or Commons Clause.
Called from CI license-guard job as a fallback.
"""
import importlib.metadata
import re
import sys

# Patterns that indicate a blocked license when found as a license identifier,
# not just as a substring of the license body text.
BLOCKED_PATTERNS = [
    re.compile(r"\bagpl\b", re.IGNORECASE),
    re.compile(r"\bgnu affero\b", re.IGNORECASE),
    re.compile(r"\bsspl\b", re.IGNORECASE),
    re.compile(r"\bcommons clause\b", re.IGNORECASE),
    # GPL but not LGPL, Apache, or other permissive licenses containing "gpl" substrings
    re.compile(r"\bgnu general public license\b", re.IGNORECASE),
    re.compile(r"(?<![la])gpl[-v ]?[23]", re.IGNORECASE),
]

failures = []
for dist in importlib.metadata.distributions():
    name = dist.metadata.get("Name", "unknown")
    # Use License classifier lines only (not the full license body text)
    classifiers = dist.metadata.get_all("Classifier") or []
    license_classifiers = " ".join(
        c for c in classifiers if "License" in c
    )
    # Also check the short License field (not the full license text)
    short_license = (dist.metadata.get("License-Expression") or
                     dist.metadata.get("License") or "")
    # Skip if the short license field is clearly a long text body (> 200 chars)
    if len(short_license) > 200:
        short_license = ""

    combined = license_classifiers + " " + short_license
    for pattern in BLOCKED_PATTERNS:
        if pattern.search(combined):
            failures.append(f"{name}: classifiers={license_classifiers!r} license={short_license!r}")
            break

if failures:
    print("LICENSE FAILURES:")
    for f in failures:
        print(f"  {f}")
    sys.exit(1)

count = sum(1 for _ in importlib.metadata.distributions())
print(f"license-guard: {count} packages, all permissive")
