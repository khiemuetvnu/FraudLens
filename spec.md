# TECHNICAL SPECIFICATION: FRAUDLENS (ANALYST WORKFLOW MODULE)

## 1. Mục tiêu giai đoạn hiện tại
Xây dựng hoàn chỉnh **Analyst Workflow Module (FastAPI)** kết nối với **PostgreSQL** theo kiến trúc phân lớp. 
- Toàn bộ các thành phần ngoại vi gồm `ML Scoring`, `LLM RAG`, và `Client Simulator` hiện tại được viết dưới dạng **Stubs (hàm giả lập đồng bộ)** gọi trực tiếp trong code để kiểm thử luồng End-to-End trước khi tách thành Worker chạy qua Redis Queue ở giai đoạn sau.
- Tuân thủ tuyệt đối cấu trúc bảng, tên cột và các ràng buộc `CHECK` trong file `schema.sql` đính kèm.

## 2. Cấu trúc thư mục bắt buộc
```text
fraud_copilot_project/
├── main.py                  # Khởi tạo FastAPI, gắn routers, CORS
├── connections/
│   ├── database.py          # Khai báo Write Engine & ReadOnly Engine (SQLAlchemy)
│   ├── redis_client.py      # Placeholder cho Redis Queue (chưa dùng ở giai đoạn Stub)
│   └── dependencies.py      # get_write_db, get_read_db, get_current_user (JWT & RBAC)
├── models/                  # SQLAlchemy ORM khớp 100% với schema.sql
│   ├── user.py              # Bảng: users, auth_events
│   ├── transaction.py       # Bảng: transactions, scores, delayed_labels
│   ├── case.py              # Bảng: cases, briefs (quan hệ 1-1 với cases), case_notes
│   └── audit_log.py         # Bảng: audit_log
├── schemas/                 # Pydantic v2 DTO (Request / Response)
│   ├── user_schema.py
│   ├── transaction_schema.py
│   └── case_schema.py
├── routers/                 # FastAPI APIRouter
│   ├── auth.py
│   ├── transactions.py
│   ├── cases.py
│   └── audits.py
├── services/                # Business Logic & ORM Queries
│   ├── auth_service.py
│   ├── transaction_service.py
│   └── case_service.py
└── stubs/                   # Các module giả lập
    ├── ml_scoring_stub.py
    ├── llm_rag_stub.py
    └── simulator_stub.py
```
