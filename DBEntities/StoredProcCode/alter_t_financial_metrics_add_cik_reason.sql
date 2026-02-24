-- Migration: add edgar_cik and missing_data_reason to t_financial_metrics
-- Run once against the Cloud SQL database.

ALTER TABLE t_financial_metrics
    ADD COLUMN IF NOT EXISTS edgar_cik            INTEGER,
    ADD COLUMN IF NOT EXISTS missing_data_reason  TEXT;

-- Optional index: useful for filtering rows with gaps in the dashboard
CREATE INDEX IF NOT EXISTS idx_financial_metrics_missing_reason
    ON t_financial_metrics (company_name)
    WHERE missing_data_reason IS NOT NULL;

COMMENT ON COLUMN t_financial_metrics.edgar_cik IS
    'SEC EDGAR CIK of the entity whose XBRL facts were used for this row';

COMMENT ON COLUMN t_financial_metrics.missing_data_reason IS
    'Comma-separated list of field names that are NULL/0 after extraction, with a brief reason where known (e.g. "eps: no XBRL tag; revenue: pre-IPO")';
