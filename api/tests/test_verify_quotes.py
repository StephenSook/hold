"""Task 2.16: the refetching quote check reads its plan from the registry and judges a fetched body by
content, never by status code."""
from __future__ import annotations

from pathlib import Path

from scripts.verify_quotes import Fetched, classify, plan

ROOT = Path(__file__).resolve().parents[2]


def test_plan_names_every_distinct_source_with_the_records_that_cite_it() -> None:
    rows = plan(ROOT / "rules")
    assert len(rows) > 10
    urls = {r.url for r in rows}
    assert "https://rules.sos.ga.gov/gac/300-7-1" in urls
    ga = next(r for r in rows if r.url == "https://rules.sos.ga.gov/gac/300-7-1")
    assert ga.snapshot == "ga-300-7-1.txt" and len(ga.quotes) >= 2 and all(q.strip() for q in ga.quotes)


def test_classify_judges_the_body_not_the_status() -> None:
    """Every verdict is decided by the bytes: a 200 carrying a challenge stub, a truncated page or a
    body that no longer states the quote is never a pass."""
    quote = "No work day shall start earlier than 5:00 A.M."
    page = "<html><body>" + ("filler text about child performers. " * 80) + "{}</body></html>"
    assert classify(Fetched(status=200, body=page.format(quote), is_pdf=False), [quote]) == "unchanged"
    assert classify(Fetched(status=200, body=page.format("the rule was amended in 2027"), is_pdf=False), [quote]) == "drifted"
    assert classify(Fetched(status=200, body=page.format(quote).replace("<html>", "<html>Request unsuccessful. Incapsula "), is_pdf=False), [quote]) == "refused"
    assert classify(Fetched(status=200, body=f"<html>{quote}</html>", is_pdf=False), [quote]) == "refused"  # too small to be the real page
    assert classify(Fetched(status=403, body="", is_pdf=False), [quote]) == "blocked"
    assert classify(Fetched(status=200, body="%PDF-1.7 binary", is_pdf=True), [quote]) == "unchanged"
    assert classify(Fetched(status=200, body="not a pdf at all", is_pdf=True), [quote]) == "refused"
    assert classify(Fetched(status=500, body="", is_pdf=False), [quote]) == "error"
