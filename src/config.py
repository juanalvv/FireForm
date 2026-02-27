"""
Configuration validation and safe URL handling for FireForm.

All environment-based settings are validated at startup via validate_config().
URLs are built with urllib.parse.urljoin() to avoid double-slash bugs.
"""

import os
from urllib.parse import urljoin


# ---------------------------------------------------------------------------
# Default values
# ---------------------------------------------------------------------------
_DEFAULT_OLLAMA_HOST = "http://localhost:11434"
_DEFAULT_OLLAMA_API_PATH = "/api/generate"
_DEFAULT_OUTPUT_PDF_SUFFIX = "_filled.pdf"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_config() -> None:
    """Validate environment-variable configuration at startup.

    Raises ``ValueError`` with a descriptive message when a setting is
    invalid.  Call this once during application initialisation.
    """
    ollama_host = os.getenv("OLLAMA_HOST", _DEFAULT_OLLAMA_HOST)
    ollama_api_path = os.getenv("OLLAMA_API_PATH", _DEFAULT_OLLAMA_API_PATH)
    output_pdf_suffix = os.getenv("OUTPUT_PDF_SUFFIX", _DEFAULT_OUTPUT_PDF_SUFFIX)

    if not ollama_host.startswith(("http://", "https://")):
        raise ValueError(
            f"OLLAMA_HOST must start with http:// or https://, got: {ollama_host!r}"
        )

    if not ollama_api_path.startswith("/"):
        raise ValueError(
            f"OLLAMA_API_PATH must start with /, got: {ollama_api_path!r}"
        )

    if not output_pdf_suffix.endswith(".pdf"):
        raise ValueError(
            f"OUTPUT_PDF_SUFFIX must end with .pdf, got: {output_pdf_suffix!r}"
        )


# ---------------------------------------------------------------------------
# Safe URL builder
# ---------------------------------------------------------------------------

def build_ollama_url() -> str:
    """Return the full Ollama API URL built with :func:`urllib.parse.urljoin`.

    This avoids the double-slash bug that occurs with naive string
    concatenation (e.g. ``http://host//api/generate``).
    """
    host = os.getenv("OLLAMA_HOST", _DEFAULT_OLLAMA_HOST)
    path = os.getenv("OLLAMA_API_PATH", _DEFAULT_OLLAMA_API_PATH)
    return urljoin(host, path)
