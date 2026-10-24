"""
FraudLens - Reset Database Utility
Xóa sạch toàn bộ dữ liệu kiểm thử trên localhost và khởi tạo lại các tài khoản mặc định.
Chạy: d:\\FraudLens\\.conda\\python.exe reset_database.py
"""
import sys
import psycopg
from sqlalchemy import text
from connections.database import WriteSessionLocal
from services.auth_service import auth_service

def reset_db():
    print("🧹 Bắt đầu dọn dẹp cơ sở dữ liệu trên PostgreSQL localhost...")

    truncate_sql = """
    TRUNCATE TABLE 
        audit_log, 
        case_notes, 
        briefs, 
        cases, 
        scores, 
        delayed_labels, 
        transactions, 
        auth_events, 
        users 
    RESTART IDENTITY CASCADE;
    """

    with WriteSessionLocal() as db:
        db.execute(text(truncate_sql))
        db.commit()
        print("✅ Đã dọn sạch toàn bộ dữ liệu trong các bảng nghiệp vụ và audit log.")

        print("👤 Khởi tạo lại các tài khoản mẫu...")
        auth_service.seed_initial_users(db)
        print("✅ Đã tạo sẵn 4 tài khoản mặc định:")
        print("   - admin          (Mật khẩu: AdminPassword123!     | Role: admin)")
        print("   - analyst1       (Mật khẩu: AnalystPassword123!   | Role: analyst)")
        print("   - lead1          (Mật khẩu: LeadPassword123!      | Role: risk_lead)")
        print("   - simulator_svc  (Mật khẩu: ServicePassword123!   | Role: service)")

    print("\n🎉 CƠ SỞ DỮ LIỆU ĐÃ SẴN SÀNG VÀ HOÀN TOÀN TRẮNG ĐỂ BẮT ĐẦU TEST MỚI!")

if __name__ == "__main__":
    reset_db()
