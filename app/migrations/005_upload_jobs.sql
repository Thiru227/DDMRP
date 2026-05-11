CREATE TABLE IF NOT EXISTS upload_jobs (
    id            TEXT PRIMARY KEY,
    filename      TEXT NOT NULL,
    format        TEXT NOT NULL,
    uploaded_by   TEXT,
    uploaded_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    total_rows    INTEGER NOT NULL DEFAULT 0,
    valid_rows    INTEGER NOT NULL DEFAULT 0,
    invalid_rows  INTEGER NOT NULL DEFAULT 0,
    committed_at  TEXT,
    status        TEXT NOT NULL DEFAULT 'preview',
    rejection_reasons TEXT,
    staged_rows   TEXT,
    CHECK (format IN ('clean','legacy')),
    CHECK (status IN ('preview','committed','rejected','expired'))
);

CREATE INDEX IF NOT EXISTS idx_upload_jobs_uploaded_at ON upload_jobs (uploaded_at DESC);
