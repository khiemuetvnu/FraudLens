"""
FraudLens - Transaction Service
Xử lý Ingest giao dịch, cách ly nhãn ground truth vào delayed_labels,
kích hoạt ML Scoring (Hot Path) và tự động tạo Case khi rủi ro cao.
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import HTTPException
from sqlalchemy.orm import Session

from models.transaction import Transaction, Score, DelayedLabel
from schemas.transaction_schema import TransactionIngestInput
from stubs.ml_scoring_stub import ml_scorer
from stubs.simulator_stub import simulator
from services.case_service import case_service


class TransactionService:
    @classmethod
    def ingest_transaction(
        cls,
        db: Session,
        txn_in: TransactionIngestInput,
        auto_score: bool = True
    ) -> Transaction:
        """Tiếp nhận giao dịch từ Simulator / Ingest Gateway"""
        # 1. Kiểm tra validation schema cơ bản (FR-01)
        is_valid = True
        if txn_in.amt <= 0 or not txn_in.cc_num or not txn_in.merchant:
            is_valid = False

        input_status = "VALID" if is_valid else "INVALID"

        # 2. Lưu giao dịch gốc vào bảng transactions
        existing = db.query(Transaction).filter(Transaction.transaction_id == txn_in.transaction_id).first()
        if existing:
            return existing

        txn = Transaction(
            transaction_id=txn_in.transaction_id,
            cc_num=txn_in.cc_num,
            merchant=txn_in.merchant,
            category=txn_in.category,
            amt=txn_in.amt,
            first_name=txn_in.first_name,
            last_name=txn_in.last_name,
            gender=txn_in.gender,
            street=txn_in.street,
            city=txn_in.city,
            state=txn_in.state,
            zip=txn_in.zip,
            lat=txn_in.lat,
            long=txn_in.long,
            city_pop=txn_in.city_pop,
            job=txn_in.job,
            dob=txn_in.dob,
            merch_lat=txn_in.merch_lat,
            merch_long=txn_in.merch_long,
            trans_time=txn_in.trans_time,
            unix_time=txn_in.unix_time,
            input_status=input_status
        )
        db.add(txn)
        db.flush()

        # 3. Xử lý chống lộ nhãn (Data Leakage): tách is_fraud lưu độc lập vào delayed_labels
        if txn_in.ground_truth_is_fraud is not None:
            # Mô phỏng độ trễ giám sát (ví dụ sẵn sàng sau 24h hoặc ngay lập tức cho simulation)
            available_time = txn_in.trans_time + timedelta(hours=24)
            label = DelayedLabel(
                transaction_id=txn.transaction_id,
                is_fraud=txn_in.ground_truth_is_fraud,
                available_at=available_time
            )
            db.add(label)

        db.commit()
        db.refresh(txn)

        # 4. Kích hoạt Chấm điểm tự động nếu hợp lệ
        if auto_score:
            cls.score_transaction(db, txn.transaction_id)
            db.refresh(txn)

        return txn

    @classmethod
    def score_transaction(cls, db: Session, transaction_id: str) -> Score:
        """Kích hoạt chấm điểm giao dịch qua ML Scoring Stub (Hot Path)"""
        txn = db.query(Transaction).filter(Transaction.transaction_id == transaction_id).first()
        if not txn:
            raise HTTPException(status_code=404, detail=f"Transaction {transaction_id} not found")

        # Chuẩn bị dữ liệu gửi sang ML Stub
        txn_data = {
            "transaction_id": txn.transaction_id,
            "cc_num": txn.cc_num,
            "merchant": txn.merchant,
            "category": txn.category,
            "amt": float(txn.amt),
            "trans_time": txn.trans_time
        }

        # Gọi ML Scoring Stub
        result = ml_scorer.score_transaction(txn_data)

        # Lưu kết quả chấm điểm vào bảng scores
        existing_score = db.query(Score).filter(Score.transaction_id == transaction_id).first()
        if existing_score:
            existing_score.risk_score = result["risk_score"]
            existing_score.calibrated_prob = result["calibrated_prob"]
            existing_score.routing = result["routing"]
            existing_score.model_version = result["model_version"]
            existing_score.threshold_config_version = result["threshold_config_version"]
            existing_score.features = result["features"]
            existing_score.scored_at = datetime.now()
            score_record = existing_score
        else:
            score_record = Score(
                transaction_id=txn.transaction_id,
                risk_score=result["risk_score"],
                calibrated_prob=result["calibrated_prob"],
                routing=result["routing"],
                model_version=result["model_version"],
                threshold_config_version=result["threshold_config_version"],
                features=result["features"]
            )
            db.add(score_record)

        db.commit()
        db.refresh(score_record)

        # Tự động tạo hồ sơ điều tra nếu rủi ro là MEDIUM hoặc HIGH (Bước 3 - Nhánh Auto)
        if result["routing"] in ["MEDIUM", "HIGH"]:
            case_service.create_case_auto(db, transaction_id=transaction_id, priority=result["routing"])

        return score_record

    @classmethod
    def get_transaction(cls, db: Session, transaction_id: str) -> Optional[Transaction]:
        return db.query(Transaction).filter(Transaction.transaction_id == transaction_id).first()

    @classmethod
    def list_transactions(
        cls,
        db: Session,
        skip: int = 0,
        limit: int = 50,
        status: Optional[str] = None
    ) -> List[Transaction]:
        query = db.query(Transaction)
        if status:
            query = query.filter(Transaction.input_status == status)
        return query.order_by(Transaction.trans_time.desc()).offset(skip).limit(limit).all()

    @classmethod
    def get_special_inspection_queue(
        cls,
        db: Session,
        skip: int = 0,
        limit: int = 50
    ) -> List[Transaction]:
        """
        FR-07: Hàng đợi kiểm tra đặc biệt (Special Inspection / Fallback Queue).
        Lấy các giao dịch bị lỗi hoặc gán nhãn MANUAL_FALLBACK_UNSCORED.
        Tận dụng index idx_scores_routing (routing, scored_at).
        """
        return (
            db.query(Transaction)
            .join(Score, Transaction.transaction_id == Score.transaction_id)
            .filter(Score.routing == "MANUAL_FALLBACK_UNSCORED")
            .order_by(Score.scored_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    @classmethod
    def ingest_simulation_batch(cls, db: Session, count: int = 10, inject_fault: bool = False) -> List[Transaction]:
        """Tiện ích nạp nhanh 1 batch từ simulator_stub để test luồng"""
        batch_data = simulator.get_batch(size=count, inject_fault=inject_fault)
        created_txns = []
        for item in batch_data:
            txn_in = TransactionIngestInput(**item)
            txn = cls.ingest_transaction(db, txn_in, auto_score=True)
            created_txns.append(txn)
        return created_txns


transaction_service = TransactionService()
