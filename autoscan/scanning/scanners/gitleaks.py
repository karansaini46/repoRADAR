import asyncio
import json
import logging
from pathlib import Path
from typing import List

from autoscan.scanning.base_scanner import BaseScanner, Finding, Severity

logger = logging.getLogger(__name__)

class GitleaksScanner(BaseScanner):
    name = "gitleaks"
    languages_supported = []  # All languages

    async def run(self, repo_path: Path) -> List[Finding]:
        findings = []
        # Need to use a temporary file for gitleaks json output, or stdout. 
        # Newer versions of gitleaks can print to stdout using --report-path /dev/stdout or similar,
        # but the prompt says: gitleaks detect --source {path} --report-format json
        # Let's specify --report-path to a temp file and read it, or try to get it from stdout if supported.
        # Often `gitleaks detect --no-git --source {path} -v --report-format json --report-path {tmp}`
        # Let's assume the basic command logs json to a file. We will use a temp file.
        import tempfile
        import os
        
        fd, temp_path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        
        cmd = f"gitleaks detect --no-git --source {repo_path} --report-format json --report-path {temp_path}"
        
        try:
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            try:
                # Gitleaks exits with 1 if leaks are found
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=self.timeout_seconds
                )
            except asyncio.TimeoutError:
                process.kill()
                logger.error(f"Gitleaks scanner timed out after {self.timeout_seconds}s for {repo_path}")
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                return []
                
            if stderr:
                err_str = stderr.decode()
                if "command not found" in err_str:
                    logger.warning(f"Gitleaks tool not installed: {err_str.strip()}")
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                    return []

            if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
                with open(temp_path, 'r') as f:
                    try:
                        data = json.load(f)
                        for leak in data:
                            finding = Finding(
                                type="Hardcoded Secret",
                                severity=Severity.CRITICAL,
                                title=leak.get("Description", "Gitleaks Secret"),
                                description=f"Rule: {leak.get('RuleID')}, Match: {leak.get('Match')}",
                                file_path=leak.get("File"),
                                line_no=leak.get("StartLine"),
                                scanner_name=self.name,
                                confidence="High",
                                raw=leak,
                            )
                            findings.append(finding)
                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse JSON from Gitleaks output")
                        
        except Exception as e:
            logger.error(f"Error running Gitleaks: {e}")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            
        return findings
