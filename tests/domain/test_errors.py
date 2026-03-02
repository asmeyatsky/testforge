"""Tests for domain errors."""

import pytest

from testforge.domain.errors import (
    AnalysisError,
    ConfigError,
    DomainError,
    GenerationError,
    ScannerError,
    StrategyError,
    UnsupportedLanguageError,
)


class TestErrorHierarchy:
    def test_all_inherit_from_domain_error(self):
        for cls in (AnalysisError, ScannerError, StrategyError, GenerationError, ConfigError, UnsupportedLanguageError):
            assert issubclass(cls, DomainError)

    def test_domain_error_is_exception(self):
        assert issubclass(DomainError, Exception)

    def test_unsupported_language_message(self):
        err = UnsupportedLanguageError("rust")
        assert "rust" in str(err)
        assert err.language == "rust"

    def test_can_raise_and_catch(self):
        with pytest.raises(DomainError):
            raise AnalysisError("something failed")

    def test_config_error(self):
        with pytest.raises(ConfigError, match="bad config"):
            raise ConfigError("bad config")
