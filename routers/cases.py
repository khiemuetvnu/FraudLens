"""
FraudLens - Cases Router
Quản lý Hàng đợi Điều tra (Review Queue), Chi tiết Case, Ghi nhận điều tra (Case Notes),
Chuyển cấp (Escalate), Phê duyệt/Đóng case và Sinh lại LLM Brief.
"""
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from connections.dependencies import get_write_db, get_read_db, get_current_user, require_role
from models.user import User
from schemas.case_schema import (
    CaseResponse,
    CaseDetailResponse,
    CaseCreateManual,
    CaseStatusUpdate,
    CaseOutcomeUpdate,
    CaseAssignUpdate,
    CaseNoteCreate,
    CaseNoteResponse,
    BriefResponse
)
from services.case_service import case_service

router = APIRouter(prefix="/api/cases", tags=["Investigation Cases"])


@router.get("/", response_model=List[CaseResponse])
def get_review_queue(
    status_filter: Optional[str] = Query(None, description="NEW, UNDER_REVIEW, NEEDS_MORE_INFO, ESCALATED, CLOSED"),
    priority_filter: Optional[str] = Query(None, description="MEDIUM, HIGH"),
    assigned_to: Optional[uuid.UUID] = Query(None, description="Lọc theo chuyên viên phụ trách"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_read_db)
):
    """
    Hàng đợi điều tra (Review Queue):
    Sắp xếp ưu tiên rủi ro HIGH lên trước, theo thời gian khởi tạo giảm dần.
    """
    return case_service.list_cases(
        db,
        status_filter=status_filter,
        priority_filter=priority_filter,
        assigned_to=assigned_to,
        skip=skip,
        limit=limit
    )


@router.get("/{case_id}", response_model=CaseDetailResponse)
def get_case_detail(
    case_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_read_db)
):
    """Xem chi tiết toàn diện hồ sơ điều tra gồm giao dịch gốc, điểm rủi ro, LLM Brief và Notes"""
    case = case_service.get_case_by_id(db, case_id=case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
    
    # Chuẩn bị dữ liệu trả về kèm quan hệ
    res = CaseDetailResponse.model_validate(case)
    if case.transaction:
        res.transaction = case.transaction
        if case.transaction.score:
            res.score = case.transaction.score
    if case.brief:
        res.brief = case.brief
    if case.notes:
        note_list = []
        for n in case.notes:
            n_res = CaseNoteResponse.model_validate(n)
            n_res.author_username = n.author.username if n.author else None
            note_list.append(n_res)
        res.notes = note_list
    return res


@router.post("/manual", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
def create_case_manual(
    payload: CaseCreateManual,
    current_user: User = Depends(require_role(["analyst", "risk_lead", "admin"])),
    db: Session = Depends(get_write_db)
):
    """
    Bước 3 (Nhánh 2): Chuyên viên chủ động tạo Case thủ công
    cho giao dịch đáng ngờ dù ML đánh giá mức thấp hoặc unscored.
    """
    return case_service.create_case_manual(
        db,
        transaction_id=payload.transaction_id,
        manual_reason=payload.manual_reason,
        priority=payload.priority,
        user=current_user
    )


@router.put("/{case_id}/status", response_model=CaseResponse)
def update_case_status(
    case_id: uuid.UUID,
    payload: CaseStatusUpdate,
    request: Request,
    current_user: User = Depends(require_role(["analyst", "risk_lead", "admin"])),
    db: Session = Depends(get_write_db)
):
    """
    Bước 5: Cập nhật trạng thái xử lý trên Case.
    - Chuyên viên có thể chuyển: UNDER_REVIEW, NEEDS_MORE_INFO, ESCALATED.
    - Chỉ Risk Lead hoặc Admin mới có quyền chuyển: CLOSED (hoặc mở lại case).
    - Tự động kích hoạt Trigger audit_case_status ghi vào audit_log.
    """
    req_id = getattr(request.state, "request_id", None)
    return case_service.update_case_status(
        db,
        case_id=case_id,
        new_status=payload.status,
        user=current_user,
        request_id=req_id
    )


@router.put("/{case_id}/outcome", response_model=CaseResponse)
def update_case_outcome(
    case_id: uuid.UUID,
    payload: CaseOutcomeUpdate,
    request: Request,
    current_user: User = Depends(require_role(["analyst", "risk_lead", "admin"])),
    db: Session = Depends(get_write_db)
):
    """
    Bước 5: Kết luận vụ việc (outcome).
    Giá trị: CONFIRMED_FRAUD_SIM, DISMISSED, INSUFFICIENT_EVIDENCE.
    Tự động ghi vết vào bảng audit_log qua Trigger.
    """
    req_id = getattr(request.state, "request_id", None)
    return case_service.update_case_outcome(
        db,
        case_id=case_id,
        outcome=payload.outcome,
        user=current_user,
        request_id=req_id
    )


@router.put("/{case_id}/assign", response_model=CaseResponse)
def assign_case(
    case_id: uuid.UUID,
    payload: CaseAssignUpdate,
    current_user: User = Depends(require_role(["risk_lead", "admin", "analyst"])),
    db: Session = Depends(get_write_db)
):
    """Phân công chuyên viên phụ trách hồ sơ điều tra"""
    return case_service.assign_case(
        db,
        case_id=case_id,
        assigned_to=payload.assigned_to,
        user=current_user
    )


@router.post("/{case_id}/notes", response_model=CaseNoteResponse, status_code=status.HTTP_201_CREATED)
def add_case_note(
    case_id: uuid.UUID,
    payload: CaseNoteCreate,
    current_user: User = Depends(require_role(["analyst", "risk_lead", "admin"])),
    db: Session = Depends(get_write_db)
):
    """
    Bước 5: Ghi nhận nhận định điều tra (Case Notes).
    Nguyên tắc bảo toàn chứng cứ: chỉ cho phép thêm mới (append-only), không cho phép sửa/xóa.
    """
    note = case_service.add_case_note(
        db,
        case_id=case_id,
        author_id=current_user.user_id,
        content=payload.content
    )
    res = CaseNoteResponse.model_validate(note)
    res.author_username = current_user.username
    return res


@router.post("/{case_id}/brief/regenerate", response_model=BriefResponse)
def regenerate_brief(
    case_id: uuid.UUID,
    current_user: User = Depends(require_role(["analyst", "risk_lead", "admin"])),
    db: Session = Depends(get_write_db)
):
    """
    Bước 4 (Thủ công): Chuyên viên yêu cầu tạo lại Brief bằng LLM & Playbook RAG.
    Ghi đè cập nhật vào bản ghi briefs hiện có (tuân thủ quan hệ 1-1).
    """
    return case_service.regenerate_brief(
        db,
        case_id=case_id,
        user=current_user
    )
