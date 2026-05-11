CREATE TABLE IF NOT EXISTS alerts (
    id            TEXT PRIMARY KEY,
    msku_code     TEXT NOT NULL,
    branch_code   TEXT NOT NULL,
    alert_type    TEXT NOT NULL,
    severity      TEXT NOT NULL,
    message       TEXT NOT NULL,
    created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved      INTEGER NOT NULL DEFAULT 0,
    resolved_at   TEXT,
    CHECK (alert_type IN ('red','yellow')),
    CHECK (severity IN ('high','medium'))
);

CREATE INDEX IF NOT EXISTS idx_alerts_pair_resolved ON alerts (msku_code, branch_code, resolved);
