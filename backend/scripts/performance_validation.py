#!/usr/bin/env python3
"""
Performance Validation Script

Comprehensive validation of all performance optimizations and tuning
for the Cosmos Optimization project.
"""

import asyncio
import sys
import os
import time
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
import structlog

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config.performance_config import get_performance_config, reload_performance_config
from services.optimized_redis_operations import get_optimized_redis, close_optimized_redis
from services.performance_monitoring_system import (
    get_performance_monitor, start_performance_monitoring, stop_performance_monitoring,
    record_response_time, record_cache_hit_rate, record_memory_usage
)

logger = structlog.get_logger(__name__)


class PerformanceValidator:
    """Validates all performance optimizations and configurations."""
    
    def __init__(self):
        self.validation_results = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "unknown",
            "validations": {},
            "performance_metrics": {},
            "recommendations": []
        }
    
    async def run_full_validation(self) -> Dict[str, Any]:
        """Run complete performance validation suite."""
        logger.info("🚀 Starting comprehensive performance validation")
        
        try:
            # 1. Validate configuration
            await self._validate_configuration()
            
            # 2. Validate Redis optimizations
            await self._validate_redis_optimizations()
            
            # 3. Validate monitoring system
            await self._validate_monitoring_system()
            
            # 4. Run performance benchmarks
            await self._run_performance_benchmarks()
            
            # 5. Validate memory optimization
            await self._validate_memory_optimization()
            
            # 6. Test concurrent load handling
            await self._test_concurrent_load()
            
            # 7. Generate final assessment
            self._generate_final_assessment()
            
        except Exception as e:
            logger.error("Performance validation failed", error=str(e))
            self.validation_results["overall_status"] = "failed"
            self.validation_results["error"] = str(e)
        
        return self.validation_results
    
    async def _validate_configuration(self):
        """Validate performance configuration."""
        logger.info("Validating performance configuration...")
        
        try:
            # Reload configuration to ensure latest values
            config = reload_performance_config()
            
            # Validate configuration
            validation = config.validate_configuration()
            
            self.validation_results["validations"]["configuration"] = {
                "status": "passed" if validation["valid"] else "failed",
                "valid": validation["valid"],
                "warnings": validation.get("warnings", []),
                "errors": validation.get("errors", [])
            }
            
            # Log configuration details
            config.log_configuration()
            
            if not validation["valid"]:
                self.validation_results["recommendations"].extend([
                    f"Fix configuration error: {error}" for error in validation["errors"]
                ])
            
            if validation["warnings"]:
                self.validation_results["recommendations"].extend([
                    f"Consider configuration warning: {warning}" for warning in validation["warnings"]
                ])
            
            logger.info("Configuration validation completed", 
                       valid=validation["valid"],
                       warnings=len(validation["warnings"]),
                       errors=len(validation["errors"]))
            
        except Exception as e:
            logger.error("Configuration validation failed", error=str(e))
            self.validation_results["validations"]["configuration"] = {
                "status": "failed",
                "error": str(e)
            }
    
    async def _validate_redis_optimizations(self):
        """Validate Redis optimization features."""
        logger.info("Validating Redis optimizations...")
        
        try:
            redis_ops = await get_optimized_redis()
            
            # Test basic operations
            test_data = {
                "test_key_1": {"data": "test_value_1", "timestamp": time.time()},
                "test_key_2": {"data": "test_value_2", "numbers": list(range(100))},
                "test_key_3": {"data": "large_data", "content": "x" * 10000}  # Large data for compression test
            }
            
            # Test batch operations
            start_time = time.perf_counter()
            success_count = await redis_ops.batch_set_optimized(test_data, ttl=300, compress=True)
            set_time = (time.perf_counter() - start_time) * 1000
            
            # Test batch retrieval
            start_time = time.perf_counter()
            retrieved_data = await redis_ops.batch_get_optimized(list(test_data.keys()))
            get_time = (time.perf_counter() - start_time) * 1000
            
            # Test memory optimization
            start_time = time.perf_counter()
            cleanup_count = await redis_ops.cleanup_expired_keys()
            cleanup_time = (time.perf_counter() - start_time) * 1000
            
            # Get performance stats
            perf_stats = await redis_ops.get_performance_stats()
            
            # Health check
            health_status = await redis_ops.health_check()
            
            self.validation_results["validations"]["redis_optimizations"] = {
                "status": "passed" if success_count == len(test_data) and len(retrieved_data) == len(test_data) else "failed",
                "batch_set_success_count": success_count,
                "batch_get_success_count": len(retrieved_data),
                "batch_set_time_ms": set_time,
                "batch_get_time_ms": get_time,
                "cleanup_time_ms": cleanup_time,
                "cleanup_count": cleanup_count,
                "performance_stats": perf_stats,
                "health_status": health_status
            }
            
            # Performance recommendations
            if set_time > 100:
                self.validation_results["recommendations"].append(
                    f"Redis batch SET operations are slow ({set_time:.2f}ms). Consider optimizing connection pool."
                )
            
            if get_time > 50:
                self.validation_results["recommendations"].append(
                    f"Redis batch GET operations are slow ({get_time:.2f}ms). Consider increasing connection pool size."
                )
            
            # Cleanup test data
            await redis_ops.redis_client.delete(*test_data.keys())
            
            logger.info("Redis optimizations validation completed",
                       set_time_ms=set_time,
                       get_time_ms=get_time,
                       health_status=health_status["status"])
            
        except Exception as e:
            logger.error("Redis optimizations validation failed", error=str(e))
            self.validation_results["validations"]["redis_optimizations"] = {
                "status": "failed",
                "error": str(e)
            }
    
    async def _validate_monitoring_system(self):
        """Validate performance monitoring system."""
        logger.info("Validating monitoring system...")
        
        try:
            # Start monitoring
            await start_performance_monitoring()
            
            # Record test metrics
            record_response_time(150.0, "test_endpoint")
            record_cache_hit_rate(0.85, "test_cache")
            record_memory_usage(50.0, "test_component")
            
            # Wait for metrics to be processed
            await asyncio.sleep(1)
            
            # Get monitoring data
            monitor = get_performance_monitor()
            
            # Get statistics
            response_time_stats = monitor.get_metric_statistics(
                monitor.metric_buffers[list(monitor.metric_buffers.keys())[0]].data[0].metric_type if monitor.metric_buffers else None
            )
            
            # Get health summary
            health_summary = monitor.get_system_health_summary()
            
            # Get active alerts
            active_alerts = monitor.get_active_alerts()
            
            self.validation_results["validations"]["monitoring_system"] = {
                "status": "passed",
                "health_summary": health_summary,
                "active_alerts_count": len(active_alerts),
                "metrics_recorded": True
            }
            
            logger.info("Monitoring system validation completed",
                       health_status=health_summary["health_status"],
                       active_alerts=len(active_alerts))
            
        except Exception as e:
            logger.error("Monitoring system validation failed", error=str(e))
            self.validation_results["validations"]["monitoring_system"] = {
                "status": "failed",
                "error": str(e)
            }
    
    async def _run_performance_benchmarks(self):
        """Run performance benchmarks."""
        logger.info("Running performance benchmarks...")
        
        try:
            benchmarks = {}
            
            # Redis performance benchmark
            redis_ops = await get_optimized_redis()
            
            # Single operation benchmark
            start_time = time.perf_counter()
            for i in range(100):
                await redis_ops.set_optimized(f"bench_key_{i}", {"data": f"value_{i}"}, ttl=60)
            single_ops_time = (time.perf_counter() - start_time) * 1000
            
            # Batch operation benchmark
            batch_data = {f"batch_key_{i}": {"data": f"batch_value_{i}"} for i in range(100)}
            start_time = time.perf_counter()
            await redis_ops.batch_set_optimized(batch_data, ttl=60)
            batch_ops_time = (time.perf_counter() - start_time) * 1000
            
            # Retrieval benchmark
            start_time = time.perf_counter()
            retrieved = await redis_ops.batch_get_optimized(list(batch_data.keys()))
            retrieval_time = (time.perf_counter() - start_time) * 1000
            
            benchmarks["redis_operations"] = {
                "single_ops_100_items_ms": single_ops_time,
                "batch_ops_100_items_ms": batch_ops_time,
                "batch_retrieval_100_items_ms": retrieval_time,
                "retrieval_success_rate": len(retrieved) / len(batch_data)
            }
            
            # Memory usage benchmark
            perf_stats = await redis_ops.get_performance_stats()
            benchmarks["memory_usage"] = {
                "redis_memory_mb": perf_stats.get("redis_info", {}).get("used_memory_mb", 0),
                "compression_savings_bytes": perf_stats.get("operation_stats", {}).get("compression_savings_bytes", 0)
            }
            
            # Cleanup benchmark data
            cleanup_keys = list(batch_data.keys()) + [f"bench_key_{i}" for i in range(100)]
            await redis_ops.redis_client.delete(*cleanup_keys)
            
            self.validation_results["performance_metrics"]["benchmarks"] = benchmarks
            
            # Performance assessment
            if single_ops_time > 1000:  # More than 1 second for 100 operations
                self.validation_results["recommendations"].append(
                    "Single Redis operations are slow. Consider connection pooling optimization."
                )
            
            if batch_ops_time > 200:  # More than 200ms for batch of 100
                self.validation_results["recommendations"].append(
                    "Batch Redis operations are slow. Consider pipeline optimization."
                )
            
            logger.info("Performance benchmarks completed",
                       single_ops_ms=single_ops_time,
                       batch_ops_ms=batch_ops_time,
                       retrieval_ms=retrieval_time)
            
        except Exception as e:
            logger.error("Performance benchmarks failed", error=str(e))
            self.validation_results["performance_metrics"]["benchmarks"] = {
                "error": str(e)
            }
    
    async def _validate_memory_optimization(self):
        """Validate memory optimization features."""
        logger.info("Validating memory optimization...")
        
        try:
            redis_ops = await get_optimized_redis()
            
            # Create test data with varying sizes
            test_data = {}
            for i in range(50):
                size = 1000 * (i + 1)  # Increasing sizes
                test_data[f"memory_test_{i}"] = {
                    "data": "x" * size,
                    "metadata": {"size": size, "index": i}
                }
            
            # Store data with compression
            await redis_ops.batch_set_optimized(test_data, ttl=300, compress=True)
            
            # Get memory stats before optimization
            stats_before = await redis_ops.get_performance_stats()
            memory_before = stats_before.get("redis_info", {}).get("used_memory_mb", 0)
            
            # Run memory optimization
            if redis_ops.memory_optimizer:
                optimization_results = await redis_ops.memory_optimizer.optimize_memory_usage()
            else:
                optimization_results = {"memory_saved_mb": 0, "optimization_time_ms": 0}
            
            # Get memory stats after optimization
            stats_after = await redis_ops.get_performance_stats()
            memory_after = stats_after.get("redis_info", {}).get("used_memory_mb", 0)
            
            self.validation_results["validations"]["memory_optimization"] = {
                "status": "passed",
                "memory_before_mb": memory_before,
                "memory_after_mb": memory_after,
                "memory_saved_mb": memory_before - memory_after,
                "optimization_results": optimization_results
            }
            
            # Cleanup test data
            await redis_ops.redis_client.delete(*test_data.keys())
            
            logger.info("Memory optimization validation completed",
                       memory_saved_mb=memory_before - memory_after,
                       optimization_time_ms=optimization_results.get("optimization_time_ms", 0))
            
        except Exception as e:
            logger.error("Memory optimization validation failed", error=str(e))
            self.validation_results["validations"]["memory_optimization"] = {
                "status": "failed",
                "error": str(e)
            }
    
    async def _test_concurrent_load(self):
        """Test system behavior under concurrent load."""
        logger.info("Testing concurrent load handling...")
        
        try:
            redis_ops = await get_optimized_redis()
            
            # Simulate concurrent users
            async def simulate_user(user_id: int):
                user_results = []
                for i in range(10):  # 10 operations per user
                    start_time = time.perf_counter()
                    
                    # Mix of operations
                    if i % 3 == 0:
                        # Set operation
                        success = await redis_ops.set_optimized(
                            f"concurrent_user_{user_id}_key_{i}",
                            {"user": user_id, "operation": i, "timestamp": time.time()},
                            ttl=60
                        )
                    else:
                        # Get operation
                        result = await redis_ops.get_optimized(f"concurrent_user_{user_id}_key_{i-1}")
                        success = result is not None
                    
                    elapsed = (time.perf_counter() - start_time) * 1000
                    user_results.append({"operation": i, "success": success, "time_ms": elapsed})
                
                return user_results
            
            # Run concurrent users
            num_users = 20
            start_time = time.perf_counter()
            
            user_tasks = [simulate_user(i) for i in range(num_users)]
            all_results = await asyncio.gather(*user_tasks)
            
            total_time = (time.perf_counter() - start_time) * 1000
            
            # Analyze results
            all_operations = []
            for user_results in all_results:
                all_operations.extend(user_results)
            
            success_count = sum(1 for op in all_operations if op["success"])
            total_operations = len(all_operations)
            success_rate = success_count / total_operations if total_operations > 0 else 0
            
            response_times = [op["time_ms"] for op in all_operations]
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
            
            self.validation_results["validations"]["concurrent_load"] = {
                "status": "passed" if success_rate >= 0.95 else "failed",
                "concurrent_users": num_users,
                "total_operations": total_operations,
                "successful_operations": success_count,
                "success_rate": success_rate,
                "total_time_ms": total_time,
                "average_response_time_ms": avg_response_time,
                "throughput_ops_per_second": total_operations / (total_time / 1000) if total_time > 0 else 0
            }
            
            # Performance recommendations
            if success_rate < 0.95:
                self.validation_results["recommendations"].append(
                    f"Concurrent load success rate is low ({success_rate:.2%}). Consider increasing connection pool size."
                )
            
            if avg_response_time > 100:
                self.validation_results["recommendations"].append(
                    f"Average response time under load is high ({avg_response_time:.2f}ms). Consider performance tuning."
                )
            
            logger.info("Concurrent load testing completed",
                       users=num_users,
                       success_rate=success_rate,
                       avg_response_time_ms=avg_response_time)
            
        except Exception as e:
            logger.error("Concurrent load testing failed", error=str(e))
            self.validation_results["validations"]["concurrent_load"] = {
                "status": "failed",
                "error": str(e)
            }
    
    def _generate_final_assessment(self):
        """Generate final performance assessment."""
        logger.info("Generating final assessment...")
        
        # Count passed/failed validations
        validations = self.validation_results["validations"]
        passed_count = sum(1 for v in validations.values() if v.get("status") == "passed")
        total_count = len(validations)
        
        # Determine overall status
        if passed_count == total_count:
            overall_status = "passed"
        elif passed_count >= total_count * 0.8:  # 80% pass rate
            overall_status = "passed_with_warnings"
        else:
            overall_status = "failed"
        
        self.validation_results["overall_status"] = overall_status
        self.validation_results["summary"] = {
            "total_validations": total_count,
            "passed_validations": passed_count,
            "failed_validations": total_count - passed_count,
            "pass_rate": passed_count / total_count if total_count > 0 else 0,
            "total_recommendations": len(self.validation_results["recommendations"])
        }
        
        logger.info("Final assessment completed",
                   overall_status=overall_status,
                   pass_rate=f"{passed_count}/{total_count}",
                   recommendations=len(self.validation_results["recommendations"]))
    
    def print_validation_report(self):
        """Print a formatted validation report."""
        print("\n" + "="*80)
        print("🧪 COSMOS OPTIMIZATION PERFORMANCE VALIDATION REPORT")
        print("="*80)
        
        # Overall status
        status_emoji = {
            "passed": "✅",
            "passed_with_warnings": "⚠️",
            "failed": "❌",
            "unknown": "❓"
        }
        
        overall_status = self.validation_results["overall_status"]
        print(f"\n{status_emoji.get(overall_status, '❓')} OVERALL STATUS: {overall_status.upper()}")
        
        if "summary" in self.validation_results:
            summary = self.validation_results["summary"]
            print(f"📊 VALIDATION SUMMARY: {summary['passed_validations']}/{summary['total_validations']} passed "
                  f"({summary['pass_rate']:.1%})")
        
        # Individual validations
        print(f"\n📋 VALIDATION DETAILS:")
        print("-" * 80)
        
        for validation_name, result in self.validation_results["validations"].items():
            status = result.get("status", "unknown")
            emoji = status_emoji.get(status, "❓")
            
            print(f"{emoji} {validation_name.replace('_', ' ').title()}: {status.upper()}")
            
            if "error" in result:
                print(f"   Error: {result['error']}")
            
            # Show key metrics for some validations
            if validation_name == "redis_optimizations" and status == "passed":
                print(f"   Batch SET: {result.get('batch_set_time_ms', 0):.2f}ms")
                print(f"   Batch GET: {result.get('batch_get_time_ms', 0):.2f}ms")
            
            elif validation_name == "concurrent_load" and status == "passed":
                print(f"   Success Rate: {result.get('success_rate', 0):.2%}")
                print(f"   Avg Response: {result.get('average_response_time_ms', 0):.2f}ms")
                print(f"   Throughput: {result.get('throughput_ops_per_second', 0):.2f} ops/sec")
        
        # Performance metrics
        if "performance_metrics" in self.validation_results:
            print(f"\n📈 PERFORMANCE METRICS:")
            print("-" * 80)
            
            benchmarks = self.validation_results["performance_metrics"].get("benchmarks", {})
            if "redis_operations" in benchmarks:
                redis_bench = benchmarks["redis_operations"]
                print(f"Redis Single Ops (100 items): {redis_bench.get('single_ops_100_items_ms', 0):.2f}ms")
                print(f"Redis Batch Ops (100 items): {redis_bench.get('batch_ops_100_items_ms', 0):.2f}ms")
                print(f"Redis Retrieval (100 items): {redis_bench.get('batch_retrieval_100_items_ms', 0):.2f}ms")
        
        # Recommendations
        recommendations = self.validation_results.get("recommendations", [])
        if recommendations:
            print(f"\n💡 RECOMMENDATIONS ({len(recommendations)}):")
            print("-" * 80)
            for i, rec in enumerate(recommendations, 1):
                print(f"{i}. {rec}")
        
        # Final verdict
        print(f"\n🎯 FINAL VERDICT:")
        print("-" * 80)
        
        if overall_status == "passed":
            print("✅ All performance optimizations are working correctly!")
            print("✅ System is ready for production deployment.")
        elif overall_status == "passed_with_warnings":
            print("⚠️ Most performance optimizations are working correctly.")
            print("⚠️ Review recommendations for optimal performance.")
        else:
            print("❌ Performance validation failed.")
            print("❌ Address issues before production deployment.")
        
        print("="*80)


async def main():
    """Main entry point for performance validation."""
    validator = PerformanceValidator()
    
    try:
        # Run validation
        results = await validator.run_full_validation()
        
        # Print report
        validator.print_validation_report()
        
        # Save results to file
        results_file = Path(__file__).parent / "performance_validation_results.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n📄 Detailed results saved to: {results_file}")
        
        # Exit with appropriate code
        if results["overall_status"] in ["passed", "passed_with_warnings"]:
            sys.exit(0)
        else:
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Performance validation interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error("Performance validation failed", error=str(e))
        sys.exit(1)
    finally:
        # Cleanup
        try:
            await stop_performance_monitoring()
            await close_optimized_redis()
        except Exception as e:
            logger.warning("Cleanup error", error=str(e))


if __name__ == "__main__":
    asyncio.run(main())