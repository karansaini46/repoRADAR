import asyncio
import json
import logging
from pathlib import Path
from typing import List

from autoscan.scanning.base_scanner import BaseScanner, Finding, Severity

logger = logging.getLogger(__name__)

class TrivyScanner(BaseScanner):
    name = "trivy"
    languages_supported = []  # Trivy supports many languages via FS scan

    def _map_severity(self, trivy_severity: str) -> Severity:
        mapping = {
            "CRITICAL": Severity.CRITICAL,
            "HIGH": Severity.HIGH,
            "MEDIUM": Severity.MEDIUM,
            "LOW": Severity.LOW,
            "UNKNOWN": Severity.INFO,
        }
        return mapping.get(trivy_severity.upper(), Severity.INFO)

    async def run(self, repo_path: Path) -> List[Finding]:
        findings = []
        cmd = f"trivy fs --format json {repo_path}"
        
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
                logger.error(f"Trivy scanner timed out after {self.timeout_seconds}s for {repo_path}")
                return []
                
            if stderr:
                err_str = stderr.decode()
                if "command not found" in err_str:
                    logger.warning(f"Trivy tool not installed: {err_str.strip()}")
                    return []

            if not stdout:
                return []
                
            try:
                data = json.loads(stdout.decode())
                results = data.get("Results", [])
                for result in results:
                    target = result.get("Target", "")
                    vulnerabilities = result.get("Vulnerabilities", [])
                    for vuln in vulnerabilities:
                        finding = Finding(
                            type="Vulnerability",
                            severity=self._map_severity(vuln.get("Severity", "UNKNOWN")),
                            title=vuln.get("VulnerabilityID", "Unknown Vuln"),
                            description=vuln.get("Title", vuln.get("Description", "")),
                            file_path=target,
                            line_no=None, # Trivy FS might not always give line numbers
                            scanner_name=self.name,
                            confidence="High", # Usually high for CVEs
                            raw=vuln,
                        )
                        findings.append(finding)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse JSON from Trivy output")
                    
        except Exception as e:
            logger.error(f"Error running Trivy: {e}")
            
        return findings
