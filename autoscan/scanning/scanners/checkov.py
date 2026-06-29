import asyncio
import json
import logging
from pathlib import Path
from typing import List

from autoscan.scanning.base_scanner import BaseScanner, Finding, Severity

logger = logging.getLogger(__name__)

class CheckovScanner(BaseScanner):
    name = "checkov"
    # Technically applies to IaC. We could list specific IaC files, but Checkov handles filtering mostly on its own.
    languages_supported = ["HCL", "Terraform", "CloudFormation", "Dockerfile", "Kubernetes", "YAML", "JSON"] 

    def _map_severity(self, checkov_severity: str) -> Severity:
        if not checkov_severity:
            return Severity.INFO
        mapping = {
            "CRITICAL": Severity.CRITICAL,
            "HIGH": Severity.HIGH,
            "MEDIUM": Severity.MEDIUM,
            "LOW": Severity.LOW,
        }
        return mapping.get(checkov_severity.upper(), Severity.INFO)

    async def run(self, repo_path: Path) -> List[Finding]:
        findings = []
        cmd = f"checkov -d {repo_path} -o json"
        
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
                logger.error(f"Checkov scanner timed out after {self.timeout_seconds}s for {repo_path}")
                return []
                
            if stderr:
                err_str = stderr.decode()
                if "command not found" in err_str:
                    logger.warning(f"Checkov tool not installed: {err_str.strip()}")
                    return []

            if not stdout:
                return []
                
            try:
                data = json.loads(stdout.decode())
                # Checkov might return a list of reports or a single report
                if isinstance(data, dict):
                    reports = [data]
                elif isinstance(data, list):
                    reports = data
                else:
                    reports = []

                for report in reports:
                    results = report.get("results", {}).get("failed_checks", [])
                    for result in results:
                        finding = Finding(
                            type="Misconfiguration",
                            severity=self._map_severity(result.get("severity")),
                            title=result.get("check_id", "Checkov Finding"),
                            description=result.get("check_name", ""),
                            file_path=result.get("file_path"),
                            line_no=result.get("file_line_range", [None])[0] if result.get("file_line_range") else None,
                            scanner_name=self.name,
                            confidence="High",
                            raw=result,
                        )
                        findings.append(finding)
            except json.JSONDecodeError:
                # Sometimes Checkov prints parsing errors before the JSON
                logger.error(f"Failed to parse JSON from Checkov output")
                    
        except Exception as e:
            logger.error(f"Error running Checkov: {e}")
            
        return findings
