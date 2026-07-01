import argparse
import asyncio
import os
import sys
from datetime import datetime, timezone
from urllib.parse import urlparse

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

from autoscan.enrichment.clearbit_client import ClearbitEnricher
from autoscan.enrichment.dns_check import check_domain
from autoscan.enrichment.scorer import CompanyScorer
from autoscan.enrichment.tech_stack import detect_tech_stack
from autoscan.shared.db.models import Company, Repository

def get_db_url() -> str:
    return os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///autoscan.db")

def extract_domain(url: str) -> str:
    if not url:
        return ""
    if not url.startswith("http"):
        url = f"https://{url}"
    try:
        parsed = urlparse(url)
        return parsed.netloc.replace("www.", "")
    except Exception:
        return ""

async def run_enrichment(min_github_score: float = 0.6, limit: int = 100, force_refresh: bool = False):
    db_url = get_db_url()
    engine = create_async_engine(db_url, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    
    clearbit_api_key = os.environ.get("CLEARBIT_API_KEY", "")
    enricher = ClearbitEnricher(api_key=clearbit_api_key)
    scorer = CompanyScorer()
    
    processed = 0

    try:
        async with async_session() as session:
            # Query companies that need enrichment
            query = select(Company).options(selectinload(Company.repositories)).where(
                Company.qualification_score >= min_github_score
            )
            
            if not force_refresh:
                query = query.where(Company.status == "QUALIFIED")
                
            query = query.limit(limit)
            
            result = await session.execute(query)
            companies = result.scalars().all()
            
            logger.info(f"Found {len(companies)} companies to enrich.")
            
            for company in companies:
                logger.info(f"Enriching {company.github_org}...")
                
                domain = extract_domain(company.website)
                
                # Fetch enrichment data concurrently
                clearbit_task = enricher.enrich_company(domain) if domain else asyncio.sleep(0, result={})
                dns_task = check_domain(domain) if domain else asyncio.sleep(0, result={})
                tech_task = detect_tech_stack(company.website) if company.website else asyncio.sleep(0, result=[])
                
                cb_data, dns_data, tech_data = await asyncio.gather(
                    clearbit_task, dns_task, tech_task
                )
                
                # Calculate Github metrics for scorer
                total_stars = sum(r.stars for r in company.repositories)
                
                days_since_commit = None
                now = datetime.now(timezone.utc)
                recent_commits = [
                    (now - r.last_commit_at.replace(tzinfo=timezone.utc)).days 
                    for r in company.repositories if r.last_commit_at
                ]
                if recent_commits:
                    days_since_commit = min(recent_commits)
                
                enrichment_dict = {
                    **cb_data,
                    **dns_data,
                    "tech_stack": tech_data,
                    "total_github_stars": total_stars,
                    "days_since_last_commit": days_since_commit,
                }
                
                # Score company
                score = scorer.score(company, enrichment_dict)
                
                # Update DB record
                company.employee_count = cb_data.get("employees") or company.employee_count
                company.funding_status = cb_data.get("funding_stage") or company.funding_status
                company.tech_stack = tech_data
                company.enrichment_score = score
                
                # Minimum viable enrichment score to proceed
                if score >= 0.4:
                    company.status = "ENRICHED"
                else:
                    company.status = "SKIP"
                    
                await session.commit()
                processed += 1
                
    finally:
        await engine.dispose()
        
    print(f"\n--- Enrichment Summary ---")
    print(f"Companies processed: {processed}")
    print(f"--------------------------\n")

def run_enrichment_sync(*args, **kwargs):
    """Synchronous wrapper for RQ worker execution."""
    asyncio.run(run_enrichment(*args, **kwargs))

def main():
    parser = argparse.ArgumentParser(description="AutoScan Enrichment Engine")
    parser.add_argument("--min-score", type=float, default=0.6, help="Minimum GitHub score to enrich")
    parser.add_argument("--limit", type=int, default=100, help="Maximum number of companies to enrich")
    parser.add_argument("--force-refresh", action="store_true", help="Re-enrich companies even if already processed")
    
    args = parser.parse_args()
    
    logger.remove()
    logger.add(sys.stderr, format="{time} {level} {message}", level="INFO")
    
    asyncio.run(run_enrichment(
        min_github_score=args.min_score,
        limit=args.limit,
        force_refresh=args.force_refresh
    ))

if __name__ == "__main__":
    main()
