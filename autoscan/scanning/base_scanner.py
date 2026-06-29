from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional, Any

class Severity(Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"

@dataclass
class Finding:
    type: str
    severity: Severity
    title: str
    description: Optional[str]
    file_path: Optional[str]
    line_no: Optional[int]
    scanner_name: str
    confidence: Optional[str] = None
    raw: Optional[Any] = None

class BaseScanner(ABC):
    name: str
    languages_supported: List[str]
    timeout_seconds: int = 300

    @abstractmethod
    async def run(self, repo_path: Path) -> List[Finding]:
        """
        Run the scanner on the given repository path.
        Returns a list of Findings.
        """
        pass

    def is_applicable(self, inventory: dict) -> bool:
        """
        Check if this scanner is applicable based on the languages_inventory.
        A return value of True means the scanner should be run.
        """
        # If no specific languages are required by the scanner, it applies to all.
        if not self.languages_supported:
            return True
            
        if not inventory:
            return False
            
        repo_languages = set(inventory.keys())
        # Check if there is any intersection between supported languages and repo languages
        return any(lang in repo_languages for lang in self.languages_supported)
