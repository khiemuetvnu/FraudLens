import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, ConfigDict, Field
from schemas.transaction_schema import TransactionResponse, ScoreResponse


class CaseCreateManual(BaseModel):
    transaction_id: str
    manual_reason: str = Field(..., min_length=5, description="Analyst justification for manual case creation")
    priority: Literal['MEDIUM', 'HIGH'] = 'MEDIUM'


class CaseStatusUpdate(BaseModel):
    status: Literal['NEW', 'UNDER_REVIEW', 'NEEDS_MORE_INFO', 'ESCALATED', 'CLOSED']


class CaseOutcomeUpdate(BaseModel):
    outcome: Literal['CONFIRMED_FRAUD_SIM', 'DISMISSED', 'INSUFFICIENT_EVIDENCE']


class CaseAssignUpdate(BaseModel):
    assigned_to: Optional[uuid.UUID]


class CaseNoteCreate(BaseModel):
    content: str = Field(..., min_length=2, description="Investigation notes (append-only)")


class CaseNoteResponse(BaseModel):
    note_id: int
    case_id: uuid.UUID
    author_id: uuid.UUID
    content: str
    created_at: datetime
    author_username: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class BriefResponse(BaseModel):
    brief_id: uuid.UUID
    case_id: uuid.UUID
    prompt_version: str
    playbook_version: str
    status: str
    content: Optional[Dict[str, Any]] = None
    requested_by: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CaseResponse(BaseModel):
    case_id: uuid.UUID
    transaction_id: str
    source: str
    manual_reason: Optional[str] = None
    priority: str
    status: str
    outcome: Optional[str] = None
    assigned_to: Optional[uuid.UUID] = None
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CaseDetailResponse(CaseResponse):
    transaction: Optional[TransactionResponse] = None
    score: Optional[ScoreResponse] = None
    brief: Optional[BriefResponse] = None
    notes: List[CaseNoteResponse] = []

    model_config = ConfigDict(from_attributes=True)
