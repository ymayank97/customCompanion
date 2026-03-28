-- Database schema for storing customs tariff data and scraping logs

-- ============================================================
-- 1. TARIFF ENTRIES TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS tariff_entries (
    id SERIAL PRIMARY KEY,
    cth_code VARCHAR(8) NOT NULL,
    description TEXT NOT NULL,
    bcd_rate VARCHAR(20),
    unit VARCHAR(50),
    chapter VARCHAR(2),
    source VARCHAR(50),  -- 'icegate', 'cbic', 'indian_trade_portal'
    scrape_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(cth_code, source)
);

-- Index for faster lookups
CREATE INDEX idx_tariff_cth_code ON tariff_entries(cth_code);
CREATE INDEX idx_tariff_chapter ON tariff_entries(chapter);
CREATE INDEX idx_tariff_source ON tariff_entries(source);
CREATE INDEX idx_tariff_scrape_timestamp ON tariff_entries(scrape_timestamp);

-- ============================================================
-- 2. CBIC NOTIFICATIONS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS cbic_notifications (
    id SERIAL PRIMARY KEY,
    notification_number VARCHAR(50) NOT NULL UNIQUE,
    title TEXT,
    notification_date DATE,
    pdf_url TEXT,
    pdf_downloaded BOOLEAN DEFAULT FALSE,
    pdf_parsed BOOLEAN DEFAULT FALSE,
    scrape_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Index for faster lookups
CREATE INDEX idx_notification_number ON cbic_notifications(notification_number);
CREATE INDEX idx_notification_date ON cbic_notifications(notification_date);

-- ============================================================
-- 3. CTH CHANGES TABLE (from PDF parsing)
-- ============================================================
CREATE TABLE IF NOT EXISTS cth_changes (
    id SERIAL PRIMARY KEY,
    cth_code VARCHAR(8) NOT NULL,
    formatted_cth VARCHAR(10),
    context TEXT,
    page_number INTEGER,
    notification_id INTEGER REFERENCES cbic_notifications(id) ON DELETE CASCADE,
    pdf_url TEXT,
    scrape_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Index for faster lookups
CREATE INDEX idx_cth_changes_code ON cth_changes(cth_code);
CREATE INDEX idx_cth_changes_notification ON cth_changes(notification_id);

-- ============================================================
-- 4. SCRAPE LOG TABLE (error tracking)
-- ============================================================
CREATE TABLE IF NOT EXISTS scrape_log (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    function_name VARCHAR(100) NOT NULL,
    input_params TEXT,
    error_type VARCHAR(100),
    error_message TEXT,
    traceback TEXT,
    severity VARCHAR(20) DEFAULT 'ERROR'  -- 'ERROR', 'WARNING', 'INFO'
);

-- Index for faster lookups
CREATE INDEX idx_scrape_log_timestamp ON scrape_log(timestamp);
CREATE INDEX idx_scrape_log_function ON scrape_log(function_name);
CREATE INDEX idx_scrape_log_severity ON scrape_log(severity);

-- ============================================================
-- 5. SCRAPE METADATA TABLE (track scrape runs)
-- ============================================================
CREATE TABLE IF NOT EXISTS scrape_metadata (
    id SERIAL PRIMARY KEY,
    scrape_type VARCHAR(50) NOT NULL,  -- 'icegate', 'cbic', 'indian_portal', 'full'
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    status VARCHAR(20),  -- 'running', 'completed', 'failed', 'partial'
    entries_scraped INTEGER DEFAULT 0,
    errors_count INTEGER DEFAULT 0,
    chapter_range VARCHAR(20),  -- e.g., '01-99'
    days_back INTEGER,  -- for notifications
    notes TEXT
);

-- Index for faster lookups
CREATE INDEX idx_scrape_metadata_type ON scrape_metadata(scrape_type);
CREATE INDEX idx_scrape_metadata_start_time ON scrape_metadata(start_time);
CREATE INDEX idx_scrape_metadata_status ON scrape_metadata(status);

-- ============================================================
-- 6. VIEWS FOR EASY QUERYING
-- ============================================================

-- Latest tariff data by CTH code
CREATE OR REPLACE VIEW latest_tariffs AS
SELECT DISTINCT ON (cth_code)
    cth_code,
    description,
    bcd_rate,
    unit,
    chapter,
    source,
    scrape_timestamp
FROM tariff_entries
ORDER BY cth_code, scrape_timestamp DESC;

-- Recent notifications with CTH change counts
CREATE OR REPLACE VIEW notifications_with_changes AS
SELECT
    n.notification_number,
    n.title,
    n.notification_date,
    n.pdf_url,
    COUNT(c.id) as cth_changes_count
FROM cbic_notifications n
LEFT JOIN cth_changes c ON n.id = c.notification_id
GROUP BY n.id, n.notification_number, n.title, n.notification_date, n.pdf_url
ORDER BY n.notification_date DESC;

-- Scraping error summary
CREATE OR REPLACE VIEW error_summary AS
SELECT
    function_name,
    error_type,
    COUNT(*) as error_count,
    MAX(timestamp) as last_occurrence
FROM scrape_log
WHERE severity = 'ERROR'
GROUP BY function_name, error_type
ORDER BY error_count DESC;

-- ============================================================
-- 7. USEFUL QUERIES
-- ============================================================

-- Find all tariff entries for a specific chapter
-- SELECT * FROM tariff_entries WHERE chapter = '01' ORDER BY cth_code;

-- Get latest notifications with most CTH changes
-- SELECT * FROM notifications_with_changes ORDER BY cth_changes_count DESC LIMIT 10;

-- Find all CTH codes affected by a specific notification
-- SELECT c.* FROM cth_changes c
-- JOIN cbic_notifications n ON c.notification_id = n.id
-- WHERE n.notification_number = '12/2024-Customs';

-- Get scraping error statistics
-- SELECT * FROM error_summary;

-- Find tariff entries with no BCD rate
-- SELECT * FROM tariff_entries WHERE bcd_rate IS NULL OR bcd_rate = '';

-- Compare entries from different sources
-- SELECT
--     cth_code,
--     source,
--     bcd_rate,
--     scrape_timestamp
-- FROM tariff_entries
-- WHERE cth_code IN (
--     SELECT cth_code FROM tariff_entries GROUP BY cth_code HAVING COUNT(DISTINCT source) > 1
-- )
-- ORDER BY cth_code, source;
