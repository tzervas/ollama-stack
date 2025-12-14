#!/bin/bash

LOG_DIR="/app/test/logs"

# Function to display available logs (defined early for command line use)
show_available_logs() {
    echo "📋 Available log files:"
    if [ -d "$LOG_DIR" ]; then
        ls -la "$LOG_DIR" 2>/dev/null || echo "No log files found"
    else
        echo "Log directory does not exist yet"
    fi
}

# Check for command line arguments
if [ "$1" = "--logs" ] || [ "$1" = "-l" ]; then
    show_available_logs
    exit 0
fi

if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Run comprehensive integration tests for Ollama + Open-WebUI"
    echo ""
    echo "Options:"
    echo "  --logs, -l    Show available log files from previous test runs"
    echo "  --help, -h    Show this help message"
    echo ""
    echo "Log files are stored in test/logs/ directory and persist after container shutdown"
    exit 0
fi

echo "Running comprehensive integration tests with Python setup script..."

# Function to collect and save container logs
collect_container_logs() {
    local timestamp=$(date +"%Y%m%d_%H%M%S")
    local log_file="$LOG_DIR/container_logs_${timestamp}.log"
    
    echo "📋 Collecting container logs to $log_file..."
    
    echo "=== CONTAINER LOGS COLLECTED AT $(date) ===" > "$log_file"
    echo "" >> "$log_file"
    
    # Get logs from all running containers
    for container in $(docker ps --format "table {{.Names}}" | tail -n +2); do
        echo "=== LOGS FROM CONTAINER: $container ===" >> "$log_file"
        docker logs "$container" >> "$log_file" 2>&1
        echo "" >> "$log_file"
        echo "=== END LOGS FROM CONTAINER: $container ===" >> "$log_file"
        echo "" >> "$log_file"
    done
    
    echo "✅ Container logs saved to $log_file"
}

# Function to collect system information
collect_system_info() {
    local timestamp=$(date +"%Y%m%d_%H%M%S")
    local info_file="$LOG_DIR/system_info_${timestamp}.txt"
    
    echo "📊 Collecting system information to $info_file..."
    
    echo "=== SYSTEM INFORMATION COLLECTED AT $(date) ===" > "$info_file"
    echo "" >> "$info_file"
    
    echo "=== DOCKER VERSION ===" >> "$info_file"
    docker --version >> "$info_file" 2>&1
    echo "" >> "$info_file"
    
    echo "=== DOCKER COMPOSE VERSION ===" >> "$info_file"
    docker-compose --version >> "$info_file" 2>&1
    echo "" >> "$info_file"
    
    echo "=== RUNNING CONTAINERS ===" >> "$info_file"
    docker ps -a >> "$info_file" 2>&1
    echo "" >> "$info_file"
    
    echo "=== DOCKER NETWORKS ===" >> "$info_file"
    docker network ls >> "$info_file" 2>&1
    echo "" >> "$info_file"
    
    echo "=== DOCKER VOLUMES ===" >> "$info_file"
    docker volume ls >> "$info_file" 2>&1
    echo "" >> "$info_file"
    
    echo "=== SYSTEM RESOURCES ===" >> "$info_file"
    df -h >> "$info_file" 2>&1
    echo "" >> "$info_file"
    free -h >> "$info_file" 2>&1
    echo "" >> "$info_file"
    
    echo "✅ System information saved to $info_file"
}

# Set up trap to collect logs on unexpected exit
trap 'echo "🛑 Test interrupted, collecting emergency logs..."; collect_container_logs; collect_system_info' INT TERM

# Function to log with structured format
log() {
    local level=$1
    local component=$2
    local message=$3
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    echo "{\"timestamp\":\"$timestamp\",\"level\":\"$level\",\"component\":\"$component\",\"message\":\"$message\"}"
}

# Function to collect system metrics using Python
collect_system_metrics() {
    python -c "
import psutil
import json
from datetime import datetime

try:
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    mem_percent = memory.percent

    # Try to get GPU info if available
    gpu_info = 'N/A'
    try:
        import GPUtil
        gpus = GPUtil.getGPUs()
        if gpus:
            gpu_info = f'{gpus[0].load * 100:.1f}%'
    except ImportError:
        pass

    metrics = {
        'cpu_usage': f'{cpu_percent:.1f}%',
        'mem_usage': f'{mem_percent:.1f}%',
        'gpu_usage': gpu_info,
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }
    print(json.dumps(metrics))
except Exception as e:
    print(f'Error collecting metrics: {e}')
"
}

# Function to collect container metrics
collect_container_metrics() {
    local container=$1
    if docker ps | grep -q "$container"; then
        stats=$(docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" "$container" 2>/dev/null | tail -1)
        echo "$stats"
    else
        echo "Container $container not running"
    fi
}

log "INFO" "test" "Starting integration tests"

# Collect initial logs after service startup
collect_container_logs
collect_system_info

# Wait for services to be healthy
log "INFO" "test" "Waiting for services to be healthy"
sleep 30

# Test Ollama API
log "INFO" "test" "Testing Ollama API"
if curl -f http://ollama:11434/api/tags >/dev/null 2>&1; then
    log "INFO" "test" "Ollama API is responding"
else
    log "ERROR" "test" "Ollama API is not responding"
fi

# Test Open-WebUI
log "INFO" "test" "Testing Open-WebUI"
if curl -f http://open-webui:8080/health >/dev/null 2>&1; then
    log "INFO" "test" "Open-WebUI is responding"
else
    log "ERROR" "test" "Open-WebUI is not responding"
fi

# Test Caddy reverse proxy
log "INFO" "test" "Testing Caddy reverse proxy"
if curl -f -k https://caddy:443 >/dev/null 2>&1; then
    log "INFO" "test" "Caddy reverse proxy is responding"
else
    log "ERROR" "test" "Caddy reverse proxy is not responding"
fi

# Collect and log system metrics
log "INFO" "test" "Collecting system metrics"
system_metrics=$(collect_system_metrics)
log "INFO" "metrics" "System metrics: $system_metrics"

# Collect container metrics
log "INFO" "test" "Collecting container metrics"
for container in "ollama-test-ollama" "ollama-test-open-webui" "ollama-test-caddy"; do
    container_metrics=$(collect_container_metrics "$container")
    log "INFO" "metrics" "Container $container: $container_metrics"
done

# Run certificate checks using Python script
log "INFO" "test" "Running certificate checks"
if python ../setup.py certs --skip-dns --skip-caddy; then
    log "INFO" "test" "Certificate checks completed"
else
    log "WARN" "test" "Certificate checks had issues"
fi

# Test basic functionality
log "INFO" "test" "Testing basic Ollama functionality"
if docker exec ollama-test-ollama ollama list >/dev/null 2>&1; then
    log "INFO" "test" "Ollama list command works"
else
    log "ERROR" "test" "Ollama list command failed"
fi

log "INFO" "test" "Integration tests completed"

# Optional: Keep services running for manual testing
if [ "$1" = "--keep-running" ]; then
    log "INFO" "test" "Keeping services running for manual testing"
    log "INFO" "test" "Press Ctrl+C to stop"
    trap "log 'INFO' 'test' 'Stopping services'; python ../setup.py compose -f docker-compose.test.yml down" INT
    wait
else
    # Stop services
    log "INFO" "test" "Stopping services"
    python ../setup.py compose -f docker-compose.test.yml down
fi

exit 0

# Function to test endpoint
test_endpoint() {
    local url=$1
    local expected_status=${2:-200}
    if curl -k -s -o /dev/null -w "%{http_code}" "$url" | grep -q "$expected_status"; then
        log "INFO" "test" "✓ $url: PASSED"
        return 0
    else
        log "ERROR" "test" "✗ $url: FAILED"
        return 1
    fi
}

# Function to get LAN IP
get_lan_ip() {
    case $PLATFORM in
        windows)
            # Use PowerShell to get IP
            powershell.exe -Command "Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias 'Ethernet*','Wi-Fi*' | Where-Object { \$_.IPAddress -notlike '127.*' -and \$_.IPAddress -notlike '169.*' } | Select-Object -First 1 -ExpandProperty IPAddress" 2>/dev/null || echo "localhost"
            ;;
        linux)
            hostname -I | awk '{print $1}' || echo "localhost"
            ;;
        macos)
            ipconfig getifaddr en0 2>/dev/null || hostname -I | awk '{print $1}' || echo "localhost"
            ;;
        *)
            echo "localhost"
            ;;
    esac
}

# Get LAN IP
LAN_IP=$(get_lan_ip)
echo "Detected LAN IP: $LAN_IP"

# Start services
echo "Starting services..."
docker-compose up -d

# Wait for services with progress
echo "Waiting for services to be healthy (this may take several minutes)..."
for i in {1..12}; do  # 12 * 30s = 6 minutes max
    echo "Checking health at $(date)..."
    
    # Check if Ollama is healthy
    if docker ps | grep -q "ollama-test-ollama" && docker exec ollama-test-ollama curl -f http://localhost:11434/ >/dev/null 2>&1; then
        echo "✓ Ollama is healthy"
        ollama_healthy=true
    else
        echo "⏳ Ollama not yet healthy..."
        ollama_healthy=false
    fi
    
    # If Ollama healthy, check others
    if [ "$ollama_healthy" = true ]; then
        if docker ps | grep -q "ollama-test-open-webui" && docker exec ollama-test-open-webui curl -f http://localhost:8080/ >/dev/null 2>&1; then
            echo "✓ Open-WebUI is healthy"
            webui_healthy=true
        else
            echo "⏳ Open-WebUI not yet healthy..."
            webui_healthy=false
        fi
        
        if docker ps | grep -q "ollama-caddy-1"; then
            echo "✓ Caddy is running"
            caddy_running=true
        else
            echo "⏳ Caddy not yet running..."
            caddy_running=false
        fi
        
        if [ "$webui_healthy" = true ] && [ "$caddy_running" = true ]; then
            break
        fi
    fi
    
    sleep 30
done

# Test service health
echo "Testing service health..."

# Ollama API direct test
if docker exec ollama-test-ollama curl -f http://localhost:11434/api/tags >/dev/null 2>&1; then
    echo "✓ Ollama API accessible"
else
    echo "✗ Ollama API not accessible"
    ((failures++))
fi

# Open-WebUI API test
if docker exec ollama-test-open-webui curl -f http://localhost:8080/api/config >/dev/null 2>&1; then
    echo "✓ Open-WebUI API accessible"
else
    echo "✗ Open-WebUI API not accessible"
    ((failures++))
fi

# Test data persistence
echo "Testing data persistence..."
# Check if volumes exist and have content
if docker volume ls | grep -q "ollama-test_ollama-test"; then
    echo "✓ Ollama volume exists"
else
    echo "✗ Ollama volume missing"
    ((failures++))
fi

if docker volume ls | grep -q "ollama-test_open-webui-test"; then
    echo "✓ Open-WebUI volume exists"
else
    echo "✗ Open-WebUI volume missing"
    ((failures++))
fi

# Capture logs
timestamp=$(date +%Y%m%d_%H%M%S)
logfile="../test/logs_${PLATFORM}_${timestamp}.txt"
echo "Capturing logs to $logfile..."
docker-compose logs > "$logfile"

# Stop services
echo "Stopping services..."
docker-compose down

# Analyze logs for errors
echo "Analyzing logs for critical errors..."
if grep -i "error\|failed\|exception" "$logfile" | grep -v -i "debug\|info\|warn"; then
    echo "⚠ Found potential errors in logs - check $logfile"
fi

# Collect final logs before cleanup
echo "📋 Collecting final logs..."
collect_container_logs
collect_system_info

if [ $failures -eq 0 ]; then
    echo "All integration tests PASSED"
    echo "Services are healthy and accessible!"
    echo "LAN access URL: https://$LAN_IP"
    exit 0
else
    echo "$failures integration tests FAILED"
    echo "Check logs in $LOG_DIR for details"
    exit 1
fi