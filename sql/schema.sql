-- Market Analysis System - SQLite Schema v2
-- Fund: Nu Reserva Planejada (CNPJ: 43.121.002/0001-41)
--
-- NOTE: The authoritative DDL lives in
--   src/market_analysis/infrastructure/database.py (SCHEMA_DDL constant).
-- This file is a copy for manual inspection and tooling.

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;
PRAGMA busy_timeout = 5000;

-- BCB time-series data (SELIC daily, CDI daily, IPCA monthly)
CREATE TABLE IF NOT EXISTS bcb_data (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    series_code     TEXT    NOT NULL,
    indicator       TEXT    NOT NULL CHECK (indicator IN ('SELIC', 'CDI', 'IPCA')),
    reference_date  TEXT    NOT NULL,
    value           TEXT    NOT NULL,
    collected_at    TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    UNIQUE (series_code, reference_date)
);

CREATE INDEX IF NOT EXISTS idx_bcb_indicator_date
    ON bcb_data (indicator, reference_date DESC);

-- Google News RSS items
CREATE TABLE IF NOT EXISTS news_data (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    title           TEXT    NOT NULL,
    link            TEXT    NOT NULL UNIQUE,
    published_at    TEXT    NOT NULL,
    description     TEXT    NOT NULL DEFAULT '',
    source          TEXT    NOT NULL DEFAULT 'unknown',
    search_query    TEXT,
    sentiment       TEXT    CHECK (sentiment IS NULL
                            OR sentiment IN ('positive', 'negative', 'neutral')),
    collected_at    TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_news_published
    ON news_data (published_at DESC);

-- Tracked fund metadata
CREATE TABLE IF NOT EXISTS funds_metadata (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    cnpj            TEXT    NOT NULL UNIQUE,
    name            TEXT    NOT NULL,
    short_name      TEXT,
    fund_type       TEXT    NOT NULL,
    manager         TEXT    NOT NULL,
    administrator   TEXT,
    admin_fee       REAL,
    benchmark       TEXT,
    inception_date  TEXT,
    status          TEXT    NOT NULL DEFAULT 'active'
                           CHECK (status IN ('active', 'inactive')),
    created_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

-- Email recipients
CREATE TABLE IF NOT EXISTS recipients (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL,
    email           TEXT    NOT NULL UNIQUE,
    active          INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

-- System configuration (SMTP, thresholds, etc.)
CREATE TABLE IF NOT EXISTS system_config (
    key             TEXT    PRIMARY KEY,
    value           TEXT    NOT NULL,
    description     TEXT    NOT NULL DEFAULT '',
    is_sensitive    INTEGER NOT NULL DEFAULT 0,
    updated_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

-- Collection execution log (append-only)
CREATE TABLE IF NOT EXISTS collection_metadata (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    collector_type  TEXT    NOT NULL,
    status          TEXT    NOT NULL DEFAULT 'running'
                           CHECK (status IN ('running', 'success', 'partial', 'failure')),
    started_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    finished_at     TEXT,
    items_count     INTEGER NOT NULL DEFAULT 0,
    duration_secs   REAL,
    retry_count     INTEGER NOT NULL DEFAULT 0,
    error_code      TEXT,
    error_message   TEXT,
    error_context   TEXT,
    created_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_collection_type_status
    ON collection_metadata (collector_type, status, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_collection_started
    ON collection_metadata (started_at DESC);

-- Performance reports
CREATE TABLE IF NOT EXISTS performance_reports (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    report_date     TEXT    NOT NULL,
    fund_cnpj       TEXT    NOT NULL,
    report_data     TEXT    NOT NULL,
    pdf_path        TEXT,
    sent_at         TEXT,
    created_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    FOREIGN KEY (fund_cnpj) REFERENCES funds_metadata (cnpj)
);

CREATE INDEX IF NOT EXISTS idx_reports_date
    ON performance_reports (report_date DESC);

-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_version (
    version         INTEGER PRIMARY KEY,
    applied_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

-- Seed data
INSERT OR IGNORE INTO funds_metadata (cnpj, name, short_name, fund_type, manager, benchmark)
VALUES (
    '43.121.002/0001-41',
    'Nu Reserva Planejada Fundo de Investimento Renda Fixa',
    'Nu Reserva Planejada',
    'Renda Fixa',
    'Nu Asset Management',
    'CDI'
);

INSERT OR IGNORE INTO system_config (key, value, description)
VALUES
    ('bcb.series.selic', '432',  'BCB series code for SELIC target rate'),
    ('bcb.series.cdi',   '4389', 'BCB series code for CDI daily rate'),
    ('bcb.series.ipca',  '433',  'BCB series code for IPCA monthly');

INSERT OR IGNORE INTO schema_version (version) VALUES (2);
