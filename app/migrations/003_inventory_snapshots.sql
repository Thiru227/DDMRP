CREATE TABLE IF NOT EXISTS inventory_snapshots (
    msku_code              TEXT NOT NULL,
    branch_code            TEXT NOT NULL,
    snapshot_date          TEXT NOT NULL,
    on_hand_qty            REAL NOT NULL DEFAULT 0,
    on_order_qty           REAL NOT NULL DEFAULT 0,
    qualified_demand_qty   REAL NOT NULL DEFAULT 0,
    sales_90d              REAL NOT NULL DEFAULT 0,
    adu_days               REAL NOT NULL DEFAULT 90,
    source_adu                       REAL,
    source_red                       REAL,
    source_yellow                    REAL,
    source_green                     REAL,
    source_tog                       REAL,
    source_net_flow                  REAL,
    source_order_recommendation      REAL,
    uploaded_by            TEXT,
    upload_job_id          TEXT,
    PRIMARY KEY (msku_code, branch_code, snapshot_date),
    FOREIGN KEY (msku_code)   REFERENCES msku_master (msku_code),
    FOREIGN KEY (branch_code) REFERENCES branches (branch_code)
);

CREATE INDEX IF NOT EXISTS idx_inv_snap_msku_branch ON inventory_snapshots (msku_code, branch_code);
