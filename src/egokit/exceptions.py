"""Custom exceptions for EgoKit."""

from typing import Any


class EgoKitError(Exception):
    """Base exception for all EgoKit errors."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.details = details or {}


class PolicyValidationError(EgoKitError):
    """Raised when policy configuration is invalid."""


class EgoValidationError(EgoKitError):
    """Raised when ego configuration is invalid."""


class ScopeError(EgoKitError):
    """Raised when scope resolution fails."""


class CompilationError(EgoKitError):
    """Raised when artifact compilation fails."""


class RegistryError(EgoKitError):
    """Raised when policy registry operations fail."""
