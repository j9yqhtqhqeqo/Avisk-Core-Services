-- Update t_data_source content_type based on filename patterns
-- content_type: 1 = Sustainability/ESG, 2 = Annual/10K, 3 = Other, 4 = Earnings Transcripts
-- Run this script to fix existing records that were all set to 1

-- First, let's see the current distribution
SELECT content_type, COUNT(*) as count 
FROM t_data_source 
GROUP BY content_type
ORDER BY content_type;

-- Preview what will be updated (run this first to verify)
SELECT 
    unique_id,
    company_name,
    year,
    source_url,
    content_type as current_type,
    CASE 
        -- Sustainability/ESG patterns (check first - priority)
        WHEN LOWER(source_url) ~ '(sustainability|esg|csr|corporate.?responsibility|environmental|social.?responsibility|impact.?report|citizenship|climate|carbon|emissions|responsible|stewardship|green|progress.?report|cdp|tcfd|sasb|gri|net.?zero|decarbonization)'
        THEN 1
        -- Earnings Transcripts patterns (check before Annual/10K)
        WHEN LOWER(source_url) ~ '(transcript|earnings.?call|conference.?call|investor.?call|q[1-4].?call|quarterly.?call|earnings.?conference)'
        THEN 4
        -- Annual/10K patterns
        WHEN LOWER(source_url) ~ '(10k|10-k|form.?10k|annual.?report|annualreport|_ar_|-ar-|_ar\.|-ar\.|proxy|def14a|10q|10-q|quarterly|investor.?relations|investors|sec.?filings|financial.?report)'
        THEN 2
        -- Other
        ELSE 3
    END as new_type
FROM t_data_source
WHERE content_type = 1
ORDER BY company_name, year;

-- Count of changes by new type
SELECT 
    CASE 
        WHEN LOWER(source_url) ~ '(sustainability|esg|csr|corporate.?responsibility|environmental|social.?responsibility|impact.?report|citizenship|climate|carbon|emissions|responsible|stewardship|green|progress.?report|cdp|tcfd|sasb|gri|net.?zero|decarbonization)'
        THEN 'Sustainability/ESG (1)'
        WHEN LOWER(source_url) ~ '(transcript|earnings.?call|conference.?call|investor.?call|q[1-4].?call|quarterly.?call|earnings.?conference)'
        THEN 'Earnings Transcripts (4)'
        WHEN LOWER(source_url) ~ '(10k|10-k|form.?10k|annual.?report|annualreport|_ar_|-ar-|_ar\.|-ar\.|proxy|def14a|10q|10-q|quarterly|investor.?relations|investors|sec.?filings|financial.?report)'
        THEN 'Annual/10K (2)'
        ELSE 'Other (3)'
    END as report_type,
    COUNT(*) as count
FROM t_data_source
GROUP BY 1
ORDER BY 1;

-- ============================================================
-- ACTUAL UPDATE STATEMENTS (run these after verifying above)
-- ============================================================

-- Step 1: Update Earnings Transcripts to content_type = 4
-- (Check before Annual/10K since some transcript URLs may contain "earnings")
UPDATE t_data_source
SET content_type = 4,
    modify_dt = CURRENT_TIMESTAMP,
    modify_by = 'ContentTypeUpdate_Script'
WHERE LOWER(source_url) ~ '(transcript|earnings.?call|conference.?call|investor.?call|q[1-4].?call|quarterly.?call|earnings.?conference)'
  AND NOT LOWER(source_url) ~ '(sustainability|esg|csr|corporate.?responsibility|environmental|social.?responsibility|impact.?report|citizenship|climate|carbon|emissions|responsible|stewardship|green|progress.?report|cdp|tcfd|sasb|gri|net.?zero|decarbonization)';

-- Step 2: Update Annual/10K reports to content_type = 2
-- (Do this after transcripts since sustainability has priority - we'll fix any overlaps next)
UPDATE t_data_source
SET content_type = 2,
    modify_dt = CURRENT_TIMESTAMP,
    modify_by = 'ContentTypeUpdate_Script'
WHERE LOWER(source_url) ~ '(10k|10-k|form.?10k|annual.?report|annualreport|_ar_|-ar-|_ar\.|-ar\.|proxy|def14a|10q|10-q|quarterly|investor.?relations|investors|sec.?filings|financial.?report)'
  AND NOT LOWER(source_url) ~ '(sustainability|esg|csr|corporate.?responsibility|environmental|social.?responsibility|impact.?report|citizenship|climate|carbon|emissions|responsible|stewardship|green|progress.?report|cdp|tcfd|sasb|gri|net.?zero|decarbonization)'
  AND NOT LOWER(source_url) ~ '(transcript|earnings.?call|conference.?call|investor.?call|q[1-4].?call|quarterly.?call|earnings.?conference)';

-- Step 3: Update Other reports to content_type = 3
-- (Files that don't match any pattern)
UPDATE t_data_source
SET content_type = 3,
    modify_dt = CURRENT_TIMESTAMP,
    modify_by = 'ContentTypeUpdate_Script'
WHERE NOT LOWER(source_url) ~ '(sustainability|esg|csr|corporate.?responsibility|environmental|social.?responsibility|impact.?report|citizenship|climate|carbon|emissions|responsible|stewardship|green|progress.?report|cdp|tcfd|sasb|gri|net.?zero|decarbonization)'
  AND NOT LOWER(source_url) ~ '(10k|10-k|form.?10k|annual.?report|annualreport|_ar_|-ar-|_ar\.|-ar\.|proxy|def14a|10q|10-q|quarterly|investor.?relations|investors|sec.?filings|financial.?report)'
  AND NOT LOWER(source_url) ~ '(transcript|earnings.?call|conference.?call|investor.?call|q[1-4].?call|quarterly.?call|earnings.?conference)';

-- Step 3: Ensure Sustainability/ESG reports are content_type = 1
-- (This should already be the case, but run to ensure consistency)
UPDATE t_data_source
SET content_type = 1,
    modify_dt = CURRENT_TIMESTAMP,
    modify_by = 'ContentTypeUpdate_Script'
WHERE LOWER(source_url) ~ '(sustainability|esg|csr|corporate.?responsibility|environmental|social.?responsibility|impact.?report|citizenship|climate|carbon|emissions|responsible|stewardship|green|progress.?report|cdp|tcfd|sasb|gri|net.?zero|decarbonization)'
  AND content_type != 1;

-- Verify final distribution
SELECT 
    content_type,
    CASE content_type
        WHEN 1 THEN 'Sustainability/ESG'
        WHEN 2 THEN 'Annual/10K'
        WHEN 3 THEN 'Other'
        WHEN 4 THEN 'Earnings Transcripts'
        ELSE 'Unknown'
    END as type_name,
    COUNT(*) as count 
FROM t_data_source 
GROUP BY content_type
ORDER BY content_type;

-- Sample records by type for verification
SELECT 'Sustainability/ESG' as type, source_url FROM t_data_source WHERE content_type = 1 LIMIT 5;
SELECT 'Annual/10K' as type, source_url FROM t_data_source WHERE content_type = 2 LIMIT 5;
SELECT 'Other' as type, source_url FROM t_data_source WHERE content_type = 3 LIMIT 5;
SELECT 'Earnings Transcripts' as type, source_url FROM t_data_source WHERE content_type = 4 LIMIT 5;
