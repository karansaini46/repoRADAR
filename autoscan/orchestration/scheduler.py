import asyncio
import logging
import time
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Import pipeline run functions
from autoscan.discovery.pipeline import run_discovery
from autoscan.enrichment.pipeline import run_enrichment
from autoscan.cloning.pipeline import run_cloning
from autoscan.scanning.pipeline import run_scanning
from autoscan.ai_layer.pipeline import run_verification
from autoscan.impact.pipeline import run_impact_calculation
from autoscan.reports.pipeline import run_report_generation
from autoscan.outreach.pipeline_contacts import run_contact_discovery
from autoscan.outreach.pipeline_email import run_outreach

logger = logging.getLogger(__name__)

async def run_sync_in_thread(func, *args, **kwargs):
    """Runs a synchronous function in a separate thread to avoid blocking the event loop."""
    return await asyncio.to_thread(func, *args, **kwargs)

async def wrapped_job(job_name: str, func, is_async: bool = False, *args, **kwargs):
    """Wrapper to measure execution time and handle logging/errors for jobs."""
    logger.info(f"--- Starting scheduled job: {job_name} ---")
    start_time = time.time()
    try:
        if is_async:
            result = await func(*args, **kwargs)
        else:
            result = await run_sync_in_thread(func, *args, **kwargs)
        duration = time.time() - start_time
        logger.info(f"--- Completed scheduled job: {job_name} in {duration:.2f}s ---")
        return result
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"!!! Failed scheduled job: {job_name} after {duration:.2f}s - {e} !!!", exc_info=True)

def start_scheduler():
    """Initializes and starts the APScheduler."""
    scheduler = AsyncIOScheduler()

    # Define scheduled jobs based on operational requirements
    
    # 1. Discovery (Async) - Daily at 02:00
    scheduler.add_job(
        wrapped_job, 'cron', hour=2, minute=0,
        args=["Discovery", run_discovery, True]
    )
    
    # 2. Enrichment (Async) - Every 6 hours
    scheduler.add_job(
        wrapped_job, 'interval', hours=6,
        args=["Enrichment", run_enrichment, True]
    )
    
    # 3. Cloning (Async) - Every 4 hours
    scheduler.add_job(
        wrapped_job, 'interval', hours=4,
        args=["Cloning", run_cloning, True]
    )
    
    # 4. Scanning (Sync) - Every 2 hours
    scheduler.add_job(
        wrapped_job, 'interval', hours=2,
        args=["Scanning", run_scanning, False]
    )
    
    # 5. Verification (Sync) - Hourly
    scheduler.add_job(
        wrapped_job, 'interval', hours=1,
        args=["Verification", run_verification, False]
    )
    
    # 6. Impact Calculation (Sync) - Every 2 hours
    scheduler.add_job(
        wrapped_job, 'interval', hours=2,
        args=["Impact Calculation", run_impact_calculation, False]
    )
    
    # 7. Report Generation (Sync) - Every 4 hours
    scheduler.add_job(
        wrapped_job, 'interval', hours=4,
        args=["Report Generation", run_report_generation, False]
    )
    
    # 8. Contact Discovery (Sync) - Daily at 06:00
    scheduler.add_job(
        wrapped_job, 'cron', hour=6, minute=0,
        args=["Contact Discovery", run_contact_discovery, False]
    )
    
    # 9. Outreach (Sync) - Daily at 08:00
    scheduler.add_job(
        wrapped_job, 'cron', hour=8, minute=0,
        args=["Outreach", run_outreach, False]
    )

    scheduler.start()
    logger.info("Scheduler started successfully with 9 pipeline jobs.")
    return scheduler

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger.info("Starting AutoScan standalone scheduler process...")
    try:
        loop = asyncio.get_event_loop()
        scheduler = start_scheduler()
        loop.run_forever()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler shutting down...")
