"""
Health Check and Monitoring for Production Deployments
Real-time system metrics and status endpoints
"""

import logging
import psutil
import asyncio
import json
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import asdict

logger = logging.getLogger(__name__)


class HealthCheck:
    """
    Comprehensive health check for the video processing system
    Monitors CPU, memory, disk, FFmpeg availability, and queue status
    """
    
    def __init__(self, critical_thresholds: Optional[Dict[str, float]] = None):
        self.critical_thresholds = critical_thresholds or {
            'cpu_percent': 90.0,
            'memory_percent': 85.0,
            'disk_percent': 90.0,
        }
        self.status_history = []
        self.max_history = 100  # Keep last 100 checks
        
        logger.info("✓ Health check system initialized")
    
    async def check_system(self) -> Dict[str, Any]:
        """Perform comprehensive system health check"""
        
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Check FFmpeg availability
            ffmpeg_available = await self._check_ffmpeg()
            
            # Determine overall status
            status = "healthy"
            warnings = []
            
            if cpu_percent > self.critical_thresholds['cpu_percent']:
                status = "degraded"
                warnings.append(f"High CPU: {cpu_percent:.1f}%")
            
            if memory.percent > self.critical_thresholds['memory_percent']:
                status = "degraded"
                warnings.append(f"High memory: {memory.percent:.1f}%")
            
            if disk.percent > self.critical_thresholds['disk_percent']:
                status = "critical"
                warnings.append(f"Low disk space: {disk.percent:.1f}%")
            
            if not ffmpeg_available:
                status = "critical"
                warnings.append("FFmpeg not available")
            
            result = {
                'timestamp': datetime.now().isoformat(),
                'status': status,
                'system': {
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory.percent,
                    'memory_available_mb': memory.available / (1024 ** 2),
                    'disk_percent': disk.percent,
                    'disk_free_gb': disk.free / (1024 ** 3),
                },
                'services': {
                    'ffmpeg_available': ffmpeg_available,
                },
                'warnings': warnings,
            }
            
            # Store in history
            self.status_history.append(result)
            if len(self.status_history) > self.max_history:
                self.status_history.pop(0)
            
            return result
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'status': 'error',
                'error': str(e),
            }
    
    async def _check_ffmpeg(self) -> bool:
        """Check if FFmpeg and ffprobe are available"""
        try:
            import subprocess
            
            # Check ffmpeg
            result = subprocess.run(
                ['ffmpeg', '-version'],
                capture_output=True,
                timeout=5
            )
            ffmpeg_ok = result.returncode == 0
            
            # Check ffprobe
            result = subprocess.run(
                ['ffprobe', '-version'],
                capture_output=True,
                timeout=5
            )
            ffprobe_ok = result.returncode == 0
            
            return ffmpeg_ok and ffprobe_ok
        except:
            return False
    
    async def get_queue_stats(self, job_queue) -> Dict[str, Any]:
        """Get job queue statistics"""
        try:
            metrics = job_queue.get_metrics()
            return {
                'queue_size': metrics.get('queue_size', 0),
                'active_jobs': metrics.get('active_jobs', 0),
                'completed_jobs': metrics.get('completed_jobs', 0),
                'failed_jobs': metrics.get('failed_jobs', 0),
                'success_rate': f"{metrics.get('success_rate', 0):.1f}%",
                'avg_processing_time_seconds': f"{metrics.get('avg_processing_time', 0):.1f}",
                'total_jobs_processed': metrics.get('total_jobs', 0),
            }
        except Exception as e:
            logger.error(f"Could not get queue stats: {e}")
            return {'error': str(e)}
    
    def get_history(self, limit: int = 10) -> list:
        """Get recent health check history"""
        return self.status_history[-limit:]


class PerformanceMonitor:
    """Track performance metrics over time for optimization"""
    
    def __init__(self):
        self.metrics = {
            'video_processing': {
                'total': 0,
                'successful': 0,
                'failed': 0,
                'avg_duration': 0,
                'total_duration': 0,
            },
            'image_processing': {
                'total': 0,
                'successful': 0,
                'failed': 0,
                'avg_duration': 0,
                'total_duration': 0,
            },
            'queue': {
                'max_queue_size': 0,
                'max_active_jobs': 0,
                'avg_wait_time': 0,
            }
        }
        logger.info("✓ Performance monitor initialized")
    
    def record_video_processing(self, duration: float, success: bool):
        """Record video processing metrics"""
        metric = self.metrics['video_processing']
        metric['total'] += 1
        
        if success:
            metric['successful'] += 1
        else:
            metric['failed'] += 1
        
        metric['total_duration'] += duration
        metric['avg_duration'] = (
            metric['total_duration'] / metric['successful']
            if metric['successful'] > 0 else 0
        )
    
    def record_image_processing(self, duration: float, success: bool):
        """Record image processing metrics"""
        metric = self.metrics['image_processing']
        metric['total'] += 1
        
        if success:
            metric['successful'] += 1
        else:
            metric['failed'] += 1
        
        metric['total_duration'] += duration
        metric['avg_duration'] = (
            metric['total_duration'] / metric['successful']
            if metric['successful'] > 0 else 0
        )
    
    def get_report(self) -> Dict[str, Any]:
        """Get performance report"""
        return {
            'timestamp': datetime.now().isoformat(),
            'metrics': self.metrics,
            'uptime_hours': 0,  # Would need to track start time
        }


class MetricsExporter:
    """Export metrics in various formats for monitoring tools"""
    
    @staticmethod
    def to_prometheus_format(health: Dict[str, Any]) -> str:
        """Export metrics in Prometheus format"""
        lines = [
            '# HELP video_editor_system_health System health status',
            '# TYPE video_editor_system_health gauge',
        ]
        
        system = health.get('system', {})
        lines.append(f'video_editor_cpu_percent {system.get("cpu_percent", 0)}')
        lines.append(f'video_editor_memory_percent {system.get("memory_percent", 0)}')
        lines.append(f'video_editor_disk_percent {system.get("disk_percent", 0)}')
        
        return '\n'.join(lines)
    
    @staticmethod
    def to_json(health: Dict[str, Any]) -> str:
        """Export metrics as JSON"""
        return json.dumps(health, indent=2)


# Global instances
health_check: Optional[HealthCheck] = None
performance_monitor: Optional[PerformanceMonitor] = None


async def init_monitoring() -> tuple[HealthCheck, PerformanceMonitor]:
    """Initialize monitoring systems"""
    global health_check, performance_monitor
    
    health_check = HealthCheck()
    performance_monitor = PerformanceMonitor()
    
    logger.info("✓ All monitoring systems initialized")
    return health_check, performance_monitor


async def get_health_check() -> HealthCheck:
    """Get global health check instance"""
    global health_check
    if health_check is None:
        health_check, _ = await init_monitoring()
    return health_check


async def get_performance_monitor() -> PerformanceMonitor:
    """Get global performance monitor instance"""
    global performance_monitor
    if performance_monitor is None:
        _, performance_monitor = await init_monitoring()
    return performance_monitor
