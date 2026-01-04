-- ============================================================================
-- Migration: v4.10.0 - Immediate Blank Presentation (OPERATING_MODEL_BUILDER_V2)
-- Date: 2026-01-03
-- Description: Adds session fields for blank presentation and edit sync support
-- ============================================================================

-- Phase 1: Blank Presentation & Edit Sync session fields
ALTER TABLE dr_sessions_v4
ADD COLUMN IF NOT EXISTS has_blank_presentation BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS blank_presentation_id TEXT,
ADD COLUMN IF NOT EXISTS edit_sync_state JSONB,
ADD COLUMN IF NOT EXISTS user_slide_count INTEGER,
ADD COLUMN IF NOT EXISTS user_has_content BOOLEAN DEFAULT FALSE;

-- Index for Phase 4 cleanup job (find orphaned blank sessions)
-- Targets: has_blank_presentation=TRUE, has_topic=FALSE, older than 24h
CREATE INDEX IF NOT EXISTS idx_sessions_blank_cleanup
ON dr_sessions_v4 (has_blank_presentation, has_topic, created_at)
WHERE has_blank_presentation = TRUE AND has_topic = FALSE;

-- Verify columns added
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'dr_sessions_v4'
  AND column_name IN ('has_blank_presentation', 'blank_presentation_id', 'edit_sync_state', 'user_slide_count', 'user_has_content');
