"""Task 0.15: Verify GEMINI_MODEL is a 3.x id, not a 2.5 id."""
from api.hold.config import GEMINI_MODEL, GOOGLE_CLOUD_LOCATION, ADK_VERSION


def test_gemini_model_is_not_2_5() -> None:
    """GEMINI_MODEL must not be a gemini-2.5 id (retires 2026-10-16)."""
    assert "gemini-2.5" not in GEMINI_MODEL, (
        f"GEMINI_MODEL={GEMINI_MODEL!r} is a 2.5 id which retires 2026-10-16. "
        "Update to a 3.x Flash id."
    )
    assert "2.5" not in GEMINI_MODEL.split("-")[:3], (
        f"GEMINI_MODEL={GEMINI_MODEL!r} appears to reference the 2.5 family. "
        "Update to a 3.x Flash id."
    )


def test_gemini_model_is_non_empty() -> None:
    assert GEMINI_MODEL, "GEMINI_MODEL must not be empty"


def test_gemini_model_contains_flash() -> None:
    assert "flash" in GEMINI_MODEL.lower(), (
        f"GEMINI_MODEL={GEMINI_MODEL!r} does not appear to be a Flash model. "
        "HOLD requires a Flash-class model for latency and cost."
    )


def test_google_cloud_location_is_non_empty() -> None:
    assert GOOGLE_CLOUD_LOCATION, "GOOGLE_CLOUD_LOCATION must not be empty"


def test_adk_version_pinned() -> None:
    assert ADK_VERSION == "2.6.3", (
        f"ADK_VERSION={ADK_VERSION!r} must be '2.6.3' per pyproject.toml pin"
    )
