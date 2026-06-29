import asyncio
import logging
from pathlib import Path
from typing import List

from autoscan.shared.db.models import Repository
from autoscan.scanning.base_scanner import BaseScanner, Finding
from autoscan.scanning.deduplicator import deduplicate, _SEVERITY_WEIGHT

logger = logging.getLogger(__name__)

class ScanOrchestrator:
    def __init__(self, scanners: List[BaseScanner]):
        self.scanners = scanners

    async def scan(self, repo: Repository, inventory: dict) -> List[Finding]:
        """
        Runs all applicable scanners in parallel.
        Deduplicates results.
        Returns sorted findings (CRITICAL first).
        """
        if not repo.local_path:
            logger.error(f"Repository {repo.full_name} has no local_path set.")
            return []
            
        repo_path = Path(repo.local_path)
        if not repo_path.exists() or not repo_path.is_dir():
            logger.error(f"Repository path {repo_path} does not exist or is not a directory.")
            return []

        applicable_scanners = [s for s in self.scanners if s.is_applicable(inventory)]
        if not applicable_scanners:
            logger.info(f"No applicable scanners found for {repo.full_name} based on inventory.")
            return []

        logger.info(f"Running {len(applicable_scanners)} scanners for {repo.full_name}")
        
        # Run all applicable scanners concurrently
        tasks = [scanner.run(repo_path) for scanner in applicable_scanners]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_findings = []
        for i, result in enumerate(results):
            scanner_name = applicable_scanners[i].name
            if isinstance(result, Exception):
                logger.error(f"Scanner {scanner_name} raised an exception: {result}")
            else:
                logger.info(f"Scanner {scanner_name} returned {len(result)} findings.")
                all_findings.extend(result)

        # Deduplicate
        deduped = deduplicate(all_findings)
        
        # Sort findings (CRITICAL first). We use the _SEVERITY_WEIGHT defined in deduplicator
        deduped.sort(key=lambda x: _SEVERITY_WEIGHT.get(x.severity, 0), reverse=True)
        
        return deduped
