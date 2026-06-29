import shutil
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import List

from loguru import logger
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from autoscan.shared.db.models import Repository

async def cleanup_old_clones(session: AsyncSession, base_dir: str, max_age_hours: int = 48) -> List[str]:
    """
    Deletes clone directories older than max_age_hours.
    Updates the database to set local_path = None for cleaned repositories.
    Logs how much disk space was freed.
    Returns a list of deleted paths.
    """
    base = Path(base_dir)
    if not base.exists() or not base.is_dir():
        logger.warning(f"Cleanup base directory {base_dir} does not exist.")
        return []

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=max_age_hours)
    
    deleted_paths = []
    freed_bytes = 0

    for item in base.iterdir():
        if item.is_dir():
            try:
                mtime = item.stat().st_mtime
                item_time = datetime.fromtimestamp(mtime, tz=timezone.utc)
                
                if item_time < cutoff:
                    # Calculate size before deleting
                    item_size = sum(f.stat().st_size for f in item.rglob('*') if f.is_file())
                    
                    # Delete the directory
                    shutil.rmtree(item)
                    
                    freed_bytes += item_size
                    deleted_paths.append(str(item.absolute()))
                    logger.debug(f"Deleted old clone: {item}")
            except Exception as e:
                logger.error(f"Error cleaning up {item}: {e}")

    if deleted_paths:
        freed_gb = freed_bytes / (1024 ** 3)
        logger.info(f"Cleaned up {len(deleted_paths)} old clones. Freed {freed_gb:.2f} GB.")
        
        # Update database
        try:
            await session.execute(
                update(Repository)
                .where(Repository.local_path.in_(deleted_paths))
                .values(local_path=None)
            )
            await session.commit()
            logger.info("Database updated to remove local_path for cleaned repositories.")
        except Exception as e:
            logger.error(f"Error updating database for cleaned paths: {e}")
            await session.rollback()
            
    return deleted_paths
