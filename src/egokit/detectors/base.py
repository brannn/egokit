"""Base classes and protocols for policy detectors."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol

from ..exceptions import DetectorError
from ..models import DetectionResult, Severity


class DetectorProtocol(Protocol):
    """Protocol defining the detector interface."""
    
    def run(self, content: str, file_path: Path) -> List[DetectionResult]:
        """Execute detector on file content.
        
        Args:
            content: File content to analyze
            file_path: Path to the file being analyzed
            
        Returns:
            List of detection results
        """
        ...


class DetectorBase(ABC):
    """Abstract base class for policy detectors."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize detector with optional configuration.
        
        Args:
            config: Detector-specific configuration
        """
        self.config = config or {}
        self.timeout_seconds = self.config.get("timeout_seconds", 30.0)
        self.max_file_size = self.config.get("max_file_size_bytes", 1024 * 1024)  # 1MB
    
    @abstractmethod
    def can_handle_file(self, file_path: Path) -> bool:
        """Check if this detector can analyze the given file.
        
        Args:
            file_path: Path to file to check
            
        Returns:
            True if detector can handle this file type
        """
        ...
    
    @abstractmethod
    def detect_violations(
        self, 
        content: str, 
        file_path: Path
    ) -> List[DetectionResult]:
        """Core detection logic - implement in subclasses.
        
        Args:
            content: File content to analyze
            file_path: Path to the file being analyzed
            
        Returns:
            List of detected violations
        """
        ...
    
    def run(self, content: str, file_path: Path) -> List[DetectionResult]:
        """Execute detector with safety checks and error handling.
        
        Args:
            content: File content to analyze
            file_path: Path to the file being analyzed
            
        Returns:
            List of detection results
            
        Raises:
            DetectorError: If detection fails critically
        """
        # Pre-flight checks
        if not self.can_handle_file(file_path):
            return []
        
        if len(content.encode('utf-8')) > self.max_file_size:
            return [
                DetectionResult(
                    rule="ENGINE-001",
                    level=Severity.WARNING,
                    message=f"File too large for analysis: {len(content)} bytes",
                    file_path=file_path,
                )
            ]
        
        # Execute with timeout protection
        start_time = time.time()
        try:
            results = self.detect_violations(content, file_path)
            
            # Verify execution time
            elapsed = time.time() - start_time
            if elapsed > self.timeout_seconds:
                return [
                    DetectionResult(
                        rule="ENGINE-002",
                        level=Severity.WARNING,
                        message=f"Detector timeout: {elapsed:.2f}s > {self.timeout_seconds}s",
                        file_path=file_path,
                    )
                ]
            
            return results
            
        except Exception as e:
            raise DetectorError(
                f"Detector execution failed: {e}",
                detector_name=self.__class__.__name__,
                file_path=str(file_path),
                details={"elapsed_time": time.time() - start_time}
            ) from e
    
    def _create_result(
        self,
        rule_id: str,
        severity: Severity,
        message: str,
        file_path: Path,
        line_number: Optional[int] = None,
        column: Optional[int] = None,
        span: Optional[tuple[int, int]] = None,
        suggestion: Optional[str] = None,
    ) -> DetectionResult:
        """Helper to create detection results with consistent formatting.
        
        Args:
            rule_id: Policy rule ID this violation relates to
            severity: Severity level of the violation
            message: Human-readable violation message
            file_path: Path to file containing violation
            line_number: Line number if applicable
            column: Column number if applicable
            span: Character span (start, end) if applicable
            suggestion: Suggested fix if available
            
        Returns:
            Formatted detection result
        """
        return DetectionResult(
            rule=rule_id,
            level=severity,
            message=message,
            file_path=file_path,
            line_number=line_number,
            column=column,
            span=span,
            suggestion=suggestion,
        )