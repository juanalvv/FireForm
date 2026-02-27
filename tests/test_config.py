"""Tests for src.config – configuration validation and safe URL building."""

import os
import pytest

from src.config import validate_config, build_ollama_url


# ---------------------------------------------------------------------------
# validate_config – happy path
# ---------------------------------------------------------------------------

class TestValidateConfigValid:
    """Default values and well-formed overrides should pass silently."""

    def test_defaults_are_valid(self, monkeypatch):
        """With no env vars set the defaults must pass validation."""
        monkeypatch.delenv("OLLAMA_HOST", raising=False)
        monkeypatch.delenv("OLLAMA_API_PATH", raising=False)
        monkeypatch.delenv("OUTPUT_PDF_SUFFIX", raising=False)
        validate_config()  # should not raise

    def test_custom_valid_config(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_HOST", "https://ollama.example.com")
        monkeypatch.setenv("OLLAMA_API_PATH", "/v1/generate")
        monkeypatch.setenv("OUTPUT_PDF_SUFFIX", "_output.pdf")
        validate_config()  # should not raise


# ---------------------------------------------------------------------------
# validate_config – invalid OLLAMA_HOST
# ---------------------------------------------------------------------------

class TestValidateConfigInvalidHost:

    def test_missing_scheme(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_HOST", "localhost:11434")
        with pytest.raises(ValueError, match="OLLAMA_HOST must start with http:// or https://"):
            validate_config()

    def test_ftp_scheme(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_HOST", "ftp://localhost:11434")
        with pytest.raises(ValueError, match="OLLAMA_HOST must start with http:// or https://"):
            validate_config()


# ---------------------------------------------------------------------------
# validate_config – invalid OLLAMA_API_PATH
# ---------------------------------------------------------------------------

class TestValidateConfigInvalidApiPath:

    def test_missing_leading_slash(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_API_PATH", "api/generate")
        with pytest.raises(ValueError, match="OLLAMA_API_PATH must start with /"):
            validate_config()


# ---------------------------------------------------------------------------
# validate_config – invalid OUTPUT_PDF_SUFFIX
# ---------------------------------------------------------------------------

class TestValidateConfigInvalidSuffix:

    def test_wrong_extension(self, monkeypatch):
        monkeypatch.setenv("OUTPUT_PDF_SUFFIX", "_filled.docx")
        with pytest.raises(ValueError, match="OUTPUT_PDF_SUFFIX must end with .pdf"):
            validate_config()

    def test_empty_suffix(self, monkeypatch):
        monkeypatch.setenv("OUTPUT_PDF_SUFFIX", "")
        with pytest.raises(ValueError, match="OUTPUT_PDF_SUFFIX must end with .pdf"):
            validate_config()


# ---------------------------------------------------------------------------
# build_ollama_url – urljoin correctness
# ---------------------------------------------------------------------------

class TestBuildOllamaUrl:

    def test_default_url(self, monkeypatch):
        monkeypatch.delenv("OLLAMA_HOST", raising=False)
        monkeypatch.delenv("OLLAMA_API_PATH", raising=False)
        assert build_ollama_url() == "http://localhost:11434/api/generate"

    def test_trailing_slash_on_host(self, monkeypatch):
        """The classic double-slash bug must not occur."""
        monkeypatch.setenv("OLLAMA_HOST", "http://localhost:11434/")
        monkeypatch.setenv("OLLAMA_API_PATH", "/api/generate")
        url = build_ollama_url()
        assert url == "http://localhost:11434/api/generate"
        assert "//" not in url.split("://", 1)[1]  # no double-slash after scheme

    def test_no_trailing_slash_on_host(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_HOST", "http://localhost:11434")
        monkeypatch.setenv("OLLAMA_API_PATH", "/api/generate")
        assert build_ollama_url() == "http://localhost:11434/api/generate"

    def test_custom_host_and_path(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_HOST", "https://ai.example.com:8080")
        monkeypatch.setenv("OLLAMA_API_PATH", "/v2/chat")
        assert build_ollama_url() == "https://ai.example.com:8080/v2/chat"
