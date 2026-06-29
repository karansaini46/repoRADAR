import asyncio
import json
import logging
from pathlib import Path
from typing import List

from autoscan.scanning.base_scanner import BaseScanner, Finding, Severity

logger = logging.getLogger(__name__)

class BanditScanner(BaseScanner):
    name = "bandit"
    languages_supported = ["Python"]

    def _map_severity(self, bandit_severity: str) -> Severity:
        mapping = {
            "HIGH": Severity.HIGH,
            "MEDIUM": Severity.MEDIUM,
            "LOW": Severity.LOW,
        }
        return mapping.get(bandit_severity.upper(), Severity.INFO)

    async def run(self, repo_path: Path) -> List[Finding]:
        findings = []
        cmd = f"bandit -r {repo_path} -f json"
        
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
                logger.error(f"Bandit scanner timed out after {self.timeout_seconds}s for {repo_path}")
                return []
                
            if stderr:
                err_str = stderr.decode()
                if "command not found" in err_str:
                    logger.warning(f"Bandit tool not installed: {err_str.strip()}")
                    return []

            if not stdout:
                return []
                
            try:
                data = json.loads(stdout.decode())
                results = data.get("results", [])
                for result in results:
                    finding = Finding(
                        type="SAST",
                        severity=self._map_severity(result.get("issue_severity", "LOW")),
                        title=result.get("test_id", "Bandit Finding"),
                        description=result.get("issue_text", ""),
                        file_path=result.get("filename"),
                        line_no=result.get("line_number"),
                        scanner_name=self.name,
                        confidence=result.get("issue_confidence", "Unknown"),
                        raw=result,
                    )
                    findings.append(finding)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse JSON from Bandit output")
                    
        except Exception as e:
            logger.error(f"Error running Bandit: {e}")
            
        return findings
