"""
FraudLens - Analyst Workflow Module (FastAPI)
System Architecture: Service-based, PostgreSQL Write/Read-Replica, Stubs for ML/LLM/Simulator.
"""
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from connections.database import WriteSessionLocal
from services.auth_service import auth_service
from routers import auth, transactions, cases, audits


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Khởi tạo và nạp tài khoản ban đầu nếu DB chưa có
    db = WriteSessionLocal()
    try:
        auth_service.seed_initial_users(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="FraudLens - Analyst Workflow Module",
    description="Hệ thống hỗ trợ chuyên viên phát hiện, sắp xếp ưu tiên và điều tra các giao dịch có dấu hiệu gian lận.",
    version="1.0.0",
    lifespan=lifespan
)

# Cấu hình CORS cho Web App / UI Dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id_and_audit_middleware(request: Request, call_next):
    """
    Middleware gắn Request-ID cho mỗi request và đưa vào response header.
    Request-ID phục vụ truy vết kiểm toán xuyên suốt (Traceability).
    """
    req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = req_id

    response = await call_next(request)
    response.headers["X-Request-ID"] = req_id
    return response


# Mount các APIRouters
app.include_router(auth.router)
app.include_router(transactions.router)
app.include_router(cases.router)
app.include_router(audits.router)


@app.get("/", tags=["Health"])
def root():
    return {
        "service": "FraudLens Analyst Workflow Module",
        "status": "HEALTHY",
        "version": "1.0.0",
        "docs_url": "/docs"
    }


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
