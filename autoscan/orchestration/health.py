import os
import time
import shutil
from fastapi import APIRouter
from sqlalchemy import text
from autoscan.shared.db.database import SessionLocal
from autoscan.orchestration.queue_manager import get_queue_manager

router = APIRouter(prefix="/health", tags=["Health"])

def check_db_health():
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        return {"status": "ok", "latency_ms": 0} # simplified latency logic
    except Exception as e:
        return {"status": "down", "error": str(e)}

def check_redis_health():
    qm = get_queue_manager()
    if not qm.conn:
        return {"status": "down", "error": "Redis connection not established"}
    try:
        qm.conn.ping()
        return {"status": "ok"}
    except Exception as e:
        return {"status": "down", "error": str(e)}

def check_disk_space():
    total, used, free = shutil.disk_usage("/")
    pct_used = (used / total) * 100
    status = "ok"
    if pct_used > 85:
        status = "degraded"
    if pct_used > 95:
        status = "down"
    return {
        "status": status,
        "percent_used": round(pct_used, 2),
        "free_gb": round(free / (1024**3), 2)
    }

@router.get("/")
def get_health():
    db = check_db_health()
    redis = check_redis_health()
    disk = check_disk_space()
    
    overall_status = "ok"
    if any(c["status"] == "down" for c in [db, redis, disk]):
        overall_status = "down"
    elif any(c["status"] == "degraded" for c in [db, redis, disk]):
        overall_status = "degraded"
        
    return {
        "status": overall_status,
        "checks": {
            "database": db,
            "redis": redis,
            "disk": disk
        }
    }

@router.get("/detailed")
def get_detailed_health():
    base_health = get_health()
    qm = get_queue_manager()
    base_health["queues"] = qm.get_queue_stats()
    return base_health
