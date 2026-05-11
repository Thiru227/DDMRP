-- Recreate upload_jobs allowing format = 'sales' in addition to 'legacy' and 'clean'.
-- SQLite does not support ALTER TABLE ... ALTER CONSTRAINT, so we recreate the table.

CREATE TABLE IF NOT EXISTS upload_jobs_new (
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
    CHECK (format IN ('clean','legacy','sales')),
    CHECK (status IN ('preview','committed','rejected','expired'))
);

INSERT INTO upload_jobs_new SELECT * FROM upload_jobs;
DROP TABLE upload_jobs;
ALTER TABLE upload_jobs_new RENAME TO upload_jobs;

CREATE INDEX IF NOT EXISTS idx_upload_jobs_uploaded_at ON upload_jobs (uploaded_at DESC);
