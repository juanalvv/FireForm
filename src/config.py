"""
Centralized configuration for FireForm.

All tuneable values live here.  Every setting can be overridden with an
environment variable; a ``.env`` file in the project root is loaded
automatically when present (via python-dotenv).
"""

from pathlib import Path

from dotenv import load_dotenv
import os

load_dotenv()

# ── Paths ────────────────────────────────────────────────────────────
BASE_DIR: Path = Path(__file__).resolve().parent  # …/src/

DEFAULT_INPUT_PDF: Path = BASE_DIR / "inputs" / "file.pdf"
DEFAULT_PREPARED_PDF: Path = BASE_DIR / "temp_outfile.pdf"

OUTPUT_PDF_SUFFIX: str = os.getenv("OUTPUT_PDF_SUFFIX", "_filled.pdf")

# ── Ollama / LLM ────────────────────────────────────────────────────
OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "mistral")
OLLAMA_API_PATH: str = os.getenv("OLLAMA_API_PATH", "/api/generate")
