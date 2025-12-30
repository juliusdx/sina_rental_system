-- Migration: Add archive and metadata fields to Property table
-- Run this SQL against your SQLite database

ALTER TABLE property ADD COLUMN archived BOOLEAN DEFAULT 0;
ALTER TABLE property ADD COLUMN archived_date DATETIME;
ALTER TABLE property ADD COLUMN size_sqft REAL;
ALTER TABLE property ADD COLUMN notes TEXT;

-- Verify all columns exist
SELECT sql FROM sqlite_master WHERE type='table' AND name='property';
