"""Policy validation orchestrator."""

from __future__ import annotations

import time
from pathlib import Path
from typing import List, Optional

from .detectors import DetectorLoader
from .exceptions import DetectorError
from .models import DetectionResult, PolicyRule, ValidationReport
from .registry import PolicyRegistry


class PolicyValidator:
    """Orchestrates policy detection and validation."""
    
    def __init__(
        self, 
        registry: PolicyRegistry,
        detector_loader: Optional[DetectorLoader] = None
    ) -> None:
        """Initialize validator with registry and detector loader.
        
        Args:
            registry: Policy registry instance
            detector_loader: Detector loader, defaults to built-in loader
        """
        self.registry = registry
        self.detector_loader = detector_loader or DetectorLoader()
    
    def validate_files(
        self, 
        file_paths: List[Path],
        scope_precedence: Optional[List[str]] = None
    ) -> ValidationReport:
        """Validate files against merged policy rules.
        
        Args:
            file_paths: Files to validate
            scope_precedence: Scope precedence for rule merging
            
        Returns:
            Complete validation report
        """
        start_time = time.time()
        
        if scope_precedence is None:
            scope_precedence = ["global"]
        
        # Load and merge policies
        charter = self.registry.load_charter()
        merged_rules = self.registry.merge_scope_rules(charter, scope_precedence)
        
        # Get unique detector names
        detector_names = list(set(rule.detector for rule in merged_rules))
        detectors = self.detector_loader.load_detectors(detector_names)
        
        violations: List[DetectionResult] = []
        files_checked: List[Path] = []
        
        for file_path in file_paths:
            if not file_path.exists():
                continue
            
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            
            files_checked.append(file_path)
            
            # Run all applicable detectors
            for detector_name, detector_class in detectors.items():
                try:
                    detector_instance = detector_class()
                    file_violations = detector_instance.run(content, file_path)
                    violations.extend(file_violations)
                except DetectorError:
                    # Skip detectors that fail
                    continue
        
        execution_time = time.time() - start_time
        
        # Determine if validation passed (no critical violations)
        passed = not any(
            v.level.value == "critical" for v in violations
        )
        
        return ValidationReport(
            passed=passed,
            violations=violations,
            files_checked=files_checked,
            detectors_run=list(detectors.keys()),
            execution_time=execution_time,
        )