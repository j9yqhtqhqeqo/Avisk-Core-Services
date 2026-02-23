-- ============================================================
-- ALTER TABLE t_data_source - Add ticker column
-- Purpose: Store the stock ticker symbol alongside company_name
--          so filters can resolve company_name -> ticker without
--          parsing filenames at runtime.
-- Date: 2026-02-23
-- ============================================================

-- 1. Add the column (safe to run multiple times)
ALTER TABLE t_data_source
ADD COLUMN IF NOT EXISTS ticker VARCHAR(20);

-- 2. One-time backfill: derive ticker from the source_url filename prefix.
--    Files are stored as  SYMBOL_<rest>.pdf / SYMBOL_<rest>.txt
--    SPLIT_PART(source_url, '_', 1) gives us the ticker for existing rows.
UPDATE t_data_source
SET    ticker = UPPER(SPLIT_PART(source_url, '_', 1))
WHERE  ticker IS NULL
  AND  source_url IS NOT NULL
  AND  source_url <> '';

-- 3. Optional index for filter performance
CREATE INDEX IF NOT EXISTS idx_t_data_source_ticker
ON t_data_source (ticker);

-- Verify
SELECT ticker, COUNT(*) AS cnt
FROM   t_data_source
GROUP  BY ticker
ORDER  BY ticker;
