CREATE TABLE IF NOT EXISTS rs_sequence (
    year     INTEGER PRIMARY KEY,
    last_num INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS requirement_slips (
    id              TEXT PRIMARY KEY,
    order_rec_id    TEXT NOT NULL,
    msku_code       TEXT NOT NULL,
    total_qty       INTEGER NOT NULL DEFAULT 0,
    status          TEXT NOT NULL DEFAULT 'pending_release',
    sent_at         TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    released_by     TEXT,
    released_at     TEXT,
    updated_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (status IN ('pending_release','released','in_transit','received','returned')),
    FOREIGN KEY (order_rec_id) REFERENCES order_recommendations (id)
);

CREATE INDEX IF NOT EXISTS idx_req_slips_status ON requirement_slips (status);
