"""
FraudLens - Authentication & User Management Router
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from connections.dependencies import get_write_db, get_read_db, get_current_user, require_role
from models.user import User, AuthEvent
from schemas.user_schema import (
    UserLogin,
    UserCreate,
    UserResponse,
    TokenResponse,
    AuthEventResponse
)
from services.auth_service import auth_service

router = APIRouter(prefix="/api/auth", tags=["Authentication & Users"])


@router.post("/login", response_model=TokenResponse)
def login(
    payload: UserLogin,
    request: Request,
    db: Session = Depends(get_write_db)
):
    """Đăng nhập hệ thống và cấp JWT Bearer Token"""
    ip_addr = request.client.host if request.client else None
    user = auth_service.authenticate_user(
        db,
        username=payload.username,
        password=payload.password,
        ip_address=ip_addr
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tên đăng nhập hoặc mật khẩu không chính xác"
        )

    token = auth_service.create_access_token({
        "sub": user.username,
        "user_id": str(user.user_id),
        "role": user.role
    })

    return TokenResponse(
        access_token=token,
        role=user.role,
        username=user.username,
        user_id=user.user_id
    )


@router.post("/logout")
def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_write_db)
):
    """Đăng xuất và ghi nhận nhật ký auth_events"""
    ip_addr = request.client.host if request.client else None
    auth_service.log_auth_event(
        db,
        username=current_user.username,
        event_type="logout",
        ip_address=ip_addr
    )
    return {"message": "Đăng xuất thành công"}


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Lấy thông tin tài khoản đang đăng nhập"""
    return current_user


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_new_user(
    payload: UserCreate,
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_write_db)
):
    """Admin tạo tài khoản người dùng mới (Analyst, Risk Lead, Service)"""
    existing = db.query(User).filter(User.username == payload.username).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tên tài khoản '{payload.username}' đã tồn tại."
        )

    return auth_service.create_user(
        db,
        username=payload.username,
        password=payload.password,
        role=payload.role
    )


@router.get("/users", response_model=List[UserResponse])
def list_users(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(require_role(["admin", "risk_lead"])),
    db: Session = Depends(get_read_db)
):
    """Danh sách người dùng hệ thống"""
    return db.query(User).offset(skip).limit(limit).all()


@router.get("/events", response_model=List[AuthEventResponse])
def list_auth_events(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_read_db)
):
    """Admin xem nhật ký đăng nhập/đăng xuất"""
    return db.query(AuthEvent).order_by(AuthEvent.occurred_at.desc()).offset(skip).limit(limit).all()
