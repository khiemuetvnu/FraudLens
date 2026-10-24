"""
FraudLens - Audit Service
Truy vấn nhật ký kiểm toán hệ thống từ bảng audit_log.
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from models.audit_log import AuditLog


class AuditService:
    @classmethod
    def list_logs(
        cls,
        db: Session,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        actor_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[AuditLog]:
        query = db.query(AuditLog)
        if entity_type:
            query = query.filter(AuditLog.entity_type == entity_type)
        if entity_id:
            query = query.filter(AuditLog.entity_id == entity_id)
        if actor_id:
            query = query.filter(AuditLog.actor_id == actor_id)

        return query.order_by(AuditLog.occurred_at.desc()).offset(skip).limit(limit).all()


audit_service = AuditService()
