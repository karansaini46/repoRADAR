import asyncio
import json
import logging
from pathlib import Path
from typing import List

from autoscan.scanning.base_scanner import BaseScanner, Finding, Severity

logger = logging.getLogger(__name__)

class PipAuditScanner(BaseScanner):
    name = "pip_audit"
    languages_supported = ["Python"]

    async def run(self, repo_path: Path) -> List[Finding]:
        findings = []
        cmd = f"pip-audit --path {repo_path} -f json"
        
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
                logger.error(f"pip-audit scanner timed out after {self.timeout_seconds}s for {repo_path}")
                return []
                
            if stderr:
                err_str = stderr.decode()
                if "command not found" in err_str:
                    logger.warning(f"pip-audit tool not installed: {err_str.strip()}")
                    return []

            if not stdout:
                return []
                
            try:
                data = json.loads(stdout.decode())
                # pip-audit returns a list of dependencies, some with vulns
                for dep in data:
                    vulns = dep.get("vulns", [])
                    for vuln in vulns:
                        finding = Finding(
                            type="SCA",
                            severity=Severity.HIGH, # pip-audit doesn't strictly provide severity in base json without osv, defaulting to high
                            title=vuln.get("id", "Dependency Vulnerability"),
                            description=f"Package {dep.get('name')} {dep.get('version')} has {vuln.get('id')}",
                            file_path=None, # It scans requirements.txt/pyproject.toml, path not explicitly in vuln
                            line_no=None,
                            scanner_name=self.name,
                            confidence="High",
                            raw=vuln,
                        )
                        findings.append(finding)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse JSON from pip-audit output")
                    
        except Exception as e:
            logger.error(f"Error running pip-audit: {e}")
            
        return findings
