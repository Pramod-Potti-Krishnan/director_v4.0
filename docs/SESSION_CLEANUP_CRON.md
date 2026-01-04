# Session Cleanup Cron Job

## Overview

The session cleanup cron job removes orphaned blank presentation sessions that were created but never used. This prevents database bloat from users who connect but never provide a topic.

**Version**: v4.10.2+
**Feature**: OPERATING_MODEL_BUILDER_V2 Phase 4

---

## What Gets Cleaned Up

Sessions matching ALL of these criteria:
- `has_blank_presentation = TRUE` (created with immediate blank presentation)
- `has_topic = FALSE` (user never provided a topic)
- `created_at < (now - SESSION_CLEANUP_HOURS)` (older than threshold)

Default threshold: **24 hours**

---

## Files

| File | Purpose |
|------|---------|
| `cleanup_cron.py` | Railway cron entry point |
| `src/utils/session_cleanup.py` | Core cleanup logic |

---

## Railway Setup

### Step 1: Create a New Service

1. Go to Railway Dashboard → Your Project
2. Click **"+ New"** → **"GitHub Repo"**
3. Select the same repository as your main Director service
4. Select the same branch (e.g., `feature/v4.4-service-alignment` or `main`)

### Step 2: Configure Service Settings

| Setting | Value |
|---------|-------|
| **Service Name** | `director-cleanup-cron` |
| **Start Command** | `python cleanup_cron.py` |
| **Root Directory** | Same as main service (leave blank if same) |

### Step 3: Add Environment Variables

Copy these from your main Director service:

```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-key
SESSION_CLEANUP_HOURS=24
```

### Step 4: Set Cron Schedule

1. Go to **Settings** tab
2. Scroll to **"Cron Schedule"** (in Deploy section)
3. Enter cron expression (see options below)
4. Save

---

## Cron Schedule Options

| Use Case | Expression | Description |
|----------|------------|-------------|
| **Recommended** | `0 */6 * * *` | Every 6 hours |
| Conservative | `0 */12 * * *` | Every 12 hours |
| Daily | `0 0 * * *` | Once daily at midnight UTC |
| Daily off-peak | `0 3 * * *` | Once daily at 3am UTC |

### Cron Expression Format

```
┌───────────── minute (0-59)
│ ┌───────────── hour (0-23)
│ │ ┌───────────── day of month (1-31)
│ │ │ ┌───────────── month (1-12)
│ │ │ │ ┌───────────── day of week (0-6, Sunday=0)
│ │ │ │ │
* * * * *
```

**Examples**:
- `0 */6 * * *` = At minute 0 past every 6th hour
- `30 2 * * *` = At 02:30 UTC daily
- `0 0 * * 0` = At midnight UTC every Sunday

**Note**: Railway uses UTC timezone. Minimum interval is 5 minutes.

---

## Manual Execution

### From Railway Dashboard

1. Go to the cron service
2. Click **"Deploy"** to trigger immediately
3. View logs for output

### From Local Machine

```bash
# Show statistics only
python -m src.utils.session_cleanup --stats

# Dry run (show what would be deleted)
python -m src.utils.session_cleanup --dry-run

# Run actual cleanup
python -m src.utils.session_cleanup

# Custom max age (48 hours)
python -m src.utils.session_cleanup --max-age 48
```

---

## Expected Output

```
============================================================
Session Cleanup Job - 2026-01-04T06:00:00.123456Z
============================================================

Checking orphaned sessions...
  Total orphaned: 15
  By age: <1h=3, 1-6h=5, 6-24h=4, >24h=3

Running cleanup...

Cleanup Result:
  Success: True
  Sessions found: 3
  Sessions deleted: 3
  Cutoff time: 2026-01-03T06:00:00.123456

============================================================
Cleanup completed successfully
============================================================
```

---

## Monitoring

### Check Cleanup History

View logs in Railway dashboard for the cron service to see:
- When cleanup ran
- How many sessions were deleted
- Any errors

### Database Verification

Run this query in Supabase SQL Editor to check orphaned sessions:

```sql
-- Count orphaned sessions by age
SELECT
  CASE
    WHEN created_at > NOW() - INTERVAL '1 hour' THEN '<1h'
    WHEN created_at > NOW() - INTERVAL '6 hours' THEN '1-6h'
    WHEN created_at > NOW() - INTERVAL '24 hours' THEN '6-24h'
    ELSE '>24h'
  END as age_bucket,
  COUNT(*) as count
FROM dr_sessions_v4
WHERE has_blank_presentation = TRUE
  AND has_topic = FALSE
GROUP BY age_bucket
ORDER BY age_bucket;
```

---

## Troubleshooting

### Cron Not Running

1. Verify service is deployed (green status)
2. Check cron expression syntax
3. Ensure start command is `python cleanup_cron.py`
4. Railway minimum interval is 5 minutes

### Cleanup Failing

1. Check environment variables are set
2. Verify Supabase connection
3. Check logs for specific error messages

### No Sessions Being Deleted

This is normal if:
- All orphaned sessions are newer than `SESSION_CLEANUP_HOURS`
- No users have connected without providing a topic

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SESSION_CLEANUP_HOURS` | `24` | Hours before session is considered orphaned |
| `SUPABASE_URL` | - | Supabase project URL |
| `SUPABASE_SERVICE_KEY` | - | Supabase service role key |

### Adjusting Cleanup Threshold

To change how long before sessions are cleaned:

1. Update `SESSION_CLEANUP_HOURS` in Railway environment variables
2. Redeploy the cron service

---

## Database Index

The cleanup job uses this index for efficient queries:

```sql
CREATE INDEX IF NOT EXISTS idx_sessions_blank_cleanup
ON dr_sessions_v4 (has_blank_presentation, has_topic, created_at)
WHERE has_blank_presentation = TRUE AND has_topic = FALSE;
```

This was created in the v4.10.0 migration.

---

## Related Documentation

- [OPERATING_MODEL_BUILDER_V2.md](/docs/OPERATING_MODEL_BUILDER_V2.md) - Full feature specification
- [Railway Cron Jobs Docs](https://docs.railway.com/reference/cron-jobs) - Railway documentation
