CREATE TABLE IF NOT EXISTS planning_snapshots (
    msku_code              TEXT NOT NULL,
    branch_code            TEXT NOT NULL,
    snapshot_date          TEXT NOT NULL,
    adu                    REAL NOT NULL DEFAULT 0,
    red_zone               REAL NOT NULL DEFAULT 0,
    yellow_zone            REAL NOT NULL DEFAULT 0,
    green_zone             REAL NOT NULL DEFAULT 0,
    tor                    REAL NOT NULL DEFAULT 0,
    toy                    REAL NOT NULL DEFAULT 0,
    tog                    REAL NOT NULL DEFAULT 0,
    net_flow               REAL NOT NULL DEFAULT 0,
    planning_priority      REAL NOT NULL DEFAULT 0,
    order_recommendation   REAL NOT NULL DEFAULT 0,
    alert_level            TEXT NOT NULL DEFAULT 'healthy',
    engine_minus_source_adu                  REAL,
    engine_minus_source_red                  REAL,
    engine_minus_source_yellow               REAL,
    engine_minus_source_green                REAL,
    engine_minus_source_tog                  REAL,
    engine_minus_source_net_flow             REAL,
    engine_minus_source_order_recommendation REAL,
    flagged_diff           INTEGER NOT NULL DEFAULT 0,
    calculated_at          TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (msku_code, branch_code, snapshot_date),
    CHECK (alert_level IN ('red','yellow','healthy'))
);

CREATE INDEX IF NOT EXISTS idx_plan_snap_alert ON planning_snapshots (alert_level);
