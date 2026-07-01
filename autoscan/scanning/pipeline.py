import asyncio
import logging
from datetime import datetime
from sqlalchemy import select

from autoscan.shared.db.database import get_db, SessionLocal
from autoscan.shared.db.models import Repository, Finding as DBFinding
from autoscan.scanning.orchestrator import ScanOrchestrator
from autoscan.scanning.scanners.trufflehog import TruffleHogScanner
from autoscan.scanning.scanners.semgrep import SemgrepScanner
from autoscan.scanning.scanners.trivy import TrivyScanner
from autoscan.scanning.scanners.bandit import BanditScanner
from autoscan.scanning.scanners.gitleaks import GitleaksScanner
from autoscan.scanning.scanners.checkov import CheckovScanner
from autoscan.scanning.scanners.pip_audit import PipAuditScanner
from autoscan.scanning.scanners.npm_audit import NpmAuditScanner

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def _run_scanning_async(company_id=None, limit=10):
    scanners = [
        TruffleHogScanner(),
        SemgrepScanner(),
        TrivyScanner(),
        BanditScanner(),
        GitleaksScanner(),
        CheckovScanner(),
        PipAuditScanner(),
        NpmAuditScanner()
    ]
    orchestrator = ScanOrchestrator(scanners)
    
    with SessionLocal() as db:
        # Statuses in the database are stored in uppercase (e.g. 'NEW', 'CLONED', 'SCANNED')
        query = select(Repository).where(Repository.status == 'CLONED')
        if company_id:
            query = query.where(Repository.company_id == company_id)
        query = query.limit(limit)
        
        result = db.execute(query)
        repos = result.scalars().all()
        
        logger.info(f"Found {len(repos)} repositories to scan.")
        
        for repo in repos:
            logger.info(f"Scanning repository {repo.full_name}")
            inventory = repo.languages_inventory or {}
            
            try:
                # Run the scan orchestrator
                findings = await orchestrator.scan(repo, inventory)
                
                # Delete any existing findings for this repo to avoid duplicates on re-scan
                # The relationship has cascade delete, but if we just append it might duplicate
                db.query(DBFinding).filter(DBFinding.repository_id == repo.id).delete()
                
                # Map and insert new findings
                db_findings = []
                for f in findings:
                    db_find = DBFinding(
                        repository_id=repo.id,
                        type=f.type,
                        severity=f.severity.value,
                        title=f.title,
                        description=f.description,
                        file_path=f.file_path,
                        line_no=f.line_no,
                        scanner_name=f.scanner_name,
                        confidence=f.confidence,
                        raw_data=f.raw,
                    )
                    db_findings.append(db_find)
                    
                if db_findings:
                    db.add_all(db_findings)
                    
                repo.status = 'scanned'
                repo.finding_count = len(findings)
                # timezone=True implies UTC if standard setup
                from datetime import timezone
                repo.last_scanned_at = datetime.now(timezone.utc)
                
                db.commit()
                logger.info(f"Saved {len(findings)} findings for {repo.full_name}. Status updated to scanned.")
            except Exception as e:
                logger.error(f"Failed to scan repository {repo.full_name}: {e}")
                repo.status = 'scan_failed'
                db.commit()

def run_scanning(company_id=None, limit=10):
    """
    Synchronous wrapper to run the async scanning pipeline.
    """
    asyncio.run(_run_scanning_async(company_id, limit))

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run Multi-Scanner Pipeline")
    parser.add_argument("--company-id", type=int, help="Scan repositories for a specific company ID")
    parser.add_argument("--limit", type=int, default=10, help="Maximum number of repositories to scan")
    
    args = parser.parse_args()
    
    logger.info("Starting scanning pipeline...")
    run_scanning(company_id=args.company_id, limit=args.limit)
    logger.info("Scanning pipeline finished.")
