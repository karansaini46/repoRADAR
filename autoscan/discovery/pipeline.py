import argparse
import asyncio
import os
import sys
from datetime import datetime, timezone
from typing import List, Optional

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from autoscan.discovery.github_search import GitHubSearcher
from autoscan.discovery.org_filter import OrgFilter
from autoscan.shared.db.models import Base, Company, DiscoveryState, Repository

def get_db_url() -> str:
    """Get the database URL from environment, defaulting to an async sqlite for testing if none provided."""
    return os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///autoscan.db")

async def init_db(engine):
    """Initialize the database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def run_discovery(
    languages: List[str] = None,
    min_score: float = 0.6,
    limit: Optional[int] = None
):
    if languages is None:
        languages = ["python", "typescript", "go", "java"]
        
    github_token = os.environ.get("GITHUB_TOKEN")
    if not github_token:
        logger.error("GITHUB_TOKEN environment variable is not set.")
        sys.exit(1)

    db_url = get_db_url()
    engine = create_async_engine(db_url, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    
    await init_db(engine)

    searcher = GitHubSearcher(token=github_token)
    org_filter = OrgFilter()
    
    total_orgs_found = 0
    total_qualified = 0
    total_repos_saved = 0

    try:
        async with async_session() as session:
            for language in languages:
                if limit and total_qualified >= limit:
                    break

                # Get pagination state
                result = await session.execute(
                    select(DiscoveryState).where(DiscoveryState.language == language)
                )
                state = result.scalars().first()
                
                if not state:
                    state = DiscoveryState(language=language, last_cursor="1")
                    session.add(state)
                    await session.commit()
                    
                page = int(state.last_cursor) if state.last_cursor else 1
                
                logger.info(f"Starting search for language: {language} from page: {page}")
                
                has_next_page = True
                while has_next_page:
                    if limit and total_qualified >= limit:
                        break
                        
                    try:
                        repos, has_next_page = await searcher.search_repos(
                            query="is:public", min_stars=50, language=language, page=page
                        )
                    except Exception as e:
                        logger.error(f"Error searching repos: {e}")
                        break
                        
                    if not repos:
                        break

                    # Group repos by owner
                    repos_by_owner = {}
                    for repo in repos:
                        owner_login = repo.get("owner", {}).get("login")
                        if not owner_login:
                            continue
                        if owner_login not in repos_by_owner:
                            repos_by_owner[owner_login] = []
                        repos_by_owner[owner_login].append(repo)

                    for owner_login, owner_repos in repos_by_owner.items():
                        if limit and total_qualified >= limit:
                            break
                            
                        total_orgs_found += 1
                        
                        # Check if company already exists
                        existing_company = await session.execute(
                            select(Company).where(Company.github_org == owner_login)
                        )
                        if existing_company.scalars().first():
                            continue

                        # Get org metadata
                        org_data = await searcher.get_org_metadata(owner_login)
                        if not org_data:
                            continue

                        # Score org
                        score = org_filter.score_org(org_data, owner_repos)
                        
                        if score >= min_score:
                            total_qualified += 1
                            
                            company = Company(
                                github_org=owner_login,
                                name=org_data.get("name", owner_login),
                                website=org_data.get("blog"),
                                description=org_data.get("description"),
                                employee_count=org_data.get("followers"), # Using followers as proxy
                                qualification_score=score,
                                status="QUALIFIED"
                            )
                            session.add(company)
                            await session.flush() # To get company.id
                            
                            filtered_repos = org_filter.filter_repos(owner_repos)
                            for r in filtered_repos:
                                try:
                                    last_commit = None
                                    if r.get("pushed_at"):
                                        last_commit = datetime.strptime(
                                            r["pushed_at"], "%Y-%m-%dT%H:%M:%SZ"
                                        ).replace(tzinfo=timezone.utc)
                                        
                                    repo_obj = Repository(
                                        company_id=company.id,
                                        name=r.get("name"),
                                        full_name=r.get("full_name"),
                                        language=r.get("language"),
                                        stars=r.get("stargazers_count", 0),
                                        last_commit_at=last_commit,
                                        is_fork=r.get("fork", False),
                                        is_archived=r.get("archived", False),
                                        topics=r.get("topics", []),
                                        clone_url=r.get("clone_url"),
                                    )
                                    session.add(repo_obj)
                                    total_repos_saved += 1
                                except Exception as e:
                                    logger.warning(f"Error creating repo object {r.get('full_name')}: {e}")
                                    
                            await session.commit()
                            logger.info(f"Saved company: {owner_login} with score {score}")

                    # Update pagination state
                    page += 1
                    state.last_cursor = str(page)
                    await session.commit()
                    
    finally:
        await searcher.close()
        await engine.dispose()
        
    print(f"\n--- Discovery Summary ---")
    print(f"Organizations evaluated: {total_orgs_found}")
    print(f"Qualified companies saved: {total_qualified}")
    print(f"Repositories saved: {total_repos_saved}")
    print(f"-------------------------\n")


def run_discovery_sync(*args, **kwargs):
    """Synchronous wrapper for RQ worker execution."""
    asyncio.run(run_discovery(*args, **kwargs))

def main():
    parser = argparse.ArgumentParser(description="AutoScan GitHub Discovery Engine")
    parser.add_argument("--min-score", type=float, default=0.6, help="Minimum qualification score (0.0 to 1.0)")
    parser.add_argument("--languages", type=str, nargs="+", default=["python", "typescript", "go", "java"], help="List of languages to search")
    parser.add_argument("--limit", type=int, default=None, help="Maximum number of qualified companies to find")
    
    args = parser.parse_args()
    
    # Configure Loguru
    logger.remove()
    logger.add(sys.stderr, format="{time} {level} {message}", level="INFO")
    
    run_discovery_sync(
        languages=args.languages,
        min_score=args.min_score,
        limit=args.limit
    )

if __name__ == "__main__":
    main()
