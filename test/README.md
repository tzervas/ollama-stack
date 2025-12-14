# Testing Framework for Ollama + Open-WebUI Setup

This comprehensive testing framework ensures production-grade reliability and robustness for the Ollama + Open-WebUI deployment.

## Test Categories

### 1. Unit Tests (`test/test_setup.py`)
- **Coverage**: Core setup logic, platform detection, environment management
- **Framework**: pytest with coverage reporting
- **Requirements**: 80% code coverage minimum

### 2. Integration Tests (`test/integration.sh`)
- **Coverage**: Full stack deployment and service interaction
- **Scope**: Docker Compose orchestration, service health checks, API validation

### 3. API Integration Tests (`test/test_api_integration.py`)
- **Coverage**: REST API endpoints, service communication
- **Features**: Concurrent request testing, error handling validation

### 4. Performance Tests (`test/test_performance.py`)
- **Coverage**: Response times, throughput, resource utilization
- **Features**: Load testing, regression detection, baseline comparison

### 5. Security Tests (`test/test_security.py`)
- **Coverage**: SSL/TLS, security headers, container security, API vulnerabilities
- **Tools**: Automated security scanning with bandit, safety, and custom checks

### 6. Cross-Platform Validation (`validate.sh`, `test/wsl_test.sh`)
- **Coverage**: Multi-platform compatibility (Windows, Linux, macOS, WSL)
- **Tools**: Shell script validation, PowerShell analysis

## Quick Start

### Install Test Dependencies
```bash
# Using uv (recommended)
uv pip install -r requirements-test.txt

# Or using pip
pip install -r requirements-test.txt
```

### Run All Tests
```bash
# Comprehensive test suite
python test/run_tests.py

# Quick unit tests only
python test/run_tests.py --unit-only

# Integration tests only
python test/run_tests.py --integration-only

# Skip optional tests
python test/run_tests.py --skip-performance --skip-security
```

### Run Individual Test Suites

#### Unit Tests
```bash
python -m pytest test/test_setup.py -v --cov=setup
```

#### Integration Tests
```bash
./test/integration.sh
```

#### API Tests
```bash
export RUN_FULL_API_TESTS=1  # Enable full model testing
python -m pytest test/test_api_integration.py -v
```

#### Performance Tests
```bash
# Run performance tests
python test/test_performance.py

# Create/update performance baseline
python test/test_performance.py --baseline

# Run regression tests against baseline
python test/test_performance.py --regression
```

#### Security Tests
```bash
# Run security validation
python test/test_security.py

# Run security audit with external tools
python test/test_security.py --audit
```

## CI/CD Integration

The testing framework integrates with GitHub Actions for automated testing:

- **Unit Tests**: Run on multiple Python versions (3.8-3.12)
- **Integration Tests**: Full Docker-based testing
- **Security Tests**: Automated vulnerability scanning
- **Performance Tests**: Regression detection with baseline comparison
- **Cross-Platform**: Validation on Windows, Linux, and macOS
- **Nightly Regression**: Weekly comprehensive testing

### CI Configuration
See `.github/workflows/comprehensive-testing.yml` for the complete CI pipeline.

## Test Results and Reports

### Generated Files
- `test/test_report.json` - Comprehensive test results
- `test/coverage.html` - Code coverage report
- `test/performance_results.json` - Performance metrics
- `test/performance_baseline.json` - Performance baseline
- `test/security_results.json` - Security test results
- `test/security_audit.json` - Security audit results
- `test/logs_*.txt` - Test execution logs

### Test Report Summary
The test runner generates a detailed JSON report with:
- Test pass/fail status
- Execution duration
- Success rates
- System information
- Recommendations for failures

## Test Environment Setup

### Docker Requirements
- Docker Engine for containerized testing
- Docker Compose for service orchestration
- Sufficient resources for running multiple containers

### System Requirements
- Python 3.8+ for test execution
- uv package manager (recommended) or pip
- Git for version control
- Internet access for dependency installation

### Environment Variables
- `RUN_FULL_API_TESTS=1` - Enable comprehensive API testing (downloads models)
- `DOCKER_PLATFORM` - Override Docker platform detection
- `OLLAMA_IMAGE` - Specify Ollama Docker image

## Test Development Guidelines

### Adding New Tests

#### Unit Tests
```python
import unittest
from setup import OllamaSetup

class TestNewFeature(unittest.TestCase):
    def setUp(self):
        self.setup = OllamaSetup()

    def test_new_functionality(self):
        # Test implementation
        result = self.setup.new_method()
        self.assertEqual(result, expected_value)
```

#### Integration Tests
Add to `test/integration.sh` or create new shell scripts in `test/` directory.

#### API Tests
Extend `test/test_api_integration.py` with new endpoint validations.

### Test Naming Conventions
- Files: `test_*.py` for Python tests
- Classes: `Test*` for test classes
- Methods: `test_*` for test methods
- Integration scripts: Descriptive names in `test/` directory

### Coverage Requirements
- Minimum 80% code coverage for unit tests
- Critical paths must have 100% coverage
- Coverage reports generated automatically

## Troubleshooting

### Common Issues

#### Docker Permission Denied
```bash
# Add user to docker group
sudo usermod -aG docker $USER
# Restart session
```

#### Port Conflicts
```bash
# Check port usage
netstat -tlnp | grep :11434
# Stop conflicting services
sudo systemctl stop ollama  # If system Ollama is running
```

#### Performance Test Failures
- Ensure sufficient system resources (CPU, RAM, Disk)
- Run tests on dedicated hardware for accurate baselines
- Check Docker resource limits in docker-compose.yml

#### Security Test Warnings
- Some warnings are expected for development setups
- Review security recommendations in reports
- Adjust Caddyfile and docker-compose.yml as needed

### Debug Mode
```bash
# Enable debug logging
export PYTHONPATH=.
python -c "import logging; logging.basicConfig(level=logging.DEBUG)"

# Run tests with verbose output
python test/run_tests.py --ci
```

## Contributing

### Test Coverage
- All new code must include corresponding tests
- Maintain or improve overall test coverage
- Add performance tests for performance-critical code

### Code Quality
- Follow PEP 8 style guidelines
- Add docstrings to all test methods
- Use descriptive test names and assertions

### CI Requirements
- All tests must pass in CI environment
- No performance regressions without approval
- Security tests must pass or have documented exceptions

## Production Deployment Validation

Before deploying to production:

1. **Run Full Test Suite**
   ```bash
   python test/run_tests.py --ci
   ```

2. **Validate Performance**
   ```bash
   python test/test_performance.py --regression
   ```

3. **Security Audit**
   ```bash
   python test/test_security.py --audit
   ```

4. **Cross-Platform Validation**
   - Test on target deployment platform
   - Validate with production-like resource constraints

5. **Integration Testing**
   - Test with production network configuration
   - Validate backup and recovery procedures

## Support

For issues with the testing framework:
1. Check test logs in `test/` directory
2. Review CI pipeline results
3. Validate environment setup
4. Check Docker and system resource availability

## License

This testing framework is part of the Ollama + Open-WebUI setup project.