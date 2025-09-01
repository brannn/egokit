"""Custom exceptions for EgoKit."""

from typing import Any, Dict, List, Optional


class EgoKitError(Exception):
    """Base exception for all EgoKit errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.details = details or {}


class PolicyValidationError(EgoKitError):
    """Raised when policy configuration is invalid."""
    pass


class EgoValidationError(EgoKitError):
    """Raised when ego configuration is invalid."""
    pass


class ScopeError(EgoKitError):
    """Raised when scope resolution fails."""
    pass


class DetectorError(EgoKitError):
    """Raised when detector execution fails."""
    
    def __init__(
        self, 
        message: str, 
        detector_name: str,
        file_path: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(message, details)
        self.detector_name = detector_name
        self.file_path = file_path


class CompilationError(EgoKitError):
    """Raised when artifact compilation fails."""
    pass


class RegistryError(EgoKitError):
    """Raised when policy registry operations fail."""
    pass