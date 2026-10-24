"""
FraudLens - Transactions Router
Tiếp nhận giao dịch (Ingest), kích hoạt chấm điểm ML (Hot Path), tra cứu giao dịch gốc.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from connections.dependencies import get_write_db, get_read_db, get_current_user, require_role
from models.user import User
from schemas.transaction_schema import (
    TransactionIngestInput,
    TransactionResponse,
    TransactionDetailResponse,
    ScoreResponse
)
from services.transaction_service import transaction_service

router = APIRouter(prefix="/api/transactions", tags=["Transactions & Ingest"])


@router.post("/ingest", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
def ingest_transaction(
    payload: TransactionIngestInput,
    auto_score: bool = Query(True, description="Tự động kích hoạt ML Scoring ngay sau khi lưu"),
    current_user: User = Depends(require_role(["service", "admin", "analyst"])),
    db: Session = Depends(get_write_db)
):
    """
    Bước 1: Tiếp nhận giao dịch từ Simulator / Nginx.
    Lưu giao dịch vào bảng transactions, cách ly nhãn is_fraud vào delayed_labels.
    Nếu auto_score = True, tự động chuyển tiếp sang ML Scoring Stub.
    """
    return transaction_service.ingest_transaction(db, txn_in=payload, auto_score=auto_score)


@router.post("/simulate-batch", response_model=List[TransactionResponse])
def ingest_simulation_batch(
    count: int = Query(10, ge=1, le=100, description="Số lượng giao dịch cần nạp từ fraudTrain.csv"),
    inject_fault: bool = Query(False, description="Mô phỏng tiêm lỗi để kiểm thử Fail-safe"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_write_db)
):
    """Tiện ích nạp nhanh 1 batch giao dịch từ simulator stub để kiểm thử luồng End-to-End"""
    return transaction_service.ingest_simulation_batch(db, count=count, inject_fault=inject_fault)


@router.get("/", response_model=List[TransactionResponse])
def list_transactions(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[str] = Query(None, description="Lọc theo VALID hoặc INVALID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_read_db)
):
    """Tra cứu danh sách giao dịch gốc từ ReadOnly Replica"""
    return transaction_service.list_transactions(db, skip=skip, limit=limit, status=status)


@router.get("/special-inspection-queue", response_model=List[TransactionResponse])
def get_special_inspection_queue(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(require_role(["analyst", "risk_lead", "admin"])),
    db: Session = Depends(get_read_db)
):
    """
    FR-07: Hàng đợi kiểm tra đặc biệt (Special Inspection Queue / Fallback Queue).
    Dành riêng cho các giao dịch không thể chấm điểm tự động (MANUAL_FALLBACK_UNSCORED),
    bị lỗi dữ liệu nghiêm trọng (số tiền âm, thiếu trường bắt buộc...) cần chuyên viên xem xét thủ công.
    """
    return transaction_service.get_special_inspection_queue(db, skip=skip, limit=limit)


@router.get("/{transaction_id}", response_model=TransactionDetailResponse)
def get_transaction_detail(
    transaction_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_read_db)
):
    """Xem chi tiết đầy đủ một giao dịch kèm điểm rủi ro"""
    txn = transaction_service.get_transaction(db, transaction_id=transaction_id)
    if not txn:
        raise HTTPException(status_code=404, detail=f"Transaction {transaction_id} not found")
    return txn


@router.post("/{transaction_id}/score", response_model=ScoreResponse)
def trigger_scoring_manual(
    transaction_id: str,
    current_user: User = Depends(require_role(["analyst", "risk_lead", "admin"])),
    db: Session = Depends(get_write_db)
):
    """
    Bước 2 (Thủ công): Chuyên viên bấm nút kích hoạt chấm điểm lại trên một giao dịch.
    Nếu kết quả là MEDIUM/HIGH, hệ thống sẽ tự động khởi tạo hồ sơ Case.
    """
    return transaction_service.score_transaction(db, transaction_id=transaction_id)
