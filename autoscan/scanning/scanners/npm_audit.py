import asyncio
import json
import logging
import os
from pathlib import Path
from typing import List

from autoscan.scanning.base_scanner import BaseScanner, Finding, Severity

logger = logging.getLogger(__name__)

class NpmAuditScanner(BaseScanner):
    name = "npm_audit"
    languages_supported = ["JavaScript", "TypeScript"]

    def _map_severity(self, npm_severity: str) -> Severity:
        mapping = {
            "critical": Severity.CRITICAL,
            "high": Severity.HIGH,
            "moderate": Severity.MEDIUM,
            "low": Severity.LOW,
            "info": Severity.INFO,
        }
        return mapping.get(npm_severity.lower(), Severity.INFO)

    async def run(self, repo_path: Path) -> List[Finding]:
        findings = []
        # npm audit must run in a directory with package.json
        # We should check if package.json exists
        if not (repo_path / "package.json").exists():
            return findings

        cmd = "npm audit --json"
        
        try:
            # We must set cwd to the repo path for npm audit
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(repo_path)
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=self.timeout_seconds
                )
            except asyncio.TimeoutError:
                process.kill()
                logger.error(f"npm audit scanner timed out after {self.timeout_seconds}s for {repo_path}")
                return []
                
            if stderr:
                err_str = stderr.decode()
                if "command not found" in err_str:
                    logger.warning(f"npm tool not installed: {err_str.strip()}")
                    return []

            if not stdout:
                return []
                
            try:
                data = json.loads(stdout.decode())
                # Handle both v1 and v2 formats loosely
                vulnerabilities = data.get("vulnerabilities", {})
                if isinstance(vulnerabilities, dict):
                    # v2 format
                    for pkg_name, vuln in vulnerabilities.items():
                        finding = Finding(
                            type="SCA",
                            severity=self._map_severity(vuln.get("severity", "info")),
                            title=f"Vulnerability in {pkg_name}",
                            description=f"Package {pkg_name} has vulnerabilities via {', '.join(vuln.get('via', []))[:100]}",
                            file_path="package.json",
                            line_no=None,
                            scanner_name=self.name,
                            confidence="High",
                            raw=vuln,
                        )
                        findings.append(finding)
                elif isinstance(data.get("advisories"), dict):
                    # v1 format
                    for adv_id, adv in data["advisories"].items():
                        finding = Finding(
                            type="SCA",
                            severity=self._map_severity(adv.get("severity", "info")),
                            title=adv.get("title", f"Vulnerability {adv_id}"),
                            description=adv.get("overview", ""),
                            file_path="package.json",
                            line_no=None,
                            scanner_name=self.name,
                            confidence="High",
                            raw=adv,
                        )
                        findings.append(finding)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse JSON from npm audit output")
                    
        except Exception as e:
            logger.error(f"Error running npm audit: {e}")
            
        return findings
