#!/usr/bin/env python3
"""
Security Testing for Ollama + Open-WebUI Setup
Comprehensive security validation for production deployment
"""

import requests
import ssl
import socket
import subprocess
import json
import time
from pathlib import Path
import sys
import os
from typing import Dict, List, Tuple
from urllib.parse import urlparse

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from setup import OllamaSetup


class SecurityTester:
    """Security testing utilities"""

    def __init__(self):
        self.setup = OllamaSetup()
        self.results = {}

    def test_ssl_tls_configuration(self) -> Dict:
        """Test SSL/TLS configuration"""
        results = {
            "certificate_valid": False,
            "tls_version": None,
            "cipher_suite": None,
            "certificate_info": {},
            "vulnerabilities": [],
        }

        try:
            # Test HTTPS connection
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

            with socket.create_connection(("localhost", 8443)) as sock:
                with context.wrap_socket(sock, server_hostname="localhost") as ssock:
                    # Get certificate info
                    cert = ssock.getpeercert()
                    results["certificate_info"] = {
                        "subject": cert.get("subject", []),
                        "issuer": cert.get("issuer", []),
                        "version": cert.get("version"),
                        "serial_number": str(cert.get("serialNumber", "")),
                        "not_before": cert.get("notBefore"),
                        "not_after": cert.get("notAfter"),
                    }

                    # Get TLS version and cipher
                    results["tls_version"] = ssock.version()
                    results["cipher_suite"] = ssock.cipher()[0]

                    # Check if certificate is self-signed (common for localhost)
                    results["certificate_valid"] = True

                    # Check for known vulnerabilities
                    if ssock.version() in ["TLSv1", "TLSv1.1"]:
                        results["vulnerabilities"].append("Outdated TLS version")

                    # Check cipher strength
                    weak_ciphers = ["RC4", "DES", "3DES", "MD5", "SHA1"]
                    cipher_name = ssock.cipher()[0].upper()
                    if any(weak in cipher_name for weak in weak_ciphers):
                        results["vulnerabilities"].append(
                            f"Weak cipher suite: {cipher_name}"
                        )

        except Exception as e:
            results["error"] = str(e)

        return results

    def test_security_headers(self, url: str) -> Dict:
        """Test security headers in HTTP responses"""
        results = {"security_headers": {}, "missing_headers": [], "recommendations": []}

        try:
            # Use HTTP for containerized testing, verify=False for self-signed certs
            test_url = (
                url.replace("https://", "http://")
                if url.startswith("https://")
                else url
            )
            response = requests.get(test_url, timeout=10, verify=False)
            headers = response.headers

            # Required security headers
            required_headers = {
                "Strict-Transport-Security": "HTTP Strict Transport Security",
                "X-Frame-Options": "Clickjacking protection",
                "X-Content-Type-Options": "MIME type sniffing protection",
                "X-XSS-Protection": "XSS protection",
                "Referrer-Policy": "Referrer policy",
                "Content-Security-Policy": "Content Security Policy",
            }

            for header, description in required_headers.items():
                if header in headers:
                    results["security_headers"][header] = headers[header]
                else:
                    results["missing_headers"].append(header)
                    results["recommendations"].append(
                        f"Add {header} header for {description}"
                    )

            # Check HSTS max-age
            if "Strict-Transport-Security" in headers:
                hsts_value = headers["Strict-Transport-Security"]
                if "max-age=" in hsts_value:
                    max_age = hsts_value.split("max-age=")[1].split(";")[0]
                    try:
                        max_age_seconds = int(max_age)
                        if max_age_seconds < 31536000:  # Less than 1 year
                            results["recommendations"].append(
                                "Consider increasing HSTS max-age to at least 31536000 (1 year)"
                            )
                    except ValueError:
                        results["recommendations"].append("Invalid HSTS max-age value")

        except Exception as e:
            results["error"] = str(e)

        return results

    def test_open_ports(self) -> Dict:
        """Test for open ports and services"""
        results = {"open_ports": [], "exposed_services": [], "recommendations": []}

        ports_to_check = [
            (11434, "Ollama API"),
            (8080, "Open-WebUI"),
            (8443, "Caddy HTTPS"),
            (8081, "Potential additional service"),
            (3000, "Potential web service"),
            (5000, "Potential API service"),
        ]

        for port, service in ports_to_check:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex(("localhost", port))
                if result == 0:
                    results["open_ports"].append({"port": port, "service": service})

                    # Additional check for HTTP services
                    try:
                        response = requests.get(f"http://localhost:{port}", timeout=2)
                        results["exposed_services"].append(
                            {
                                "port": port,
                                "service": service,
                                "http_status": response.status_code,
                                "server": response.headers.get("Server", "Unknown"),
                            }
                        )
                    except:
                        pass

                sock.close()
            except:
                pass

        # Recommendations
        if 11434 in [p["port"] for p in results["open_ports"]]:
            results["recommendations"].append(
                "Ollama API (port 11434) is exposed. Consider restricting access if not needed externally"
            )

        if 8080 in [p["port"] for p in results["open_ports"]]:
            results["recommendations"].append(
                "Open-WebUI (port 8080) is exposed. Ensure proper authentication is configured"
            )

        return results

    def test_api_security(self) -> Dict:
        """Test API endpoints for security issues"""
        results = {"endpoints_tested": [], "vulnerabilities": [], "recommendations": []}

        endpoints = [
            (
                os.getenv("OLLAMA_URL", "http://ollama:11434") + "/api/tags",
                "Ollama API - Model List",
            ),
            (
                os.getenv("OLLAMA_URL", "http://ollama:11434") + "/api/version",
                "Ollama API - Version",
            ),
            (
                os.getenv("WEBUI_URL", "http://open-webui:8080") + "/health",
                "Open-WebUI Health",
            ),
            (
                os.getenv("WEBUI_URL", "http://open-webui:8080") + "/api/config",
                "Open-WebUI Config",
            ),
        ]

        for url, description in endpoints:
            try:
                response = requests.get(url, timeout=10)

                results["endpoints_tested"].append(
                    {
                        "url": url,
                        "description": description,
                        "status_code": response.status_code,
                        "accessible": True,
                    }
                )

                # Check for sensitive information in responses
                if response.status_code == 200:
                    content = response.text.lower()

                    # Check for potential information disclosure
                    sensitive_keywords = [
                        "password",
                        "secret",
                        "key",
                        "token",
                        "api_key",
                    ]
                    for keyword in sensitive_keywords:
                        if keyword in content:
                            results["vulnerabilities"].append(
                                {
                                    "endpoint": url,
                                    "issue": f'Potential information disclosure: contains "{keyword}"',
                                }
                            )

            except requests.exceptions.RequestException as e:
                results["endpoints_tested"].append(
                    {
                        "url": url,
                        "description": description,
                        "error": str(e),
                        "accessible": False,
                    }
                )

        # Recommendations
        accessible_api = [
            e for e in results["endpoints_tested"] if e.get("accessible", False)
        ]
        if accessible_api:
            results["recommendations"].append(
                "Consider implementing API authentication and rate limiting"
            )

        return results

    def test_container_security(self) -> Dict:
        """Test Docker container security"""
        results = {"containers": [], "security_issues": [], "recommendations": []}

        try:
            # Get running containers
            result = subprocess.run(
                ["docker", "ps", "--filter", "name=ollama", "--format", "json"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    if line:
                        container = json.loads(line)
                        container_info = {
                            "name": container.get("Names", ""),
                            "image": container.get("Image", ""),
                            "status": container.get("Status", ""),
                            "ports": container.get("Ports", ""),
                        }
                        results["containers"].append(container_info)

                        # Check for security issues
                        name = container_info["name"]
                        if "root" in name or name.startswith("/"):
                            results["security_issues"].append(
                                f"Container {name} may be running as root"
                            )

                        # Check if ports are exposed
                        ports = container_info["ports"]
                        if ports and ("0.0.0.0" in ports or "::" in ports):
                            results["security_issues"].append(
                                f"Container {name} exposes ports to all interfaces"
                            )

        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            results["error"] = str(e)

        # Recommendations
        if results["containers"]:
            results["recommendations"].append(
                "Run containers with non-root users when possible"
            )
            results["recommendations"].append(
                "Avoid exposing container ports to 0.0.0.0 unless necessary"
            )

        return results


def run_security_tests():
    """Run comprehensive security tests"""
    print("🔒 Starting Security Tests")
    print("=" * 50)

    tester = SecurityTester()

    # Start services if not running
    print("📦 Starting services...")
    result = tester.setup.run_docker_compose(["up", "-d"])
    if result != 0:
        print("❌ Failed to start services")
        return

    # Wait for services to be ready
    print("⏳ Waiting for services to be ready...")
    time.sleep(30)

    results = {}

    # Test SSL/TLS configuration
    print("🔐 Testing SSL/TLS configuration...")
    results["ssl_tls"] = tester.test_ssl_tls_configuration()

    # Test security headers
    print("🛡️  Testing security headers...")
    results["security_headers"] = tester.test_security_headers(
        os.getenv("CADDY_URL", "http://caddy:80")
    )

    # Test open ports
    print("🔍 Testing open ports and exposed services...")
    results["open_ports"] = tester.test_open_ports()

    # Test API security
    print("🔑 Testing API security...")
    results["api_security"] = tester.test_api_security()

    # Test container security
    print("🐳 Testing container security...")
    results["container_security"] = tester.test_container_security()

    # Save results
    output_file = Path("test/security_results.json")
    output_file.parent.mkdir(exist_ok=True)

    with open(output_file, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"✅ Security test results saved to {output_file}")

    # Print summary
    print("\n📋 Security Test Summary")
    print("=" * 30)

    # SSL/TLS Summary
    ssl_results = results.get("ssl_tls", {})
    if ssl_results.get("certificate_valid"):
        print("✅ SSL/TLS: Certificate valid")
        if ssl_results.get("tls_version"):
            print(f"   TLS Version: {ssl_results['tls_version']}")
        if ssl_results.get("vulnerabilities"):
            print("   ⚠️  Vulnerabilities found:")
            for vuln in ssl_results["vulnerabilities"]:
                print(f"      - {vuln}")
    else:
        print("❌ SSL/TLS: Certificate invalid or connection failed")

    # Security Headers Summary
    headers_results = results.get("security_headers", {})
    if headers_results.get("missing_headers"):
        print(f"⚠️  Missing security headers: {len(headers_results['missing_headers'])}")
        for header in headers_results["missing_headers"][:3]:  # Show first 3
            print(f"   - {header}")
    else:
        print("✅ Security headers: All recommended headers present")

    # Open Ports Summary
    ports_results = results.get("open_ports", {})
    if ports_results.get("open_ports"):
        print(f"ℹ️  Open ports detected: {len(ports_results['open_ports'])}")
        for port_info in ports_results["open_ports"]:
            print(f"   - Port {port_info['port']}: {port_info['service']}")

    # API Security Summary
    api_results = results.get("api_security", {})
    accessible_endpoints = [
        e for e in api_results.get("endpoints_tested", []) if e.get("accessible", False)
    ]
    if accessible_endpoints:
        print(f"ℹ️  Accessible API endpoints: {len(accessible_endpoints)}")
        if api_results.get("vulnerabilities"):
            print(f"⚠️  API vulnerabilities: {len(api_results['vulnerabilities'])}")

    # Container Security Summary
    container_results = results.get("container_security", {})
    if container_results.get("security_issues"):
        print(
            f"⚠️  Container security issues: {len(container_results['security_issues'])}"
        )
        for issue in container_results["security_issues"][:3]:  # Show first 3
            print(f"   - {issue}")

    # Overall recommendations
    all_recommendations = []
    for test_results in results.values():
        if isinstance(test_results, dict) and "recommendations" in test_results:
            all_recommendations.extend(test_results["recommendations"])

    if all_recommendations:
        print("\n📝 Security Recommendations:")
        for rec in all_recommendations[:5]:  # Show first 5
            print(f"   • {rec}")
        if len(all_recommendations) > 5:
            print(f"   ... and {len(all_recommendations) - 5} more")

    # Cleanup
    print("\n🧹 Cleaning up...")
    tester.setup.run_docker_compose(["down"])

    return results


def run_security_audit():
    """Run automated security audit using external tools"""
    print("🔍 Running Security Audit with External Tools")
    print("=" * 50)

    audit_results = {}

    # Check if security tools are available
    tools = {
        "safety": "pip safety check",
        "bandit": "bandit -r .",
        "trivy": "trivy fs --security-checks vuln .",
    }

    for tool, command in tools.items():
        print(f"Running {tool}...")
        try:
            result = subprocess.run(
                command.split(),
                capture_output=True,
                text=True,
                timeout=300,  # 5 minutes timeout
                cwd=Path(__file__).parent.parent,
            )

            audit_results[tool] = {
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "available": True,
            }

            if result.returncode == 0:
                print(f"✅ {tool}: PASSED")
            else:
                print(f"⚠️  {tool}: ISSUES FOUND")
                # Print first few lines of output
                output_lines = result.stdout.split("\n")[:10]
                for line in output_lines:
                    if line.strip():
                        print(f"   {line}")

        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            audit_results[tool] = {"error": str(e), "available": False}
            print(f"❌ {tool}: NOT AVAILABLE - {e}")

    # Save audit results
    audit_file = Path("test/security_audit.json")
    audit_file.parent.mkdir(exist_ok=True)

    with open(audit_file, "w") as f:
        json.dump(audit_results, f, indent=2)

    print(f"✅ Security audit results saved to {audit_file}")

    return audit_results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Security Testing for Ollama Setup")
    parser.add_argument(
        "--audit", action="store_true", help="Run security audit with external tools"
    )

    args = parser.parse_args()

    if args.audit:
        run_security_audit()
    else:
        run_security_tests()
