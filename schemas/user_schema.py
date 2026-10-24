import uuid
from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, ConfigDict, Field


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    role: Literal['analyst', 'risk_lead', 'admin', 'service']


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    user_id: uuid.UUID
    username: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str
    user_id: uuid.UUID


class AuthEventResponse(BaseModel):
    id: int
    occurred_at: datetime
    username: str
    event_type: str
    ip_address: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
