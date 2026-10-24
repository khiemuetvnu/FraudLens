CREATE TABLE users (
    user_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username        TEXT NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,
    role            TEXT NOT NULL CHECK (role IN ('analyst', 'risk_lead', 'admin', 'service')),
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE auth_events (
    id              BIGSERIAL PRIMARY KEY,
    occurred_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    username        TEXT NOT NULL,
    event_type      TEXT NOT NULL CHECK (event_type IN ('login_success', 'login_failed', 'logout')),
    ip_address      TEXT
);

CREATE TABLE transactions (
    transaction_id  TEXT PRIMARY KEY,
    cc_num          TEXT NOT NULL,
    merchant        TEXT NOT NULL,
    category        TEXT NOT NULL,
    amt             NUMERIC NOT NULL,
    first_name      TEXT,
    last_name       TEXT,
    gender          TEXT,
    street          TEXT,
    city            TEXT,
    state           TEXT,
    zip             TEXT,
    lat             NUMERIC,
    long            NUMERIC,
    city_pop        INTEGER,
    job             TEXT,
    dob             DATE,
    merch_lat       NUMERIC,
    merch_long      NUMERIC,
    trans_time      TIMESTAMPTZ NOT NULL,
    unix_time       BIGINT NOT NULL,
    input_status    TEXT NOT NULL CHECK (input_status IN ('VALID', 'INVALID')),
    received_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_pushed_at  TIMESTAMPTZ
);
CREATE INDEX idx_txn_cc_time ON transactions (cc_num, trans_time);
CREATE INDEX idx_txn_unscored ON transactions (received_at) WHERE input_status = 'VALID';

CREATE TABLE scores (
    transaction_id           TEXT PRIMARY KEY REFERENCES transactions(transaction_id),
    risk_score               NUMERIC NOT NULL,
    calibrated_prob          NUMERIC,
    routing                  TEXT NOT NULL CHECK (routing IN ('LOW', 'MEDIUM', 'HIGH', 'MANUAL_FALLBACK_UNSCORED')),
    model_version            TEXT NOT NULL,
    threshold_config_version TEXT NOT NULL,
    features                 JSONB NOT NULL,
    scored_at                TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_scores_routing ON scores (routing, scored_at);

CREATE TABLE cases (
    case_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id  TEXT NOT NULL UNIQUE REFERENCES transactions(transaction_id),
    source          TEXT NOT NULL CHECK (source IN ('AUTO', 'MANUAL')),
    manual_reason   TEXT,
    priority        TEXT NOT NULL CHECK (priority IN ('MEDIUM', 'HIGH')),
    status          TEXT NOT NULL DEFAULT 'NEW'
                    CHECK (status IN ('NEW', 'UNDER_REVIEW', 'NEEDS_MORE_INFO', 'ESCALATED', 'CLOSED')),
    outcome         TEXT CHECK (outcome IN ('CONFIRMED_FRAUD_SIM', 'DISMISSED', 'INSUFFICIENT_EVIDENCE')),
    assigned_to     UUID REFERENCES users(user_id),
    version         INTEGER NOT NULL DEFAULT 1,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_cases_queue ON cases (status, priority, created_at);
CREATE INDEX idx_cases_assigned ON cases (assigned_to, status);

-- Quan hệ 1-1 với cases (case_id là UNIQUE), sinh lại sẽ UPDATE đè lên dòng cũ
CREATE TABLE briefs (
    brief_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id           UUID NOT NULL UNIQUE REFERENCES cases(case_id),
    prompt_version    TEXT NOT NULL,
    playbook_version  TEXT NOT NULL,
    status            TEXT NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'READY', 'FAILED')),
    content           JSONB,
    requested_by      UUID REFERENCES users(user_id),
    last_pushed_at    TIMESTAMPTZ,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_briefs_pending ON briefs (status, created_at) WHERE status = 'PENDING';

CREATE TABLE case_notes (
    note_id     BIGSERIAL PRIMARY KEY,
    case_id     UUID NOT NULL REFERENCES cases(case_id),
    author_id   UUID NOT NULL REFERENCES users(user_id),
    content     TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_notes_case ON case_notes (case_id, created_at);

CREATE TABLE delayed_labels (
    transaction_id  TEXT PRIMARY KEY REFERENCES transactions(transaction_id),
    is_fraud        BOOLEAN NOT NULL,
    available_at    TIMESTAMPTZ NOT NULL
);

CREATE TABLE audit_log (
    id            BIGSERIAL PRIMARY KEY,
    occurred_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    request_id    UUID NOT NULL,
    actor_id      TEXT NOT NULL,
    action        TEXT NOT NULL,
    entity_type   TEXT NOT NULL,
    entity_id     TEXT NOT NULL,
    before_state  JSONB,
    after_state   JSONB,
    meta          JSONB
);
CREATE INDEX idx_audit_entity ON audit_log (entity_type, entity_id, occurred_at);
CREATE INDEX idx_audit_request ON audit_log (request_id);

-- Trigger có COALESCE để không bị lỗi crash khi backend quên SET LOCAL
CREATE OR REPLACE FUNCTION audit_case_status() RETURNS trigger AS $$
BEGIN
    IF NEW.status IS DISTINCT FROM OLD.status OR NEW.outcome IS DISTINCT FROM OLD.outcome THEN
        INSERT INTO audit_log (request_id, actor_id, action, entity_type, entity_id, before_state, after_state)
        VALUES (
            COALESCE(NULLIF(current_setting('app.request_id', true), '')::uuid, gen_random_uuid()),
            COALESCE(NULLIF(current_setting('app.actor_id', true), ''), 'system'),
            'case.status_change',
            'case',
            OLD.case_id::text,
            jsonb_build_object('status', OLD.status, 'outcome', OLD.outcome),
            jsonb_build_object('status', NEW.status, 'outcome', NEW.outcome)
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_case_audit
    AFTER UPDATE ON cases
    FOR EACH ROW EXECUTE FUNCTION audit_case_status();
