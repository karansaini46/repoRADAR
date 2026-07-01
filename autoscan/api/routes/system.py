import subprocess
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from autoscan.shared.settings import SystemSettings, get_settings, save_settings
from autoscan.orchestration.queue_manager import get_queue_manager
from autoscan.discovery.pipeline import run_discovery_sync

router = APIRouter(prefix="/api/system", tags=["system"])

LOG_DIR = Path("/app/autoscan/logs")

@router.get("/logs")
def get_system_logs(
    service: str = Query("worker", description="Service name: api, worker, or scheduler"),
    lines: int = Query(500, description="Number of lines to fetch")
):
    """
    Returns the tail of the log file for the given service.
    """
    if service not in ["api", "worker", "scheduler"]:
        raise HTTPException(status_code=400, detail="Invalid service specified")
        
    log_file = LOG_DIR / f"{service}.log"
    
    if not log_file.exists():
        return {"logs": f"Log file for {service} does not exist yet."}
        
    try:
        # Use tail command to efficiently read the last N lines
        result = subprocess.run(
            ["tail", "-n", str(lines), str(log_file)],
            capture_output=True,
            text=True,
            check=True
        )
        return {"logs": result.stdout}
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Failed to read logs: {e.stderr}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/settings", response_model=SystemSettings)
def api_get_settings():
    return get_settings()

@router.post("/settings", response_model=SystemSettings)
def api_save_settings(settings: SystemSettings):
    save_settings(settings)
    return settings

@router.post("/manual-start")
def manual_start_discovery():
    job_id = get_queue_manager().enqueue("discovery", run_discovery_sync)
    if not job_id:
        raise HTTPException(status_code=500, detail="Failed to enqueue manual discovery job. Redis might be down.")
    return {"status": "started", "job_id": job_id}
