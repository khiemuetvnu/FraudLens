"""
FraudLens - Authentication & User Service
Xử lý mã hóa mật khẩu, JWT Token, RBAC và ghi nhật ký auth_events.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import bcrypt
import jwt
from sqlalchemy.orm import Session

from models.user import User, AuthEvent
from connections.dependencies import JWT_SECRET_KEY, JWT_ALGORITHM

ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 12  # 12 hours


class AuthService:
    @staticmethod
    def hash_password(password: str) -> str:
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        try:
            return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
        except Exception:
            return False

    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        to_encode = data.copy()
        now = datetime.now(timezone.utc)
        if expires_delta:
            expire = now + expires_delta
        else:
            expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire, "iat": now})
        return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

    @staticmethod
    def log_auth_event(db: Session, username: str, event_type: str, ip_address: Optional[str] = None):
        """Ghi nhận sự kiện xác thực vào bảng auth_events"""
        try:
            event = AuthEvent(
                username=username,
                event_type=event_type,
                ip_address=ip_address
            )
            db.add(event)
            db.commit()
        except Exception:
            db.rollback()

    @classmethod
    def authenticate_user(
        cls,
        db: Session,
        username: str,
        password: str,
        ip_address: Optional[str] = None
    ) -> Optional[User]:
        user = db.query(User).filter(User.username == username).first()
        if not user or not cls.verify_password(password, user.password_hash):
            cls.log_auth_event(db, username=username, event_type="login_failed", ip_address=ip_address)
            return None

        if not user.is_active:
            cls.log_auth_event(db, username=username, event_type="login_failed", ip_address=ip_address)
            return None

        cls.log_auth_event(db, username=username, event_type="login_success", ip_address=ip_address)
        return user

    @classmethod
    def create_user(
        cls,
        db: Session,
        username: str,
        password: str,
        role: str,
        is_active: bool = True
    ) -> User:
        user = User(
            username=username,
            password_hash=cls.hash_password(password),
            role=role,
            is_active=is_active
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @classmethod
    def seed_initial_users(cls, db: Session):
        """Khởi tạo tài khoản mẫu nếu hệ thống chưa có dữ liệu người dùng"""
        count = db.query(User).count()
        if count == 0:
            initial_accounts = [
                ("admin", "AdminPassword123!", "admin"),
                ("analyst1", "AnalystPassword123!", "analyst"),
                ("lead1", "LeadPassword123!", "risk_lead"),
                ("simulator_svc", "ServicePassword123!", "service"),
            ]
            for username, pwd, role in initial_accounts:
                cls.create_user(db, username=username, password=pwd, role=role)


auth_service = AuthService()
