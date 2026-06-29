import asyncio
import json
import logging
from pathlib import Path
from typing import List

from autoscan.scanning.base_scanner import BaseScanner, Finding, Severity

logger = logging.getLogger(__name__)

class TruffleHogScanner(BaseScanner):
    name = "trufflehog"
    languages_supported = []  # Empty means all languages (or language agnostic)

    async def run(self, repo_path: Path) -> List[Finding]:
        findings = []
        cmd = f"trufflehog filesystem {repo_path} --json --no-verification"
        
        try:
            # Note: trufflehog exits with non-zero code if it finds secrets
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
                logger.error(f"TruffleHog scanner timed out after {self.timeout_seconds}s for {repo_path}")
                return []
                
            if stderr:
                err_str = stderr.decode()
                # TruffleHog might print some non-error warnings to stderr
                if "command not found" in err_str or "no such file or directory" in err_str.lower():
                    logger.warning(f"Trufflehog tool not installed or accessible: {err_str.strip()}")
                    return []

            if not stdout:
                return []
                
            for line in stdout.decode().strip().split('\n'):
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    # Example format structure from TruffleHog (structure may vary based on version, assuming generic structure)
                    source_metadata = data.get("SourceMetadata", {}).get("Data", {}).get("Filesystem", {})
                    file_path = source_metadata.get("file", "")
                    
                    finding = Finding(
                        type="Hardcoded Secret",
                        severity=Severity.CRITICAL,  # Secrets are generally critical
                        title=f"Secret found: {data.get('DetectorName', 'Unknown')}",
                        description=f"Raw secret found: {data.get('Raw', '')[:50]}...",
                        file_path=file_path,
                        line_no=source_metadata.get("line", None),
                        scanner_name=self.name,
                        confidence="High",
                        raw=data,
                    )
                    findings.append(finding)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse JSON from TruffleHog: {line}")
                    
        except Exception as e:
            logger.error(f"Error running TruffleHog: {e}")
            
        return findings
