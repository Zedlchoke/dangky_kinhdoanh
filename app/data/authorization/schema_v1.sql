-- Schema v1 — profile người làm thủ tục + audit (module ủy quyền dịch vụ)
-- Không lưu scan CCCD; PII chỉ trong authorized_agent_profiles.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_migrations (
    version     INTEGER PRIMARY KEY,
    applied_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS authorized_agent_profiles (
    agent_id          TEXT PRIMARY KEY,
    ho_ten            TEXT NOT NULL,
    ngay_sinh         TEXT,
    gioi_tinh         TEXT,
    quoc_tich         TEXT DEFAULT 'Việt Nam',
    so_cccd           TEXT NOT NULL,
    ngay_cap          TEXT,
    noi_cap           TEXT,
    dia_chi_lien_he   TEXT,
    dien_thoai        TEXT,
    email             TEXT,
    chuc_danh         TEXT,
    don_vi_dich_vu    TEXT,
    trang_thai        TEXT NOT NULL DEFAULT 'active'
                      CHECK (trang_thai IN ('active', 'locked', 'expired')),
    ghi_chu           TEXT,
    created_at        TEXT NOT NULL,
    updated_at        TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_agent_status ON authorized_agent_profiles(trang_thai);
CREATE INDEX IF NOT EXISTS idx_agent_cccd ON authorized_agent_profiles(so_cccd);

CREATE TABLE IF NOT EXISTS authorization_audit (
    event_id    TEXT PRIMARY KEY,
    event_type  TEXT NOT NULL,
    entity_id   TEXT,
    detail      TEXT,
    created_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_created ON authorization_audit(created_at);

-- Hồ sơ ủy quyền (draft cập nhật theo profile; snapshot khi phát hành — Wave I4)
CREATE TABLE IF NOT EXISTS authorization_cases (
    authorization_id    TEXT PRIMARY KEY,
    case_id             TEXT NOT NULL,
    agent_id            TEXT NOT NULL,
    template_ids_json   TEXT NOT NULL DEFAULT '[]',
    status              TEXT NOT NULL DEFAULT 'draft'
                        CHECK (status IN (
                            'draft', 'ready', 'signed', 'submitted',
                            'revoked', 'expired'
                        )),
    scope_text          TEXT,
    co_quan_tiep_nhan   TEXT,
    thoi_han_den        TEXT,
    draft_meta_json     TEXT,
    snapshot_json       TEXT,
    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL,
    FOREIGN KEY (agent_id) REFERENCES authorized_agent_profiles(agent_id)
);

CREATE INDEX IF NOT EXISTS idx_auth_case_agent ON authorization_cases(agent_id);
CREATE INDEX IF NOT EXISTS idx_auth_case_status ON authorization_cases(status);
