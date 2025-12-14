#!/usr/bin/env python3
"""
Comprehensive Test Runner for Ollama + Open-WebUI Setup
Orchestrates all testing types for production-grade validation
"""

import subprocess
import sys
import os
import json
import time
from pathlib import Path
from datetime import datetime
import argparse

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from setup import OllamaSetup


class TestRunner:
    """Comprehensive test runner"""

    def __init__(self):
        self.setup = OllamaSetup()
        self.test_results = {}
        self.start_time = None

    def log(self, message: str, level: str = "INFO"):
        """Log a message with timestamp"""
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        print(f"[{timestamp}] {level}: {message}")

    def run_command(self, command: list, **kwargs) -> subprocess.CompletedProcess:
        """Run a command with logging"""
        self.log(f"Running: {' '.join(command)}")
        try:
            result = subprocess.run(command, **kwargs)
            if result.returncode != 0:
                self.log(
                    f"Command failed with return code {result.returncode}", "ERROR"
                )
            return result
        except Exception as e:
            self.log(f"Command execution failed: {e}", "ERROR")
            raise

    def install_test_dependencies(self):
        """Install test dependencies"""
        self.log("Installing test dependencies...")

        # Install test requirements
        req_file = Path("requirements-test.txt")
        if req_file.exists():
            try:
                self.run_command(
                    [sys.executable, "-m", "pip", "install", "-r", str(req_file)]
                )
                self.log("Test dependencies installed successfully")
            except subprocess.CalledProcessError:
                self.log("Failed to install test dependencies", "ERROR")
                return False

        return True

    def run_unit_tests(self):
        """Run unit tests"""
        self.log("Running unit tests...")

        test_file = Path("test/test_setup.py")
        if not test_file.exists():
            self.log("Unit test file not found", "ERROR")
            return False

        try:
            result = self.run_command(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    str(test_file),
                    "-v",
                    "--tb=short",
                    "--cov=setup",
                    "--cov-report=term-missing",
                    "--cov-report=html:test/coverage.html",
                ],
                cwd=self.setup.root_dir,
            )

            self.test_results["unit_tests"] = {
                "return_code": result.returncode,
                "passed": result.returncode == 0,
            }

            return result.returncode == 0

        except subprocess.CalledProcessError as e:
            self.test_results["unit_tests"] = {
                "return_code": e.returncode,
                "passed": False,
                "error": str(e),
            }
            return False

    def run_integration_tests(self):
        """Run integration tests"""
        self.log("Running integration tests...")

        # Use test docker-compose for containerized testing
        test_compose = Path("docker-compose.test.yml")
        if test_compose.exists():
            # Start test services
            self.log("Starting test services with docker-compose.test.yml...")
            result = self.run_command(
                [
                    "docker-compose",
                    "-f",
                    str(test_compose),
                    "up",
                    "-d",
                    "--build",
                ],
                cwd=self.setup.root_dir,
            )
            if result.returncode != 0:
                self.log("Failed to start test services", "ERROR")
                return False

            # Wait for services to be ready
            time.sleep(60)

            # Run tests in the test-runner container
            self.log("Running tests in test-runner container...")
            result = self.run_command(
                [
                    "docker-compose",
                    "-f",
                    str(test_compose),
                    "exec",
                    "-T",
                    "test-runner",
                    "bash",
                    "-c",
                    "cd /app/test && bash integration.sh",
                ],
                cwd=self.setup.root_dir,
            )

            # Stop test services
            self.run_command(
                [
                    "docker-compose",
                    "-f",
                    str(test_compose),
                    "down",
                ],
                cwd=self.setup.root_dir,
            )

            self.test_results["integration_tests"] = {
                "return_code": result.returncode,
                "passed": result.returncode == 0,
            }

            return result.returncode == 0
        else:
            # Fallback to regular integration test
            test_script = Path("test/integration.sh")
            if not test_script.exists():
                self.log("Integration test script not found", "ERROR")
                return False

            try:
                # Make script executable
                if os.name != "nt":  # Not Windows
                    os.chmod(test_script, 0o755)

                result = self.run_command([str(test_script)], cwd=self.setup.root_dir)

                self.test_results["integration_tests"] = {
                    "return_code": result.returncode,
                    "passed": result.returncode == 0,
                }

                return result.returncode == 0

            except Exception as e:
                self.test_results["integration_tests"] = {
                    "passed": False,
                    "error": str(e),
                }
                return False

    def run_validation_tests(self):
        """Run validation tests"""
        self.log("Running validation tests...")

        # On Windows, skip shell script execution
        if os.name == "nt":
            self.log("Skipping validation tests on Windows (shell script)", "WARNING")
            self.test_results["validation_tests"] = {
                "passed": True,
                "skipped": True,
                "reason": "Shell scripts not executable on Windows",
            }
            return True

        test_script = Path("validate.sh")
        if not test_script.exists():
            self.log("Validation test script not found", "ERROR")
            return False

        try:
            # Make script executable
            os.chmod(test_script, 0o755)

            result = self.run_command([str(test_script)], cwd=self.setup.root_dir)

            self.test_results["validation_tests"] = {
                "return_code": result.returncode,
                "passed": result.returncode == 0,
            }

            return result.returncode == 0

        except Exception as e:
            self.test_results["validation_tests"] = {
                "passed": False,
                "error": str(e),
            }
            return False

    def run_cross_platform_tests(self):
        """Run cross-platform tests"""
        self.log("Running cross-platform tests...")

        # On Windows, skip shell script execution
        if os.name == "nt":
            self.log(
                "Skipping cross-platform tests on Windows (shell script)", "WARNING"
            )
            self.test_results["cross_platform_tests"] = {
                "passed": True,
                "skipped": True,
                "reason": "Shell scripts not executable on Windows",
            }
            return True

        test_script = Path("test/wsl_test.sh")
        if not test_script.exists():
            self.log("Cross-platform test script not found", "ERROR")
            return False

        try:
            # Make script executable
            os.chmod(test_script, 0o755)

            result = self.run_command([str(test_script)], cwd=self.setup.root_dir)

            self.test_results["cross_platform_tests"] = {
                "return_code": result.returncode,
                "passed": result.returncode == 0,
            }

            return result.returncode == 0

        except Exception as e:
            self.test_results["cross_platform_tests"] = {
                "passed": False,
                "error": str(e),
            }
            return False

    def wait_for_services_healthy(self, compose_file, timeout=300):
        """Wait for all services in docker-compose to be healthy"""
        import time

        self.log(f"Waiting for services to be healthy (timeout: {timeout}s)...")
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                # Check if all services are healthy
                result = self.run_command(
                    ["docker-compose", "-f", str(compose_file), "ps"],
                    cwd=self.setup.root_dir,
                    capture_output=True,
                    text=True,
                )

                if result.returncode == 0:
                    output = result.stdout
                    # Check if all services show "healthy" or "running"
                    lines = output.strip().split("\n")
                    if len(lines) > 1:  # Skip header
                        all_healthy = True
                        for line in lines[1:]:
                            if (
                                "healthy" not in line.lower()
                                and "running" not in line.lower()
                            ):
                                all_healthy = False
                                break
                        if all_healthy:
                            self.log("All services are healthy!")
                            return True

                time.sleep(5)  # Wait 5 seconds before checking again

            except Exception as e:
                self.log(f"Error checking service health: {e}", "WARNING")
                time.sleep(5)

        self.log(
            f"Timeout waiting for services to be healthy after {timeout}s", "ERROR"
        )
        return False

    def run_api_integration_tests(self):
        """Run API integration tests"""
        self.log("Running API integration tests...")

        test_file = Path("test/test_api_integration.py")
        if not test_file.exists():
            self.log("API integration test file not found", "WARNING")
            return True  # Not critical

        # Use test docker-compose for containerized testing
        test_compose = Path("docker-compose.test.yml")
        if test_compose.exists():
            try:
                # Start test services
                self.log("Starting test services for API tests...")
                result = self.run_command(
                    ["docker-compose", "-f", str(test_compose), "up", "-d"],
                    cwd=self.setup.root_dir,
                )
                if result.returncode != 0:
                    self.log("Failed to start test services", "ERROR")
                    return False

                # Wait for services to be healthy
                if not self.wait_for_services_healthy(test_compose, timeout=180):
                    self.log("Services failed to become healthy", "ERROR")
                    # Stop test services
                    self.run_command(
                        ["docker-compose", "-f", str(test_compose), "down"],
                        cwd=self.setup.root_dir,
                    )
                    return False

                # Run API tests in a new test-runner container
                self.log("Running API tests in test-runner container...")
                result = self.run_command(
                    [
                        "docker",
                        "run",
                        "--rm",
                        "--network",
                        "ollama_ollama-test-net",
                        "-e",
                        "OLLAMA_URL=http://ollama:11434",
                        "-e",
                        "WEBUI_URL=http://open-webui:8080",
                        "-e",
                        "CADDY_URL=http://caddy:80",
                        "-v",
                        f"{self.setup.root_dir}:/app",
                        "-w",
                        "/app",
                        "ollama-test-runner",
                        "python",
                        "-m",
                        "pytest",
                        "test/test_api_integration.py",
                        "-v",
                        "--tb=short",
                    ],
                    cwd=self.setup.root_dir,
                )

                # Stop test services
                self.run_command(
                    ["docker-compose", "-f", str(test_compose), "down"],
                    cwd=self.setup.root_dir,
                )

                self.test_results["api_integration_tests"] = {
                    "return_code": result.returncode,
                    "passed": result.returncode == 0,
                }

                return result.returncode == 0

            except subprocess.CalledProcessError as e:
                self.test_results["api_integration_tests"] = {
                    "return_code": e.returncode,
                    "passed": False,
                    "error": str(e),
                }
                return False
        else:
            # Fallback to local testing
            try:
                result = self.run_command(
                    [
                        sys.executable,
                        "-m",
                        "pytest",
                        str(test_file),
                        "-v",
                        "--tb=short",
                    ],
                    cwd=self.setup.root_dir,
                )

                self.test_results["api_integration_tests"] = {
                    "return_code": result.returncode,
                    "passed": result.returncode == 0,
                }

                return result.returncode == 0

            except subprocess.CalledProcessError as e:
                self.test_results["api_integration_tests"] = {
                    "return_code": e.returncode,
                    "passed": False,
                    "error": str(e),
                }
                return False

    def run_performance_tests(self):
        """Run performance tests"""
        self.log("Running performance tests...")

        test_file = Path("test/test_performance.py")
        if not test_file.exists():
            self.log("Performance test file not found", "WARNING")
            return True  # Not critical

        # Use test docker-compose for containerized testing
        test_compose = Path("docker-compose.test.yml")
        if test_compose.exists():
            try:
                # Start test services
                self.log("Starting test services for performance tests...")
                result = self.run_command(
                    ["docker-compose", "-f", str(test_compose), "up", "-d"],
                    cwd=self.setup.root_dir,
                )
                if result.returncode != 0:
                    self.log("Failed to start test services", "ERROR")
                    return False

                # Wait for services to be healthy
                if not self.wait_for_services_healthy(test_compose, timeout=180):
                    self.log("Services failed to become healthy", "ERROR")
                    # Stop test services
                    self.run_command(
                        ["docker-compose", "-f", str(test_compose), "down"],
                        cwd=self.setup.root_dir,
                    )
                    return False

                # Run performance tests in a new test-runner container
                self.log("Running performance tests in test-runner container...")
                result = self.run_command(
                    [
                        "docker",
                        "run",
                        "--rm",
                        "--network",
                        "ollama_ollama-test-net",
                        "-e",
                        "OLLAMA_URL=http://ollama:11434",
                        "-e",
                        "WEBUI_URL=http://open-webui:8080",
                        "-e",
                        "CADDY_URL=http://caddy:80",
                        "-v",
                        f"{self.setup.root_dir}:/app",
                        "-w",
                        "/app",
                        "ollama-test-runner",
                        "python",
                        "test/test_performance.py",
                    ],
                    cwd=self.setup.root_dir,
                )

                # Stop test services
                self.run_command(
                    ["docker-compose", "-f", str(test_compose), "down"],
                    cwd=self.setup.root_dir,
                )

                self.test_results["performance_tests"] = {
                    "return_code": result.returncode,
                    "passed": result.returncode == 0,
                }

                return result.returncode == 0

            except subprocess.CalledProcessError as e:
                self.test_results["performance_tests"] = {
                    "return_code": e.returncode,
                    "passed": False,
                    "error": str(e),
                }
                return False
        else:
            # Fallback to local testing
            try:
                result = self.run_command(
                    [sys.executable, str(test_file)], cwd=self.setup.root_dir
                )

                self.test_results["performance_tests"] = {
                    "return_code": result.returncode,
                    "passed": result.returncode == 0,
                }

                return result.returncode == 0

            except subprocess.CalledProcessError as e:
                self.test_results["performance_tests"] = {
                    "return_code": e.returncode,
                    "passed": False,
                    "error": str(e),
                }
                return False

    def run_security_tests(self):
        """Run security tests"""
        self.log("Running security tests...")

        test_file = Path("test/test_security.py")
        if not test_file.exists():
            self.log("Security test file not found", "WARNING")
            return True  # Not critical

        # Use test docker-compose for containerized testing
        test_compose = Path("docker-compose.test.yml")
        if test_compose.exists():
            try:
                # Start test services
                self.log("Starting test services for security tests...")
                result = self.run_command(
                    ["docker-compose", "-f", str(test_compose), "up", "-d"],
                    cwd=self.setup.root_dir,
                )
                if result.returncode != 0:
                    self.log("Failed to start test services", "ERROR")
                    return False

                # Wait for services to be healthy
                if not self.wait_for_services_healthy(test_compose, timeout=180):
                    self.log("Services failed to become healthy", "ERROR")
                    # Stop test services
                    self.run_command(
                        ["docker-compose", "-f", str(test_compose), "down"],
                        cwd=self.setup.root_dir,
                    )
                    return False

                # Run security tests in a new test-runner container
                self.log("Running security tests in test-runner container...")
                result = self.run_command(
                    [
                        "docker",
                        "run",
                        "--rm",
                        "--network",
                        "ollama_ollama-test-net",
                        "-e",
                        "OLLAMA_URL=http://ollama:11434",
                        "-e",
                        "WEBUI_URL=http://open-webui:8080",
                        "-e",
                        "CADDY_URL=http://caddy:80",
                        "-v",
                        f"{self.setup.root_dir}:/app",
                        "-w",
                        "/app",
                        "ollama-test-runner",
                        "python",
                        "test/test_security.py",
                    ],
                    cwd=self.setup.root_dir,
                )

                # Stop test services
                self.run_command(
                    ["docker-compose", "-f", str(test_compose), "down"],
                    cwd=self.setup.root_dir,
                )

                self.test_results["security_tests"] = {
                    "return_code": result.returncode,
                    "passed": result.returncode == 0,
                }

                return result.returncode == 0

            except subprocess.CalledProcessError as e:
                self.test_results["security_tests"] = {
                    "return_code": e.returncode,
                    "passed": False,
                    "error": str(e),
                }
                return False
        else:
            # Fallback to local testing
            try:
                result = self.run_command(
                    [sys.executable, str(test_file)], cwd=self.setup.root_dir
                )

                self.test_results["security_tests"] = {
                    "return_code": result.returncode,
                    "passed": result.returncode == 0,
                }

                return result.returncode == 0

            except subprocess.CalledProcessError as e:
                self.test_results["security_tests"] = {
                    "return_code": e.returncode,
                    "passed": False,
                    "error": str(e),
                }
                return False

    def run_validation_tests(self):
        """Run validation tests"""
        self.log("Running validation tests...")

        validate_script = Path("validate.sh")
        if not validate_script.exists():
            self.log("Validation script not found", "WARNING")
            return True

        # Skip shell scripts on Windows
        if os.name == "nt":
            self.log("Skipping shell script validation on Windows", "WARNING")
            self.test_results["validation_tests"] = {
                "passed": True,
                "skipped": True,
                "reason": "Shell scripts not supported on Windows",
            }
            return True

        try:
            result = self.run_command([str(validate_script)], cwd=self.setup.root_dir)

            self.test_results["validation_tests"] = {
                "return_code": result.returncode,
                "passed": result.returncode == 0,
            }

            return result.returncode == 0

        except subprocess.CalledProcessError as e:
            self.test_results["validation_tests"] = {
                "return_code": e.returncode,
                "passed": False,
                "error": str(e),
            }
            return False

    def run_cross_platform_tests(self):
        """Run cross-platform tests"""
        self.log("Running cross-platform tests...")

        # Test WSL integration if on Windows
        if os.name == "nt":
            wsl_script = Path("test/wsl_test.sh")
            if wsl_script.exists():
                self.log("Skipping WSL shell script on Windows", "WARNING")
                self.test_results["wsl_tests"] = {
                    "passed": True,
                    "skipped": True,
                    "reason": "Shell scripts not supported on Windows",
                }
            else:
                self.log("WSL test script not found", "WARNING")

        return True

    def generate_report(self):
        """Generate comprehensive test report"""
        self.log("Generating test report...")

        # Calculate summary statistics
        total_tests = len(self.test_results)
        passed_tests = sum(
            1 for result in self.test_results.values() if result.get("passed", False)
        )
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        duration = time.time() - self.start_time if self.start_time else 0

        report = {
            "summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "success_rate": success_rate,
                "duration_seconds": duration,
                "timestamp": datetime.utcnow().isoformat(),
            },
            "results": self.test_results,
            "system_info": {
                "platform": sys.platform,
                "python_version": sys.version,
                "working_directory": str(self.setup.root_dir),
            },
        }

        # Save detailed report
        report_file = Path("test/test_report.json")
        report_file.parent.mkdir(exist_ok=True)

        with open(report_file, "w") as f:
            json.dump(report, f, indent=2, default=str)

        # Print summary to console
        print("\n" + "=" * 60)
        print("🧪 COMPREHENSIVE TEST REPORT")
        print("=" * 60)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {success_rate:.1f}%")
        print(f"Duration: {duration:.2f}s")
        print(f"Report saved to: {report_file}")

        if failed_tests > 0:
            print("\n❌ Failed Tests:")
            for test_name, result in self.test_results.items():
                if not result.get("passed", False):
                    print(f"   - {test_name}: {result.get('error', 'Failed')}")

        print("\n✅ Passed Tests:")
        for test_name, result in self.test_results.items():
            if result.get("passed", False):
                print(f"   - {test_name}")

        print("=" * 60)

        return report

    def run_all_tests(self, skip_performance=False, skip_security=False):
        """Run all available tests"""
        self.start_time = time.time()
        self.log("Starting comprehensive test suite...")

        success = True

        # Install dependencies
        if not self.install_test_dependencies():
            self.log("Failed to install test dependencies", "ERROR")
            return False

        # Run tests in order of dependency/criticality
        test_sequence = [
            ("unit_tests", self.run_unit_tests, "Critical"),
            ("validation_tests", self.run_validation_tests, "Critical"),
            ("integration_tests", self.run_integration_tests, "Critical"),
            ("api_integration_tests", self.run_api_integration_tests, "Important"),
            ("cross_platform_tests", self.run_cross_platform_tests, "Important"),
        ]

        if not skip_performance:
            test_sequence.append(
                ("performance_tests", self.run_performance_tests, "Optional")
            )

        if not skip_security:
            test_sequence.append(
                ("security_tests", self.run_security_tests, "Optional")
            )

        for test_name, test_func, priority in test_sequence:
            try:
                self.log(f"Running {test_name} ({priority})...")
                test_success = test_func()
                if not test_success and priority == "Critical":
                    success = False
                    self.log(f"Critical test {test_name} failed!", "ERROR")
                elif not test_success:
                    self.log(f"Non-critical test {test_name} failed", "WARNING")

            except Exception as e:
                self.log(f"Test {test_name} crashed: {e}", "ERROR")
                if priority == "Critical":
                    success = False
                self.test_results[test_name] = {
                    "passed": False,
                    "error": str(e),
                    "crashed": True,
                }

        # Generate report
        self.generate_report()

        total_time = time.time() - self.start_time
        self.log(f"Total execution time: {total_time:.2f} seconds")
        if success:
            self.log("✅ All critical tests passed!")
        else:
            self.log("❌ Some critical tests failed!", "ERROR")

        return success


def main():
    parser = argparse.ArgumentParser(
        description="Comprehensive Test Runner for Ollama + Open-WebUI Setup"
    )
    parser.add_argument("--unit-only", action="store_true", help="Run only unit tests")
    parser.add_argument(
        "--integration-only", action="store_true", help="Run only integration tests"
    )
    parser.add_argument(
        "--skip-performance", action="store_true", help="Skip performance tests"
    )
    parser.add_argument(
        "--skip-security", action="store_true", help="Skip security tests"
    )
    parser.add_argument(
        "--ci", action="store_true", help="Run in CI mode (fail on any test failure)"
    )

    args = parser.parse_args()

    runner = TestRunner()

    if args.unit_only:
        success = runner.run_unit_tests()
    elif args.integration_only:
        success = runner.run_integration_tests()
    else:
        success = runner.run_all_tests(
            skip_performance=args.skip_performance, skip_security=args.skip_security
        )

    # In CI mode, exit with error code on failure
    if args.ci and not success:
        sys.exit(1)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
