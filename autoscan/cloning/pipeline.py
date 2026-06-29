import argparse
import asyncio
import os
import sys

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

from autoscan.cloning.cloner import RepoCloner
from autoscan.cloning.inventory import RepoInventory
from autoscan.cloning.cleanup import cleanup_old_clones
from autoscan.shared.db.models import Company, Repository

def get_db_url() -> str:
    return os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///autoscan.db")

async def run_cloning(company_id: int = None, limit: int = 20):
    db_url = get_db_url()
    engine = create_async_engine(db_url, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    
    cloner = RepoCloner()
    inventory = RepoInventory()
    
    processed = 0

    try:
        async with async_session() as session:
            # 1. Optional cleanup of old clones
            # Just to keep disk usage in check before cloning more
            await cleanup_old_clones(session, str(cloner.base_dir), max_age_hours=48)
            
            # 2. Select repositories to clone
            query = select(Repository).join(Company).where(
                Company.status == "ENRICHED",
                (Repository.status == "NEW") | (Repository.status == None)
            )
            
            if company_id:
                query = query.where(Company.id == company_id)
                
            query = query.limit(limit)
            
            result = await session.execute(query)
            repos_to_clone = result.scalars().all()
            
            if not repos_to_clone:
                logger.info("No new repositories found for cloning.")
                return
                
            logger.info(f"Found {len(repos_to_clone)} repositories to clone.")
            
            # 3. Clone concurrently
            cloned_paths = await cloner.clone_many(repos_to_clone, max_concurrent=5)
            
            # 4. Run inventory and update DB
            for repo in repos_to_clone:
                if repo.id in cloned_paths:
                    local_path = cloned_paths[repo.id]
                    
                    logger.info(f"Running inventory for {repo.full_name}...")
                    
                    # Run inventory synchronously since it uses os.walk
                    # For huge repos this could be put in a ThreadPoolExecutor, 
                    # but for now we run it directly.
                    try:
                        scan_result = inventory.scan(local_path)
                        
                        repo.local_path = str(local_path.absolute())
                        repo.file_count = scan_result["file_count"]
                        repo.size_mb = scan_result["total_size_mb"]
                        repo.languages_inventory = scan_result["languages"]
                        repo.has_secrets_risk = scan_result["secret_patterns_present"]
                        repo.status = "CLONED"
                        
                        processed += 1
                    except Exception as e:
                        logger.error(f"Error analyzing inventory for {repo.full_name}: {e}")
                        repo.status = "FAILED"
                else:
                    repo.status = "FAILED"
                    
            await session.commit()
            
    finally:
        await engine.dispose()
        
    print(f"\n--- Cloning Summary ---")
    print(f"Repositories processed: {processed} / {len(repos_to_clone)}")
    print(f"-----------------------\n")


def main():
    parser = argparse.ArgumentParser(description="AutoScan Cloning & Inventory Engine")
    parser.add_argument("--limit", type=int, default=20, help="Maximum number of repositories to clone")
    parser.add_argument("--company-id", type=int, default=None, help="Specific company ID to clone repos for")
    
    args = parser.parse_args()
    
    logger.remove()
    logger.add(sys.stderr, format="{time} {level} {message}", level="INFO")
    
    asyncio.run(run_cloning(
        company_id=args.company_id,
        limit=args.limit
    ))

if __name__ == "__main__":
    main()
