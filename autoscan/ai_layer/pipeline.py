import asyncio
import logging
import argparse
from sqlalchemy import select

from autoscan.shared.db.database import get_db, SessionLocal
from autoscan.shared.db.models import Repository
from autoscan.ai_layer.batch_processor import process_repo_findings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def _run_verification_async(company_id=None, limit=5):
    with SessionLocal() as db:
        query = select(Repository).where(Repository.status == 'scanned')
        if company_id:
            query = query.where(Repository.company_id == company_id)
        query = query.limit(limit)
        
        result = db.execute(query)
        repos = result.scalars().all()
        
        logger.info(f"Found {len(repos)} repositories awaiting verification.")
        
        for repo in repos:
            logger.info(f"Starting verification for {repo.full_name} (ID: {repo.id})")
            try:
                await process_repo_findings(repo.id)
                repo.status = 'verified'
                db.commit()
                logger.info(f"Repository {repo.full_name} status updated to 'verified'.")
            except Exception as e:
                logger.error(f"Failed to process verification for {repo.full_name}: {e}")
                repo.status = 'verification_failed'
                db.commit()

def run_verification(company_id=None, limit=5):
    """
    Synchronous wrapper to run the async verification pipeline.
    """
    asyncio.run(_run_verification_async(company_id, limit))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run AI Verification Pipeline")
    parser.add_argument("--company-id", type=int, help="Verify repositories for a specific company ID")
    parser.add_argument("--limit", type=int, default=5, help="Maximum number of repositories to process")
    
    args = parser.parse_args()
    
    logger.info("Starting AI Verification pipeline...")
    run_verification(company_id=args.company_id, limit=args.limit)
    logger.info("AI Verification pipeline finished.")
