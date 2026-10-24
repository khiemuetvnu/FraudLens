"""
FraudLens - Audit Log Router
Tra cứu lịch sử kiểm toán & truy vết quyết định (FR-08 Auditability & Traceability).
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from connections.dependencies import get_read_db, require_role
from models.user import User
from schemas.audit_schema import AuditLogResponse
from services.audit_service import audit_service

router = APIRouter(prefix="/api/audits", tags=["Audit Log & Traceability"])


@router.get("/", response_model=List[AuditLogResponse])
def list_audit_logs(
    entity_type: Optional[str] = Query(None, description="Lọc theo loại thực thể (ví dụ: 'case')"),
    entity_id: Optional[str] = Query(None, description="Lọc theo ID thực thể"),
    actor_id: Optional[str] = Query(None, description="Lọc theo người thực hiện (username)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(require_role(["analyst", "risk_lead", "admin"])),
    db: Session = Depends(get_read_db)
):
    """Truy vấn nhật ký kiểm toán hệ thống từ ReadOnly Replica"""
    return audit_service.list_logs(
        db,
        entity_type=entity_type,
        entity_id=entity_id,
        actor_id=actor_id,
        skip=skip,
        limit=limit
    )
