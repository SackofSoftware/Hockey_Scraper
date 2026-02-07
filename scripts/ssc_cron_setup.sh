#!/bin/bash

################################################################################
# SSC Hockey Cron Job Setup Script
#
# This script helps you configure a cron job for weekly automated scraping
# of SSC Hockey data.
#
# Usage:
#   ./ssc_cron_setup.sh install    # Install cron job
#   ./ssc_cron_setup.sh uninstall  # Remove cron job
#   ./ssc_cron_setup.sh status     # Check if cron job is installed
#   ./ssc_cron_setup.sh test       # Test run the scraper
################################################################################

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WEEKLY_SCRIPT="${SCRIPT_DIR}/ssc_weekly_update.sh"
CRON_MARKER="# SSC Hockey Weekly Scraper"

# Default schedule: Sundays at 2:00 AM
DEFAULT_SCHEDULE="0 2 * * 0"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

################################################################################
# Check if weekly script exists
################################################################################
check_weekly_script() {
    if [ ! -f "$WEEKLY_SCRIPT" ]; then
        log_error "Weekly update script not found: $WEEKLY_SCRIPT"
        exit 1
    fi

    if [ ! -x "$WEEKLY_SCRIPT" ]; then
        log_warn "Weekly script is not executable. Making it executable..."
        chmod +x "$WEEKLY_SCRIPT"
    fi
}

################################################################################
# Install cron job
################################################################################
install_cron() {
    check_weekly_script

    # Check if cron job already exists
    if crontab -l 2>/dev/null | grep -q "$CRON_MARKER"; then
        log_warn "Cron job already installed. Uninstall first to reinstall."
        exit 1
    fi

    log_info "Installing SSC Hockey weekly scraper cron job..."
    log_info ""

    # Prompt for schedule (or use default)
    echo "Enter cron schedule (default: $DEFAULT_SCHEDULE for Sundays at 2 AM):"
    echo "Format: minute hour day_of_month month day_of_week"
    echo "Examples:"
    echo "  0 2 * * 0       = Sundays at 2:00 AM"
    echo "  0 2 * * 1       = Mondays at 2:00 AM"
    echo "  0 14 * * 6      = Saturdays at 2:00 PM"
    echo "  0 3 * * 1-5     = Weekdays at 3:00 AM"
    echo ""
    read -p "Schedule (press Enter for default): " SCHEDULE

    if [ -z "$SCHEDULE" ]; then
        SCHEDULE="$DEFAULT_SCHEDULE"
    fi

    log_info "Using schedule: $SCHEDULE"
    log_info ""

    # Create cron entry
    CRON_ENTRY="$SCHEDULE $WEEKLY_SCRIPT $CRON_MARKER"

    # Add to crontab
    (crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -

    if [ $? -eq 0 ]; then
        log_info "✓ Cron job installed successfully!"
        log_info ""
        log_info "Current crontab:"
        crontab -l | grep -A 1 "$CRON_MARKER"
        log_info ""
        log_info "The scraper will run automatically according to the schedule."
        log_info "Logs will be saved to: ${SCRIPT_DIR}/logs/"
    else
        log_error "Failed to install cron job"
        exit 1
    fi
}

################################################################################
# Uninstall cron job
################################################################################
uninstall_cron() {
    if ! crontab -l 2>/dev/null | grep -q "$CRON_MARKER"; then
        log_warn "Cron job not found. Nothing to uninstall."
        exit 0
    fi

    log_info "Uninstalling SSC Hockey weekly scraper cron job..."

    # Remove from crontab
    crontab -l 2>/dev/null | grep -v "$CRON_MARKER" | crontab -

    if [ $? -eq 0 ]; then
        log_info "✓ Cron job uninstalled successfully!"
    else
        log_error "Failed to uninstall cron job"
        exit 1
    fi
}

################################################################################
# Check cron job status
################################################################################
check_status() {
    log_info "Checking SSC Hockey cron job status..."
    log_info ""

    if crontab -l 2>/dev/null | grep -q "$CRON_MARKER"; then
        log_info "✓ Cron job is INSTALLED"
        log_info ""
        log_info "Current cron entry:"
        crontab -l | grep "$CRON_MARKER"
        log_info ""

        # Parse schedule
        CRON_LINE=$(crontab -l | grep "$CRON_MARKER")
        SCHEDULE=$(echo "$CRON_LINE" | awk '{print $1, $2, $3, $4, $5}')
        log_info "Schedule: $SCHEDULE"

        # Show next run time (if possible)
        if command -v systemctl &> /dev/null; then
            log_info ""
            log_info "Cron service status:"
            systemctl status cron 2>/dev/null || systemctl status crond 2>/dev/null || echo "Unable to check cron service status"
        fi
    else
        log_warn "✗ Cron job is NOT installed"
        log_info ""
        log_info "Run './ssc_cron_setup.sh install' to install it."
    fi

    log_info ""
    log_info "Recent logs:"
    if [ -d "${SCRIPT_DIR}/logs" ]; then
        ls -lt "${SCRIPT_DIR}/logs"/ssc_weekly_*.log 2>/dev/null | head -5 || log_info "No logs found"
    else
        log_info "No logs directory found"
    fi
}

################################################################################
# Test run
################################################################################
test_run() {
    check_weekly_script

    log_info "Running test scrape..."
    log_info "This will run the weekly update script manually."
    log_info ""

    read -p "Continue? (y/N): " CONFIRM
    if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
        log_info "Test run cancelled."
        exit 0
    fi

    log_info ""
    log_info "Starting test run..."
    log_info "================================================"

    bash "$WEEKLY_SCRIPT"

    log_info "================================================"
    log_info "Test run complete!"
}

################################################################################
# Setup log rotation (optional)
################################################################################
setup_log_rotation() {
    log_info "Setting up log rotation..."

    LOG_DIR="${SCRIPT_DIR}/logs"
    LOGROTATE_CONF="/etc/logrotate.d/ssc-hockey"

    if [ ! -w "/etc/logrotate.d" ]; then
        log_error "Cannot write to /etc/logrotate.d (need sudo)"
        log_info "You can manually configure log rotation or run with sudo"
        return 1
    fi

    cat > "$LOGROTATE_CONF" <<EOF
$LOG_DIR/ssc_weekly_*.log {
    weekly
    rotate 12
    compress
    delaycompress
    missingok
    notifempty
    create 0644 $(whoami) $(whoami)
}
EOF

    log_info "✓ Log rotation configured (keeps last 12 weeks)"
    log_info "  Config file: $LOGROTATE_CONF"
}

################################################################################
# Main
################################################################################

case "$1" in
    install)
        install_cron
        ;;
    uninstall)
        uninstall_cron
        ;;
    status)
        check_status
        ;;
    test)
        test_run
        ;;
    logrotate)
        setup_log_rotation
        ;;
    *)
        echo "SSC Hockey Cron Setup Script"
        echo ""
        echo "Usage: $0 {install|uninstall|status|test|logrotate}"
        echo ""
        echo "Commands:"
        echo "  install    - Install weekly cron job"
        echo "  uninstall  - Remove cron job"
        echo "  status     - Check if cron job is installed"
        echo "  test       - Run a test scrape manually"
        echo "  logrotate  - Setup log rotation (requires sudo)"
        echo ""
        echo "Examples:"
        echo "  $0 install          # Install with interactive prompts"
        echo "  $0 status           # Check current status"
        echo "  $0 test             # Test the scraper"
        echo ""
        exit 1
        ;;
esac

exit 0
