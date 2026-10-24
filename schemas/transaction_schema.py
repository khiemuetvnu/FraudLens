from datetime import datetime, date
from decimal import Decimal
from typing import Optional, Any, Dict
from pydantic import BaseModel, ConfigDict, Field


class TransactionIngestInput(BaseModel):
    transaction_id: str = Field(..., description="Unique transaction ID / trans_num")
    cc_num: str = Field(..., description="Credit card number")
    merchant: str
    category: str
    amt: Decimal = Field(..., description="Transaction amount")
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    gender: Optional[str] = None
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    lat: Optional[Decimal] = None
    long: Optional[Decimal] = None
    city_pop: Optional[int] = None
    job: Optional[str] = None
    dob: Optional[date] = None
    merch_lat: Optional[Decimal] = None
    merch_long: Optional[Decimal] = None
    trans_time: datetime
    unix_time: int
    # Separated label for delayed evaluation (not leaked into scoring!)
    ground_truth_is_fraud: Optional[bool] = Field(None, description="Ground truth saved strictly to delayed_labels")


class ScoreResponse(BaseModel):
    transaction_id: str
    risk_score: Decimal
    calibrated_prob: Optional[Decimal] = None
    routing: str
    model_version: str
    threshold_config_version: str
    features: Dict[str, Any]
    scored_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TransactionResponse(BaseModel):
    transaction_id: str
    cc_num: str
    merchant: str
    category: str
    amt: Decimal
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    trans_time: datetime
    input_status: str
    received_at: datetime
    score: Optional[ScoreResponse] = None

    model_config = ConfigDict(from_attributes=True)


class TransactionDetailResponse(TransactionResponse):
    gender: Optional[str] = None
    street: Optional[str] = None
    zip: Optional[str] = None
    lat: Optional[Decimal] = None
    long: Optional[Decimal] = None
    city_pop: Optional[int] = None
    job: Optional[str] = None
    dob: Optional[date] = None
    merch_lat: Optional[Decimal] = None
    merch_long: Optional[Decimal] = None
    unix_time: int
    last_pushed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
