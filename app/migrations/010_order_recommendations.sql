CREATE TABLE IF NOT EXISTS order_recommendations (
    id              TEXT PRIMARY KEY,
    msku_code       TEXT NOT NULL,
    hub_code        TEXT NOT NULL DEFAULT 'MDU-HUB',
    total_qty       INTEGER NOT NULL DEFAULT 0,
    status          TEXT NOT NULL DEFAULT 'draft',
    allocation_json TEXT,
    notes           TEXT,
    created_by      TEXT,
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (status IN ('draft','sent_to_executor','returned'))
);

CREATE INDEX IF NOT EXISTS idx_order_recs_msku   ON order_recommendations (msku_code);
CREATE INDEX IF NOT EXISTS idx_order_recs_status ON order_recommendations (status);
