-- ============================================================
-- ALTER TABLE t_data_source - Add Authenticity & Trust Columns
-- Purpose: Enable robust document verification and source tracking
-- Date: 2026-02-20
-- ============================================================

-- First, check current table structure
SELECT column_name, data_type, character_maximum_length, is_nullable
FROM information_schema.columns
WHERE table_name = 't_data_source'
ORDER BY ordinal_position;

-- ============================================================
-- SECTION 1: AUTHENTICITY & TRUST COLUMNS
-- ============================================================

-- Source domain extracted from URL (e.g., 'investor.apple.com')
ALTER TABLE t_data_source 
ADD COLUMN IF NOT EXISTS source_domain VARCHAR(255);

-- Whether the source is an official company IR domain
ALTER TABLE t_data_source 
ADD COLUMN IF NOT EXISTS is_official_source BOOLEAN DEFAULT FALSE;

-- Trust score based on source quality (1-100, higher = more trusted)
-- 90-100: Official company IR site
-- 70-89: SEC EDGAR, reputable financial sites
-- 50-69: News sites, third-party aggregators
-- 1-49: Unknown/unverified sources
ALTER TABLE t_data_source 
ADD COLUMN IF NOT EXISTS source_confidence_score INTEGER DEFAULT 0;

-- Verification status
-- 0 = Unverified (default)
-- 1 = Auto-verified (domain/hash matched)
-- 2 = Manually verified by user
-- 3 = Flagged for review (suspicious)
-- 4 = Rejected (confirmed fake/wrong)
ALTER TABLE t_data_source 
ADD COLUMN IF NOT EXISTS verification_status INTEGER DEFAULT 0;

-- ============================================================
-- SECTION 2: DOCUMENT INTEGRITY COLUMNS
-- ============================================================

-- SHA-256 hash of the downloaded file for integrity verification
ALTER TABLE t_data_source 
ADD COLUMN IF NOT EXISTS file_hash_sha256 VARCHAR(64);

-- File size in bytes (for quick integrity check)
ALTER TABLE t_data_source 
ADD COLUMN IF NOT EXISTS file_size_bytes BIGINT;

-- Whether the PDF has a digital signature
ALTER TABLE t_data_source 
ADD COLUMN IF NOT EXISTS pdf_is_signed BOOLEAN DEFAULT FALSE;

-- Whether the digital signature is valid
ALTER TABLE t_data_source 
ADD COLUMN IF NOT EXISTS pdf_signature_valid BOOLEAN;

-- ============================================================
-- SECTION 3: SOURCE TRACKING COLUMNS
-- ============================================================

-- Full original URL where the file was downloaded from
ALTER TABLE t_data_source 
ADD COLUMN IF NOT EXISTS original_source_url TEXT;

-- The search query that found this document
ALTER TABLE t_data_source 
ADD COLUMN IF NOT EXISTS search_query_used TEXT;

-- Position in search results (1 = top result, more trusted)
ALTER TABLE t_data_source 
ADD COLUMN IF NOT EXISTS search_result_rank INTEGER;

-- Referrer URL (page that linked to the document)
ALTER TABLE t_data_source 
ADD COLUMN IF NOT EXISTS referrer_url VARCHAR(500);

-- ============================================================
-- SECTION 4: SEC CROSS-REFERENCE COLUMNS (for 10-K/10-Q)
-- ============================================================

-- SEC Central Index Key (CIK) - unique company identifier
ALTER TABLE t_data_source 
ADD COLUMN IF NOT EXISTS sec_cik VARCHAR(20);

-- SEC filing accession number (unique filing identifier)
ALTER TABLE t_data_source 
ADD COLUMN IF NOT EXISTS sec_accession_number VARCHAR(30);

-- Whether this document was verified against SEC EDGAR
ALTER TABLE t_data_source 
ADD COLUMN IF NOT EXISTS sec_verified BOOLEAN DEFAULT FALSE;

-- ============================================================
-- SECTION 5: AUDIT TRAIL COLUMNS
-- ============================================================

-- Exact timestamp when the file was downloaded
ALTER TABLE t_data_source 
ADD COLUMN IF NOT EXISTS download_timestamp TIMESTAMP WITH TIME ZONE;

-- HTTP response code from the download (200 = success)
ALTER TABLE t_data_source 
ADD COLUMN IF NOT EXISTS http_response_code INTEGER;

-- ============================================================
-- CREATE INDEXES FOR PERFORMANCE
-- ============================================================

-- Index on source_domain for quick filtering by domain
CREATE INDEX IF NOT EXISTS idx_t_data_source_domain 
ON t_data_source(source_domain);

-- Index on is_official_source for filtering trusted sources
CREATE INDEX IF NOT EXISTS idx_t_data_source_official 
ON t_data_source(is_official_source);

-- Index on verification_status for filtering by verification state
CREATE INDEX IF NOT EXISTS idx_t_data_source_verification 
ON t_data_source(verification_status);

-- Index on file_hash for duplicate detection
CREATE INDEX IF NOT EXISTS idx_t_data_source_hash 
ON t_data_source(file_hash_sha256);

-- Composite index for SEC lookups
CREATE INDEX IF NOT EXISTS idx_t_data_source_sec 
ON t_data_source(sec_cik, sec_accession_number);

-- ============================================================
-- ADD LOOKUP VALUES FOR VERIFICATION STATUS
-- ============================================================

-- Check if verification status lookups exist
SELECT * FROM t_data_lookups WHERE data_lookups_group = 'verification_status';

-- Get the next available data_lookups_id
-- SELECT COALESCE(MAX(data_lookups_id), 0) + 1 as next_id FROM t_data_lookups;

-- Get the next available group_id for verification_status
-- SELECT COALESCE(MAX(data_lookups_group_id), 0) + 1 as next_group_id FROM t_data_lookups;

-- Insert lookup values if they don't exist (adjust IDs as needed based on existing data)
-- Note: Run the SELECT queries above first to determine the correct starting IDs

-- Example inserts (uncomment and adjust IDs after checking existing data):
/*
INSERT INTO t_data_lookups (data_lookups_id, data_lookups_group_id, data_lookups_group, data_lookups_description, added_dt, added_by, modify_dt, modify_by)
SELECT 100, 10, 'verification_status', 'Unverified', CURRENT_TIMESTAMP, 'System', CURRENT_TIMESTAMP, 'System'
WHERE NOT EXISTS (SELECT 1 FROM t_data_lookups WHERE data_lookups_group = 'verification_status' AND data_lookups_description = 'Unverified');

INSERT INTO t_data_lookups (data_lookups_id, data_lookups_group_id, data_lookups_group, data_lookups_description, added_dt, added_by, modify_dt, modify_by)
SELECT 101, 10, 'verification_status', 'Auto-Verified', CURRENT_TIMESTAMP, 'System', CURRENT_TIMESTAMP, 'System'
WHERE NOT EXISTS (SELECT 1 FROM t_data_lookups WHERE data_lookups_group = 'verification_status' AND data_lookups_description = 'Auto-Verified');

INSERT INTO t_data_lookups (data_lookups_id, data_lookups_group_id, data_lookups_group, data_lookups_description, added_dt, added_by, modify_dt, modify_by)
SELECT 102, 10, 'verification_status', 'Manually Verified', CURRENT_TIMESTAMP, 'System', CURRENT_TIMESTAMP, 'System'
WHERE NOT EXISTS (SELECT 1 FROM t_data_lookups WHERE data_lookups_group = 'verification_status' AND data_lookups_description = 'Manually Verified');

INSERT INTO t_data_lookups (data_lookups_id, data_lookups_group_id, data_lookups_group, data_lookups_description, added_dt, added_by, modify_dt, modify_by)
SELECT 103, 10, 'verification_status', 'Flagged for Review', CURRENT_TIMESTAMP, 'System', CURRENT_TIMESTAMP, 'System'
WHERE NOT EXISTS (SELECT 1 FROM t_data_lookups WHERE data_lookups_group = 'verification_status' AND data_lookups_description = 'Flagged for Review');

INSERT INTO t_data_lookups (data_lookups_id, data_lookups_group_id, data_lookups_group, data_lookups_description, added_dt, added_by, modify_dt, modify_by)
SELECT 104, 10, 'verification_status', 'Rejected', CURRENT_TIMESTAMP, 'System', CURRENT_TIMESTAMP, 'System'
WHERE NOT EXISTS (SELECT 1 FROM t_data_lookups WHERE data_lookups_group = 'verification_status' AND data_lookups_description = 'Rejected');
*/

-- Alternative: Use a sequence or max+1 approach
-- First, find the max IDs:
SELECT MAX(data_lookups_id) as max_id, MAX(data_lookups_group_id) as max_group_id FROM t_data_lookups;

-- ============================================================
-- VERIFICATION QUERIES
-- ============================================================

-- Verify columns were added
SELECT column_name, data_type, character_maximum_length, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 't_data_source'
ORDER BY ordinal_position;

-- Check indexes
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 't_data_source';

-- ============================================================
-- SAMPLE QUERIES FOR NEW COLUMNS
-- ============================================================

-- Find all documents from official sources
-- SELECT * FROM t_data_source WHERE is_official_source = TRUE;

-- Find documents needing verification
-- SELECT * FROM t_data_source WHERE verification_status = 0;

-- Find documents flagged for review
-- SELECT * FROM t_data_source WHERE verification_status = 3;

-- Find potential duplicates by hash
-- SELECT file_hash_sha256, COUNT(*) as count 
-- FROM t_data_source 
-- WHERE file_hash_sha256 IS NOT NULL 
-- GROUP BY file_hash_sha256 
-- HAVING COUNT(*) > 1;

-- Distribution of sources by confidence score
-- SELECT 
--     CASE 
--         WHEN source_confidence_score >= 90 THEN 'High (90-100)'
--         WHEN source_confidence_score >= 70 THEN 'Medium-High (70-89)'
--         WHEN source_confidence_score >= 50 THEN 'Medium (50-69)'
--         ELSE 'Low (1-49)'
--     END as confidence_tier,
--     COUNT(*) as document_count
-- FROM t_data_source
-- GROUP BY 1
-- ORDER BY 1;
