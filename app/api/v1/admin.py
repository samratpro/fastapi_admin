from typing import List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.core.security import get_current_active_user, is_admin
from app.db.base import get_db
from app.models.user import User
from app.models.audit import AuditLog
from app.utils.audit import log_activity
from app.schemas.user import User as UserSchema
from datetime import datetime, timedelta
import json

router = APIRouter()

@router.get("/dashboard")
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get dashboard statistics.
    """
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # Get counts
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    verified_users = db.query(User).filter(User.is_verified == True).count()

    # Get recent activity
    recent_logs = db.query(AuditLog).order_by(
        desc(AuditLog.timestamp)
    ).limit(10).all()

    # Get user registration trends
    now = datetime.utcnow()
    last_week = now - timedelta(days=7)
    new_users = db.query(User).filter(
        User.created_at >= last_week
    ).count()

    return {
        "statistics": {
            "total_users": total_users,
            "active_users": active_users,
            "verified_users": verified_users,
            "new_users_last_week": new_users
        },
        "recent_activity": [
            {
                "action": log.action,
                "resource_type": log.resource_type,
                "user": log.user.email,
                "timestamp": log.timestamp
            }
            for log in recent_logs
        ]
    }

@router.get("/audit-logs")
async def get_audit_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    skip: int = 0,
    limit: int = 100,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    user_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> Any:
    """
    Get audit logs with filtering options.
    """
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    query = db.query(AuditLog)

    if action:
        query = query.filter(AuditLog.action == action)
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if start_date:
        query = query.filter(AuditLog.timestamp >= start_date)
    if end_date:
        query = query.filter(AuditLog.timestamp <= end_date)

    total = query.count()
    logs = query.order_by(desc(AuditLog.timestamp)).offset(skip).limit(limit).all()

    return {
        "total": total,
        "logs": [
            {
                "id": log.id,
                "user": log.user.email,
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "changes": log.changes,
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
                "timestamp": log.timestamp
            }
            for log in logs
        ]
    }

@router.post("/system-health")
async def check_system_health(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Check system health and perform maintenance tasks.
    """
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # Check database connection
    try:
        db.execute("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    # Check for unverified users
    unverified_users = db.query(User).filter(
        User.is_verified == False,
        User.created_at <= datetime.utcnow() - timedelta(days=7)
    ).count()

    return {
        "status": "ok",
        "database_status": db_status,
        "unverified_users": unverified_users,
        "timestamp": datetime.utcnow()
    }
