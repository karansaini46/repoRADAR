import asyncio
import os
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timezone, timedelta

from loguru import logger
from autoscan.shared.db.models import Repository

class RepoCloner:
    def __init__(self, base_dir: str = "/tmp/autoscan"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    async def clone(self, repo: Repository) -> Optional[Path]:
        """
        Clones a repository using git.
        Returns the path to the cloned repository or None if it fails.
        """
        if not repo.clone_url or not repo.full_name:
            logger.warning(f"Repository {repo.id} is missing clone_url or full_name")
            return None

        # Define destination path
        dest = self.base_dir / repo.full_name.replace("/", "_")
        
        # Check if already exists and is < 24 hours old
        if dest.exists() and dest.is_dir():
            mtime = dest.stat().st_mtime
            age = datetime.now(timezone.utc) - datetime.fromtimestamp(mtime, tz=timezone.utc)
            if age < timedelta(hours=24):
                logger.debug(f"Repo {repo.full_name} already cloned recently at {dest}")
                return dest
            else:
                # We could delete it here or let git fail/overwrite.
                # Actually, git clone will fail if the directory exists and is not empty.
                # It's better to remove it if it's too old.
                import shutil
                try:
                    # Run synchronously to clean up old repo before clone
                    shutil.rmtree(dest)
                except Exception as e:
                    logger.warning(f"Failed to remove old clone directory {dest}: {e}")

        # Ensure parent exists
        dest.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"Cloning {repo.full_name} to {dest}...")
        
        cmd = [
            "git", "clone", 
            "--depth=1", 
            "--no-tags", 
            repo.clone_url, 
            str(dest)
        ]
        
        try:
            # Create subprocess
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Wait with timeout
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=120.0)
            except asyncio.TimeoutError:
                logger.error(f"Clone timed out for {repo.full_name}")
                # Kill process to avoid zombies
                try:
                    process.terminate()
                    await process.wait()
                except Exception:
                    pass
                return None
                
            if process.returncode != 0:
                logger.error(f"Clone failed for {repo.full_name}: {stderr.decode()}")
                return None
                
            logger.success(f"Successfully cloned {repo.full_name}")
            return dest
            
        except Exception as e:
            logger.error(f"Error executing git clone for {repo.full_name}: {e}")
            return None

    async def _clone_with_semaphore(self, repo: Repository, semaphore: asyncio.Semaphore) -> tuple[int, Optional[Path]]:
        async with semaphore:
            path = await self.clone(repo)
            return repo.id, path

    async def clone_many(self, repos: List[Repository], max_concurrent: int = 5) -> Dict[int, Path]:
        """
        Clones multiple repositories concurrently using a semaphore.
        Returns a dictionary mapping repo.id to the cloned path.
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        tasks = [
            self._clone_with_semaphore(repo, semaphore)
            for repo in repos
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        cloned_paths = {}
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Concurrent clone task failed: {result}")
                continue
                
            repo_id, path = result
            if path:
                cloned_paths[repo_id] = path
                
        return cloned_paths
