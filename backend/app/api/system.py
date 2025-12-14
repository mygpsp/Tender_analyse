"""API routes for system operations and monitoring."""
import logging
import json
from fastapi import APIRouter, HTTPException
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/system", tags=["system"])

# Paths
_project_root = Path(__file__).parent.parent.parent.parent
_logs_dir = _project_root / "logs"
_update_log_file = _logs_dir / "update_history.json"


@router.get("/update-logs")
async def get_update_logs():
    """
    Get data update history logs.
    
    Returns:
        - logs: List of update log entries (newest first)
        - latest_status: Status of most recent run
        - last_run_age_hours: Hours since last run
    """
    try:
        if not _update_log_file.exists():
            return {
                "logs": [],
                "latest_status": None,
                "last_run_age_hours": None
            }
        
        # Load logs
        with open(_update_log_file, 'r', encoding='utf-8') as f:
            logs = json.load(f)
        
        # Sort by timestamp (newest first)
        logs.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # Calculate age of last run
        latest_status = None
        last_run_age_hours = None
        
        if logs:
            latest_status = logs[0]['status']
            last_run_time = datetime.fromisoformat(logs[0]['timestamp'])
            age = datetime.now() - last_run_time
            last_run_age_hours = round(age.total_seconds() / 3600, 2)
        
        return {
            "logs": logs,
            "latest_status": latest_status,
            "last_run_age_hours": last_run_age_hours
        }
        
    except Exception as e:
        logger.error(f"Error reading update logs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def get_system_health():
    """
    Get overall system health status.
    
    Returns health indicators for data sync and system status.
    """
    try:
        health = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "checks": {}
        }
        
        # Check if update logs exist
        if _update_log_file.exists():
            with open(_update_log_file, 'r', encoding='utf-8') as f:
                logs = json.load(f)
            
            if logs:
                latest = logs[-1]  # Last entry
                last_run_time = datetime.fromisoformat(latest['timestamp'])
                age_hours = (datetime.now() - last_run_time).total_seconds() / 3600
                
                health["checks"]["data_sync"] = {
                    "status": "healthy" if latest['status'] == 'SUCCESS' and age_hours < 48 else "warning",
                    "last_run": latest['timestamp'],
                    "last_status": latest['status'],
                    "age_hours": round(age_hours, 2)
                }
            else:
                health["checks"]["data_sync"] = {
                    "status": "warning",
                    "message": "No update logs found"
                }
        else:
            health["checks"]["data_sync"] = {
                "status": "warning",
                "message": "Update log file not found"
            }
        
        # Overall status
        if any(check.get("status") == "warning" for check in health["checks"].values()):
            health["status"] = "warning"
        
        return health
        
    except Exception as e:
        logger.error(f"Error checking system health: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
