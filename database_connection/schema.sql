-- ========================================================
-- FRAUDLENS DATABASE SCHEMA (PostgreSQL)
-- Core Tables for Transaction Fraud Triage & Investigation
-- ========================================================

-- 1. BẢNG TRANSACTIONS (Lưu giao dịch khớp trực tiếp với CSV)
CREATE TABLE IF NOT EXISTS transactions (
    transaction_id VARCHAR(64) PRIMARY KEY,          -- Dùng chính trans_num từ CSV
    trans_date_trans_time TIMESTAMP NOT NULL,
    cc_num VARCHAR(32) NOT NULL,                     -- Lưu trực tiếp số thẻ từ CSV
    merchant VARCHAR(128) NOT NULL,
    category VARCHAR(64) NOT NULL,
    amt NUMERIC(12, 2) NOT NULL,
    first_name VARCHAR(64),
    last_name VARCHAR(64),
    gender VARCHAR(8),
    street VARCHAR(128),
    city VARCHAR(64),
    state VARCHAR(32),
    zip VARCHAR(16),
    lat NUMERIC(9, 6),
    long NUMERIC(9, 6),
    city_pop INTEGER,
    job VARCHAR(128),
    dob DATE,
    trans_num VARCHAR(64) UNIQUE,
    unix_time BIGINT,
    merch_lat NUMERIC(9, 6),
    merch_long NUMERIC(9, 6),
    distance_km NUMERIC(10, 2),                      -- Khoảng cách (km)
    validation_status VARCHAR(32) DEFAULT 'VALID',    -- VALID, INVALID
    is_fraud_ground_truth INTEGER DEFAULT 0,         -- Cột is_fraud từ CSV (0/1)
    raw_payload JSONB,                               -- JSON gốc (tùy chọn)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_trans_time ON transactions(trans_date_trans_time);
CREATE INDEX IF NOT EXISTS idx_trans_status ON transactions(validation_status);


-- 2. BẢNG CASES (Hàng đợi điều tra & Kết quả chấm điểm ML)
-- Nhận điểm từ Scoring Module và quản lý trạng thái xử lý của Analyst
CREATE TABLE IF NOT EXISTS cases (
    case_id VARCHAR(64) PRIMARY KEY,                 -- Ví dụ: CASE-2026-XXXX
    transaction_id VARCHAR(64) NOT NULL REFERENCES transactions(transaction_id) ON DELETE CASCADE,
    risk_score NUMERIC(5, 4),                        -- Điểm rủi ro ML chấm (0.0000 - 1.0000)
    risk_level VARCHAR(16) DEFAULT 'PENDING',        -- PENDING, LOW, MEDIUM, HIGH, UNSCORED_ERROR
    model_version VARCHAR(32) DEFAULT 'v1.0.0',      -- Phiên bản mô hình ML đã chấm
    feature_contributions JSONB,                     -- Top các yếu tố đáng ngờ (SHAP / Explainability)
    status VARCHAR(32) DEFAULT 'PENDING_REVIEW',     -- PENDING_REVIEW, UNDER_INVESTIGATION, RESOLVED_FRAUD, RESOLVED_LEGITIMATE, ESCALATED
    priority VARCHAR(16) DEFAULT 'NORMAL',           -- NORMAL, HIGH, CRITICAL
    assigned_analyst VARCHAR(64),                    -- Tên / ID chuyên viên phụ trách
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_cases_risk_level ON cases(risk_level);
CREATE INDEX IF NOT EXISTS idx_cases_status ON cases(status);
CREATE INDEX IF NOT EXISTS idx_cases_trans_id ON cases(transaction_id);


-- 3. BẢNG CASE_BRIEFS (Sản phẩm của LLM Module & RAG Playbook)
CREATE TABLE IF NOT EXISTS case_briefs (
    brief_id VARCHAR(64) PRIMARY KEY,
    case_id VARCHAR(64) NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    summary TEXT,                                    -- Tóm tắt bối cảnh giao dịch
    risk_factors_explained JSONB,                    -- Giải thích các tín hiệu rủi ro
    investigation_checklist JSONB,                   -- Checklist các bước xác minh kèm tick-box
    playbook_citations JSONB,                        -- Trích dẫn nguồn quy trình Playbook (VD: PB-GEO-01)
    llm_model VARCHAR(64) DEFAULT 'gemini-1.5-flash',
    llm_status VARCHAR(16) DEFAULT 'PENDING',        -- PENDING, GENERATING, COMPLETED, FAILED
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_briefs_case_id ON case_briefs(case_id);


-- 4. BẢNG AUDIT_LOGS (Ghi nhận thao tác & quyết định của Analyst - FR-06, FR-08)
CREATE TABLE IF NOT EXISTS audit_logs (
    log_id BIGSERIAL PRIMARY KEY,
    case_id VARCHAR(64) NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    analyst_id VARCHAR(64) NOT NULL,
    action VARCHAR(64) NOT NULL,                     -- VIEW_CASE, ADD_NOTE, CLOSE_FRAUD, CLOSE_LEGIT, ESCALATE
    notes TEXT,                                      -- Nhận định của Analyst
    checklist_progress JSONB,                        -- Tiến độ các bước checklist đã làm
    metadata JSONB,                                  -- Thông tin bổ sung
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audit_case_id ON audit_logs(case_id);