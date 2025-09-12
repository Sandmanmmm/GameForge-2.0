#!/usr/bin/env python3
"""
========================================================================
GameForge AI - Simplified Load Testing Framework
Basic performance validation without external dependencies
========================================================================
"""

import time
import json
import logging
import asyncio
import subprocess
import sys
import os
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor
import urllib.request
import urllib.error
import statistics
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('simple_load_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class SimpleLoadTestResult:
    """Simple load test result"""
    test_name: str
    start_time: str
    end_time: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    requests_per_second: float
    error_rate: float
    test_duration: float

class SimpleLoadTester:
    """Simplified load testing without external dependencies"""
    
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url.rstrip('/')
        self.results = []
    
    def make_simple_request(self, endpoint: str, timeout: int = 10) -> Dict:
        """Make a simple HTTP request"""
        start_time = time.time()
        
        try:
            url = f"{self.base_url}{endpoint}"
            req = urllib.request.Request(url)
            
            with urllib.request.urlopen(req, timeout=timeout) as response:
                response_data = response.read()
                end_time = time.time()
                
                return {
                    'success': True,
                    'response_time': end_time - start_time,
                    'status_code': response.getcode(),
                    'response_size': len(response_data)
                }
                
        except Exception as e:
            end_time = time.time()
            return {
                'success': False,
                'response_time': end_time - start_time,
                'status_code': 0,
                'error': str(e)
            }
    
    def run_sequential_test(self, endpoint: str, num_requests: int = 100) -> SimpleLoadTestResult:
        """Run sequential load test"""
        logger.info(f"Running sequential test: {num_requests} requests to {endpoint}")
        
        start_time = time.time()
        start_timestamp = datetime.now().isoformat()
        
        results = []
        for i in range(num_requests):
            if i % 10 == 0:
                logger.info(f"Completed {i}/{num_requests} requests")
            
            result = self.make_simple_request(endpoint)
            results.append(result)
            
            # Small delay to prevent overwhelming
            time.sleep(0.1)
        
        end_time = time.time()
        end_timestamp = datetime.now().isoformat()
        test_duration = end_time - start_time
        
        # Calculate metrics
        successful = [r for r in results if r['success']]
        failed = [r for r in results if not r['success']]
        response_times = [r['response_time'] for r in results]
        
        test_result = SimpleLoadTestResult(
            test_name=f"Sequential Test - {endpoint}",
            start_time=start_timestamp,
            end_time=end_timestamp,
            total_requests=len(results),
            successful_requests=len(successful),
            failed_requests=len(failed),
            avg_response_time=statistics.mean(response_times) if response_times else 0,
            min_response_time=min(response_times) if response_times else 0,
            max_response_time=max(response_times) if response_times else 0,
            requests_per_second=len(results) / test_duration,
            error_rate=len(failed) / len(results) if results else 1.0,
            test_duration=test_duration
        )
        
        self.results.append(test_result)
        return test_result
    
    def run_concurrent_test(self, endpoint: str, concurrent_users: int = 10, requests_per_user: int = 10) -> SimpleLoadTestResult:
        """Run concurrent load test using ThreadPoolExecutor"""
        logger.info(f"Running concurrent test: {concurrent_users} users, {requests_per_user} requests each")
        
        start_time = time.time()
        start_timestamp = datetime.now().isoformat()
        
        def worker_requests(user_id: int) -> List[Dict]:
            """Worker function for each concurrent user"""
            user_results = []
            for _ in range(requests_per_user):
                result = self.make_simple_request(endpoint)
                result['user_id'] = user_id
                user_results.append(result)
                time.sleep(0.05)  # Small delay between requests
            return user_results
        
        # Run concurrent requests
        all_results = []
        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [executor.submit(worker_requests, i) for i in range(concurrent_users)]
            
            for future in futures:
                try:
                    user_results = future.result(timeout=60)  # 60 second timeout
                    all_results.extend(user_results)
                except Exception as e:
                    logger.error(f"Concurrent test worker failed: {e}")
        
        end_time = time.time()
        end_timestamp = datetime.now().isoformat()
        test_duration = end_time - start_time
        
        # Calculate metrics
        successful = [r for r in all_results if r['success']]
        failed = [r for r in all_results if not r['success']]
        response_times = [r['response_time'] for r in all_results]
        
        test_result = SimpleLoadTestResult(
            test_name=f"Concurrent Test - {concurrent_users} users - {endpoint}",
            start_time=start_timestamp,
            end_time=end_timestamp,
            total_requests=len(all_results),
            successful_requests=len(successful),
            failed_requests=len(failed),
            avg_response_time=statistics.mean(response_times) if response_times else 0,
            min_response_time=min(response_times) if response_times else 0,
            max_response_time=max(response_times) if response_times else 0,
            requests_per_second=len(all_results) / test_duration,
            error_rate=len(failed) / len(all_results) if all_results else 1.0,
            test_duration=test_duration
        )
        
        self.results.append(test_result)
        return test_result
    
    def test_service_availability(self) -> Dict[str, bool]:
        """Test if services are available"""
        logger.info("Testing service availability...")
        
        endpoints = [
            '/health',
            '/api/health',
            '/api/v1/health',
            '/',
            '/status'
        ]
        
        availability = {}
        for endpoint in endpoints:
            try:
                result = self.make_simple_request(endpoint, timeout=5)
                availability[endpoint] = result['success'] and result['status_code'] == 200
                logger.info(f"Endpoint {endpoint}: {'✓' if availability[endpoint] else '✗'}")
            except Exception as e:
                availability[endpoint] = False
                logger.error(f"Endpoint {endpoint} failed: {e}")
        
        return availability
    
    def run_comprehensive_load_test(self) -> List[SimpleLoadTestResult]:
        """Run comprehensive load testing suite"""
        logger.info("Starting comprehensive load testing...")
        
        # Test service availability first
        availability = self.test_service_availability()
        available_endpoints = [ep for ep, available in availability.items() if available]
        
        if not available_endpoints:
            logger.error("No endpoints available for testing")
            return []
        
        test_endpoint = available_endpoints[0]
        logger.info(f"Using endpoint for testing: {test_endpoint}")
        
        test_results = []
        
        try:
            # Test 1: Sequential baseline
            logger.info("Running Test 1: Sequential Baseline")
            result1 = self.run_sequential_test(test_endpoint, 50)
            test_results.append(result1)
            
            # Small break between tests
            time.sleep(5)
            
            # Test 2: Light concurrent load
            logger.info("Running Test 2: Light Concurrent Load")
            result2 = self.run_concurrent_test(test_endpoint, 5, 10)
            test_results.append(result2)
            
            # Small break between tests
            time.sleep(5)
            
            # Test 3: Medium concurrent load
            logger.info("Running Test 3: Medium Concurrent Load")
            result3 = self.run_concurrent_test(test_endpoint, 10, 10)
            test_results.append(result3)
            
            # Small break between tests
            time.sleep(5)
            
            # Test 4: High concurrent load
            logger.info("Running Test 4: High Concurrent Load")
            result4 = self.run_concurrent_test(test_endpoint, 20, 5)
            test_results.append(result4)
            
        except Exception as e:
            logger.error(f"Load testing failed: {e}")
        
        return test_results
    
    def generate_load_test_report(self, results: List[SimpleLoadTestResult]) -> str:
        """Generate load test report"""
        
        if not results:
            return "No load test results available"
        
        report = []
        report.append("=" * 80)
        report.append("GAMEFORGE AI - LOAD TESTING REPORT")
        report.append("=" * 80)
        report.append("")
        
        # Summary table
        report.append("TEST RESULTS SUMMARY:")
        report.append("-" * 80)
        report.append(f"{'Test Name':<40} {'Total':<8} {'Success':<8} {'RPS':<8} {'Avg RT':<8} {'Error%':<8}")
        report.append("-" * 80)
        
        for result in results:
            report.append(
                f"{result.test_name[:39]:<40} "
                f"{result.total_requests:<8} "
                f"{result.successful_requests:<8} "
                f"{result.requests_per_second:<8.1f} "
                f"{result.avg_response_time:<8.3f} "
                f"{result.error_rate:<8.1%}"
            )
        
        report.append("")
        
        # Performance analysis
        report.append("PERFORMANCE ANALYSIS:")
        report.append("-" * 30)
        
        # Find best and worst performing tests
        if results:
            best_rps = max(results, key=lambda x: x.requests_per_second)
            worst_error = max(results, key=lambda x: x.error_rate)
            fastest_response = min(results, key=lambda x: x.avg_response_time)
            
            report.append(f"• Best throughput: {best_rps.requests_per_second:.1f} RPS ({best_rps.test_name})")
            report.append(f"• Fastest response: {fastest_response.avg_response_time:.3f}s ({fastest_response.test_name})")
            report.append(f"• Highest error rate: {worst_error.error_rate:.1%} ({worst_error.test_name})")
        
        report.append("")
        
        # Recommendations
        report.append("PERFORMANCE RECOMMENDATIONS:")
        report.append("-" * 30)
        
        avg_error_rate = sum(r.error_rate for r in results) / len(results) if results else 0
        avg_response_time = sum(r.avg_response_time for r in results) / len(results) if results else 0
        max_rps = max(r.requests_per_second for r in results) if results else 0
        
        if avg_error_rate > 0.05:
            report.append("• HIGH ERROR RATE DETECTED - Review error handling and capacity")
        if avg_response_time > 2.0:
            report.append("• SLOW RESPONSE TIMES - Consider performance optimization")
        if max_rps < 10:
            report.append("• LOW THROUGHPUT - Review server configuration and resources")
        
        if avg_error_rate <= 0.01 and avg_response_time <= 1.0 and max_rps >= 50:
            report.append("• PERFORMANCE LOOKS GOOD - System handles load well")
        
        return "\n".join(report)
    
    def save_results(self, filename: str = "load_test_results.json"):
        """Save results to JSON file"""
        with open(filename, 'w') as f:
            json.dump([asdict(result) for result in self.results], f, indent=2)
        logger.info(f"Load test results saved to {filename}")

def main():
    """Main load testing execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Simple Load Testing Framework')
    parser.add_argument('--url', default='http://localhost:8080', help='Base URL to test')
    parser.add_argument('--output', default='simple_load_test_results', help='Output directory')
    
    args = parser.parse_args()
    
    # Create output directory
    os.makedirs(args.output, exist_ok=True)
    
    # Initialize tester
    tester = SimpleLoadTester(args.url)
    
    try:
        logger.info(f"Starting load testing against {args.url}")
        
        # Run comprehensive tests
        results = tester.run_comprehensive_load_test()
        
        if not results:
            logger.error("No test results generated")
            return 1
        
        # Generate report
        report = tester.generate_load_test_report(results)
        print("\n" + report)
        
        # Save results
        results_file = os.path.join(args.output, 'load_test_results.json')
        tester.save_results(results_file)
        
        # Save report
        report_file = os.path.join(args.output, 'load_test_report.txt')
        with open(report_file, 'w') as f:
            f.write(report)
        
        logger.info(f"Load testing complete. Results saved to {args.output}")
        
        # Determine success/failure
        avg_error_rate = sum(r.error_rate for r in results) / len(results)
        if avg_error_rate > 0.10:
            logger.error("LOAD TEST FAILED: High error rate")
            return 1
        else:
            logger.info("LOAD TEST PASSED: Performance acceptable")
            return 0
            
    except Exception as e:
        logger.error(f"Load testing failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())