"""Domain error hierarchy."""

from __future__ import annotations


class DomainError(Exception):
    """Base error for all domain errors."""


class AnalysisError(DomainError):
    """Raised when codebase analysis fails."""


class ScannerError(DomainError):
    """Raised when a code scanner encounters an error."""


class StrategyError(DomainError):
    """Raised when strategy generation fails."""


class GenerationError(DomainError):
    """Raised when test generation fails."""


class ConfigError(DomainError):
    """Raised when configuration is invalid or missing."""


class UnsupportedLanguageError(DomainError):
    """Raised when a language is not yet supported."""

    def __init__(self, language: str) -> None:
        super().__init__(f"Language not yet supported: {language}")
        self.language = language
