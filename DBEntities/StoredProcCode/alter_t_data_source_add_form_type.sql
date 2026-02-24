-- Migration: add form_type column to t_data_source
-- Stores the exact SEC EDGAR form string (e.g. '10-K', '8-K', 'DEF 14A', '10-Q')
-- NULL for non-EDGAR records (sustainability PDFs, web downloads, transcripts)

ALTER TABLE t_data_source
    ADD COLUMN IF NOT EXISTS form_type VARCHAR(20) DEFAULT NULL;

CREATE INDEX IF NOT EXISTS idx_t_data_source_form_type
    ON t_data_source (form_type);

-- Backfill from existing filenames where possible
-- Filenames follow pattern: SYMBOL_FORMTYPE_DATE_ACCESSION.ext
UPDATE t_data_source
SET form_type = CASE
    WHEN source_url LIKE '%_10K_%'   THEN '10-K'
    WHEN source_url LIKE '%_10KT_%'  THEN '10-KT'
    WHEN source_url LIKE '%_10Q_%'   THEN '10-Q'
    WHEN source_url LIKE '%_8K_%'    THEN '8-K'
    WHEN source_url LIKE '%_DEF14A_%' THEN 'DEF 14A'
    WHEN source_url LIKE '%_20F_%'   THEN '20-F'
    ELSE NULL
END
WHERE form_type IS NULL
  AND content_type IN (2, 3);  -- Only EDGAR records
