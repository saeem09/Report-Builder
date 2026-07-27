CREATE TABLE IF NOT EXISTS reports (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    logo_file_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS report_fields (
    id TEXT PRIMARY KEY,
    report_id TEXT NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    label TEXT NOT NULL,
    content TEXT NOT NULL DEFAULT '',
    sort_order INTEGER NOT NULL,
    is_user_edited INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS report_sources (
    id TEXT PRIMARY KEY,
    report_id TEXT NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    file_id TEXT NOT NULL,
    original_name TEXT NOT NULL,
    cleaned_text TEXT NOT NULL,
    sort_order INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS diagrams (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    logo_file_id TEXT,
    bpmn_xml TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS files (
    id TEXT PRIMARY KEY,
    original_name TEXT NOT NULL,
    stored_path TEXT NOT NULL,
    content_type TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_report_fields_report_id
    ON report_fields (report_id, sort_order);

CREATE INDEX IF NOT EXISTS idx_report_sources_report_id
    ON report_sources (report_id, sort_order);

CREATE INDEX IF NOT EXISTS idx_reports_updated_at
    ON reports (updated_at DESC);
