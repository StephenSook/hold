"""Task 2.16: the refetching quote check reads its plan from the registry and judges a fetched body by
content, never by status code."""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

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
    assert classify(Fetched(status=200, body="not a pdf at all", is_pdf=True, raw=b"not a pdf at all"), [quote]) == "refused"
    assert classify(Fetched(status=500, body="", is_pdf=False), [quote]) == "error"


def test_html_entities_do_not_read_as_drift() -> None:
    """First live run: sagindie.org serves "Pension &amp; Health" and the quote says "Pension & Health";
    an entity-blind check called an unchanged page drifted."""
    quote = "Pension & Health contribution is also owed (21% for performers)"
    page = "<html><body>" + ("filler about low budget agreements. " * 80) + "Pension &amp; Health contribution is also owed (21% for performers)</body></html>"
    assert classify(Fetched(status=200, body=page, is_pdf=False), [quote]) == "unchanged"


def test_error_rows_say_what_happened() -> None:
    from scripts.verify_quotes import describe

    assert describe(Fetched(status=0, body="", is_pdf=False, note="TimeoutError")) == "error (TimeoutError)"
    assert describe(Fetched(status=500, body="", is_pdf=False)) == "error (HTTP 500)"
    assert describe(Fetched(status=200, body="", is_pdf=False)) == ""


def _pdf(text: str) -> bytes:
    """A minimal one-page PDF carrying `text`, enough for pdftotext to extract it."""
    stream = f"BT /F1 12 Tf 40 700 Td ({text}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, obj in enumerate(objects, 1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)


def test_a_pdf_is_judged_by_its_extracted_text_not_its_magic_bytes() -> None:
    """Round nine, finding 1: any body starting with %PDF was called unchanged without reading it, so
    five sources carrying 23 verified records were reported as checked when nothing was compared. The
    extractor is injected here, so this asserts the decision and not whether poppler is installed."""
    quote = "No work day shall start earlier than 5:00 A.M."
    pdf = Fetched(status=200, body="", is_pdf=True, raw=b"%PDF-1.4 whatever bytes")
    assert classify(pdf, [quote], extract=lambda raw: f"preamble {quote} tail") == "unchanged"
    assert classify(pdf, [quote], extract=lambda raw: "an unrelated sentence") == "drifted"
    assert classify(pdf, [quote], extract=lambda raw: None) == "unreadable"
    assert classify(pdf, [quote], extract=lambda raw: "") == "unreadable"


@pytest.mark.skipif(shutil.which("pdftotext") is None, reason="poppler is not installed on this machine; the injected-extractor test above covers the decision")
def test_the_default_extractor_reads_a_real_pdf() -> None:
    """Where poppler exists, prove the shipped default actually reads a document rather than only the
    injected stub. CI has no poppler, so this runs on a developer machine and the operator script."""
    quote = "No work day shall start earlier than 5:00 A.M."
    assert classify(Fetched(status=200, body="", is_pdf=True, raw=_pdf(quote)), [quote]) == "unchanged"
    assert classify(Fetched(status=200, body="", is_pdf=True, raw=_pdf("an unrelated sentence")), [quote]) == "drifted"
