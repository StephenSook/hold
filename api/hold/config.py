"""
Runtime configuration constants for HOLD.

GEMINI_MODEL: pinned to a Gemini 3.x Flash id verified in Vertex AI Model Garden
on 2026-09-03. gemini-2.5 retires 2026-10-16 per the Vertex AI release notes
(https://cloud.google.com/vertex-ai/generative-ai/docs/learn/model-versions).
gemini-3.1-flash-lite answered a generateContent probe on the global Vertex location
from project hold-2026 on 2026-09-03 (0.8 s, modelVersion gemini-3.1-flash-lite).
"""

# Gemini 3.x Flash - non-preview, non-2.5 id.
# Update this constant when a newer stable 3.x Flash id supersedes it.
GEMINI_MODEL: str = "gemini-3.1-flash-lite"

# Vertex AI location for Gemini. On project hold-2026 the 3.x line generates only from the
# "global" location: us-central1 lists gemini-3.1-flash-lite but generateContent answers 404
# there (checked 2026-09-03 with a probe call). Cloud Run itself stays in us-central1.
GOOGLE_CLOUD_LOCATION: str = "global"

# google-adk version pinned in pyproject.toml
ADK_VERSION: str = "2.6.3"


def env_value(name: str) -> str | None:
    """An environment value, or None when it is empty or the literal placeholder "unset" (Secret
    Manager refuses an empty payload, so scripts/gcp_setup.sh seeds unknown secrets with that word)."""
    import os

    value = os.environ.get(name, "").strip()
    return None if value == "" or value.lower() == "unset" else value
