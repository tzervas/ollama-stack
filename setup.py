#!/usr/bin/env python3
"""
Ollama + Open-WebUI Setup and Management Script
Cross-platform Python script for setup, configuration, and management
"""

import os
import sys
import platform
import subprocess
import argparse
import json
from pathlib import Path
from typing import Dict, Optional, Tuple


class OllamaSetup:
    def __init__(self):
        self.root_dir = Path(__file__).parent.absolute()
        self.env_file = self.root_dir / ".env"
        self.env_example = self.root_dir / ".env.example"

    def run_command(self, cmd: list, **kwargs) -> subprocess.CompletedProcess:
        """Run a command with proper error handling"""
        try:
            return subprocess.run(
                cmd, check=True, capture_output=True, text=True, **kwargs
            )
        except subprocess.CalledProcessError as e:
            print(f"❌ Command failed: {' '.join(cmd)}")
            print(f"Error: {e.stderr}")
            raise

    def install_package(self, package: str, **kwargs) -> bool:
        """Install a Python package using uv (localhost) or pip (container)"""
        if self.is_running_in_container():
            # In containers, use pip directly
            try:
                self.run_command(
                    [sys.executable, "-m", "pip", "install", package], **kwargs
                )
                print(f"✅ Installed {package} with pip (container)")
                return True
            except subprocess.CalledProcessError:
                print(f"❌ Failed to install {package}")
                return False
        else:
            # On localhost, try uv first, then pip
            try:
                self.run_command(["uv", "pip", "install", package], **kwargs)
                print(f"✅ Installed {package} with uv")
                return True
            except (subprocess.CalledProcessError, FileNotFoundError):
                try:
                    # Fallback to pip
                    self.run_command(
                        [sys.executable, "-m", "pip", "install", package], **kwargs
                    )
                    print(f"✅ Installed {package} with pip")
                    return True
                except subprocess.CalledProcessError:
                    print(f"❌ Failed to install {package}")
                    return False

    def install_requirements(self, requirements_file: str, **kwargs) -> bool:
        """Install Python packages from requirements file using uv (localhost) or pip (container)"""
        req_path = self.root_dir / requirements_file
        if not req_path.exists():
            print(f"❌ Requirements file not found: {requirements_file}")
            return False

        if self.is_running_in_container():
            # In containers, use pip directly
            try:
                self.run_command(
                    [sys.executable, "-m", "pip", "install", "-r", str(req_path)],
                    **kwargs,
                )
                print(
                    f"✅ Installed requirements from {requirements_file} with pip (container)"
                )
                return True
            except subprocess.CalledProcessError:
                print(f"❌ Failed to install requirements from {requirements_file}")
                return False
        else:
            # On localhost, try uv first, then pip
            try:
                self.run_command(
                    ["uv", "pip", "install", "-r", str(req_path)], **kwargs
                )
                print(f"✅ Installed requirements from {requirements_file} with uv")
                return True
            except (subprocess.CalledProcessError, FileNotFoundError):
                try:
                    # Fallback to pip
                    self.run_command(
                        [sys.executable, "-m", "pip", "install", "-r", str(req_path)],
                        **kwargs,
                    )
                    print(
                        f"✅ Installed requirements from {requirements_file} with pip"
                    )
                    return True
                except subprocess.CalledProcessError:
                    print(f"❌ Failed to install requirements from {requirements_file}")
                    return False

    def detect_platform(self) -> str:
        """Detect Docker platform based on system architecture and OS"""
        system = platform.system().lower()
        machine = platform.machine().lower()

        # Architecture mapping
        arch_map = {
            "x86_64": "amd64",
            "amd64": "amd64",
            "aarch64": "arm64",
            "arm64": "arm64",
            "armv7l": "arm/v7",
            "armv7": "arm/v7",
        }

        arch = arch_map.get(machine, "amd64")

        # For Docker, we always use 'linux' as the OS since containers run on Linux
        # regardless of the host OS (Windows, macOS, Linux)
        if arch == "arm64":
            return f"linux/arm64"
        else:
            return f"linux/amd64"

    def load_env(self) -> Dict[str, str]:
        """Load environment variables from .env file"""
        env_vars = {}

        # Load from .env.example first (defaults)
        if self.env_example.exists():
            with open(self.env_example, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        env_vars[key] = value

        # Override with .env if it exists
        if self.env_file.exists():
            with open(self.env_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        env_vars[key] = value

        return env_vars

    def save_env(self, env_vars: Dict[str, str]):
        """Save environment variables to .env file"""
        with open(self.env_file, "w") as f:
            f.write("# Environment configuration for Ollama + Open-WebUI\n")
            f.write("# Generated by setup script\n\n")

            for key, value in env_vars.items():
                f.write(f"{key}={value}\n")

    def run_docker_compose(self, args: list) -> int:
        """Run docker-compose with detected platform"""
        platform = self.detect_platform()
        env = os.environ.copy()
        env["DOCKER_PLATFORM"] = platform

        print(f"🐳 Detected Docker platform: {platform}")

        try:
            return self.run_command(
                ["docker-compose"] + args, env=env, cwd=self.root_dir
            ).returncode
        except subprocess.CalledProcessError:
            return 1
        except FileNotFoundError:
            print(
                "❌ docker-compose not found. Please install Docker and Docker Compose."
            )
            return 1

    def check_dns(self, domain: str) -> bool:
        """Check DNS resolution for domain"""
        try:
            import socket

            socket.gethostbyname(domain)
            print(f"✅ DNS resolution successful for {domain}")
            return True
        except socket.gaierror:
            print(f"❌ DNS resolution failed for {domain}")
            return False

    def check_caddy_config(self) -> bool:
        """Validate Caddy configuration"""
        caddyfile = self.root_dir / "Caddyfile"
        if not caddyfile.exists():
            print("❌ Caddyfile not found")
            return False

        try:
            cmd = [
                "docker",
                "run",
                "--rm",
                "-v",
                f"{caddyfile}:/etc/caddy/Caddyfile",
                "caddy:2",
                "caddy",
                "validate",
            ]
            self.run_command(cmd, cwd=self.root_dir)
            print("✅ Caddy configuration is valid")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Caddy configuration error: {e.stderr}")
            return False
        except FileNotFoundError:
            print("⚠️  Docker not available for Caddy validation")
            return True  # Assume valid if Docker not available

    def check_certificates(self) -> bool:
        """Check existing SSL certificates"""
        try:
            result = self.run_command(["docker", "volume", "ls"])
            if "caddy_data" in result.stdout:
                print("✅ Caddy data volume exists (certificates may be stored)")
                return True
            else:
                print("ℹ️  Caddy data volume not found (will be created on first run)")
                return False
        except subprocess.CalledProcessError:
            print("⚠️  Docker not available for certificate check")
            return False
        except FileNotFoundError:
            print("⚠️  Docker not available for certificate check")
            return False

    def setup_interactive(self):
        """Interactive setup wizard"""
        print("🚀 Ollama + Open-WebUI Setup Wizard")
        print("=" * 40)

        env_vars = self.load_env()

        # Domain setup
        current_domain = env_vars.get("DOMAIN", "localhost")
        domain = input(f"Domain [{current_domain}]: ").strip() or current_domain
        env_vars["DOMAIN"] = domain

        # Email setup
        current_email = env_vars.get("EMAIL", "user@localhost")
        email = (
            input(f"Email for SSL certificates [{current_email}]: ").strip()
            or current_email
        )
        env_vars["EMAIL"] = email

        # Platform detection
        detected_platform = self.detect_platform()
        current_platform = env_vars.get("DOCKER_PLATFORM", detected_platform)
        platform_input = input(
            f"Docker platform (auto-detected: {detected_platform}) [{current_platform}]: "
        ).strip()
        env_vars["DOCKER_PLATFORM"] = platform_input or detected_platform

        # Save configuration
        self.save_env(env_vars)
        print("✅ Configuration saved to .env")

        # DNS check if domain is set
        if domain and domain != "localhost":
            print("\n🔍 Checking DNS resolution...")
            self.check_dns(domain)

        print("\n🎯 Setup complete! Run the following to start services:")
        print("python setup.py compose up -d")

    def is_running_in_container(self) -> bool:
        """Check if we're running inside a container"""
        return (
            os.path.exists("/.dockerenv")
            or os.path.exists("/run/.containerenv")
            or os.environ.get("RUNNING_IN_CONTAINER") == "true"
            or os.environ.get("CONTAINER") == "docker"
        )

    def ensure_uv_venv(self) -> bool:
        """Ensure uv virtual environment is set up and activated (localhost only)"""
        if self.is_running_in_container():
            print("ℹ️  Running in container, using container Python environment")
            return True

        venv_path = self.root_dir / ".venv"

        # Check if uv is available
        try:
            self.run_command(["uv", "--version"])
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("⚠️  uv not found, falling back to system Python")
            return True

        # Create venv if it doesn't exist
        if not venv_path.exists():
            print("🐍 Creating uv virtual environment...")
            try:
                self.run_command(["uv", "venv", str(venv_path)])
                print("✅ Virtual environment created")
            except subprocess.CalledProcessError as e:
                print(f"❌ Failed to create virtual environment: {e}")
                return False

        # Activate venv by modifying PATH
        venv_bin = venv_path / "bin" if os.name != "nt" else venv_path / "Scripts"
        venv_python = venv_bin / ("python.exe" if os.name == "nt" else "python")

        if venv_python.exists():
            # Add venv to PATH for subsequent commands
            os.environ["PATH"] = str(venv_bin) + os.pathsep + os.environ.get("PATH", "")
            os.environ["VIRTUAL_ENV"] = str(venv_path)
            print(f"✅ Using virtual environment: {venv_path}")
            return True
        else:
            print("❌ Virtual environment Python not found")
            return False

    def cmd_setup(self, args):
        """Handle setup command"""
        # Ensure proper Python environment
        if not self.ensure_uv_venv():
            print("❌ Failed to set up Python environment")
            return

        # Install requirements
        if not self.install_requirements("requirements.txt"):
            print("❌ Failed to install requirements")
            return

        if args.interactive:
            self.setup_interactive()
        else:
            # Auto-setup with defaults
            env_vars = self.load_env()
            env_vars["DOCKER_PLATFORM"] = self.detect_platform()
            self.save_env(env_vars)
            print("✅ Auto-setup complete with detected platform")

    def cmd_compose(self, args):
        """Handle docker-compose commands"""
        compose_args = args.compose_args
        if args.file:
            compose_args = ["-f", args.file] + compose_args
        return self.run_docker_compose(compose_args)

    def cmd_certs(self, args):
        """Handle certificate management"""
        env_vars = self.load_env()
        domain = env_vars.get("DOMAIN", "localhost")

        print("🔒 SSL Certificate Management")
        print("=" * 30)

        if domain == "localhost":
            print("ℹ️  Domain not configured. Using self-signed certificates.")
            print("   To use domain certificates:")
            print("   1. Run: python setup.py setup --interactive")
            print("   2. Set DOMAIN and EMAIL")
            print("   3. Run: python setup.py certs")
            return

        print(f"Domain: {domain}")
        print(f"Email: {env_vars.get('EMAIL', 'not set')}")
        print()

        # DNS check
        if not args.skip_dns:
            print("🔍 Checking DNS resolution...")
            self.check_dns(domain)
            print()

        # Caddy config check
        if not args.skip_caddy:
            print("� Checking Caddy configuration...")
            self.check_caddy_config()
            print()

        # Certificate check
        if not args.skip_certs:
            print("� Checking existing certificates...")
            self.check_certificates()
            print()

        # Cloudflare check
        cloudflare_token = env_vars.get("CLOUDFLARE_API_TOKEN")
        if cloudflare_token:
            print("✅ Cloudflare API token configured")
            print("   DNS challenge will be tested when services start")
        else:
            print("ℹ️  Cloudflare API token not configured")
            print("   For Squarespace domains, use HTTP-01 challenge")
            print("   Edit Caddyfile and uncomment HTTP challenge section")

        print("\n📋 Next steps:")
        print("1. Ensure DNS points to your LAN IP")
        print("2. Run: python setup.py compose up -d")
        print("3. Check logs: python setup.py compose logs caddy")
        print(f"4. Test access: curl -I https://{domain}")

    def cmd_test(self, args):
        """Handle test command"""
        import subprocess

        print("🧪 Running integration tests...")

        # Run the integration test script
        test_script = self.root_dir / "test" / "integration.sh"
        if not test_script.exists():
            print("❌ Integration test script not found")
            return 1

        try:
            # Make script executable if needed
            if os.name != "nt":  # Not Windows
                os.chmod(test_script, 0o755)

            # Run the test script
            result = subprocess.run(
                [str(test_script)] + args.test_args,
                cwd=self.root_dir,
                capture_output=False,
            )
            return result.returncode
        except Exception as e:
            print(f"❌ Test execution failed: {e}")
            return 1


def main():
    parser = argparse.ArgumentParser(
        description="Ollama + Open-WebUI Setup and Management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python setup.py setup --interactive    # Interactive setup
  python setup.py setup                  # Auto-setup with defaults
  python setup.py compose up -d          # Start services
  python setup.py compose logs           # View logs
  python setup.py certs                  # Check certificates and DNS
  python setup.py test                   # Run integration tests
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Setup command
    setup_parser = subparsers.add_parser("setup", help="Setup configuration")
    setup_parser.add_argument(
        "--interactive", "-i", action="store_true", help="Interactive setup wizard"
    )

    # Compose command
    compose_parser = subparsers.add_parser(
        "compose", help="Run docker-compose commands"
    )
    compose_parser.add_argument("-f", "--file", help="Specify docker-compose file")
    compose_parser.add_argument(
        "compose_args",
        nargs=argparse.REMAINDER,
        help="Arguments to pass to docker-compose",
    )

    # Certs command
    certs_parser = subparsers.add_parser("certs", help="Certificate and DNS management")
    certs_parser.add_argument("--skip-dns", action="store_true", help="Skip DNS check")
    certs_parser.add_argument(
        "--skip-caddy", action="store_true", help="Skip Caddy config check"
    )
    certs_parser.add_argument(
        "--skip-certs", action="store_true", help="Skip certificate check"
    )

    # Test command
    test_parser = subparsers.add_parser("test", help="Run integration tests")
    test_parser.add_argument(
        "test_args", nargs=argparse.REMAINDER, help="Arguments to pass to test script"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    setup = OllamaSetup()

    try:
        if args.command == "setup":
            setup.cmd_setup(args)
        elif args.command == "compose":
            return setup.cmd_compose(args)
        elif args.command == "certs":
            setup.cmd_certs(args)
        elif args.command == "test":
            return setup.cmd_test(args)
        else:
            parser.print_help()
    except KeyboardInterrupt:
        print("\n⚠️  Operation cancelled")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
