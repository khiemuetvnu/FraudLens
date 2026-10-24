import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    id: int
    occurred_at: datetime
    request_id: uuid.UUID
    actor_id: str
    action: str
    entity_type: str
    entity_id: str
    before_state: Optional[Dict[str, Any]] = None
    after_state: Optional[Dict[str, Any]] = None
    meta: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)
