import asyncio
import json
import logging
from pathlib import Path
from typing import List

from autoscan.scanning.base_scanner import BaseScanner, Finding, Severity

logger = logging.getLogger(__name__)

class SemgrepScanner(BaseScanner):
    name = "semgrep"
    languages_supported = []  # Semgrep supports many, we can let it run on all and it will figure it out

    def _map_severity(self, semgrep_severity: str) -> Severity:
        mapping = {
            "ERROR": Severity.HIGH,
            "WARNING": Severity.MEDIUM,
            "INFO": Severity.LOW,
        }
        return mapping.get(semgrep_severity.upper(), Severity.INFO)

    async def run(self, repo_path: Path) -> List[Finding]:
        findings = []
        cmd = f"semgrep --config=p/security-audit --json {repo_path}"
        
        try:
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=self.timeout_seconds
                )
            except asyncio.TimeoutError:
                process.kill()
                logger.error(f"Semgrep scanner timed out after {self.timeout_seconds}s for {repo_path}")
                return []
                
            if stderr:
                err_str = stderr.decode()
                if "command not found" in err_str:
                    logger.warning(f"Semgrep tool not installed: {err_str.strip()}")
                    return []
                # Semgrep prints progress and other non-error info to stderr

            if not stdout:
                return []
                
            try:
                data = json.loads(stdout.decode())
                for result in data.get("results", []):
                    extra = result.get("extra", {})
                    finding = Finding(
                        type="SAST",
                        severity=self._map_severity(extra.get("severity", "INFO")),
                        title=result.get("check_id", "Semgrep Finding"),
                        description=extra.get("message", ""),
                        file_path=result.get("path"),
                        line_no=result.get("start", {}).get("line"),
                        scanner_name=self.name,
                        confidence=extra.get("confidence", "Unknown"),
                        raw=result,
                    )
                    findings.append(finding)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse JSON from Semgrep output")
                    
        except Exception as e:
            logger.error(f"Error running Semgrep: {e}")
            
        return findings
