"""Secret detection using regex patterns."""

import re
from pathlib import Path
from typing import List

from ...models import DetectionResult, Severity
from ..base import DetectorBase


class Detector(DetectorBase):
    """Detects potential secrets in source code using regex patterns."""
    
    # Common secret patterns
    SECRET_PATTERNS = [
        # API keys
        (r"(?i)(api[_-]?key|apikey)\s*[=:]\s*['\"][a-z0-9_\-]{12,}['\"]", "API key"),
        # JWT tokens  
        (r"(?i)(jwt|token)\s*[=:]\s*['\"]ey[a-z0-9_\-]+['\"]", "JWT token"),
        # AWS keys
        (r"(?i)(aws[_-]?access[_-]?key|aws[_-]?secret)\s*[=:]\s*['\"][a-z0-9/+=]{20,}['\"]", "AWS key"),
        # Generic secrets
        (r"(?i)(secret|password|passwd)\s*[=:]\s*['\"][a-z0-9_\-@#$%^&*!]{8,}['\"]", "Secret/password"),
        # Database URLs with credentials
        (r"(?i)(database[_-]?url|db[_-]?url)\s*[=:]\s*['\"][^'\"]*://[^'\"]*:[^'\"]*@[^'\"]*['\"]", "Database URL with credentials"),
    ]
    
    def can_handle_file(self, file_path: Path) -> bool:
        """Check if this detector can analyze the given file."""
        # Skip binary files and common non-source extensions
        skip_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.ico', '.pdf', '.zip', '.tar', '.gz'}
        return file_path.suffix.lower() not in skip_extensions
    
    def detect_violations(
        self, 
        content: str, 
        file_path: Path
    ) -> List[DetectionResult]:
        """Detect potential secrets in file content."""
        violations = []
        
        for pattern, secret_type in self.SECRET_PATTERNS:
            for match in re.finditer(pattern, content):
                # Get line number for better reporting
                line_number = content[:match.start()].count('\n') + 1
                
                # Extract matched content (but redact for security)
                matched_text = match.group(0)
                if '=' in matched_text:
                    var_part, _ = matched_text.split('=', 1)
                    redacted = f"{var_part.strip()} = '[REDACTED]'"
                else:
                    redacted = "[REDACTED SECRET]"
                
                violations.append(
                    self._create_result(
                        rule_id="SEC-001",
                        severity=Severity.CRITICAL,
                        message=f"Potential {secret_type.lower()} detected: {redacted}",
                        file_path=file_path,
                        line_number=line_number,
                        span=match.span(),
                        suggestion="Use environment variables or secure credential storage"
                    )
                )
        
        return violations