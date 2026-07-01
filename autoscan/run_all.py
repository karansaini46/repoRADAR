import asyncio
import os
import sys

from loguru import logger
from autoscan.cloning.pipeline import run_cloning
from autoscan.scanning.pipeline import run_scanning
from autoscan.ai_layer.pipeline import run_verification
from autoscan.impact.pipeline import run_impact_calculation
from autoscan.reports.pipeline import run_report_generation
from autoscan.outreach.pipeline_contacts import run_contact_discovery
from autoscan.outreach.pipeline_email import run_outreach
from autoscan.shared.db.database import SessionLocal
from autoscan.shared.db.models import Company

async def main():
    logger.remove()
    logger.add(sys.stderr, format="{time} {level} {message}", level="INFO")
    
    limit = 2
    logger.info(f"Starting FULL PIPELINE test for {limit} companies...")
    
    logger.info("1. Manually setting first 2 companies to ENRICHED...")
    db = SessionLocal()
    companies = db.query(Company).filter(Company.status == "QUALIFIED").limit(limit).all()
    for c in companies:
        c.status = "ENRICHED"
    db.commit()
    db.close()
    
    logger.info("2. Running Cloning...")
    await run_cloning(limit=limit*5) # repos per company
    
    # Sync functions below, we can run them in a thread pool but since we're in async main, 
    # we can just use asyncio.to_thread
    
    logger.info("3. Running Scanning...")
    await asyncio.to_thread(run_scanning, None, limit*5)
    
    logger.info("4. Running AI Verification...")
    await asyncio.to_thread(run_verification, None, limit*5)
    
    logger.info("5. Running Impact Calculation...")
    await asyncio.to_thread(run_impact_calculation)
    
    logger.info("6. Running Report Generation...")
    await asyncio.to_thread(run_report_generation, None, limit)
    
    logger.info("7. Running Contact Discovery...")
    await asyncio.to_thread(run_contact_discovery, None, limit)
    
    logger.info("8. Running Outreach (DRY RUN)...")
    await asyncio.to_thread(run_outreach, None, limit, True) # dry_run=True so we don't actually send emails
    
    logger.info("PIPELINE COMPLETE.")

if __name__ == "__main__":
    asyncio.run(main())
