from sqlalchemy import Column, String, Numeric, Integer, BigInteger, Date, DateTime, Boolean, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from connections.database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    transaction_id = Column(String, primary_key=True)
    cc_num = Column(String, nullable=False)
    merchant = Column(String, nullable=False)
    category = Column(String, nullable=False)
    amt = Column(Numeric, nullable=False)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    gender = Column(String, nullable=True)
    street = Column(String, nullable=True)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    zip = Column(String, nullable=True)
    lat = Column(Numeric, nullable=True)
    long = Column(Numeric, nullable=True)
    city_pop = Column(Integer, nullable=True)
    job = Column(String, nullable=True)
    dob = Column(Date, nullable=True)
    merch_lat = Column(Numeric, nullable=True)
    merch_long = Column(Numeric, nullable=True)
    trans_time = Column(DateTime(timezone=True), nullable=False)
    unix_time = Column(BigInteger, nullable=False)
    input_status = Column(String, nullable=False)
    received_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_pushed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("input_status IN ('VALID', 'INVALID')", name="check_transaction_input_status"),
    )

    # Relationships
    score = relationship("Score", back_populates="transaction", uselist=False, cascade="all, delete-orphan")
    case = relationship("Case", back_populates="transaction", uselist=False)
    delayed_label = relationship("DelayedLabel", back_populates="transaction", uselist=False)


class Score(Base):
    __tablename__ = "scores"

    transaction_id = Column(String, ForeignKey("transactions.transaction_id"), primary_key=True)
    risk_score = Column(Numeric, nullable=False)
    calibrated_prob = Column(Numeric, nullable=True)
    routing = Column(String, nullable=False)
    model_version = Column(String, nullable=False)
    threshold_config_version = Column(String, nullable=False)
    features = Column(JSONB, nullable=False)
    scored_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("routing IN ('LOW', 'MEDIUM', 'HIGH', 'MANUAL_FALLBACK_UNSCORED')", name="check_score_routing"),
    )

    # Relationship
    transaction = relationship("Transaction", back_populates="score")


class DelayedLabel(Base):
    __tablename__ = "delayed_labels"

    transaction_id = Column(String, ForeignKey("transactions.transaction_id"), primary_key=True)
    is_fraud = Column(Boolean, nullable=False)
    available_at = Column(DateTime(timezone=True), nullable=False)

    # Relationship
    transaction = relationship("Transaction", back_populates="delayed_label")
