#!/usr/bin/env python3
"""
API Integration Tests for Ollama + Open-WebUI Setup
Tests all service endpoints and interactions for production reliability
"""

import time
import unittest
import requests
import subprocess
import os
import json
from pathlib import Path
import os
import sys
from unittest.mock import patch

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from setup import OllamaSetup


class TestAPIIntegration(unittest.TestCase):
    """Integration tests for API endpoints and service interactions"""

    def setUp(self):
        """Set up test environment"""
        self.setup = OllamaSetup()
        self.services_started = False

        # Service URLs (using Docker service names for containerized testing)
        self.ollama_url = os.getenv("OLLAMA_URL", "http://ollama:11434")
        self.webui_url = os.getenv("WEBUI_URL", "http://open-webui:8080")
        self.caddy_url = os.getenv("CADDY_URL", "http://caddy:80")

        # Test timeout settings
        self.timeout = 30
        self.health_check_interval = 5

    def tearDown(self):
        """Clean up test environment"""
        if self.services_started:
            try:
                self.setup.run_docker_compose(["down"])
            except:
                pass  # Ignore cleanup errors

    def wait_for_service(self, url, timeout=60, interval=5):
        """Wait for a service to become available"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(url, timeout=10, verify=False)
                if response.status_code < 500:  # Accept any non-server error
                    return True
            except (requests.exceptions.RequestException, ConnectionError):
                pass
            time.sleep(interval)
        return False

    def test_services_startup(self):
        """Test that all services start correctly"""
        # Skip this test when running in containerized environment
        # Services are already started by the test runner
        if os.path.exists("/.dockerenv") or os.environ.get("RUNNING_IN_CONTAINER"):
            self.skipTest("Services startup test skipped in containerized environment")

        # Start services
        result = self.setup.run_docker_compose(["up", "-d"])
        self.assertEqual(result, 0, "Failed to start services")
        self.services_started = True

        # Wait for services to be healthy
        time.sleep(30)  # Initial startup time

        # Test Ollama API availability
        self.assertTrue(
            self.wait_for_service(f"{self.ollama_url}/api/tags"),
            "Ollama API not available",
        )

        # Test Open-WebUI availability
        self.assertTrue(
            self.wait_for_service(f"{self.webui_url}/health"),
            "Open-WebUI not available",
        )

        # Test Caddy reverse proxy
        self.assertTrue(
            self.wait_for_service(self.caddy_url), "Caddy reverse proxy not available"
        )

    def test_ollama_api_endpoints(self):
        """Test Ollama API endpoints functionality"""
        if not self.services_started:
            self.skipTest("Services not started")

        # Test /api/tags endpoint
        response = requests.get(f"{self.ollama_url}/api/tags", timeout=self.timeout)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("models", data)

        # Test /api/version endpoint
        response = requests.get(f"{self.ollama_url}/api/version", timeout=self.timeout)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("version", data)

    def test_open_webui_endpoints(self):
        """Test Open-WebUI API endpoints"""
        if not self.services_started:
            self.skipTest("Services not started")

        # Test health endpoint
        response = requests.get(f"{self.webui_url}/health", timeout=self.timeout)
        self.assertEqual(response.status_code, 200)

        # Test config endpoint
        response = requests.get(f"{self.webui_url}/api/config", timeout=self.timeout)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, dict)

    def test_caddy_reverse_proxy(self):
        """Test Caddy reverse proxy functionality"""
        if not self.services_started:
            self.skipTest("Services not started")

        # Test HTTPS access (should proxy to Open-WebUI)
        response = requests.get(self.caddy_url, timeout=self.timeout, verify=False)
        self.assertEqual(response.status_code, 200)

        # Test that it's actually proxying to Open-WebUI
        webui_response = requests.get(f"{self.webui_url}/", timeout=self.timeout)
        caddy_response = requests.get(
            self.caddy_url, timeout=self.timeout, verify=False
        )

        # Should have similar content or at least same status
        self.assertEqual(webui_response.status_code, caddy_response.status_code)

    def test_service_interaction(self):
        """Test interaction between services"""
        if not self.services_started:
            self.skipTest("Services not started")

        # Test that Ollama is accessible from Open-WebUI container
        # This requires checking the Open-WebUI configuration
        response = requests.get(f"{self.webui_url}/api/config", timeout=self.timeout)
        config = response.json()

        # Open-WebUI should be configured to connect to Ollama
        # The exact configuration depends on the Open-WebUI version
        self.assertIsInstance(config, dict)

    def test_error_handling(self):
        """Test error handling for invalid requests"""
        if not self.services_started:
            self.skipTest("Services not started")

        # Test invalid Ollama API endpoint
        response = requests.get(f"{self.ollama_url}/api/invalid", timeout=self.timeout)
        self.assertEqual(response.status_code, 404)

        # Test invalid Open-WebUI endpoint
        response = requests.get(f"{self.webui_url}/invalid", timeout=self.timeout)
        self.assertEqual(response.status_code, 404)

    def test_service_health_checks(self):
        """Test that services pass their health checks"""
        if not self.services_started:
            self.skipTest("Services not started")

        # Check Docker health status
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=ollama-", "--format", "json"],
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0)
        containers = [
            json.loads(line) for line in result.stdout.strip().split("\n") if line
        ]

        # Should have ollama, open-webui, and caddy containers
        container_names = [c.get("Names", "") for c in containers]
        self.assertTrue(any("ollama-ollama" in name for name in container_names))
        self.assertTrue(any("ollama-open-webui" in name for name in container_names))
        self.assertTrue(any("ollama-caddy" in name for name in container_names))


class TestAPIRegression(unittest.TestCase):
    """Regression tests for API functionality"""

    def setUp(self):
        """Set up regression test environment"""
        self.setup = OllamaSetup()
        self.test_model = "llama2:7b"  # Use a small model for testing

    def test_ollama_model_operations(self):
        """Test Ollama model pull, list, and delete operations"""
        # This test requires Ollama to be running and may take time
        # Skip if not in full test environment
        if not os.getenv("RUN_FULL_API_TESTS"):
            self.skipTest("Full API tests disabled")

        # Test model listing
        response = requests.get("http://localhost:11434/api/tags", timeout=30)
        self.assertEqual(response.status_code, 200)

        # Test model pull (if model not present)
        # Note: This may take a long time and require internet access
        # pull_response = requests.post(
        #     "http://localhost:11434/api/pull",
        #     json={"name": self.test_model},
        #     timeout=300  # 5 minutes timeout
        # )
        # self.assertEqual(pull_response.status_code, 200)

        # Test model listing after pull
        response = requests.get("http://localhost:11434/api/tags", timeout=30)
        self.assertEqual(response.status_code, 200)
        models = response.json().get("models", [])
        model_names = [m["name"] for m in models]

        # Should have at least some models if pull succeeded
        if os.getenv("RUN_FULL_API_TESTS"):
            self.assertIn(self.test_model, model_names)

    def test_concurrent_requests(self):
        """Test handling of concurrent requests"""
        if not os.getenv("RUN_FULL_API_TESTS"):
            self.skipTest("Full API tests disabled")

        import threading
        import queue

        results = queue.Queue()
        errors = []

        def make_request(request_id):
            try:
                response = requests.get("http://localhost:11434/api/tags", timeout=10)
                results.put((request_id, response.status_code))
            except Exception as e:
                errors.append((request_id, str(e)))

        # Make 10 concurrent requests
        threads = []
        for i in range(10):
            t = threading.Thread(target=make_request, args=(i,))
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # Check results
        successful_requests = 0
        while not results.empty():
            request_id, status_code = results.get()
            if status_code == 200:
                successful_requests += 1

        # Should have at least some successful requests
        self.assertGreater(successful_requests, 5)
        self.assertEqual(len(errors), 0)


class TestSecurity(unittest.TestCase):
    """Security tests for the setup"""

    def setUp(self):
        """Set up security test environment"""
        self.setup = OllamaSetup()

    def test_ssl_configuration(self):
        """Test SSL/TLS configuration"""
        # Use caddy service within Docker network for containerized tests
        caddy_url = os.environ.get("CADDY_URL", "http://caddy").replace(
            "http://", "https://"
        )

        # Test HTTPS access
        try:
            response = requests.get(caddy_url, timeout=10, verify=False)
            self.assertEqual(response.status_code, 200)
        except requests.exceptions.RequestException:
            self.fail("HTTPS access failed")

    def test_security_headers(self):
        """Test security headers in responses"""
        # Use caddy service within Docker network for containerized tests
        caddy_url = os.environ.get("CADDY_URL", "http://caddy").replace(
            "http://", "https://"
        )
        response = requests.get(caddy_url, timeout=10, verify=False)

        # Check for security headers
        headers = response.headers

        # Should have security headers configured in Caddyfile
        self.assertIn("Strict-Transport-Security", headers)
        self.assertIn("X-Frame-Options", headers)
        self.assertIn("X-Content-Type-Options", headers)
        self.assertIn("Referrer-Policy", headers)

    def test_cors_configuration(self):
        """Test CORS configuration"""
        # Use caddy service within Docker network for containerized tests
        caddy_url = os.environ.get("CADDY_URL", "http://caddy").replace(
            "http://", "https://"
        )

        # Test preflight request
        response = requests.options(
            f"{caddy_url}/api/config",
            headers={
                "Origin": caddy_url,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Content-Type",
            },
            timeout=10,
            verify=False,
        )

        # Should handle CORS properly
        self.assertIn(
            response.status_code, [200, 404]
        )  # 404 is acceptable if endpoint doesn't exist


if __name__ == "__main__":
    # Run tests with environment variable to control full API testing
    if os.getenv("RUN_FULL_API_TESTS"):
        print("Running full API integration tests (may take time)...")
    else:
        print("Running basic API integration tests...")
        print("Set RUN_FULL_API_TESTS=1 to run full model tests")

    unittest.main(verbosity=2)
