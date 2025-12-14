#!/usr/bin/env python3
"""
Performance and Load Testing for Ollama + Open-WebUI Setup
Comprehensive testing for production performance requirements
"""

import time
import statistics
import psutil
import requests
import json
import subprocess
from pathlib import Path
import sys
import os
from typing import Dict, List, Tuple
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from setup import OllamaSetup


class PerformanceTester:
    """Performance testing utilities"""

    def __init__(self):
        self.setup = OllamaSetup()
        self.results = {}

    def collect_system_metrics(self) -> Dict:
        """Collect current system metrics"""
        return {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_usage': psutil.disk_usage('/').percent,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }

    def collect_container_metrics(self) -> Dict:
        """Collect Docker container metrics"""
        metrics = {}
        try:
            result = subprocess.run(
                ['docker', 'stats', '--no-stream', '--format', 'json'],
                capture_output=True, text=True, timeout=10
            )

            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line:
                        container = json.loads(line)
                        name = container.get('Name', '').replace('ollama-', '')
                        if name:
                            metrics[name] = {
                                'cpu_percent': container.get('CPUPerc', '0%'),
                                'memory_usage': container.get('MemUsage', ''),
                                'network_io': container.get('NetIO', ''),
                                'block_io': container.get('BlockIO', '')
                            }
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        return metrics

    def measure_response_time(self, url: str, method: str = 'GET',
                            data: Dict = None, headers: Dict = None,
                            num_requests: int = 10) -> Dict:
        """Measure response times for an endpoint"""
        response_times = []

        for _ in range(num_requests):
            try:
                start_time = time.time()
                if method.upper() == 'GET':
                    response = requests.get(url, timeout=30, headers=headers, verify=False)
                elif method.upper() == 'POST':
                    response = requests.post(url, json=data, timeout=30,
                                           headers=headers, verify=False)
                else:
                    continue

                response_time = time.time() - start_time
                if response.status_code < 400:  # Only count successful requests
                    response_times.append(response_time)

            except (requests.exceptions.RequestException, TimeoutError):
                continue

        if not response_times:
            return {'error': 'No successful requests'}

        return {
            'min': min(response_times),
            'max': max(response_times),
            'avg': statistics.mean(response_times),
            'median': statistics.median(response_times),
            'p95': statistics.quantiles(response_times, n=20)[18],  # 95th percentile
            'p99': statistics.quantiles(response_times, n=100)[98],  # 99th percentile
            'success_rate': len(response_times) / num_requests,
            'total_requests': num_requests
        }

    def run_load_test(self, url: str, concurrent_users: int = 10,
                     duration: int = 60) -> Dict:
        """Run a basic load test"""
        import threading
        import queue

        results_queue = queue.Queue()
        stop_event = threading.Event()

        def worker(worker_id: int):
            """Worker thread for load testing"""
            local_results = []
            request_count = 0

            while not stop_event.is_set():
                try:
                    start_time = time.time()
                    response = requests.get(url, timeout=10, verify=False)
                    response_time = time.time() - start_time

                    if response.status_code < 400:
                        local_results.append(response_time)
                        request_count += 1

                except (requests.exceptions.RequestException, TimeoutError):
                    pass

                time.sleep(0.1)  # Small delay between requests

            results_queue.put((worker_id, local_results, request_count))

        # Start workers
        threads = []
        for i in range(concurrent_users):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        # Run for specified duration
        time.sleep(duration)
        stop_event.set()

        # Collect results
        all_response_times = []
        total_requests = 0

        for t in threads:
            t.join()
            worker_id, times, count = results_queue.get()
            all_response_times.extend(times)
            total_requests += count

        if not all_response_times:
            return {'error': 'No successful requests during load test'}

        return {
            'total_requests': total_requests,
            'requests_per_second': total_requests / duration,
            'concurrent_users': concurrent_users,
            'duration_seconds': duration,
            'response_times': {
                'min': min(all_response_times),
                'max': max(all_response_times),
                'avg': statistics.mean(all_response_times),
                'median': statistics.median(all_response_times),
                'p95': statistics.quantiles(all_response_times, n=20)[18],
                'p99': statistics.quantiles(all_response_times, n=100)[98]
            }
        }


def run_performance_tests():
    """Run comprehensive performance tests"""
    print("🚀 Starting Performance Tests")
    print("=" * 50)

    tester = PerformanceTester()

    # Start services if not running
    print("📦 Starting services...")
    result = tester.setup.run_docker_compose(['up', '-d'])
    if result != 0:
        print("❌ Failed to start services")
        return

    # Wait for services to be ready
    print("⏳ Waiting for services to be ready...")
    time.sleep(60)

    results = {}

    # Test baseline system metrics
    print("📊 Collecting baseline metrics...")
    results['baseline'] = {
        'system': tester.collect_system_metrics(),
        'containers': tester.collect_container_metrics()
    }

    # Test API response times
    print("⚡ Testing API response times...")

    endpoints = [
        ('Ollama API /tags', os.getenv('OLLAMA_URL', 'http://ollama:11434') + '/api/tags'),
        ('Ollama API /version', os.getenv('OLLAMA_URL', 'http://ollama:11434') + '/api/version'),
        ('Open-WebUI /health', os.getenv('WEBUI_URL', 'http://open-webui:8080') + '/health'),
        ('Open-WebUI /api/config', os.getenv('WEBUI_URL', 'http://open-webui:8080') + '/api/config'),
        ('Caddy Proxy', os.getenv('CADDY_URL', 'http://caddy:80'))
    ]

    results['api_performance'] = {}
    for name, url in endpoints:
        print(f"  Testing {name}...")
        try:
            perf_data = tester.measure_response_time(url, num_requests=20)
            results['api_performance'][name] = perf_data
            print(f"    ✅ {name}: {perf_data['avg_response_time']:.3f}s avg, {perf_data['success_rate']:.1f}% success")
        except Exception as e:
            print(f"    ❌ Error: {e}")
            results['api_performance'][name] = {'error': str(e)}

    # Test load performance
    print("🔥 Running load tests...")

    load_tests = [
        ('Light Load (5 users)', os.getenv('CADDY_URL', 'http://caddy:80'), 5, 30),
        ('Medium Load (10 users)', os.getenv('CADDY_URL', 'http://caddy:80'), 10, 30),
        ('Heavy Load (20 users)', os.getenv('CADDY_URL', 'http://caddy:80'), 20, 30)
    ]

    results['load_tests'] = {}
    for name, url, users, duration in load_tests:
        print(f"  Running {name}...")
        try:
            load_data = tester.run_load_test(url, users, duration)
            results['load_tests'][name] = load_data
            print(f"    ✅ {name}: {load_data.get('requests_per_second', 0):.1f} req/s, {load_data.get('avg_response_time', 0):.1f}ms avg")
        except Exception as e:
            print(f"    ❌ Error: {e}")
            results['load_tests'][name] = {'error': str(e)}

    # Test resource usage during load
    print("📈 Testing resource usage under load...")
    results['resource_usage'] = {}

    # Run a moderate load test and monitor resources
    load_thread = threading.Thread(
        target=lambda: tester.run_load_test('https://localhost', 15, 45)
    )
    load_thread.start()

    # Monitor resources during load
    resource_samples = []
    for _ in range(9):  # Sample every 5 seconds for 45 seconds
        time.sleep(5)
        resource_samples.append({
            'system': tester.collect_system_metrics(),
            'containers': tester.collect_container_metrics()
        })

    load_thread.join()
    results['resource_usage']['samples'] = resource_samples

    # Calculate resource usage statistics
    if resource_samples:
        cpu_usage = [s['system']['cpu_percent'] for s in resource_samples]
        mem_usage = [s['system']['memory_percent'] for s in resource_samples]

        results['resource_usage']['summary'] = {
            'cpu_avg': statistics.mean(cpu_usage),
            'cpu_max': max(cpu_usage),
            'mem_avg': statistics.mean(mem_usage),
            'mem_max': max(mem_usage)
        }

    # Save results
    output_file = Path('test/performance_results.json')
    output_file.parent.mkdir(exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    print(f"✅ Performance test results saved to {output_file}")

    # Print summary
    print("\n📋 Performance Test Summary")
    print("=" * 30)

    if 'api_performance' in results:
        print("API Response Times:")
        for name, data in results['api_performance'].items():
            if 'error' not in data:
                print(".3f"            else:
                print(f"  {name}: ERROR - {data['error']}")

    if 'load_tests' in results:
        print("\nLoad Test Results:")
        for name, data in results['load_tests'].items():
            if 'error' not in data:
                print(f"  {name}: {data['response_time']:.1f}ms")
            else:
                print(f"  {name}: ERROR - {data['error']}")

    if 'resource_usage' in results and 'summary' in results['resource_usage']:
        summary = results['resource_usage']['summary']
        print("\n📊 Resource Usage Under Load:")
        print(f"  CPU Usage: {summary.get('cpu_percent', 0):.1f}%")
        print(f"  Memory Usage: {summary.get('memory_mb', 0):.1f} MB")
    # Cleanup
    print("\n🧹 Cleaning up...")
    tester.setup.run_docker_compose(['down'])

    return results


def run_regression_tests():
    """Run performance regression tests against baseline"""
    print("🔄 Running Performance Regression Tests")
    print("=" * 50)

    baseline_file = Path('test/performance_baseline.json')
    current_file = Path('test/performance_results.json')

    if not baseline_file.exists():
        print("⚠️  No baseline performance data found. Creating baseline...")
        if current_file.exists():
            import shutil
            shutil.copy(current_file, baseline_file)
            print("✅ Baseline created from current results")
        else:
            print("❌ No performance data available")
        return

    if not current_file.exists():
        print("❌ No current performance data available")
        return

    # Load baseline and current results
    with open(baseline_file) as f:
        baseline = json.load(f)

    with open(current_file) as f:
        current = json.load(f)

    regressions = []
    improvements = []

    # Compare API performance
    if 'api_performance' in baseline and 'api_performance' in current:
        print("Comparing API Performance...")

        for endpoint in baseline['api_performance']:
            if endpoint in current['api_performance']:
                base_data = baseline['api_performance'][endpoint]
                curr_data = current['api_performance'][endpoint]

                if 'error' in base_data or 'error' in curr_data:
                    continue

                # Check for significant regressions (20% increase in response time)
                avg_regression = (curr_data['avg'] - base_data['avg']) / base_data['avg']
                p95_regression = (curr_data['p95'] - base_data['p95']) / base_data['p95']

                if avg_regression > 0.20:  # 20% slower
                    regressions.append(f"{endpoint} avg response time: +{avg_regression:.1%}")
                elif avg_regression < -0.10:  # 10% faster
                    improvements.append(f"{endpoint} avg response time: {avg_regression:.1%}")

                if p95_regression > 0.20:
                    regressions.append(f"{endpoint} P95 response time: +{p95_regression:.1%}")

    # Compare load test performance
    if 'load_tests' in baseline and 'load_tests' in current:
        print("Comparing Load Test Performance...")

        for test_name in baseline['load_tests']:
            if test_name in current['load_tests']:
                base_data = baseline['load_tests'][test_name]
                curr_data = current['load_tests'][test_name]

                if 'error' in base_data or 'error' in curr_data:
                    continue

                rps_regression = (base_data['requests_per_second'] - curr_data['requests_per_second']) / base_data['requests_per_second']

                if rps_regression > 0.15:  # 15% drop in throughput
                    regressions.append(f"{test_name} throughput: -{rps_regression:.1%}")

    # Report results
    if regressions:
        print("❌ Performance Regressions Detected:")
        for regression in regressions:
            print(f"  - {regression}")
    else:
        print("✅ No significant performance regressions detected")

    if improvements:
        print("\n✅ Performance Improvements:")
        for improvement in improvements:
            print(f"  + {improvement}")

    return len(regressions) == 0


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Performance Testing for Ollama Setup')
    parser.add_argument('--baseline', action='store_true',
                       help='Create/update performance baseline')
    parser.add_argument('--regression', action='store_true',
                       help='Run regression tests against baseline')

    args = parser.parse_args()

    if args.baseline:
        # Run tests and save as baseline
        results = run_performance_tests()
        if results:
            baseline_file = Path('test/performance_baseline.json')
            baseline_file.parent.mkdir(exist_ok=True)
            with open(baseline_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print("✅ Performance baseline updated")

    elif args.regression:
        # Run regression tests
        success = run_regression_tests()
        exit(0 if success else 1)

    else:
        # Run standard performance tests
        run_performance_tests()