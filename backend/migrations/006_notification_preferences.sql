-- Migration: Add notification_preferences to organization_config
-- Run: psql $DATABASE_URL -f 006_notification_preferences.sql
-- Or via Supabase SQL Editor
-- Created: 2026-02-26

-- ==============================================================================
-- ADD notification_preferences COLUMN
-- ==============================================================================
-- Stores per-org notification settings as JSONB

ALTER TABLE organization_config 
ADD COLUMN IF NOT EXISTS notification_preferences JSONB DEFAULT '{
    "deadline_alerts_enabled": true,
    "deadline_alert_days": [2, 7, 30],
    "morning_briefs_enabled": true,
    "email_notifications_enabled": true
}'::jsonb;

-- Add comment for documentation
COMMENT ON COLUMN organization_config.notification_preferences IS 
    'JSON object containing notification settings: deadline_alerts_enabled, deadline_alert_days (array), morning_briefs_enabled, email_notifications_enabled';

-- ==============================================================================
-- VERIFICATION QUERY
-- ==============================================================================
-- SELECT id, name, notification_preferences FROM organization_config LIMIT 5;
