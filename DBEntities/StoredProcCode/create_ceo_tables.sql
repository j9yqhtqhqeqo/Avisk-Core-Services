-- CEO Tables
-- Run once to create the CEO identification and statements tables.

CREATE TABLE IF NOT EXISTS t_ceo (
    ceo_id           SERIAL PRIMARY KEY,
    company_name     VARCHAR(255) NOT NULL,
    ticker           VARCHAR(20),
    year             INTEGER NOT NULL,
    ceo_name         VARCHAR(255),
    source           VARCHAR(100),
    confidence_score DECIMAL(3,2) DEFAULT 1.0,
    added_dt         TIMESTAMP DEFAULT NOW(),
    modify_dt        TIMESTAMP DEFAULT NOW(),
    UNIQUE (company_name, year)
);

CREATE TABLE IF NOT EXISTS t_ceo_statements (
    statement_id   SERIAL PRIMARY KEY,
    ceo_id         INTEGER REFERENCES t_ceo(ceo_id) ON DELETE CASCADE,
    company_name   VARCHAR(255),
    ticker         VARCHAR(20),
    year           INTEGER,
    ceo_name       VARCHAR(255),
    statement_text TEXT,
    statement_date DATE,
    source_url     VARCHAR(1000),
    source_title   VARCHAR(500),
    statement_type VARCHAR(50),
    search_query   VARCHAR(500),
    added_dt       TIMESTAMP DEFAULT NOW()
);
