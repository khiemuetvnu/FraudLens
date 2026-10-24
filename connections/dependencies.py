"""
FraudLens - Dependencies (Database Sessions, JWT Authentication & RBAC)
"""
import uuid
from typing import Generator, List, Optional
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from sqlalchemy.orm import Session
from sqlalchemy import text

from connections.database import WriteSessionLocal, ReadOnlySessionLocal
from models.user import User

# Configuration for JWT (can be overridden via ENV)
JWT_SECRET_KEY = "fraudlens-secret-super-key-change-in-production"
JWT_ALGORITHM = "HS256"

security = HTTPBearer(auto_error=False)


def get_write_db() -> Generator[Session, None, None]:
    """Dependency helper mở và đóng session DB Write (Master)"""
    db = WriteSessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_read_db() -> Generator[Session, None, None]:
    """Dependency helper mở và đóng session DB ReadOnly (Replica)"""
    db = ReadOnlySessionLocal()
    try:
        yield db
    finally:
        db.close()


def set_audit_context(db: Session, actor_id: str, request_id: Optional[str] = None):
    """
    Thiết lập biến môi trường session của PostgreSQL (SET LOCAL app.request_id, app.actor_id)
    để Trigger trg_case_audit tự động ghi nhận chính xác actor_id và request_id vào audit_log.
    """
    req_id = request_id or str(uuid.uuid4())
    try:
        db.execute(text(f"SET LOCAL app.request_id = '{req_id}'"))
        db.execute(text(f"SET LOCAL app.actor_id = '{actor_id}'"))
    except Exception:
        pass


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_read_db)
) -> User:
    """Xác thực JWT token từ Header Authorization: Bearer <token>"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        username: str = payload.get("sub")
        if not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account"
        )

    return user


def require_role(allowed_roles: List[str]):
    """RBAC Dependency Factory kiểm tra quyền người dùng"""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: user role '{current_user.role}' is not in allowed roles {allowed_roles}"
            )
        return current_user
    return role_checker
