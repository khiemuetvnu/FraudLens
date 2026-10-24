import uuid
from sqlalchemy import Column, String, Integer, BigInteger, DateTime, ForeignKey, CheckConstraint, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from connections.database import Base


class Case(Base):
    __tablename__ = "cases"

    case_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    transaction_id = Column(String, ForeignKey("transactions.transaction_id"), unique=True, nullable=False)
    source = Column(String, nullable=False)
    manual_reason = Column(String, nullable=True)
    priority = Column(String, nullable=False)
    status = Column(String, nullable=False, default="NEW", server_default="NEW")
    outcome = Column(String, nullable=True)
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    version = Column(Integer, nullable=False, default=1, server_default="1")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("source IN ('AUTO', 'MANUAL')", name="check_case_source"),
        CheckConstraint("priority IN ('MEDIUM', 'HIGH')", name="check_case_priority"),
        CheckConstraint("status IN ('NEW', 'UNDER_REVIEW', 'NEEDS_MORE_INFO', 'ESCALATED', 'CLOSED')", name="check_case_status"),
        CheckConstraint("outcome IN ('CONFIRMED_FRAUD_SIM', 'DISMISSED', 'INSUFFICIENT_EVIDENCE')", name="check_case_outcome"),
    )

    # Relationships
    transaction = relationship("Transaction", back_populates="case")
    brief = relationship("Brief", back_populates="case", uselist=False, cascade="all, delete-orphan")
    notes = relationship("CaseNote", back_populates="case", cascade="all, delete-orphan", order_by="CaseNote.created_at.desc()")
    assignee = relationship("User", foreign_keys=[assigned_to])


class Brief(Base):
    __tablename__ = "briefs"

    brief_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.case_id"), unique=True, nullable=False)
    prompt_version = Column(String, nullable=False)
    playbook_version = Column(String, nullable=False)
    status = Column(String, nullable=False, default="PENDING", server_default="PENDING")
    content = Column(JSONB, nullable=True)
    requested_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    last_pushed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("status IN ('PENDING', 'READY', 'FAILED')", name="check_brief_status"),
    )

    # Relationships
    case = relationship("Case", back_populates="brief")
    requester = relationship("User", foreign_keys=[requested_by])


class CaseNote(Base):
    __tablename__ = "case_notes"

    note_id = Column(BigInteger, primary_key=True, autoincrement=True)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.case_id"), nullable=False)
    author_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    content = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    case = relationship("Case", back_populates="notes")
    author = relationship("User", foreign_keys=[author_id])
