CREATE TABLE IF NOT EXISTS suppliers (
    supplier_code        TEXT PRIMARY KEY,
    name                 TEXT NOT NULL,
    unit                 TEXT,
    location             TEXT,
    contact_email        TEXT,
    credit_period_days   INTEGER NOT NULL DEFAULT 45,
    is_msme              INTEGER NOT NULL DEFAULT 0,
    stock_clearance_rule TEXT,
    moq                  INTEGER NOT NULL DEFAULT 120,
    hub_cleared_pct      REAL NOT NULL DEFAULT 100.0,
    active               INTEGER NOT NULL DEFAULT 1,
    updated_at           TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT OR IGNORE INTO suppliers
    (supplier_code, name, unit, location, contact_email, credit_period_days,
     is_msme, stock_clearance_rule, moq, hub_cleared_pct, active)
VALUES
    ('POOMEX-001', 'Poomex Textiles Ltd.', 'Unit 1 — Primary',
     'Tirupur, Tamil Nadu', 'cc@av7groups.com', 45, 1,
     'Min 50% hub clearance required before next order', 120, 78.0, 1),
    ('POOMEX-002', 'Poomex Textiles Ltd.', 'Unit 2 — Secondary',
     'Tirupur, Tamil Nadu', 'cc@av7groups.com', 45, 1,
     'Min 50% hub clearance required before next order', 120, 42.0, 1);
