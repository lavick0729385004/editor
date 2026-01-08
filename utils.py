"""Utility functions for advanced processing - VPS optimized"""

import os
import psutil
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class SystemMonitor:
    """Monitor system resources"""
    
    @staticmethod
    def get_system_info():
        """Get current system resource usage"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                'cpu': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available_mb': memory.available / (1024 * 1024),
                'disk_free_gb': disk.free / (1024 * 1024 * 1024)
            }
        except Exception as e:
            logger.error(f"Error getting system info: {e}")
            return None
    
    @staticmethod
    def check_resources(min_memory_mb=500, min_disk_gb=5):
        """Check if system has minimum required resources"""
        try:
            info = SystemMonitor.get_system_info()
            if not info:
                return False
            
            has_memory = info['memory_available_mb'] > min_memory_mb
            has_disk = info['disk_free_gb'] > min_disk_gb
            
            logger.info(f"Resources - Memory: {info['memory_available_mb']:.0f}MB, "
                       f"Disk: {info['disk_free_gb']:.1f}GB")
            
            return has_memory and has_disk
            
        except Exception as e:
            logger.error(f"Error checking resources: {e}")
            return True  # Assume OK if check fails


class PerformanceOptimizer:
    """Optimize performance for VPS"""
    
    @staticmethod
    def optimize_for_cpu_cores():
        """Get optimal thread count based on CPU cores"""
        try:
            cores = os.cpu_count() or 4
            # Use max 4 threads, or cores-1 if less
            optimal = min(max(cores - 1, 2), 4)
            logger.info(f"CPU cores detected: {cores}, optimal threads: {optimal}")
            return optimal
        except Exception as e:
            logger.error(f"Error getting CPU count: {e}")
            return 2
    
    @staticmethod
    def estimate_processing_time(video_duration_sec, complexity="medium"):
        """Estimate processing time based on video duration"""
        # Rough estimates for VPS (faster preset)
        # Adjust based on your VPS specs
        
        base_multiplier = {
            "simple": 1.0,  # Single image
            "medium": 1.5,  # 2-3 images
            "complex": 2.0   # 4+ images
        }
        
        multiplier = base_multiplier.get(complexity, 1.5)
        estimated_seconds = video_duration_sec * multiplier
        
        return {
            'estimated_seconds': estimated_seconds,
            'estimated_minutes': estimated_seconds / 60,
            'readable': format_time(estimated_seconds)
        }
    
    @staticmethod
    def format_time(seconds):
        """Format seconds to readable time"""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            return f"{int(seconds / 60)}m {int(seconds % 60)}s"
        else:
            hours = seconds / 3600
            return f"{hours:.1f}h"


def setup_logging(log_file='bot.log'):
    """Setup logging configuration"""
    
    logger = logging.getLogger()
    
    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    logger.setLevel(logging.INFO)
    
    return logger


def cleanup_old_sessions(temp_dir='temp', max_age_hours=24):
    """Clean up old temporary files"""
    
    import shutil
    from pathlib import Path
    
    try:
        cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
        
        if not os.path.exists(temp_dir):
            return
        
        cleaned = 0
        for session_dir in Path(temp_dir).iterdir():
            if session_dir.is_dir():
                # Parse timestamp from directory name
                try:
                    timestamp = float(session_dir.name.split('_')[-1])
                    if timestamp < cutoff_time:
                        shutil.rmtree(session_dir)
                        logger.info(f"Cleaned old session: {session_dir.name}")
                        cleaned += 1
                except (ValueError, IndexError):
                    pass
        
        logger.info(f"Cleanup complete: {cleaned} old sessions removed")
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")


def format_time(seconds):
    """Format seconds to readable time"""
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def validate_ffmpeg_command(cmd_list):
    """Validate FFmpeg command for common issues"""
    
    # Check for required inputs
    has_input = any(flag in str(cmd_list) for flag in ['-i', '-loop'])
    has_output = any(isinstance(item, str) and item.endswith(('.mp4', '.avi', '.mov')) 
                     for item in cmd_list)
    
    return has_input and has_output
