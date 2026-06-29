import asyncio
import os
import shutil
from pathlib import Path
from datetime import datetime, timezone, timedelta
import pytest
from unittest.mock import patch, MagicMock

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from autoscan.cloning.inventory import RepoInventory
from autoscan.cloning.cleanup import cleanup_old_clones
from autoscan.cloning.cloner import RepoCloner
from autoscan.shared.db.models import Base, Repository

@pytest.fixture
def temp_repo_dir(tmp_path):
    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir()
    
    # Create files
    (repo_dir / "package.json").write_text('{"name": "test"}')
    (repo_dir / "index.js").write_text('console.log("hello");')
    (repo_dir / ".env.example").write_text('API_KEY=')
    
    # Create nested dir
    src_dir = repo_dir / "src"
    src_dir.mkdir()
    (src_dir / "main.py").write_text('print("hello")')
    
    # Create CI config
    ci_dir = repo_dir / ".github" / "workflows"
    ci_dir.mkdir(parents=True)
    (ci_dir / "test.yml").write_text('name: Test')
    
    # Create ignored dir
    node_modules = repo_dir / "node_modules"
    node_modules.mkdir()
    (node_modules / "lib.js").write_text('// lib')
    
    return repo_dir

def test_inventory_scan(temp_repo_dir):
    inventory = RepoInventory()
    result = inventory.scan(temp_repo_dir)
    
    assert result["file_count"] == 5 # package.json, index.js, .env.example, main.py, test.yml
    assert ".js" in result["languages"]
    assert ".py" in result["languages"]
    assert ".yml" in result["languages"]
    assert result["has_ci_config"] is True
    assert result["has_env_example"] is True
    assert result["package_manifests"] == ["package.json"]
    assert result["has_dockerfile"] is False
    assert result["secret_patterns_present"] is False
    assert "node_modules" not in str(result)

@pytest.mark.asyncio
async def test_cleanup_old_clones(tmp_path):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    async with async_session() as session:
        base_dir = tmp_path / "clones"
        base_dir.mkdir()
        
        # Create an old repo
        old_repo = base_dir / "old_repo"
        old_repo.mkdir()
        (old_repo / "file.txt").write_text("old")
        
        # Create a new repo
        new_repo = base_dir / "new_repo"
        new_repo.mkdir()
        (new_repo / "file.txt").write_text("new")
        
        # Set mtime of old repo to 3 days ago
        old_time = (datetime.now(timezone.utc) - timedelta(days=3)).timestamp()
        os.utime(old_repo, (old_time, old_time))
        
        # Add to DB
        r1 = Repository(name="old_repo", full_name="user/old_repo", local_path=str(old_repo))
        r2 = Repository(name="new_repo", full_name="user/new_repo", local_path=str(new_repo))
        session.add(r1)
        session.add(r2)
        await session.commit()
        
        deleted_paths = await cleanup_old_clones(session, str(base_dir), max_age_hours=48)
        
        assert str(old_repo.absolute()) in deleted_paths
        assert str(new_repo.absolute()) not in deleted_paths
        
        # Verify old repo is deleted from disk
        assert not old_repo.exists()
        assert new_repo.exists()
        
        # Verify DB is updated
        await session.refresh(r1)
        assert r1.local_path is None
        
        await session.refresh(r2)
        assert r2.local_path == str(new_repo)

@pytest.mark.asyncio
async def test_cloner_concurrency():
    cloner = RepoCloner(base_dir="/tmp/test_autoscan")
    
    # Mock the underlying clone method to just sleep briefly
    async def mock_clone(repo):
        await asyncio.sleep(0.1)
        return Path(f"/tmp/test_autoscan/{repo.id}")
        
    cloner.clone = mock_clone
    
    repos = [Repository(id=i, full_name=f"org/repo{i}", clone_url="url") for i in range(10)]
    
    # Should take ~0.2 seconds with max_concurrent=5
    start = asyncio.get_event_loop().time()
    results = await cloner.clone_many(repos, max_concurrent=5)
    duration = asyncio.get_event_loop().time() - start
    
    assert len(results) == 10
    assert 0.1 <= duration < 0.5 # Should be fast but batched
