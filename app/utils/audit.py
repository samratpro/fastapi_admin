from fastapi import Request
from sqlalchemy.orm import Session
from app.models.audit import AuditLog
from app.models.user import User
from typing import Optional, Dict, Any

async def log_activity(
    db: Session,
    user: User,
    action: str,
    resource_type: str,
    resource_id: int,
    changes: Optional[Dict[str, Any]] = None,
    request: Optional[Request] = None
) -> None:
    ip_address = None
    user_agent = None
    
    if request:
        ip_address = request.client.host
        user_agent = request.headers.get("user-agent")

    log_entry = AuditLog(
        user_id=user.id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        changes=changes,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    db.add(log_entry)
    db.commit()
