#!/usr/bin/env python
"""
Task 2.16: refetch every rule source and report drift. The 2.10 check (api/hold/quotes.py) proves each
quote against a committed snapshot; nothing there re-reads the source, so a page amended after the
snapshot was taken would pass forever. This script closes that loop.

    uv run python scripts/verify_quotes.py                 # fetch everything, report, write the run to the cache
    uv run python scripts/verify_quotes.py --only ga-300-7-1.txt
    uv run python scripts/verify_quotes.py --write ga-300-7-1.txt   # refresh that snapshot from the fetched body

A 200 is never trusted: a PDF must start with %PDF, an HTML body smaller than a real page is a
challenge stub, and a body that no longer contains the record's quote is drift. Fetched bodies land in
rules/sources-cache/ (gitignored); the repository is written only with --write.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.hold.quotes import normalize, quote_matches  # noqa: E402
from api.hold.registry import load_rules  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "rules" / "sources-cache"
PACE_S = 8.0  # government and enterprise sites block a faster loop
_STUB = re.compile(r"incapsula|request unsuccessful|are you a human|captcha|access denied", re.IGNORECASE)
_MIN_HTML = 1500  # a challenge stub is a few hundred bytes; every real source here is far larger


@dataclass
class Source:
    url: str
    snapshot: str | None
    record_ids: list[str] = field(default_factory=list)
    quotes: list[str] = field(default_factory=list)


@dataclass
class Fetched:
    status: int
    body: str
    is_pdf: bool


def plan(rules_dir: Path) -> list[Source]:
    """One row per distinct source_url, with the records that cite it and their quotes."""
    verification = json.loads((rules_dir / "verification.json").read_text(encoding="utf-8"))
    snapshot_of = {name: entry.get("url") for name, entry in verification["snapshots"].items()}
    by_url: dict[str, Source] = {}
    for record in load_rules(rules_dir):
        row = by_url.setdefault(record.source_url, Source(url=record.source_url, snapshot=next((n for n, u in snapshot_of.items() if u == record.source_url), None)))
        row.record_ids.append(record.id)
        row.quotes.append(record.quote.strip())
    return [by_url[u] for u in sorted(by_url)]


def fetch(url: str, timeout_s: float = 60.0) -> Fetched:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (HOLD quote verification)", "Accept": "*/*"})
    try:
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
            raw = response.read()
            return Fetched(status=response.status, body=raw.decode("utf-8", "ignore"), is_pdf=raw[:5] == b"%PDF-" or url.lower().endswith(".pdf"))
    except urllib.error.HTTPError as exc:
        return Fetched(status=exc.code, body="", is_pdf=False)
    except Exception:
        return Fetched(status=0, body="", is_pdf=False)


def classify(fetched: Fetched, quotes: list[str]) -> str:
    """What the fetched body says about the snapshot, judged by content: unchanged, drifted, refused,
    blocked (the site turns scripts away) or error."""
    if fetched.status in (401, 403, 429):
        return "blocked"
    if fetched.status != 200:
        return "error"
    if fetched.is_pdf:
        return "unchanged" if fetched.body.startswith("%PDF") else "refused"
    if len(fetched.body) < _MIN_HTML or _STUB.search(fetched.body[:4000]):
        return "refused"
    text = normalize(re.sub(r"<[^>]+>", " ", fetched.body))
    variants = (text, text)
    return "unchanged" if all(quote_matches(q, variants) for q in quotes) else "drifted"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", help="one snapshot name, to check a single source")
    parser.add_argument("--write", help="refresh this snapshot from the fetched body (repository write)")
    parser.add_argument("--pace", type=float, default=PACE_S)
    args = parser.parse_args()
    CACHE.mkdir(parents=True, exist_ok=True)
    rows = [r for r in plan(ROOT / "rules") if args.only in (None, r.snapshot)]
    counts: dict[str, int] = defaultdict(int)
    print("| Source | Snapshot | Records | Verdict |\n|---|---|---|---|")
    for i, row in enumerate(rows):
        if i:
            time.sleep(args.pace)
        fetched = fetch(row.url)
        verdict = classify(fetched, row.quotes)
        counts[verdict] += 1
        if fetched.body:
            (CACHE / (row.snapshot or re.sub(r"\W+", "-", row.url)[:80])).write_text(fetched.body, encoding="utf-8")
        print(f"| {row.url} | {row.snapshot or '(none)'} | {len(row.record_ids)} | {verdict} |")
        if args.write and args.write == row.snapshot and row.snapshot:
            if verdict != "unchanged":
                print(f"\nrefusing to write {args.write}: the fetch was {verdict}", file=sys.stderr)
                return 2
            target = ROOT / "rules" / "sources" / row.snapshot
            header = target.read_text(encoding="utf-8").split("\n\n", 1)[0]
            body = subprocess.run(["pdftotext", "-", "-"], input=fetched.body.encode(), capture_output=True).stdout.decode() if fetched.is_pdf else re.sub(r"<[^>]+>", " ", fetched.body)
            target.write_text(header + "\n\n" + body, encoding="utf-8")
            print(f"\nrewrote {target.relative_to(ROOT)} from the fetched body; commit it with the header's fetched_at updated")
    print("\n" + ", ".join(f"{v} {k}" for k, v in sorted(counts.items())))
    return 1 if counts["drifted"] or counts["error"] else 0


if __name__ == "__main__":
    sys.exit(main())
