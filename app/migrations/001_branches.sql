CREATE TABLE IF NOT EXISTS branches (
    branch_code  TEXT PRIMARY KEY,
    display_name TEXT,
    active       INTEGER NOT NULL DEFAULT 1,
    CHECK (branch_code <> 'TOT')
);
