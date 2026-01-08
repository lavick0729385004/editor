"""
Advanced Error Recovery and Graceful Degradation
Ensures system continues operating under adverse conditions
"""

import logging
import asyncio
import subprocess
from typing import Optional, Tuple, Dict, Any
from enum import Enum

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = 1          # Non-critical, can continue
    MEDIUM = 2       # Degraded functionality
    HIGH = 3         # Major functionality lost
    CRITICAL = 4     # System failure imminent


class RecoveryStrategy(Enum):
    """Automatic recovery strategies"""
    RETRY = "retry"                      # Retry operation
    FALLBACK = "fallback"                # Use alternate method
    DEGRADE = "degrade"                  # Reduce quality/features
    SKIP = "skip"                        # Skip this step
    ABORT = "abort"                      # Cancel operation


class ErrorRecoveryManager:
    """Intelligent error handling with automatic recovery"""
    
    def __init__(self):
        self.error_count: Dict[str, int] = {}
        self.recovery_attempts: Dict[str, int] = {}
        self.fallback_methods: Dict[str, callable] = {}
        
        logger.info("✓ Error recovery manager initialized")
    
    def register_fallback(self, operation: str, fallback_func: callable):
        """Register a fallback method for an operation"""
        self.fallback_methods[operation] = fallback_func
        logger.info(f"✓ Registered fallback for: {operation}")
    
    async def handle_ffmpeg_error(
        self,
        error: Exception,
        operation: str,
        attempt: int = 1
    ) -> Tuple[RecoveryStrategy, Optional[str]]:
        """
        Intelligent handling of FFmpeg errors
        Returns (strategy, message)
        """
        
        error_str = str(error).lower()
        
        # Analyze error type
        if 'timeout' in error_str:
            return await self._handle_timeout(operation, attempt)
        elif 'permission denied' in error_str or 'permission' in error_str:
            return await self._handle_permission_error(operation)
        elif 'not found' in error_str or 'no such file' in error_str:
            return await self._handle_missing_file(operation)
        elif 'invalid data' in error_str or 'corrupted' in error_str:
            return await self._handle_corrupted_file(operation)
        elif 'memory' in error_str or 'out of memory' in error_str:
            return await self._handle_memory_error(operation)
        elif 'codec' in error_str or 'format' in error_str:
            return await self._handle_codec_error(operation)
        else:
            return await self._handle_generic_error(operation, error, attempt)
    
    async def _handle_timeout(
        self,
        operation: str,
        attempt: int
    ) -> Tuple[RecoveryStrategy, str]:
        """Handle timeout errors with exponential backoff"""
        
        if attempt >= 3:
            logger.error(f"⏱️ Max retries for {operation}, degrading quality")
            return RecoveryStrategy.DEGRADE, "Reducing quality to meet time limit"
        
        backoff = 2 ** attempt  # 2s, 4s, 8s
        logger.warning(
            f"⏱️ {operation} timeout, retrying in {backoff}s (attempt {attempt}/3)"
        )
        await asyncio.sleep(backoff)
        
        return RecoveryStrategy.RETRY, f"Retrying after {backoff}s backoff"
    
    async def _handle_permission_error(
        self,
        operation: str
    ) -> Tuple[RecoveryStrategy, str]:
        """Handle permission errors"""
        logger.error(f"🔒 Permission denied for {operation}")
        return RecoveryStrategy.ABORT, "Permission denied - check file permissions"
    
    async def _handle_missing_file(
        self,
        operation: str
    ) -> Tuple[RecoveryStrategy, str]:
        """Handle missing file errors"""
        logger.error(f"📁 File not found for {operation}")
        return RecoveryStrategy.SKIP, "Input file not found, skipping this step"
    
    async def _handle_corrupted_file(
        self,
        operation: str
    ) -> Tuple[RecoveryStrategy, str]:
        """Handle corrupted file errors"""
        logger.warning(f"⚠️ Corrupted file in {operation}, attempting recovery")
        return RecoveryStrategy.FALLBACK, "File corruption detected, using fallback method"
    
    async def _handle_memory_error(
        self,
        operation: str
    ) -> Tuple[RecoveryStrategy, str]:
        """Handle memory exhaustion"""
        logger.critical(f"💾 Memory error in {operation}, degrading quality")
        return RecoveryStrategy.DEGRADE, "Out of memory, reducing quality"
    
    async def _handle_codec_error(
        self,
        operation: str
    ) -> Tuple[RecoveryStrategy, str]:
        """Handle codec/format errors"""
        logger.warning(f"🎬 Codec error in {operation}, using fallback codec")
        return RecoveryStrategy.FALLBACK, "Unsupported codec, using H.264 fallback"
    
    async def _handle_generic_error(
        self,
        operation: str,
        error: Exception,
        attempt: int
    ) -> Tuple[RecoveryStrategy, str]:
        """Handle generic errors"""
        
        if attempt < 2:
            logger.warning(f"❓ Unknown error in {operation}, retrying...")
            return RecoveryStrategy.RETRY, "Retrying operation"
        else:
            logger.error(f"❓ Persistent error in {operation}: {error}")
            return RecoveryStrategy.DEGRADE, f"Error: {str(error)[:100]}"


class GracefulDegradation:
    """
    Reduce quality/features when system is under stress
    Ensures videos are still produced rather than failing
    """
    
    def __init__(self):
        self.degradation_level = 0  # 0=full, 1=medium, 2=low, 3=minimal
        self.is_degraded = False
        logger.info("✓ Graceful degradation system initialized")
    
    async def check_and_apply_degradation(
        self,
        cpu_percent: float,
        memory_percent: float,
        queue_size: int
    ) -> Dict[str, Any]:
        """
        Check system load and apply degradation if needed
        Returns degradation settings
        """
        
        settings = {
            'crf': 20,
            'preset': 'faster',
            'resolution': '1080x1350',
            'bitrate': '2500k',
            'skip_upscaling': False,
            'max_duration': 60,
        }
        
        # Determine degradation level
        if cpu_percent > 80 or memory_percent > 80 or queue_size > 10:
            self.degradation_level = 1
            self.is_degraded = True
            
            settings['crf'] = 23           # Lower quality
            settings['preset'] = 'veryfast'
            settings['bitrate'] = '1500k'
            logger.warning(f"⚠️ Level 1 degradation: CPU {cpu_percent}%, Memory {memory_percent}%")
        
        if cpu_percent > 85 or memory_percent > 85 or queue_size > 20:
            self.degradation_level = 2
            self.is_degraded = True
            
            settings['crf'] = 25
            settings['preset'] = 'ultrafast'
            settings['resolution'] = '1080x1350'  # Keep resolution
            settings['bitrate'] = '1000k'
            settings['skip_upscaling'] = True
            settings['max_duration'] = 30
            logger.error(f"⚠️ Level 2 degradation: CPU {cpu_percent}%, Memory {memory_percent}%")
        
        if cpu_percent > 90 or memory_percent > 90 or queue_size > 30:
            self.degradation_level = 3
            self.is_degraded = True
            
            settings['crf'] = 28           # Very low quality
            settings['preset'] = 'ultrafast'
            settings['bitrate'] = '800k'
            settings['skip_upscaling'] = True
            settings['max_duration'] = 15
            logger.critical(
                f"🔴 Level 3 degradation: CPU {cpu_percent}%, Memory {memory_percent}%"
            )
        
        if cpu_percent < 50 and memory_percent < 50 and queue_size < 3:
            self.degradation_level = 0
            self.is_degraded = False
            logger.info("✓ System recovered, returning to normal operation")
        
        settings['degradation_level'] = self.degradation_level
        settings['is_degraded'] = self.is_degraded
        
        return settings
    
    def get_status(self) -> Dict[str, Any]:
        """Get degradation status"""
        return {
            'is_degraded': self.is_degraded,
            'degradation_level': self.degradation_level,
            'levels': {
                0: 'Full quality - Normal operation',
                1: 'Medium degradation - Reduced quality and speed',
                2: 'Low degradation - Fast processing, poor quality',
                3: 'Minimal - Emergency mode, bare minimum quality',
            }
        }


class CircuitBreaker:
    """
    Circuit breaker pattern to prevent cascading failures
    Stops sending requests when error rate is high
    """
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
        
        logger.info(
            f"✓ Circuit breaker initialized: {failure_threshold} failures, {timeout}s timeout"
        )
    
    async def call(self, func: callable, *args, **kwargs) -> Tuple[bool, Any]:
        """
        Execute function with circuit breaker protection
        Returns (success, result)
        """
        
        if self.state == "open":
            import time
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "half-open"
                logger.warning("🔄 Circuit breaker: half-open, testing...")
            else:
                return False, "Circuit breaker open - too many failures"
        
        try:
            result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
            
            # Success - reset
            if self.state == "half-open":
                self.state = "closed"
                self.failure_count = 0
                logger.info("✓ Circuit breaker: closed, recovered")
            
            return True, result
            
        except Exception as e:
            self.failure_count += 1
            import time
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
                logger.error(
                    f"🔴 Circuit breaker: OPEN after {self.failure_count} failures"
                )
            
            return False, str(e)


# Global instances
error_recovery: Optional[ErrorRecoveryManager] = None
graceful_degradation: Optional[GracefulDegradation] = None


async def init_error_recovery() -> Tuple[ErrorRecoveryManager, GracefulDegradation]:
    """Initialize error recovery systems"""
    global error_recovery, graceful_degradation
    
    error_recovery = ErrorRecoveryManager()
    graceful_degradation = GracefulDegradation()
    
    logger.info("✓ Error recovery systems initialized")
    return error_recovery, graceful_degradation
