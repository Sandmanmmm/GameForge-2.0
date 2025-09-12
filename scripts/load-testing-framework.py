#!/usr/bin/env python3
"""
========================================================================
GameForge AI - Comprehensive Load Testing Framework
Enterprise-grade performance validation for concurrent AI workloads
========================================================================
"""

import asyncio
import aiohttp
import time
import json
import statistics
import psutil
import docker
import logging
import argparse
import sys
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('load_test_results.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class LoadTestMetrics:
    """Comprehensive load test metrics"""
    timestamp: str
    concurrent_users: int
    requests_per_second: float
    avg_response_time: float
    p95_response_time: float
    p99_response_time: float
    error_rate: float
    cpu_usage: float
    memory_usage: float
    gpu_usage: float
    gpu_memory_usage: float
    successful_requests: int
    failed_requests: int
    total_requests: int

@dataclass
class AIWorkloadTest:
    """AI-specific workload test configuration"""
    endpoint: str
    model_type: str
    input_data: Dict
    expected_response_time: float
    max_error_rate: float

class GPUMonitor:
    """Monitor GPU usage during load tests"""
    
    def __init__(self):
        self.gpu_metrics = []
        self.monitoring = False
    
    async def start_monitoring(self):
        """Start GPU monitoring in background"""
        self.monitoring = True
        while self.monitoring:
            try:
                import pynvml
                pynvml.nvmlInit()
                gpu_count = pynvml.nvmlDeviceGetCount()
                
                total_usage = 0
                total_memory = 0
                
                for i in range(gpu_count):
                    handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                    gpu_info = pynvml.nvmlDeviceGetUtilizationRates(handle)
                    memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                    
                    total_usage += gpu_info.gpu
                    total_memory += (memory_info.used / memory_info.total) * 100
                
                avg_usage = total_usage / gpu_count if gpu_count > 0 else 0
                avg_memory = total_memory / gpu_count if gpu_count > 0 else 0
                
                self.gpu_metrics.append({
                    'timestamp': time.time(),
                    'gpu_usage': avg_usage,
                    'gpu_memory': avg_memory
                })
                
            except Exception as e:
                logger.warning(f"GPU monitoring error: {e}")
                # Fallback for systems without nvidia-ml-py
                self.gpu_metrics.append({
                    'timestamp': time.time(),
                    'gpu_usage': 0,
                    'gpu_memory': 0
                })
            
            await asyncio.sleep(1)
    
    def stop_monitoring(self):
        """Stop GPU monitoring"""
        self.monitoring = False
    
    def get_average_usage(self) -> Tuple[float, float]:
        """Get average GPU usage during test"""
        if not self.gpu_metrics:
            return 0.0, 0.0
        
        avg_usage = statistics.mean([m['gpu_usage'] for m in self.gpu_metrics])
        avg_memory = statistics.mean([m['gpu_memory'] for m in self.gpu_metrics])
        
        return avg_usage, avg_memory

class LoadTestRunner:
    """Advanced load testing framework for AI services"""
    
    def __init__(self, base_url: str, test_duration: int = 300):
        self.base_url = base_url.rstrip('/')
        self.test_duration = test_duration
        self.client = docker.from_env()
        self.gpu_monitor = GPUMonitor()
        self.test_results = []
        
        # AI Workload Test Configurations
        self.ai_workloads = [
            AIWorkloadTest(
                endpoint="/api/v1/generate/text",
                model_type="text_generation",
                input_data={"prompt": "Generate a creative story about AI", "max_tokens": 100},
                expected_response_time=2.0,
                max_error_rate=0.05
            ),
            AIWorkloadTest(
                endpoint="/api/v1/generate/image",
                model_type="image_generation",
                input_data={"prompt": "A futuristic cityscape", "steps": 20},
                expected_response_time=15.0,
                max_error_rate=0.10
            ),
            AIWorkloadTest(
                endpoint="/api/v1/analyze/image",
                model_type="image_analysis",
                input_data={"image_url": "https://example.com/test.jpg"},
                expected_response_time=3.0,
                max_error_rate=0.03
            )
        ]
    
    async def make_request(self, session: aiohttp.ClientSession, workload: AIWorkloadTest) -> Dict:
        """Make a single API request and measure performance"""
        start_time = time.time()
        
        try:
            async with session.post(
                f"{self.base_url}{workload.endpoint}",
                json=workload.input_data,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                await response.read()
                end_time = time.time()
                
                return {
                    'success': response.status == 200,
                    'response_time': end_time - start_time,
                    'status_code': response.status,
                    'workload_type': workload.model_type
                }
                
        except Exception as e:
            end_time = time.time()
            logger.error(f"Request failed: {e}")
            return {
                'success': False,
                'response_time': end_time - start_time,
                'status_code': 0,
                'workload_type': workload.model_type,
                'error': str(e)
            }
    
    async def concurrent_load_test(self, concurrent_users: int) -> LoadTestMetrics:
        """Run concurrent load test with specified user count"""
        logger.info(f"Starting load test with {concurrent_users} concurrent users")
        
        # Start GPU monitoring
        monitor_task = asyncio.create_task(self.gpu_monitor.start_monitoring())
        
        start_time = time.time()
        all_results = []
        
        # Create HTTP session with connection pooling
        connector = aiohttp.TCPConnector(limit=concurrent_users * 2)
        async with aiohttp.ClientSession(connector=connector) as session:
            
            # Run for specified duration
            while time.time() - start_time < self.test_duration:
                # Create tasks for concurrent users
                tasks = []
                for _ in range(concurrent_users):
                    # Randomly select workload type
                    workload = self.ai_workloads[len(all_results) % len(self.ai_workloads)]
                    task = asyncio.create_task(self.make_request(session, workload))
                    tasks.append(task)
                
                # Wait for all requests to complete
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results
                for result in batch_results:
                    if isinstance(result, dict):
                        all_results.append(result)
                
                # Small delay to prevent overwhelming the system
                await asyncio.sleep(0.1)
        
        # Stop GPU monitoring
        self.gpu_monitor.stop_monitoring()
        monitor_task.cancel()
        
        # Calculate metrics
        return self._calculate_metrics(all_results, concurrent_users)
    
    def _calculate_metrics(self, results: List[Dict], concurrent_users: int) -> LoadTestMetrics:
        """Calculate comprehensive load test metrics"""
        
        if not results:
            return LoadTestMetrics(
                timestamp=datetime.now().isoformat(),
                concurrent_users=concurrent_users,
                requests_per_second=0,
                avg_response_time=0,
                p95_response_time=0,
                p99_response_time=0,
                error_rate=1.0,
                cpu_usage=0,
                memory_usage=0,
                gpu_usage=0,
                gpu_memory_usage=0,
                successful_requests=0,
                failed_requests=0,
                total_requests=0
            )
        
        # Response time analysis
        response_times = [r['response_time'] for r in results]
        successful_requests = len([r for r in results if r['success']])
        failed_requests = len(results) - successful_requests
        
        # Calculate percentiles
        response_times.sort()
        p95_index = int(0.95 * len(response_times))
        p99_index = int(0.99 * len(response_times))
        
        # System resource usage
        cpu_usage = psutil.cpu_percent()
        memory_info = psutil.virtual_memory()
        memory_usage = memory_info.percent
        
        # GPU usage
        gpu_usage, gpu_memory = self.gpu_monitor.get_average_usage()
        
        return LoadTestMetrics(
            timestamp=datetime.now().isoformat(),
            concurrent_users=concurrent_users,
            requests_per_second=len(results) / self.test_duration,
            avg_response_time=statistics.mean(response_times),
            p95_response_time=response_times[p95_index] if response_times else 0,
            p99_response_time=response_times[p99_index] if response_times else 0,
            error_rate=failed_requests / len(results),
            cpu_usage=cpu_usage,
            memory_usage=memory_usage,
            gpu_usage=gpu_usage,
            gpu_memory_usage=gpu_memory,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            total_requests=len(results)
        )
    
    async def run_scalability_test(self, user_levels: List[int]) -> List[LoadTestMetrics]:
        """Run scalability test across different user levels"""
        logger.info(f"Starting scalability test with user levels: {user_levels}")
        
        results = []
        for user_count in user_levels:
            logger.info(f"Testing with {user_count} concurrent users")
            
            # Wait for system to stabilize
            await asyncio.sleep(10)
            
            # Run load test
            metrics = await self.concurrent_load_test(user_count)
            results.append(metrics)
            
            # Log results
            logger.info(f"Users: {user_count}, RPS: {metrics.requests_per_second:.2f}, "
                       f"Avg Response: {metrics.avg_response_time:.2f}s, "
                       f"Error Rate: {metrics.error_rate:.2%}")
        
        return results
    
    def generate_performance_report(self, results: List[LoadTestMetrics]) -> str:
        """Generate comprehensive performance report"""
        
        report = []
        report.append("=" * 80)
        report.append("GAMEFORGE AI - LOAD TESTING PERFORMANCE REPORT")
        report.append("=" * 80)
        report.append("")
        
        # Summary table
        report.append("SCALABILITY TEST RESULTS:")
        report.append("-" * 80)
        report.append(f"{'Users':<8} {'RPS':<8} {'Avg RT':<8} {'P95 RT':<8} {'P99 RT':<8} {'Error%':<8} {'CPU%':<8} {'GPU%':<8}")
        report.append("-" * 80)
        
        for metrics in results:
            report.append(
                f"{metrics.concurrent_users:<8} "
                f"{metrics.requests_per_second:<8.1f} "
                f"{metrics.avg_response_time:<8.2f} "
                f"{metrics.p95_response_time:<8.2f} "
                f"{metrics.p99_response_time:<8.2f} "
                f"{metrics.error_rate:<8.1%} "
                f"{metrics.cpu_usage:<8.1f} "
                f"{metrics.gpu_usage:<8.1f}"
            )
        
        report.append("")
        
        # Performance analysis
        report.append("PERFORMANCE ANALYSIS:")
        report.append("-" * 40)
        
        max_rps = max(r.requests_per_second for r in results)
        max_rps_users = next(r.concurrent_users for r in results if r.requests_per_second == max_rps)
        
        report.append(f"• Maximum RPS: {max_rps:.1f} at {max_rps_users} users")
        
        # Find performance limits
        acceptable_results = [r for r in results if r.error_rate < 0.05 and r.p95_response_time < 10.0]
        if acceptable_results:
            max_acceptable_users = max(r.concurrent_users for r in acceptable_results)
            report.append(f"• Recommended max concurrent users: {max_acceptable_users}")
        
        # Resource utilization
        max_cpu = max(r.cpu_usage for r in results)
        max_gpu = max(r.gpu_usage for r in results)
        report.append(f"• Peak CPU usage: {max_cpu:.1f}%")
        report.append(f"• Peak GPU usage: {max_gpu:.1f}%")
        
        report.append("")
        
        # Recommendations
        report.append("SCALING RECOMMENDATIONS:")
        report.append("-" * 30)
        
        if max_cpu > 80:
            report.append("• CPU bottleneck detected - consider CPU scaling")
        if max_gpu > 85:
            report.append("• GPU bottleneck detected - consider GPU scaling")
        
        high_error_tests = [r for r in results if r.error_rate > 0.10]
        if high_error_tests:
            min_error_users = min(r.concurrent_users for r in high_error_tests)
            report.append(f"• Error rate increases significantly at {min_error_users}+ users")
        
        return "\n".join(report)
    
    def save_results_to_json(self, results: List[LoadTestMetrics], filename: str):
        """Save results to JSON file"""
        with open(filename, 'w') as f:
            json.dump([asdict(result) for result in results], f, indent=2)
        logger.info(f"Results saved to {filename}")
    
    def generate_performance_charts(self, results: List[LoadTestMetrics], output_dir: str = "load_test_charts"):
        """Generate performance visualization charts"""
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        # Prepare data
        users = [r.concurrent_users for r in results]
        rps = [r.requests_per_second for r in results]
        response_times = [r.avg_response_time for r in results]
        error_rates = [r.error_rate * 100 for r in results]
        cpu_usage = [r.cpu_usage for r in results]
        gpu_usage = [r.gpu_usage for r in results]
        
        # Create subplots
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
        
        # RPS vs Users
        ax1.plot(users, rps, 'b-o', linewidth=2, markersize=6)
        ax1.set_xlabel('Concurrent Users')
        ax1.set_ylabel('Requests Per Second')
        ax1.set_title('Throughput Scalability')
        ax1.grid(True, alpha=0.3)
        
        # Response Time vs Users
        ax2.plot(users, response_times, 'r-o', linewidth=2, markersize=6)
        ax2.set_xlabel('Concurrent Users')
        ax2.set_ylabel('Average Response Time (s)')
        ax2.set_title('Response Time Scalability')
        ax2.grid(True, alpha=0.3)
        
        # Error Rate vs Users
        ax3.plot(users, error_rates, 'orange', linewidth=2, marker='o', markersize=6)
        ax3.set_xlabel('Concurrent Users')
        ax3.set_ylabel('Error Rate (%)')
        ax3.set_title('Error Rate Analysis')
        ax3.grid(True, alpha=0.3)
        
        # Resource Usage
        ax4.plot(users, cpu_usage, 'g-o', label='CPU Usage (%)', linewidth=2, markersize=6)
        ax4.plot(users, gpu_usage, 'm-o', label='GPU Usage (%)', linewidth=2, markersize=6)
        ax4.set_xlabel('Concurrent Users')
        ax4.set_ylabel('Resource Usage (%)')
        ax4.set_title('Resource Utilization')
        ax4.legend()
        ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        chart_path = os.path.join(output_dir, 'load_test_performance.png')
        plt.savefig(chart_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Performance charts saved to {chart_path}")

async def main():
    """Main load testing execution"""
    parser = argparse.ArgumentParser(description='GameForge AI Load Testing Framework')
    parser.add_argument('--base-url', default='http://localhost:8080', help='Base URL for testing')
    parser.add_argument('--duration', type=int, default=300, help='Test duration in seconds')
    parser.add_argument('--max-users', type=int, default=100, help='Maximum concurrent users')
    parser.add_argument('--user-step', type=int, default=10, help='User increment step')
    parser.add_argument('--output-dir', default='load_test_results', help='Output directory')
    
    args = parser.parse_args()
    
    # Create output directory
    import os
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Initialize load tester
    load_tester = LoadTestRunner(args.base_url, args.duration)
    
    # Define user levels for scalability testing
    user_levels = list(range(1, args.max_users + 1, args.user_step))
    
    try:
        # Run scalability test
        logger.info("Starting comprehensive load testing...")
        results = await load_tester.run_scalability_test(user_levels)
        
        # Generate reports
        report = load_tester.generate_performance_report(results)
        print(report)
        
        # Save results
        results_file = os.path.join(args.output_dir, 'load_test_results.json')
        load_tester.save_results_to_json(results, results_file)
        
        # Save report
        report_file = os.path.join(args.output_dir, 'load_test_report.txt')
        with open(report_file, 'w') as f:
            f.write(report)
        
        # Generate charts
        load_tester.generate_performance_charts(results, args.output_dir)
        
        logger.info(f"Load testing complete. Results saved to {args.output_dir}")
        
        # Determine if performance is acceptable
        max_error_rate = max(r.error_rate for r in results)
        max_response_time = max(r.p95_response_time for r in results)
        
        if max_error_rate > 0.10:
            logger.error("PERFORMANCE ISSUE: High error rate detected")
            sys.exit(1)
        elif max_response_time > 30.0:
            logger.error("PERFORMANCE ISSUE: High response times detected")
            sys.exit(1)
        else:
            logger.info("PERFORMANCE VALIDATION: All tests passed")
            sys.exit(0)
            
    except Exception as e:
        logger.error(f"Load testing failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())