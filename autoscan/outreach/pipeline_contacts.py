import asyncio
import logging
import argparse
import os
from sqlalchemy import select

from autoscan.shared.db.database import get_db, SessionLocal
from autoscan.shared.db.models import Company, Repository, Contact
from autoscan.outreach.contact_discovery import ContactDiscovery

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def _run_contact_discovery_async(company_id=None, limit=20):
    github_token = os.getenv("GITHUB_TOKEN")
    hunter_key = os.getenv("HUNTER_API_KEY")
    
    if not github_token:
        logger.error("GITHUB_TOKEN environment variable is required.")
        return
        
    discovery = ContactDiscovery(github_token=github_token, hunter_key=hunter_key)
    
    with SessionLocal() as db:
        query = select(Company).where(Company.status == 'report_ready')
        if company_id:
            query = query.where(Company.id == company_id)
        query = query.limit(limit)
        
        result = db.execute(query)
        companies = result.scalars().all()
        
        logger.info(f"Found {len(companies)} companies for contact discovery.")
        
        for company in companies:
            logger.info(f"Starting contact discovery for {company.name or company.github_org} (ID: {company.id})")
            try:
                repos = db.query(Repository).filter(Repository.company_id == company.id).all()
                
                contacts = await discovery.discover(company, repos)
                
                if contacts:
                    # Save to DB
                    db.add_all(contacts)
                    company.status = 'contacts_found'
                    logger.info(f"Found and saved {len(contacts)} contacts for {company.name or company.github_org}.")
                else:
                    company.status = 'no_contacts'
                    logger.info(f"No contacts found for {company.name or company.github_org}.")
                    
                db.commit()
            except Exception as e:
                logger.error(f"Failed to discover contacts for company {company.id}: {e}")
                db.rollback()

def run_contact_discovery(company_id=None, limit=20):
    """
    Synchronous wrapper to run the async contact discovery pipeline.
    """
    asyncio.run(_run_contact_discovery_async(company_id, limit))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Contact Discovery Pipeline")
    parser.add_argument("--company-id", type=int, help="Discover contacts for a specific company ID")
    parser.add_argument("--limit", type=int, default=20, help="Maximum number of companies to process")
    
    args = parser.parse_args()
    
    logger.info("Starting Contact Discovery pipeline...")
    run_contact_discovery(company_id=args.company_id, limit=args.limit)
    logger.info("Contact Discovery pipeline finished.")
