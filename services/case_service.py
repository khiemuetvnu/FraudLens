"""
FraudLens - Case Service
Quản lý vòng đời hồ sơ điều tra (Case Lifecycle), quan hệ 1-1 với Brief,
ghi nhận Case Note (append-only) và đảm bảo Audit Log qua Trigger.
"""
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from models.case import Case, Brief, CaseNote
from models.transaction import Transaction, Score
from models.user import User
from stubs.llm_rag_stub import llm_rag
from connections.dependencies import set_audit_context


class CaseService:
    @classmethod
    def get_case_by_id(cls, db: Session, case_id: uuid.UUID) -> Optional[Case]:
        return db.query(Case).filter(Case.case_id == case_id).first()

    @classmethod
    def get_case_by_transaction_id(cls, db: Session, transaction_id: str) -> Optional[Case]:
        return db.query(Case).filter(Case.transaction_id == transaction_id).first()

    @classmethod
    def create_case_auto(
        cls,
        db: Session,
        transaction_id: str,
        priority: str = "MEDIUM"
    ) -> Optional[Case]:
        """Tự động tạo case khi ML chấm điểm ra MEDIUM hoặc HIGH"""
        # Kiểm tra quy tắc 1-1: giao dịch đã có case chưa
        existing_case = cls.get_case_by_transaction_id(db, transaction_id)
        if existing_case:
            return existing_case

        valid_priority = "HIGH" if priority == "HIGH" else "MEDIUM"
        new_case = Case(
            transaction_id=transaction_id,
            source="AUTO",
            priority=valid_priority,
            status="NEW",
            version=1
        )
        db.add(new_case)
        db.flush()

        # Tự động sinh LLM Brief
        cls._generate_and_save_brief(db, new_case)

        db.commit()
        db.refresh(new_case)
        return new_case

    @classmethod
    def create_case_manual(
        cls,
        db: Session,
        transaction_id: str,
        manual_reason: str,
        priority: str,
        user: User
    ) -> Case:
        """Analyst tạo case thủ công khi phát hiện giao dịch đáng ngờ"""
        # 1. Kiểm tra giao dịch tồn tại
        txn = db.query(Transaction).filter(Transaction.transaction_id == transaction_id).first()
        if not txn:
            raise HTTPException(status_code=404, detail=f"Transaction {transaction_id} not found")

        # 2. Kiểm tra điều kiện tiên quyết: phải có score trước khi tạo case
        score = db.query(Score).filter(Score.transaction_id == transaction_id).first()
        if not score:
            raise HTTPException(
                status_code=400,
                detail=f"Transaction {transaction_id} has not been scored yet. Please trigger ML scoring first."
            )

        # 3. Kiểm tra quan hệ 1-1
        existing_case = cls.get_case_by_transaction_id(db, transaction_id)
        if existing_case:
            raise HTTPException(
                status_code=400,
                detail=f"Case already exists for transaction {transaction_id} (Case ID: {existing_case.case_id})"
            )

        valid_priority = "HIGH" if priority == "HIGH" else "MEDIUM"
        new_case = Case(
            transaction_id=transaction_id,
            source="MANUAL",
            manual_reason=manual_reason,
            priority=valid_priority,
            status="NEW",
            assigned_to=user.user_id,
            version=1
        )
        db.add(new_case)
        db.flush()

        # Tự động sinh Brief cho case mới
        cls._generate_and_save_brief(db, new_case, requested_by=user.user_id)

        db.commit()
        db.refresh(new_case)
        return new_case

    @classmethod
    def _generate_and_save_brief(
        cls,
        db: Session,
        case: Case,
        requested_by: Optional[uuid.UUID] = None
    ) -> Brief:
        """Gọi LLM RAG Stub và lưu/ghi đè bản ghi briefs (quan hệ 1-1)"""
        txn = db.query(Transaction).filter(Transaction.transaction_id == case.transaction_id).first()
        score = db.query(Score).filter(Score.transaction_id == case.transaction_id).first()

        txn_dict = {
            "transaction_id": txn.transaction_id if txn else "",
            "merchant": txn.merchant if txn else "",
            "amt": float(txn.amt) if txn else 0.0,
            "category": txn.category if txn else ""
        }
        score_dict = {
            "routing": score.routing if score else "MEDIUM",
            "risk_score": float(score.risk_score) if score else 0.5
        }

        # Gọi LLM RAG Stub
        brief_data = llm_rag.generate_case_brief(txn_dict, score_dict)

        existing_brief = db.query(Brief).filter(Brief.case_id == case.case_id).first()
        if existing_brief:
            # Ghi đè cập nhật nếu đã tồn tại (Regenerate flow)
            existing_brief.prompt_version = brief_data["prompt_version"]
            existing_brief.playbook_version = brief_data["playbook_version"]
            existing_brief.status = brief_data["status"]
            existing_brief.content = brief_data["content"]
            existing_brief.requested_by = requested_by or existing_brief.requested_by
            existing_brief.updated_at = datetime.now()
            db.flush()
            return existing_brief
        else:
            new_brief = Brief(
                case_id=case.case_id,
                prompt_version=brief_data["prompt_version"],
                playbook_version=brief_data["playbook_version"],
                status=brief_data["status"],
                content=brief_data["content"],
                requested_by=requested_by
            )
            db.add(new_brief)
            db.flush()
            return new_brief

    @classmethod
    def regenerate_brief(cls, db: Session, case_id: uuid.UUID, user: User) -> Brief:
        """Analyst bấm tạo lại Brief (Cold Path Regenerate)"""
        case = cls.get_case_by_id(db, case_id)
        if not case:
            raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

        brief = cls._generate_and_save_brief(db, case, requested_by=user.user_id)
        db.commit()
        db.refresh(brief)
        return brief

    @classmethod
    def add_case_note(cls, db: Session, case_id: uuid.UUID, author_id: uuid.UUID, content: str) -> CaseNote:
        """Ghi nhận ghi chú điều tra (append-only)"""
        case = cls.get_case_by_id(db, case_id)
        if not case:
            raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

        note = CaseNote(
            case_id=case_id,
            author_id=author_id,
            content=content
        )
        db.add(note)
        db.commit()
        db.refresh(note)
        return note

    @classmethod
    def update_case_status(
        cls,
        db: Session,
        case_id: uuid.UUID,
        new_status: str,
        user: User,
        request_id: Optional[str] = None
    ) -> Case:
        """
        Cập nhật trạng thái case và kích hoạt Database Trigger ghi Audit Log.
        Kiểm tra quyền trạng thái theo vai trò (Analyst vs Risk Lead).
        """
        case = cls.get_case_by_id(db, case_id)
        if not case:
            raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

        # Phân quyền chuyển trạng thái:
        # - Chỉ Risk Lead mới có quyền chuyển sang CLOSED
        if new_status == "CLOSED" and user.role not in ["risk_lead", "admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Risk Lead or Admin can close a case."
            )

        # Thiết lập session settings cho trigger audit_case_status
        set_audit_context(db, actor_id=user.username, request_id=request_id)

        case.status = new_status
        case.version += 1
        case.updated_at = datetime.now()
        db.commit()
        db.refresh(case)
        return case

    @classmethod
    def update_case_outcome(
        cls,
        db: Session,
        case_id: uuid.UUID,
        outcome: str,
        user: User,
        request_id: Optional[str] = None
    ) -> Case:
        """Cập nhật kết luận vụ việc (outcome)"""
        case = cls.get_case_by_id(db, case_id)
        if not case:
            raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

        valid_outcomes = {'CONFIRMED_FRAUD_SIM', 'DISMISSED', 'INSUFFICIENT_EVIDENCE'}
        if outcome not in valid_outcomes:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid outcome '{outcome}'. Must be one of {valid_outcomes}"
            )

        set_audit_context(db, actor_id=user.username, request_id=request_id)

        case.outcome = outcome
        case.version += 1
        case.updated_at = datetime.now()
        db.commit()
        db.refresh(case)
        return case

    @classmethod
    def assign_case(cls, db: Session, case_id: uuid.UUID, assigned_to: Optional[uuid.UUID], user: User) -> Case:
        """Gán chuyên viên phụ trách vụ việc"""
        case = cls.get_case_by_id(db, case_id)
        if not case:
            raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

        if assigned_to:
            assignee = db.query(User).filter(User.user_id == assigned_to).first()
            if not assignee:
                raise HTTPException(status_code=404, detail="Assigned user not found")

        case.assigned_to = assigned_to
        case.version += 1
        case.updated_at = datetime.now()
        db.commit()
        db.refresh(case)
        return case

    @classmethod
    def list_cases(
        cls,
        db: Session,
        status_filter: Optional[str] = None,
        priority_filter: Optional[str] = None,
        assigned_to: Optional[uuid.UUID] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[Case]:
        query = db.query(Case)
        if status_filter:
            query = query.filter(Case.status == status_filter)
        if priority_filter:
            query = query.filter(Case.priority == priority_filter)
        if assigned_to:
            query = query.filter(Case.assigned_to == assigned_to)

        # Sắp xếp ưu tiên: HIGH trước, sau đó theo created_at giảm dần
        return query.order_by(Case.priority.desc(), Case.created_at.desc()).offset(skip).limit(limit).all()


case_service = CaseService()
