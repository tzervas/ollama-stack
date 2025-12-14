#!/bin/bash

# Log Analysis Script for Ollama + Open-WebUI Integration Tests
# This script helps analyze logs collected during testing

set -e

LOG_DIR="./test/logs"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_color() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Function to find latest log files
find_latest_logs() {
    local pattern=$1
    find "$LOG_DIR" -name "*$pattern*" -type f -printf '%T@ %p\n' 2>/dev/null | sort -n | tail -1 | cut -d' ' -f2-
}

# Function to analyze container logs
analyze_container_logs() {
    local log_file=$1

    if [ ! -f "$log_file" ]; then
        print_color $RED "Log file not found: $log_file"
        return 1
    fi

    print_color $BLUE "🔍 Analyzing container logs: $log_file"
    echo "========================================"

    # Check for common error patterns
    echo "❌ Error Analysis:"
    grep -i "error\|exception\|failed\|fatal" "$log_file" | head -10 || echo "  No errors found"

    echo ""
    echo "⚠️  Warning Analysis:"
    grep -i "warn\|warning" "$log_file" | head -10 || echo "  No warnings found"

    echo ""
    echo "🔄 Service Status:"
    grep -E "(healthy|unhealthy|starting|started|ready)" "$log_file" | tail -5 || echo "  No status information found"

    echo ""
    echo "🌐 Network/Connection Issues:"
    grep -i "connection\|network\|timeout\|refused" "$log_file" | head -5 || echo "  No network issues found"
}

# Function to analyze system info
analyze_system_info() {
    local info_file=$1

    if [ ! -f "$info_file" ]; then
        print_color $RED "System info file not found: $info_file"
        return 1
    fi

    print_color $BLUE "🖥️  Analyzing system information: $info_file"
    echo "========================================"

    echo "🐳 Docker Status:"
    grep -A 5 "RUNNING CONTAINERS" "$info_file" || echo "  Container info not found"

    echo ""
    echo "💾 Resource Usage:"
    grep -A 10 "SYSTEM RESOURCES" "$info_file" | head -15 || echo "  Resource info not found"
}

# Function to show test summary
show_test_summary() {
    local log_file=$(find_latest_logs "container_logs")

    if [ -z "$log_file" ]; then
        print_color $YELLOW "No container log files found"
        return
    fi

    print_color $GREEN "📊 Test Summary from: $(basename "$log_file")"
    echo "========================================"

    # Count containers
    local container_count=$(grep -c "=== LOGS FROM CONTAINER:" "$log_file" 2>/dev/null || echo "0")
    echo "🏗️  Containers analyzed: $container_count"

    # Check for failures
    local error_count=$(grep -c -i "error\|failed\|exception" "$log_file" 2>/dev/null || echo "0")
    if [ "$error_count" -gt 0 ]; then
        print_color $RED "❌ Errors found: $error_count"
    else
        print_color $GREEN "✅ No errors detected"
    fi

    # Check service health
    local healthy_count=$(grep -c "healthy" "$log_file" 2>/dev/null || echo "0")
    local unhealthy_count=$(grep -c "unhealthy" "$log_file" 2>/dev/null || echo "0")

    echo "❤️  Healthy services: $healthy_count"
    if [ "$unhealthy_count" -gt 0 ]; then
        print_color $RED "💔 Unhealthy services: $unhealthy_count"
    fi
}

# Main script logic
case "${1:-}" in
    "--summary"|"-s")
        show_test_summary
        ;;
    "--analyze"|"-a")
        container_log=$(find_latest_logs "container_logs")
        system_info=$(find_latest_logs "system_info")

        if [ -n "$container_log" ]; then
            analyze_container_logs "$container_log"
            echo ""
        fi

        if [ -n "$system_info" ]; then
            analyze_system_info "$system_info"
        fi
        ;;
    "--list"|"-l")
        print_color $BLUE "📋 Available log files in $LOG_DIR:"
        if [ -d "$LOG_DIR" ]; then
            ls -la "$LOG_DIR" 2>/dev/null | grep -v "^total" || print_color $YELLOW "No log files found"
        else
            print_color $YELLOW "Log directory does not exist: $LOG_DIR"
        fi
        ;;
    "--help"|"-h"|*)
        echo "Log Analysis Script for Ollama + Open-WebUI Integration Tests"
        echo ""
        echo "Usage: $0 [COMMAND]"
        echo ""
        echo "Commands:"
        echo "  --summary, -s    Show test execution summary"
        echo "  --analyze, -a    Perform detailed log analysis"
        echo "  --list, -l       List all available log files"
        echo "  --help, -h       Show this help message"
        echo ""
        echo "Log files are stored in: $LOG_DIR"
        echo "Run integration tests first: ./test/integration.sh"
        ;;
esac</content>
<parameter name="filePath">c:\Users\tyler\Documents\devel\github\ollama\test\analyze_logs.sh