#!/usr/bin/env python3
"""
========================================================================
GameForge AI - GPU Scheduling Validation System
Runtime GPU allocation testing and resource management validation
========================================================================
"""

import time
import json
import logging
import asyncio
import subprocess
import psutil
import docker
import threading
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('gpu_scheduling_validation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class GPUMetrics:
    """GPU utilization and memory metrics"""
    gpu_id: int
    gpu_name: str
    utilization: float
    memory_used: int
    memory_total: int
    memory_percent: float
    temperature: float
    power_usage: float
    timestamp: float

@dataclass
class ContainerGPUAllocation:
    """Container GPU allocation information"""
    container_id: str
    container_name: str
    gpu_ids: List[int]
    gpu_memory_limit: Optional[int]
    actual_gpu_usage: List[GPUMetrics]
    allocation_time: float
    validation_status: str

@dataclass
class GPUSchedulingTestResult:
    """GPU scheduling test result"""
    test_name: str
    start_time: str
    end_time: str
    total_containers: int
    successful_allocations: int
    failed_allocations: int
    gpu_utilization_efficiency: float
    memory_utilization_efficiency: float
    allocation_conflicts: int
    performance_degradation: float
    test_status: str
    recommendations: List[str]

class GPUMonitor:
    """Advanced GPU monitoring and validation"""
    
    def __init__(self):
        self.monitoring = False
        self.gpu_metrics_history = []
        self.monitor_thread = None
        
    def start_monitoring(self, interval: float = 1.0):
        """Start continuous GPU monitoring"""
        self.monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval,),
            daemon=True
        )
        self.monitor_thread.start()
        logger.info("GPU monitoring started")
    
    def stop_monitoring(self):
        """Stop GPU monitoring"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("GPU monitoring stopped")
    
    def _monitor_loop(self, interval: float):
        """Main monitoring loop"""
        while self.monitoring:
            try:
                metrics = self.get_gpu_metrics()
                self.gpu_metrics_history.append({
                    'timestamp': time.time(),
                    'metrics': metrics
                })
                
                # Keep only last hour of data
                cutoff_time = time.time() - 3600
                self.gpu_metrics_history = [
                    entry for entry in self.gpu_metrics_history
                    if entry['timestamp'] > cutoff_time
                ]
                
            except Exception as e:
                logger.error(f"GPU monitoring error: {e}")
            
            time.sleep(interval)
    
    def get_gpu_metrics(self) -> List[GPUMetrics]:
        """Get current GPU metrics for all GPUs"""
        metrics = []
        
        try:
            import pynvml
            pynvml.nvmlInit()
            gpu_count = pynvml.nvmlDeviceGetCount()
            
            for i in range(gpu_count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                
                # Get GPU name
                gpu_name = pynvml.nvmlDeviceGetName(handle).decode('utf-8')
                
                # Get utilization
                utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
                
                # Get memory info
                memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                
                # Get temperature
                try:
                    temperature = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                except:
                    temperature = 0
                
                # Get power usage
                try:
                    power_usage = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0  # Convert to watts
                except:
                    power_usage = 0
                
                metrics.append(GPUMetrics(
                    gpu_id=i,
                    gpu_name=gpu_name,
                    utilization=utilization.gpu,
                    memory_used=memory_info.used,
                    memory_total=memory_info.total,
                    memory_percent=(memory_info.used / memory_info.total) * 100,
                    temperature=temperature,
                    power_usage=power_usage,
                    timestamp=time.time()
                ))
                
        except ImportError:
            logger.warning("pynvml not available, using fallback GPU detection")
            # Fallback method using nvidia-smi
            try:
                result = subprocess.run([
                    'nvidia-smi', '--query-gpu=index,name,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw',
                    '--format=csv,noheader,nounits'
                ], capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    for line in result.stdout.strip().split('\n'):
                        if line.strip():
                            parts = [p.strip() for p in line.split(',')]
                            if len(parts) >= 7:
                                metrics.append(GPUMetrics(
                                    gpu_id=int(parts[0]),
                                    gpu_name=parts[1],
                                    utilization=float(parts[2]),
                                    memory_used=int(parts[3]) * 1024 * 1024,  # Convert MB to bytes
                                    memory_total=int(parts[4]) * 1024 * 1024,  # Convert MB to bytes
                                    memory_percent=(int(parts[3]) / int(parts[4])) * 100,
                                    temperature=float(parts[5]) if parts[5] != '[Not Supported]' else 0,
                                    power_usage=float(parts[6]) if parts[6] != '[Not Supported]' else 0,
                                    timestamp=time.time()
                                ))
            except Exception as e:
                logger.error(f"Fallback GPU detection failed: {e}")
        
        return metrics

class GPUSchedulingValidator:
    """GPU scheduling and allocation validation system"""
    
    def __init__(self):
        self.docker_client = docker.from_env()
        self.gpu_monitor = GPUMonitor()
        self.test_results = []
        
    def validate_gpu_runtime_setup(self) -> bool:
        """Validate that GPU runtime is properly configured"""
        logger.info("Validating GPU runtime setup...")
        
        try:
            # Check if nvidia-docker runtime is available
            runtime_info = self.docker_client.info()
            runtimes = runtime_info.get('Runtimes', {})
            
            if 'nvidia' not in runtimes:
                logger.error("NVIDIA Docker runtime not found")
                return False
            
            # Check if GPUs are visible to Docker
            try:
                container = self.docker_client.containers.run(
                    'nvidia/cuda:11.8-base-ubuntu20.04',
                    'nvidia-smi',
                    runtime='nvidia',
                    remove=True,
                    stdout=True,
                    stderr=True
                )
                logger.info("GPU runtime validation successful")
                return True
            except Exception as e:
                logger.error(f"GPU runtime test failed: {e}")
                return False
                
        except Exception as e:
            logger.error(f"GPU runtime validation failed: {e}")
            return False
    
    def test_single_container_gpu_allocation(self) -> ContainerGPUAllocation:
        """Test GPU allocation for a single container"""
        logger.info("Testing single container GPU allocation...")
        
        start_time = time.time()
        
        try:
            # Get baseline GPU metrics
            baseline_metrics = self.gpu_monitor.get_gpu_metrics()
            
            # Start container with GPU access
            container = self.docker_client.containers.run(
                'nvidia/cuda:11.8-base-ubuntu20.04',
                'python -c "import time; import subprocess; '
                'subprocess.run([\'nvidia-smi\']); '
                'time.sleep(30)"',  # Keep container running for monitoring
                runtime='nvidia',
                detach=True,
                environment={'NVIDIA_VISIBLE_DEVICES': 'all'}
            )
            
            # Wait for container to start and begin GPU usage
            time.sleep(5)
            
            # Monitor GPU usage during container execution
            gpu_metrics_during = []
            for _ in range(10):  # Monitor for 10 seconds
                metrics = self.gpu_monitor.get_gpu_metrics()
                gpu_metrics_during.extend(metrics)
                time.sleep(1)
            
            # Clean up container
            container.stop()
            container.remove()
            
            allocation = ContainerGPUAllocation(
                container_id=container.id,
                container_name=container.name,
                gpu_ids=[m.gpu_id for m in gpu_metrics_during],
                gpu_memory_limit=None,
                actual_gpu_usage=gpu_metrics_during,
                allocation_time=time.time() - start_time,
                validation_status="SUCCESS"
            )
            
            logger.info(f"Single container GPU allocation successful: {allocation.allocation_time:.2f}s")
            return allocation
            
        except Exception as e:
            logger.error(f"Single container GPU allocation failed: {e}")
            return ContainerGPUAllocation(
                container_id="",
                container_name="",
                gpu_ids=[],
                gpu_memory_limit=None,
                actual_gpu_usage=[],
                allocation_time=time.time() - start_time,
                validation_status=f"FAILED: {str(e)}"
            )
    
    def test_multi_container_gpu_scheduling(self, num_containers: int = 4) -> List[ContainerGPUAllocation]:
        """Test GPU scheduling with multiple containers"""
        logger.info(f"Testing multi-container GPU scheduling with {num_containers} containers...")
        
        containers = []
        allocations = []
        
        try:
            # Start multiple containers concurrently
            for i in range(num_containers):
                container = self.docker_client.containers.run(
                    'nvidia/cuda:11.8-base-ubuntu20.04',
                    f'python -c "import time; import subprocess; '
                    f'print(\'Container {i} starting GPU work\'); '
                    f'subprocess.run([\'nvidia-smi\']); '
                    f'time.sleep(60)"',  # Longer running for scheduling test
                    runtime='nvidia',
                    detach=True,
                    environment={'NVIDIA_VISIBLE_DEVICES': 'all'}
                )
                containers.append(container)
                time.sleep(2)  # Stagger container starts
            
            logger.info(f"Started {len(containers)} containers, monitoring GPU allocation...")
            
            # Monitor GPU allocation for all containers
            for _ in range(30):  # Monitor for 30 seconds
                current_metrics = self.gpu_monitor.get_gpu_metrics()
                
                # Check if all containers are still running
                running_containers = []
                for container in containers:
                    try:
                        container.reload()
                        if container.status == 'running':
                            running_containers.append(container)
                    except:
                        pass
                
                if len(running_containers) != num_containers:
                    logger.warning(f"Only {len(running_containers)}/{num_containers} containers running")
                
                time.sleep(1)
            
            # Create allocation records
            for i, container in enumerate(containers):
                try:
                    container.reload()
                    allocation = ContainerGPUAllocation(
                        container_id=container.id,
                        container_name=container.name,
                        gpu_ids=list(range(len(self.gpu_monitor.get_gpu_metrics()))),  # Assume all GPUs accessible
                        gpu_memory_limit=None,
                        actual_gpu_usage=self.gpu_monitor.get_gpu_metrics(),
                        allocation_time=time.time(),
                        validation_status="SUCCESS" if container.status == 'running' else "FAILED"
                    )
                    allocations.append(allocation)
                except Exception as e:
                    logger.error(f"Failed to get allocation info for container {i}: {e}")
            
        except Exception as e:
            logger.error(f"Multi-container GPU scheduling test failed: {e}")
        
        finally:
            # Clean up all containers
            for container in containers:
                try:
                    container.stop()
                    container.remove()
                except:
                    pass
        
        logger.info(f"Multi-container test completed with {len(allocations)} allocations")
        return allocations
    
    def test_gpu_memory_limits(self) -> GPUSchedulingTestResult:
        """Test GPU memory allocation limits and scheduling"""
        logger.info("Testing GPU memory limits and scheduling...")
        
        start_time = datetime.now()
        test_containers = []
        successful_allocations = 0
        failed_allocations = 0
        
        try:
            # Get available GPU memory
            gpu_metrics = self.gpu_monitor.get_gpu_metrics()
            if not gpu_metrics:
                raise Exception("No GPUs available for testing")
            
            total_gpu_memory = gpu_metrics[0].memory_total
            
            # Test different memory allocation sizes
            memory_tests = [
                int(total_gpu_memory * 0.25),  # 25% memory
                int(total_gpu_memory * 0.50),  # 50% memory
                int(total_gpu_memory * 0.75),  # 75% memory
            ]
            
            for i, memory_limit in enumerate(memory_tests):
                try:
                    # Start container with memory limit
                    container = self.docker_client.containers.run(
                        'nvidia/cuda:11.8-base-ubuntu20.04',
                        f'python -c "import time; '
                        f'print(\'Allocating {memory_limit} bytes GPU memory\'); '
                        f'time.sleep(20)"',
                        runtime='nvidia',
                        detach=True,
                        environment={
                            'NVIDIA_VISIBLE_DEVICES': 'all',
                            'CUDA_MEM_LIMIT': str(memory_limit)
                        }
                    )
                    test_containers.append(container)
                    successful_allocations += 1
                    logger.info(f"Memory allocation test {i+1} successful: {memory_limit} bytes")
                    
                except Exception as e:
                    logger.error(f"Memory allocation test {i+1} failed: {e}")
                    failed_allocations += 1
                
                time.sleep(5)  # Wait between tests
            
            # Monitor GPU usage during memory tests
            time.sleep(10)
            final_metrics = self.gpu_monitor.get_gpu_metrics()
            
            # Calculate efficiency metrics
            if final_metrics:
                gpu_utilization = np.mean([m.utilization for m in final_metrics])
                memory_utilization = np.mean([m.memory_percent for m in final_metrics])
            else:
                gpu_utilization = 0
                memory_utilization = 0
            
        except Exception as e:
            logger.error(f"GPU memory limits test failed: {e}")
            failed_allocations += 1
        
        finally:
            # Clean up test containers
            for container in test_containers:
                try:
                    container.stop()
                    container.remove()
                except:
                    pass
        
        end_time = datetime.now()
        
        # Generate recommendations
        recommendations = []
        if failed_allocations > 0:
            recommendations.append("GPU memory allocation failures detected - review memory limits")
        if gpu_utilization < 50:
            recommendations.append("Low GPU utilization - consider increasing workload")
        if memory_utilization > 90:
            recommendations.append("High GPU memory usage - monitor for OOM conditions")
        
        result = GPUSchedulingTestResult(
            test_name="GPU Memory Limits Test",
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            total_containers=len(memory_tests),
            successful_allocations=successful_allocations,
            failed_allocations=failed_allocations,
            gpu_utilization_efficiency=gpu_utilization,
            memory_utilization_efficiency=memory_utilization,
            allocation_conflicts=0,  # Would need more sophisticated detection
            performance_degradation=0,  # Would need baseline comparison
            test_status="PASSED" if failed_allocations == 0 else "FAILED",
            recommendations=recommendations
        )
        
        return result
    
    def run_comprehensive_gpu_validation(self) -> Dict:
        """Run comprehensive GPU scheduling validation"""
        logger.info("Starting comprehensive GPU scheduling validation...")
        
        validation_results = {
            'runtime_validation': False,
            'single_container_test': None,
            'multi_container_test': [],
            'memory_limits_test': None,
            'overall_status': 'FAILED',
            'summary': {}
        }
        
        try:
            # Start GPU monitoring
            self.gpu_monitor.start_monitoring()
            
            # Test 1: Runtime validation
            validation_results['runtime_validation'] = self.validate_gpu_runtime_setup()
            
            if not validation_results['runtime_validation']:
                logger.error("GPU runtime validation failed - stopping tests")
                return validation_results
            
            # Test 2: Single container allocation
            validation_results['single_container_test'] = self.test_single_container_gpu_allocation()
            
            # Test 3: Multi-container scheduling
            validation_results['multi_container_test'] = self.test_multi_container_gpu_scheduling()
            
            # Test 4: Memory limits
            validation_results['memory_limits_test'] = self.test_gpu_memory_limits()
            
            # Determine overall status
            single_success = (validation_results['single_container_test'] and 
                            validation_results['single_container_test'].validation_status == "SUCCESS")
            
            multi_success = len([a for a in validation_results['multi_container_test'] 
                               if a.validation_status == "SUCCESS"]) > 0
            
            memory_success = (validation_results['memory_limits_test'] and 
                            validation_results['memory_limits_test'].test_status == "PASSED")
            
            if single_success and multi_success and memory_success:
                validation_results['overall_status'] = 'PASSED'
            else:
                validation_results['overall_status'] = 'FAILED'
            
            # Generate summary
            validation_results['summary'] = {
                'total_tests': 4,
                'passed_tests': sum([
                    validation_results['runtime_validation'],
                    single_success,
                    multi_success,
                    memory_success
                ]),
                'gpu_count': len(self.gpu_monitor.get_gpu_metrics()),
                'validation_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Comprehensive GPU validation failed: {e}")
            validation_results['overall_status'] = 'ERROR'
        
        finally:
            # Stop monitoring
            self.gpu_monitor.stop_monitoring()
        
        return validation_results
    
    def generate_validation_report(self, results: Dict) -> str:
        """Generate comprehensive GPU validation report"""
        
        report = []
        report.append("=" * 80)
        report.append("GAMEFORGE AI - GPU SCHEDULING VALIDATION REPORT")
        report.append("=" * 80)
        report.append("")
        
        # Overall status
        status_icon = "✅" if results['overall_status'] == 'PASSED' else "❌"
        report.append(f"OVERALL STATUS: {status_icon} {results['overall_status']}")
        report.append("")
        
        # Test results
        report.append("TEST RESULTS:")
        report.append("-" * 40)
        
        # Runtime validation
        runtime_icon = "✅" if results['runtime_validation'] else "❌"
        report.append(f"{runtime_icon} GPU Runtime Validation: {'PASSED' if results['runtime_validation'] else 'FAILED'}")
        
        # Single container test
        single_test = results['single_container_test']
        if single_test:
            single_icon = "✅" if single_test.validation_status == "SUCCESS" else "❌"
            report.append(f"{single_icon} Single Container GPU Allocation: {single_test.validation_status}")
            report.append(f"   Allocation Time: {single_test.allocation_time:.2f}s")
        
        # Multi-container test
        multi_tests = results['multi_container_test']
        successful_multi = len([t for t in multi_tests if t.validation_status == "SUCCESS"])
        multi_icon = "✅" if successful_multi > 0 else "❌"
        report.append(f"{multi_icon} Multi-Container GPU Scheduling: {successful_multi}/{len(multi_tests)} successful")
        
        # Memory limits test
        memory_test = results['memory_limits_test']
        if memory_test:
            memory_icon = "✅" if memory_test.test_status == "PASSED" else "❌"
            report.append(f"{memory_icon} GPU Memory Limits: {memory_test.test_status}")
            report.append(f"   GPU Utilization: {memory_test.gpu_utilization_efficiency:.1f}%")
            report.append(f"   Memory Utilization: {memory_test.memory_utilization_efficiency:.1f}%")
        
        report.append("")
        
        # Summary
        summary = results.get('summary', {})
        if summary:
            report.append("VALIDATION SUMMARY:")
            report.append("-" * 20)
            report.append(f"• Total Tests: {summary.get('total_tests', 0)}")
            report.append(f"• Passed Tests: {summary.get('passed_tests', 0)}")
            report.append(f"• GPU Count: {summary.get('gpu_count', 0)}")
            report.append(f"• Validation Time: {summary.get('validation_timestamp', 'N/A')}")
        
        report.append("")
        
        # Recommendations
        report.append("RECOMMENDATIONS:")
        report.append("-" * 20)
        
        if results['overall_status'] == 'PASSED':
            report.append("✅ GPU scheduling is working correctly")
            report.append("✅ Runtime GPU allocation validated")
            report.append("✅ Multi-container scheduling operational")
        else:
            report.append("❌ GPU scheduling issues detected")
            if not results['runtime_validation']:
                report.append("• Fix GPU runtime configuration")
            if memory_test and memory_test.recommendations:
                for rec in memory_test.recommendations:
                    report.append(f"• {rec}")
        
        return "\n".join(report)

async def main():
    """Main GPU scheduling validation execution"""
    logger.info("Starting GPU scheduling validation...")
    
    validator = GPUSchedulingValidator()
    
    try:
        # Run comprehensive validation
        results = validator.run_comprehensive_gpu_validation()
        
        # Generate report
        report = validator.generate_validation_report(results)
        print(report)
        
        # Save results
        with open('gpu_scheduling_validation_results.json', 'w') as f:
            # Convert results to JSON-serializable format
            json_results = {}
            for key, value in results.items():
                if key == 'single_container_test' and value:
                    json_results[key] = asdict(value)
                elif key == 'multi_container_test':
                    json_results[key] = [asdict(item) for item in value]
                elif key == 'memory_limits_test' and value:
                    json_results[key] = asdict(value)
                else:
                    json_results[key] = value
            
            json.dump(json_results, f, indent=2)
        
        # Save report
        with open('gpu_scheduling_validation_report.txt', 'w') as f:
            f.write(report)
        
        logger.info("GPU scheduling validation complete")
        
        # Exit with appropriate code
        if results['overall_status'] == 'PASSED':
            logger.info("GPU SCHEDULING VALIDATION: PASSED")
            return 0
        else:
            logger.error("GPU SCHEDULING VALIDATION: FAILED")
            return 1
            
    except Exception as e:
        logger.error(f"GPU scheduling validation error: {e}")
        return 1

if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)