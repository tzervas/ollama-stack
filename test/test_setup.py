#!/usr/bin/env python3
"""
Unit tests for Ollama setup script
Comprehensive test coverage for production reliability
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open, MagicMock
import subprocess
import platform

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from setup import OllamaSetup


class TestOllamaSetup(unittest.TestCase):
    """Test cases for OllamaSetup class"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.root_dir = Path(self.temp_dir)

        # Create mock files
        (self.root_dir / ".env.example").write_text(
            "DOMAIN=localhost\nEMAIL=user@localhost\n"
        )
        (self.root_dir / "Caddyfile").write_text(
            "# Test Caddyfile\nlocalhost {\n    reverse_proxy localhost:8080\n}"
        )

        with patch("setup.Path") as mock_path:
            mock_path.return_value.parent.absolute.return_value = self.root_dir
            self.setup = OllamaSetup()

    def tearDown(self):
        """Clean up test fixtures"""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("platform.system")
    @patch("platform.machine")
    def test_detect_platform_linux_amd64(self, mock_machine, mock_system):
        """Test platform detection for Linux x86_64"""
        mock_system.return_value = "Linux"
        mock_machine.return_value = "x86_64"

        result = self.setup.detect_platform()
        self.assertEqual(result, "linux/amd64")

    @patch("platform.system")
    @patch("platform.machine")
    def test_detect_platform_linux_arm64(self, mock_machine, mock_system):
        """Test platform detection for Linux ARM64"""
        mock_system.return_value = "Linux"
        mock_machine.return_value = "aarch64"

        result = self.setup.detect_platform()
        self.assertEqual(result, "linux/arm64")

    @patch("platform.system")
    @patch("platform.machine")
    def test_detect_platform_windows_amd64(self, mock_machine, mock_system):
        """Test platform detection for Windows (should return linux/amd64 for containers)"""
        mock_system.return_value = "Windows"
        mock_machine.return_value = "AMD64"

        result = self.setup.detect_platform()
        self.assertEqual(result, "linux/amd64")

    def test_load_env_with_example(self):
        """Test loading environment variables from .env.example"""
        env_vars = self.setup.load_env()

        self.assertIn("DOMAIN", env_vars)
        self.assertIn("EMAIL", env_vars)
        self.assertEqual(env_vars["DOMAIN"], "localhost")
        self.assertEqual(env_vars["EMAIL"], "user@localhost")

    def test_load_env_with_override(self):
        """Test loading environment variables with .env override"""
        (self.root_dir / ".env").write_text(
            "DOMAIN=custom.domain\nEMAIL=new@email.com\n"
        )

        env_vars = self.setup.load_env()

        self.assertEqual(env_vars["DOMAIN"], "custom.domain")
        self.assertEqual(env_vars["EMAIL"], "new@email.com")

    def test_save_env(self):
        """Test saving environment variables to .env file"""
        env_vars = {"DOMAIN": "test.com", "EMAIL": "test@test.com"}

        self.setup.save_env(env_vars)

        env_file = self.root_dir / ".env"
        self.assertTrue(env_file.exists())

        content = env_file.read_text()
        self.assertIn("# Environment configuration for Ollama + Open-WebUI", content)
        self.assertIn("DOMAIN=test.com", content)
        self.assertIn("EMAIL=test@test.com", content)

    @patch("subprocess.run")
    def test_run_command_success(self, mock_run):
        """Test successful command execution"""
        mock_run.return_value = Mock(returncode=0, stdout="success", stderr="")

        result = self.setup.run_command(["echo", "test"])

        self.assertEqual(result.returncode, 0)
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_run_command_failure(self, mock_run):
        """Test failed command execution"""
        mock_run.side_effect = subprocess.CalledProcessError(
            1, ["failing", "command"], "", "error"
        )

        with self.assertRaises(subprocess.CalledProcessError):
            self.setup.run_command(["failing", "command"])

    @patch("setup.OllamaSetup.run_command")
    def test_install_package_with_uv(self, mock_run_command):
        """Test package installation with uv"""
        mock_run_command.return_value = Mock(returncode=0)

        result = self.setup.install_package("test-package")

        self.assertTrue(result)
        mock_run_command.assert_called_with(
            ["uv", "pip", "install", "test-package"], **{}
        )

    @patch("setup.OllamaSetup.run_command")
    @patch("sys.executable", "/usr/bin/python")
    def test_install_package_fallback_pip(self, mock_run_command):
        """Test package installation fallback to pip"""
        # First call (uv) fails, second call (pip) succeeds
        mock_run_command.side_effect = [
            subprocess.CalledProcessError(1, ["uv"], stderr="not found"),
            Mock(returncode=0),
        ]

        result = self.setup.install_package("test-package")

        self.assertTrue(result)
        self.assertEqual(mock_run_command.call_count, 2)

    @patch("socket.gethostbyname")
    def test_check_dns_success(self, mock_gethostbyname):
        """Test successful DNS resolution"""
        mock_gethostbyname.return_value = "127.0.0.1"

        result = self.setup.check_dns("example.com")

        self.assertTrue(result)
        mock_gethostbyname.assert_called_with("example.com")

    @patch("socket.gethostbyname")
    def test_check_dns_failure(self, mock_gethostbyname):
        """Test failed DNS resolution"""
        from socket import gaierror

        mock_gethostbyname.side_effect = gaierror("Name resolution failure")

        result = self.setup.check_dns("nonexistent.domain")

        self.assertFalse(result)

    @patch("setup.OllamaSetup.run_command")
    def test_check_caddy_config_success(self, mock_run_command):
        """Test successful Caddy configuration validation"""
        mock_run_command.return_value = Mock(returncode=0)

        result = self.setup.check_caddy_config()

        self.assertTrue(result)
        mock_run_command.assert_called_once()

    @patch("setup.OllamaSetup.run_command")
    def test_check_caddy_config_failure(self, mock_run_command):
        """Test failed Caddy configuration validation"""
        mock_run_command.side_effect = subprocess.CalledProcessError(
            1, ["caddy", "validate"], stderr="config error"
        )

        result = self.setup.check_caddy_config()

        self.assertFalse(result)

    def test_check_caddy_config_no_file(self):
        """Test Caddy config check when file doesn't exist"""
        # Remove the Caddyfile
        (self.root_dir / "Caddyfile").unlink()

        result = self.setup.check_caddy_config()

        self.assertFalse(result)

    @patch("setup.OllamaSetup.run_command")
    def test_check_certificates_exists(self, mock_run_command):
        """Test certificate check when volume exists"""
        mock_run_command.return_value = Mock(stdout="caddy_data\n", returncode=0)

        result = self.setup.check_certificates()

        self.assertTrue(result)

    @patch("setup.OllamaSetup.run_command")
    def test_check_certificates_not_exists(self, mock_run_command):
        """Test certificate check when volume doesn't exist"""
        mock_run_command.return_value = Mock(stdout="", returncode=0)

        result = self.setup.check_certificates()

        self.assertFalse(result)

    @patch("setup.OllamaSetup.run_command")
    @patch.dict(os.environ, {"DOCKER_PLATFORM": "linux/arm64"})
    def test_run_docker_compose_with_platform(self, mock_run_command):
        """Test docker-compose execution with platform detection"""
        mock_run_command.return_value = Mock(returncode=0)

        result = self.setup.run_docker_compose(["up", "-d"])

        self.assertEqual(result, 0)
        # Check that environment was set correctly
        call_args = mock_run_command.call_args
        self.assertIn("DOCKER_PLATFORM", call_args[1]["env"])

    @patch("setup.OllamaSetup.run_command")
    def test_run_docker_compose_not_found(self, mock_run_command):
        """Test docker-compose when command not found"""
        mock_run_command.side_effect = FileNotFoundError()

        result = self.setup.run_docker_compose(["up", "-d"])

        self.assertEqual(result, 1)


class TestOllamaSetupIntegration(unittest.TestCase):
    """Integration tests for OllamaSetup class"""

    def setUp(self):
        """Set up integration test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.root_dir = Path(self.temp_dir)

        # Create a complete test environment
        (self.root_dir / ".env.example").write_text(
            """
DOMAIN=localhost
EMAIL=user@localhost
OLLAMA_IMAGE=ollama/ollama:latest
DOCKER_PLATFORM=linux/amd64
""".strip()
        )

        (self.root_dir / "Caddyfile").write_text(
            """
{$DOMAIN:localhost} {
    reverse_proxy open-webui:8080
}
""".strip()
        )

        with patch("setup.Path") as mock_path:
            mock_path.return_value.parent.absolute.return_value = self.root_dir
            self.setup = OllamaSetup()

    def tearDown(self):
        """Clean up integration test fixtures"""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_full_env_loading_workflow(self):
        """Test complete environment loading workflow"""
        # Create .env with overrides
        (self.root_dir / ".env").write_text(
            "DOMAIN=custom.domain\nOLLAMA_IMAGE=ollama/ollama:custom\n"
        )

        env_vars = self.setup.load_env()

        # Check defaults from .env.example
        self.assertEqual(env_vars["EMAIL"], "user@localhost")
        self.assertEqual(env_vars["DOCKER_PLATFORM"], "linux/amd64")

        # Check overrides from .env
        self.assertEqual(env_vars["DOMAIN"], "custom.domain")
        self.assertEqual(env_vars["OLLAMA_IMAGE"], "ollama/ollama:custom")

    @patch("builtins.input")
    def test_setup_interactive_workflow(self, mock_input):
        """Test interactive setup workflow"""
        mock_input.side_effect = ["test.domain", "test@email.com", "linux/arm64", ""]

        with patch("setup.OllamaSetup.check_dns") as mock_dns:
            mock_dns.return_value = True

            self.setup.setup_interactive()

        # Check that .env was created with correct values
        env_file = self.root_dir / ".env"
        self.assertTrue(env_file.exists())

        content = env_file.read_text()
        self.assertIn("DOMAIN=test.domain", content)
        self.assertIn("EMAIL=test@email.com", content)
        self.assertIn("DOCKER_PLATFORM=linux/arm64", content)


if __name__ == "__main__":
    # Add verbose output and coverage reporting
    unittest.main(verbosity=2)
