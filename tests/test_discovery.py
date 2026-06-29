import pytest
import respx
import httpx
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from autoscan.discovery.github_search import GitHubSearcher
from autoscan.discovery.org_filter import OrgFilter
from autoscan.shared.db.models import Base, DiscoveryState

@pytest.fixture
def org_filter():
    return OrgFilter()

def test_score_org_high(org_filter):
    """Test a highly qualified organization."""
    org_data = {
        "login": "acmecorp",
        "type": "Organization",
        "followers": 10,
        "blog": "https://acme.corp",
    }
    
    recent_date = (datetime.now(timezone.utc) - timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
    repos = [
        {
            "name": "core-backend",
            "language": "Python",
            "stargazers_count": 30,
            "pushed_at": recent_date,
            "fork": False,
            "archived": False
        },
        {
            "name": "frontend",
            "language": "TypeScript",
            "stargazers_count": 25,
            "pushed_at": recent_date,
            "fork": False,
            "archived": False
        }
    ]
    
    score = org_filter.score_org(org_data, repos)
    
    # Expected score breakdown:
    # is_org: +0.3
    # members>=5 (followers): +0.2
    # stars>=50 (30+25=55): +0.1
    # recent_commit: +0.15
    # has_website: +0.1
    # has_manifest (Python/TypeScript): +0.1
    # not_fork: +0.05
    # Total: 1.0
    
    assert score >= 0.99

def test_score_org_low(org_filter):
    """Test a poorly qualified user account."""
    org_data = {
        "login": "random-user",
        "type": "User",
        "followers": 2,
        "blog": "",
    }
    
    old_date = (datetime.now(timezone.utc) - timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%SZ")
    repos = [
        {
            "name": "forked-repo",
            "language": "C++",
            "stargazers_count": 5,
            "pushed_at": old_date,
            "fork": True,
            "archived": False
        }
    ]
    
    score = org_filter.score_org(org_data, repos)
    
    # Expected score breakdown:
    # is_org: 0.0
    # members>=5: 0.0
    # stars>=50: 0.0
    # recent_commit: 0.0
    # has_website: 0.0
    # has_manifest: 0.0
    # not_fork: 0.0
    # Total: 0.0
    
    assert score == 0.0

@pytest.mark.asyncio
@respx.mock
async def test_github_searcher():
    """Test that GitHubSearcher parses responses and handles pagination correctly."""
    searcher = GitHubSearcher("dummy_token")
    
    # Mock search API
    respx.get(
        "https://api.github.com/search/repositories",
        params={"q": "is:public language:python stars:>=50", "sort": "stars", "order": "desc", "page": "1", "per_page": "30"}
    ).respond(
        status_code=200,
        json={"items": [{"id": 1, "name": "repo1"}]},
        headers={"link": '<https://api.github.com/search/repositories?page=2>; rel="next"'}
    )
    
    items, has_next = await searcher.search_repos("is:public", 50, "python", 1)
    
    assert len(items) == 1
    assert items[0]["name"] == "repo1"
    assert has_next is True
    
    await searcher.close()

@pytest.mark.asyncio
async def test_pagination_resumability():
    """Test that discovery state is correctly created and updated."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    async with async_session() as session:
        # Create initial state
        state = DiscoveryState(language="python", last_cursor="1")
        session.add(state)
        await session.commit()
        
    async with async_session() as session:
        # Update state
        from sqlalchemy import select
        result = await session.execute(select(DiscoveryState).where(DiscoveryState.language == "python"))
        loaded_state = result.scalars().first()
        assert loaded_state.last_cursor == "1"
        
        loaded_state.last_cursor = "2"
        await session.commit()
        
    async with async_session() as session:
        # Verify update
        result = await session.execute(select(DiscoveryState).where(DiscoveryState.language == "python"))
        final_state = result.scalars().first()
        assert final_state.last_cursor == "2"
        
    await engine.dispose()
