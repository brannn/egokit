"""Dynamic detector loading and management."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Dict, List, Optional, Type

from ..exceptions import DetectorError
from .base import DetectorBase, DetectorProtocol


class DetectorLoader:
    """Dynamically loads and manages policy detectors."""
    
    def __init__(self, detectors_path: Optional[Path] = None) -> None:
        """Initialize detector loader.
        
        Args:
            detectors_path: Path to detectors directory, defaults to built-in detectors
        """
        if detectors_path is None:
            self.detectors_path = Path(__file__).parent / "builtin"
        else:
            self.detectors_path = Path(detectors_path)
        
        self._detector_cache: Dict[str, Type[DetectorProtocol]] = {}
    
    def load_detector(self, detector_name: str) -> Type[DetectorProtocol]:
        """Load a detector by name.
        
        Args:
            detector_name: Name of detector to load (e.g., 'secret.regex.v1')
            
        Returns:
            Detector class
            
        Raises:
            DetectorError: If detector cannot be loaded
        """
        if detector_name in self._detector_cache:
            return self._detector_cache[detector_name]
        
        detector_path = self.detectors_path / f"{detector_name}.py"
        if not detector_path.exists():
            raise DetectorError(
                f"Detector not found: {detector_name}",
                detector_name=detector_name,
                details={"expected_path": str(detector_path)}
            )
        
        try:
            spec = importlib.util.spec_from_file_location(detector_name, detector_path)
            if spec is None or spec.loader is None:
                raise DetectorError(
                    f"Failed to create module spec for {detector_name}",
                    detector_name=detector_name
                )
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Look for detector class or function
            detector_class = None
            if hasattr(module, "Detector"):
                detector_class = module.Detector
            elif hasattr(module, "run"):
                # Legacy function-based detector - wrap it
                detector_class = self._wrap_function_detector(module.run, detector_name)
            else:
                raise DetectorError(
                    f"Detector {detector_name} must define 'Detector' class or 'run' function",
                    detector_name=detector_name
                )
            
            self._detector_cache[detector_name] = detector_class
            return detector_class
            
        except ImportError as e:
            raise DetectorError(
                f"Failed to import detector {detector_name}: {e}",
                detector_name=detector_name
            ) from e
        except Exception as e:
            raise DetectorError(
                f"Error loading detector {detector_name}: {e}",
                detector_name=detector_name
            ) from e
    
    def load_detectors(self, detector_names: List[str]) -> Dict[str, Type[DetectorProtocol]]:
        """Load multiple detectors.
        
        Args:
            detector_names: List of detector names to load
            
        Returns:
            Dictionary mapping detector names to classes
        """
        detectors = {}
        for name in detector_names:
            try:
                detectors[name] = self.load_detector(name)
            except DetectorError:
                # Skip detectors that fail to load
                continue
        
        return detectors
    
    def discover_detectors(self) -> List[str]:
        """Discover all available detectors in the detectors path.
        
        Returns:
            List of detector names
        """
        if not self.detectors_path.exists():
            return []
        
        detector_names = []
        for py_file in self.detectors_path.glob("*.py"):
            if py_file.name != "__init__.py":
                detector_name = py_file.stem
                detector_names.append(detector_name)
        
        return sorted(detector_names)
    
    def _wrap_function_detector(
        self, 
        run_func: callable, 
        detector_name: str
    ) -> Type[DetectorProtocol]:
        """Wrap a legacy function-based detector as a class.
        
        Args:
            run_func: The detector run function
            detector_name: Name of the detector
            
        Returns:
            Wrapped detector class
        """
        from ..models import DetectionResult, Severity
        
        class FunctionDetectorWrapper(DetectorBase):
            """Wrapper for function-based detectors."""
            
            def can_handle_file(self, file_path: Path) -> bool:
                """Always return True for function-based detectors."""
                return True
            
            def detect_violations(
                self, 
                content: str, 
                file_path: Path
            ) -> List[DetectionResult]:
                """Execute wrapped function and convert results."""
                try:
                    results = run_func(content, str(file_path))
                    
                    # Convert legacy format to DetectionResult objects
                    detection_results = []
                    for result in results:
                        if isinstance(result, dict):
                            detection_results.append(
                                DetectionResult(
                                    rule=result.get("rule", "UNKNOWN"),
                                    level=Severity(result.get("level", "warning")),
                                    message=result.get("msg", "Policy violation"),
                                    file_path=file_path,
                                    span=result.get("span"),
                                )
                            )
                    
                    return detection_results
                    
                except Exception as e:
                    raise DetectorError(
                        f"Function detector {detector_name} failed: {e}",
                        detector_name=detector_name,
                        file_path=str(file_path)
                    ) from e
        
        return FunctionDetectorWrapper