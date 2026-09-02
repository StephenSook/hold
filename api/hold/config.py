"""
Runtime configuration constants for HOLD.

GEMINI_MODEL: pinned to a Gemini 3.x Flash id verified in Vertex AI Model Garden
on 2026-09-03. gemini-2.5 retires 2026-10-16 per the Vertex AI release notes
(https://cloud.google.com/vertex-ai/generative-ai/docs/learn/model-versions).
gemini-3.1-flash-lite is a stable non-preview 3.x model confirmed via
google.genai client.models.list() on 2026-09-03.
"""

# Gemini 3.x Flash - non-preview, non-2.5 id.
# Update this constant when a newer stable 3.x Flash id supersedes it.
GEMINI_MODEL: str = "gemini-3.1-flash-lite"

# GCP region for Vertex AI Gemini endpoint.
GOOGLE_CLOUD_LOCATION: str = "us-central1"

# google-adk version pinned in pyproject.toml
ADK_VERSION: str = "2.6.3"
