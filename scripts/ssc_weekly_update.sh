#!/bin/bash

################################################################################
# SSC Hockey Weekly Update Script
#
# Performs weekly automated scraping of SSC Hockey data with:
# - Full season scraping (all dates)
# - Game details, stats, and standings
# - Dated output directories
# - Comprehensive logging
# - Change reporting
# - Email notifications (optional)
#
# Usage:
#   ./ssc_weekly_update.sh
#
# Cron Example (Sundays at 2 AM):
#   0 2 * * 0 /path/to/ssc_weekly_update.sh
################################################################################

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LEAGUE_ID="224428"
SUBSEASON_ID="948564"

# Output directories
DATE_SUFFIX=$(date +%Y_%m_%d)
OUTPUT_DIR="${SCRIPT_DIR}/data/ssc_${DATE_SUFFIX}"
LOG_DIR="${SCRIPT_DIR}/logs"
LOG_FILE="${LOG_DIR}/ssc_weekly_${DATE_SUFFIX}.log"

# Weekly data directory (for incremental updates)
WEEKLY_DIR="${SCRIPT_DIR}/data/weekly"

# Email configuration (optional)
SEND_EMAIL="false"  # Set to "true" to enable email notifications
EMAIL_TO="your-email@example.com"
EMAIL_SUBJECT="SSC Hockey Weekly Scrape Report - ${DATE_SUFFIX}"

# Create directories
mkdir -p "$OUTPUT_DIR"
mkdir -p "$LOG_DIR"
mkdir -p "$WEEKLY_DIR"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Error handling
set -e
trap 'log "ERROR: Script failed on line $LINENO"' ERR

################################################################################
# Main Execution
################################################################################

log "=========================================="
log "SSC Hockey Weekly Scrape Starting"
log "=========================================="
log "League ID: ${LEAGUE_ID}"
log "Subseason ID: ${SUBSEASON_ID}"
log "Output Directory: ${OUTPUT_DIR}"
log "Log File: ${LOG_FILE}"
log ""

# Step 1: Run incremental weekly scraper
log "Step 1: Running incremental weekly scraper..."
python3 "${SCRIPT_DIR}/ssc_weekly_scraper.py" \
    --league-id "$LEAGUE_ID" \
    --subseason-id "$SUBSEASON_ID" \
    --out "$WEEKLY_DIR" \
    --scrape-game-details \
    --scrape-stats \
    --scrape-standings \
    2>&1 | tee -a "$LOG_FILE"

if [ $? -eq 0 ]; then
    log "✓ Incremental scrape completed successfully"
else
    log "✗ Incremental scrape failed"
    exit 1
fi

# Step 2: Copy weekly data to dated directory (for archiving)
log ""
log "Step 2: Archiving data to dated directory..."
cp -r "$WEEKLY_DIR"/* "$OUTPUT_DIR/" 2>&1 | tee -a "$LOG_FILE"
log "✓ Data archived to ${OUTPUT_DIR}"

# Step 3: Generate summary report
log ""
log "Step 3: Generating summary report..."

# Read change report
CHANGE_REPORT="${WEEKLY_DIR}/change_report.json"
if [ -f "$CHANGE_REPORT" ]; then
    log "Change Report Summary:"
    python3 -c "
import json
with open('${CHANGE_REPORT}', 'r') as f:
    report = json.load(f)
    summary = report.get('summary', {})
    print('  - New Games: {}'.format(summary.get('new_games', 0)))
    print('  - Updated Games: {}'.format(summary.get('updated_games', 0)))
    print('  - Total Games: {}'.format(summary.get('total_games', 0)))
    print('  - Player Stats: {}'.format(summary.get('player_stats_count', 0)))
    print('  - Standings: {}'.format(summary.get('standings_count', 0)))
" | tee -a "$LOG_FILE"
else
    log "Warning: Change report not found"
fi

# Step 4: Compare with previous week (if exists)
log ""
log "Step 4: Comparing with previous week..."

# Find previous week's directory
PREV_DIR=$(ls -dt "${SCRIPT_DIR}/data/ssc_"* 2>/dev/null | grep -v "${DATE_SUFFIX}" | head -n 1)

if [ -n "$PREV_DIR" ] && [ -d "$PREV_DIR" ]; then
    log "Previous directory: ${PREV_DIR}"

    # Run comparison script
    if [ -f "${SCRIPT_DIR}/compare_ssc_data.py" ]; then
        python3 "${SCRIPT_DIR}/compare_ssc_data.py" \
            --old-dir "$PREV_DIR" \
            --new-dir "$OUTPUT_DIR" \
            --output "${OUTPUT_DIR}/comparison_report.json" \
            2>&1 | tee -a "$LOG_FILE"

        log "✓ Comparison report generated"
    else
        log "Warning: Comparison script not found"
    fi
else
    log "No previous directory found for comparison"
fi

# Step 5: Generate summary statistics
log ""
log "Step 5: Generating statistics..."
python3 -c "
import json
from pathlib import Path

schedules_file = Path('${OUTPUT_DIR}/schedules.json')
if schedules_file.exists():
    with open(schedules_file, 'r') as f:
        games = json.load(f)

    # Count games by status
    played = sum(1 for g in games if g.get('visitor_score') is not None)
    scheduled = len(games) - played

    # Count games with details
    with_details = sum(1 for g in games if g.get('period_scores') is not None)

    print(f'  - Total Games: {len(games)}')
    print(f'  - Games Played: {played}')
    print(f'  - Games Scheduled: {scheduled}')
    print(f'  - Games with Details: {with_details}')

    # Division breakdown
    divisions = {}
    for g in games:
        div = g.get('division', 'Unknown')
        divisions[div] = divisions.get(div, 0) + 1

    print('  - Division Breakdown:')
    for div, count in sorted(divisions.items()):
        print(f'    {div}: {count}')
" | tee -a "$LOG_FILE"

# Step 6: Cleanup old archives (keep last 12 weeks)
log ""
log "Step 6: Cleaning up old archives..."
cd "${SCRIPT_DIR}/data"
ls -dt ssc_* 2>/dev/null | tail -n +13 | xargs -r rm -rf
log "✓ Cleanup complete (keeping last 12 weeks)"

# Step 7: Generate email report (if enabled)
if [ "$SEND_EMAIL" = "true" ]; then
    log ""
    log "Step 7: Sending email report..."

    # Create email body
    EMAIL_BODY=$(cat <<EOF
SSC Hockey Weekly Scrape Report
Date: ${DATE_SUFFIX}

Summary:
$(cat "$CHANGE_REPORT" 2>/dev/null || echo "Change report not available")

Log file: ${LOG_FILE}
Data directory: ${OUTPUT_DIR}

This is an automated message from the SSC Hockey scraper.
EOF
)

    # Send email (requires mailx or similar)
    echo "$EMAIL_BODY" | mail -s "$EMAIL_SUBJECT" "$EMAIL_TO"

    log "✓ Email sent to ${EMAIL_TO}"
else
    log ""
    log "Step 7: Email notifications disabled (set SEND_EMAIL=true to enable)"
fi

# Final summary
log ""
log "=========================================="
log "Weekly Scrape Complete!"
log "=========================================="
log "Output: ${OUTPUT_DIR}"
log "Log: ${LOG_FILE}"
log "Change Report: ${WEEKLY_DIR}/change_report.json"
log ""
log "Next steps:"
log "  - Review change report: cat ${WEEKLY_DIR}/change_report.json"
log "  - View games: cat ${OUTPUT_DIR}/schedules.json | python3 -m json.tool"
log "  - Check logs: tail -f ${LOG_FILE}"
log "=========================================="

exit 0
