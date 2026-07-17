# Ollama + Open-WebUI Setup

<!-- FLEET-BADGES:BEGIN -->
[![CI](https://github.com/tzervas/ollama-stack/actions/workflows/fleet-ci.yml/badge.svg?branch=main)](https://github.com/tzervas/ollama-stack/actions/workflows/fleet-ci.yml?query=branch%3Amain)
[![Security](https://github.com/tzervas/ollama-stack/actions/workflows/fleet-security.yml/badge.svg?branch=main)](https://github.com/tzervas/ollama-stack/actions/workflows/fleet-security.yml?query=branch%3Amain)
<!-- FLEET-BADGES:END -->

This setup provides a one-click experience to run Ollama + Open-WebUI with persistence across multiple platforms using a unified Python-based management script.

## Prerequisites

- **Python 3.8+**
- **Docker and Docker Compose**
- **uv package manager** (recommended for faster installs):
  ```bash
  # Install uv
  curl -LsSf https://astral.sh/uv/install.sh | sh
  # Or on Windows:
  powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```

## Quick Start

1. **Clone or download** this repository
2. **Install dependencies** (if any):
   ```bash
   uv pip install -r requirements.txt
   # Or with pip:
   pip install -r requirements.txt
   ```
3. **Setup configuration** (automatic platform detection):
   ```bash
   python setup.py setup
   # Or for interactive setup:
   python setup.py setup --interactive
   ```
4. **Start services**:
   ```bash
   python setup.py compose up -d
   ```
5. **Access the interface**:
   - Local: https://localhost
   - LAN: https://<your-lan-ip>
   - Domain: https://your-domain.com (if configured)

## Features

- **Unified Setup**: Single docker-compose.yml works across Windows, Linux, and macOS
- **Automatic Platform Detection**: OS-agnostic platform detection for optimal Docker performance
- **Automatic SSL**: Self-signed certificates for immediate secure access
- **GPU Support**: NVIDIA GPU acceleration on Windows/Linux
- **Persistence**: Docker volumes for models and data
- **Health Checks**: Service monitoring and dependency management
- **Resource Management**: Automatic resource allocation and limits

## SSL Certificates and Domain Setup

### Option 1: Self-Signed Certificates (Recommended - Simplest)

**Default configuration** - works immediately for LAN access:
- Automatically generates self-signed certificates
- Access via `https://<LAN_IP>` (browser shows security warning, but connection is encrypted)
- No domain configuration required
- Perfect for self-hosted LAN access

### Option 2: Let's Encrypt with Domain (Advanced)

For trusted SSL certificates without browser warnings:

1. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env:
   DOMAIN=ollama.vectorweight.com  # Your subdomain
   EMAIL=tzervas@vectorweight.com   # Your email
   ```

2. **For Squarespace-managed domains**:
   - **HTTP-01 Challenge** (recommended for Squarespace):
     - Temporarily expose port 80 to the internet during certificate issuance
     - Edit `Caddyfile` and uncomment the HTTP challenge section
     - Run: `docker-compose up -d`
   - **DNS Challenge**: Not available for Squarespace domains

3. **Certificate Management**:
   - Certificates stored in `caddy_data` volume
   - Automatic renewal handled by Caddy
   - No manual certificate management needed

### Certificate Management

Use the Python script to manage SSL certificates:

```bash
# Check certificates and DNS
python setup.py certs

# Skip specific checks
python setup.py certs --skip-dns --skip-caddy
```

The script automatically:
- Tests DNS resolution for your domain
- Validates Caddy configuration
- Checks existing certificate status
- Provides setup guidance for Squarespace domains

## Containerized Testing

The project includes a complete containerized testing environment:

### Development Container

Build and run the development/testing container:

```bash
# Build the test container
docker build -f Dockerfile.test -t ollama-dev .

# Run the container with Docker socket access
docker run -it --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v $(pwd):/app \
  ollama-dev
```

### Integration Tests

Run comprehensive integration tests:

```bash
# Run tests using Python script
python setup.py test

# Run tests and keep services running for manual testing
python setup.py test --keep-running

# Run containerized tests
docker-compose -f docker-compose.test.yml up --abort-on-container-exit
```

### Test Features

- **Automated platform detection** using Python setup script
- **System metrics collection** with structured JSON logging
- **Container health monitoring** and performance metrics
- **Certificate validation** and DNS testing
- **Cross-platform compatibility** (Windows, Linux, macOS)

## Platform Detection

The Python setup script automatically detects your system's Docker platform:

- **x86_64/AMD64**: `linux/amd64`
- **ARM64**: `linux/arm64` (including Apple Silicon Macs)
- **ARMv7**: `linux/arm/v7`

### Docker Compose Commands

All docker-compose commands are wrapped through the Python script:

```bash
# Start services
python setup.py compose up -d

# View logs
python setup.py compose logs

# Stop services
python setup.py compose down

# Restart services
python setup.py compose restart
```

The script automatically sets the correct `DOCKER_PLATFORM` environment variable for optimal performance.

### Security Notes
- LAN-only access recommended (firewall rules)
- Domain certificates provide trusted SSL without browser warnings
- Certificates persist across deployments via Docker volumes

## Persistence
Data is persisted in Docker named volumes:
- `ollama`: Ollama models and data
- `open-webui`: Open-WebUI data
- `caddy_data`: SSL certificates and Caddy data
- `caddy_config`: Caddy configuration

## Testing

The project includes a comprehensive, production-grade testing framework with multiple test types:

### Test Types

- **Unit Tests**: Test individual Python functions and classes
- **Integration Tests**: Test service interactions and Docker Compose setup
- **API Tests**: Test REST API endpoints and responses
- **Performance Tests**: Load testing and performance regression detection
- **Security Tests**: SSL/TLS, headers, and security configuration validation
- **Cross-platform Tests**: Windows, Linux, and macOS compatibility

### Running Tests

#### Quick Test Commands

```bash
# Run all tests (containerized)
python test/run_tests.py

# Run unit tests only
python -m pytest test/test_setup.py -v

# Run integration tests (containerized)
docker-compose -f docker-compose.test.yml up --abort-on-container-exit

# Run performance tests
python test/run_tests.py --skip-security

# Run security audit
python test/test_security.py --audit
```

#### VS Code Tasks

Use the built-in VS Code tasks for testing:

- `test:all` - Run complete test suite
- `test:unit` - Unit tests only
- `test:integration` - Integration tests
- `test:api` - API integration tests
- `test:performance` - Performance tests
- `test:security` - Security tests
- `test:containerized` - Full containerized test suite

#### Containerized Testing Environment

The testing environment uses isolated Docker containers with comprehensive logging:

```bash
# Run integration tests with detailed logging
docker-compose -f docker-compose.test.yml up test-runner

# Or run directly in test-runner container
docker exec ollama-test-runner bash test/integration.sh

# View available logs after testing
docker exec ollama-test-runner bash test/integration.sh --logs

# Analyze logs for debugging
docker exec ollama-test-runner bash test/analyze_logs.sh --summary
docker exec ollama-test-runner bash test/analyze_logs.sh --analyze
```

### Log Collection & Debugging

The testing framework includes comprehensive log collection:

- **Persistent Logs**: All logs are saved to `test/logs/` volume (survives container shutdown)
- **Container Logs**: Automatic collection from all running containers
- **System Information**: Docker, networks, volumes, and resource usage
- **Error Analysis**: Automated detection of errors, warnings, and failures
- **Log Analysis Tools**: Built-in scripts for log analysis and debugging

#### Accessing Logs

```bash
# List all collected log files
docker exec ollama-test-runner ls -la test/logs/

# View latest container logs
docker exec ollama-test-runner cat test/logs/$(docker exec ollama-test-runner ls -t test/logs/container_logs_* | head -1)

# Run log analysis
docker exec ollama-test-runner bash test/analyze_logs.sh --summary
docker exec ollama-test-runner bash test/analyze_logs.sh --analyze
```

#### Log Files Structure

```
test/logs/
├── container_logs_YYYYMMDD_HHMMSS.log    # All container logs
├── system_info_YYYYMMDD_HHMMSS.txt       # System information
└── [additional logs from test runs]
```

### Test Configuration

Tests automatically detect the environment:
- **Local development**: Uses `localhost` URLs
- **Containerized testing**: Uses Docker service names (`ollama:11434`, `open-webui:8080`, etc.)

### Performance Baselines

Set performance baselines for regression detection:

```bash
# Create/update performance baseline
python test/test_performance.py --baseline

# Run regression tests
python test/test_performance.py --regression
```

### Test Results

Test results are saved to `test/` directory:
- `test_report.json` - Complete test results
- `performance_results.json` - Performance metrics
- `performance_baseline.json` - Performance baseline
- `security_results.json` - Security scan results
- `security_audit.json` - External security audit results

### CI/CD Integration

For automated testing in CI/CD pipelines:

```bash
# Run tests with CI mode (fail on any error)
python test/run_tests.py --ci

# Skip optional tests for faster CI
python test/run_tests.py --skip-performance --skip-security
```
   - Local: https://localhost
   - LAN: https://<your-lan-ip>
   - Accept the self-signed certificate warning

For LAN access from other devices:
- Ensure host firewall allows inbound on ports 80/443
- Use https://<host_LAN_IP> from other devices on the same network
- Accept the self-signed certificate warning

### Integration Tests
- **Automated testing**: Run `python setup.py test` for comprehensive integration tests
- **Containerized testing**: Use `docker-compose -f docker-compose.test.yml up` for isolated testing
- **Manual testing**: Run `python setup.py test --keep-running` to keep services running
- Logs are persisted per run with debug level information for analysis

## Stopping Services
To stop all services: `python setup.py compose down`
To restart: Run the setup script again