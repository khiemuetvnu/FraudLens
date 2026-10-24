import uuid
from sqlalchemy import Column, String, Boolean, DateTime, BigInteger, CheckConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from connections.database import Base


class User(Base):
    __tablename__ = "users"

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    username = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("role IN ('analyst', 'risk_lead', 'admin', 'service')", name="check_user_role"),
    )


class AuthEvent(Base):
    __tablename__ = "auth_events"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    occurred_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    username = Column(String, nullable=False, index=True)
    event_type = Column(String, nullable=False)
    ip_address = Column(String, nullable=True)

    __table_args__ = (
        CheckConstraint("event_type IN ('login_success', 'login_failed', 'logout')", name="check_auth_event_type"),
    )
