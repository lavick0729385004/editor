"""
Production Quality Presets and Rate Limiter for Large-Scale Deployments
Supports YouTubers with millions of subscribers
"""

import logging
from enum import Enum
from dataclasses import dataclass
from typing import Dict, Optional
from collections import defaultdict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class QualityPreset(Enum):
    """Video quality presets for different use cases"""
    FAST = "fast"           # Fast processing, lower quality - 30s max
    BALANCED = "balanced"   # Standard preset - 60s video
    QUALITY = "quality"     # High quality - 90s video
    ULTRA = "ultra"         # Ultra high quality - full duration


@dataclass
class PresetConfig:
    """Configuration for a quality preset"""
    name: str
    crf: int                    # 0-28, lower = better quality
    preset: str                 # ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow
    output_resolution: str      # 1080x1350, 1440x1800, etc
    max_duration: int           # Seconds
    bitrate: str               # Video bitrate
    description: str
    max_file_size_mb: int      # Output file size limit
    recommended_for: str


QUALITY_PRESETS: Dict[QualityPreset, PresetConfig] = {
    QualityPreset.FAST: PresetConfig(
        name="Fast",
        crf=23,                    # Lower quality
        preset="veryfast",         # Ultra-fast encoding
        output_resolution="1080x1350",
        max_duration=30,
        bitrate="1500k",
        description="Fastest processing, smallest file, lower quality",
        max_file_size_mb=20,
        recommended_for="Quick edits, social media stories, time-critical content"
    ),
    QualityPreset.BALANCED: PresetConfig(
        name="Balanced",
        crf=20,                    # Good quality
        preset="faster",           # Fast but balanced
        output_resolution="1080x1350",
        max_duration=60,
        bitrate="2500k",
        description="Default preset - balance of speed and quality",
        max_file_size_mb=50,
        recommended_for="Standard YouTube Shorts, Instagram Reels, TikTok"
    ),
    QualityPreset.QUALITY: PresetConfig(
        name="Quality",
        crf=18,                    # High quality
        preset="fast",             # Slower but better quality
        output_resolution="1440x1800",
        max_duration=120,
        bitrate="4000k",
        description="High quality, longer processing time",
        max_file_size_mb=80,
        recommended_for="Featured content, YouTube Shorts, HD social media"
    ),
    QualityPreset.ULTRA: PresetConfig(
        name="Ultra",
        crf=16,                    # Very high quality
        preset="medium",           # Much slower, best quality
        output_resolution="1440x1800",
        max_duration=300,          # 5 minutes
        bitrate="6000k",
        description="Highest quality, slowest processing, largest file",
        max_file_size_mb=200,
        recommended_for="YouTube main videos, professional content, archival"
    ),
}


class RateLimiter:
    """
    Advanced rate limiter for production deployments
    Supports per-user and global limits with quota system
    """
    
    def __init__(
        self,
        global_limit: int = 50,              # Global videos per hour
        per_user_limit: int = 5,             # Per user per hour
        per_user_daily_limit: int = 50,      # Per user per day
        premium_multiplier: float = 3.0,     # Premium users get 3x limit
    ):
        self.global_limit = global_limit
        self.per_user_limit = per_user_limit
        self.per_user_daily_limit = per_user_daily_limit
        self.premium_multiplier = premium_multiplier
        
        # Tracking
        self.global_hourly: defaultdict = defaultdict(list)  # datetime objects
        self.per_user_hourly: defaultdict = defaultdict(list)
        self.per_user_daily: defaultdict = defaultdict(list)
        
        # Premium users
        self.premium_users: set = set()
        
        logger.info(
            f"✓ Rate limiter initialized: "
            f"global={global_limit}/hr, per_user={per_user_limit}/hr, daily={per_user_daily_limit}"
        )
    
    def add_premium_user(self, user_id: int):
        """Mark a user as premium (higher limits)"""
        self.premium_users.add(user_id)
        logger.info(f"⭐ Added premium user: {user_id}")
    
    def remove_premium_user(self, user_id: int):
        """Remove premium status"""
        self.premium_users.discard(user_id)
        logger.info(f"❌ Removed premium user: {user_id}")
    
    def is_premium(self, user_id: int) -> bool:
        """Check if user is premium"""
        return user_id in self.premium_users
    
    async def check_limit(self, user_id: int) -> tuple[bool, str]:
        """
        Check if user can process another video
        Returns (allowed, message)
        """
        now = datetime.now()
        
        # Get effective limits
        is_premium = self.is_premium(user_id)
        multiplier = self.premium_multiplier if is_premium else 1.0
        
        user_hourly_limit = int(self.per_user_limit * multiplier)
        user_daily_limit = int(self.per_user_daily_limit * multiplier)
        
        # Clean old entries
        self._cleanup_old_entries(now)
        
        # Check global limit (hourly)
        one_hour_ago = now - timedelta(hours=1)
        global_recent = [
            t for t in self.global_hourly['all']
            if t > one_hour_ago
        ]
        
        if len(global_recent) >= self.global_limit:
            return False, (
                f"🌍 Global rate limit reached. "
                f"{len(global_recent)}/{self.global_limit} videos processed this hour. "
                f"Please try again later."
            )
        
        # Check per-user hourly limit
        user_hourly = [
            t for t in self.per_user_hourly[user_id]
            if t > one_hour_ago
        ]
        
        if len(user_hourly) >= user_hourly_limit:
            remaining_seconds = int(
                (user_hourly[0] + timedelta(hours=1) - now).total_seconds()
            )
            return False, (
                f"⏱️ You've reached your hourly limit "
                f"({len(user_hourly)}/{user_hourly_limit} videos). "
                f"Please wait {remaining_seconds//60} minutes."
            )
        
        # Check per-user daily limit
        one_day_ago = now - timedelta(days=1)
        user_daily = [
            t for t in self.per_user_daily[user_id]
            if t > one_day_ago
        ]
        
        if len(user_daily) >= user_daily_limit:
            remaining_seconds = int(
                (user_daily[0] + timedelta(days=1) - now).total_seconds()
            )
            remaining_hours = remaining_seconds // 3600
            return False, (
                f"📅 You've reached your daily limit "
                f"({len(user_daily)}/{user_daily_limit} videos). "
                f"Please try again in {remaining_hours} hours."
            )
        
        return True, "✅ Rate limit check passed"
    
    async def record_processing(self, user_id: int):
        """Record that a user started processing a video"""
        now = datetime.now()
        self.global_hourly['all'].append(now)
        self.per_user_hourly[user_id].append(now)
        self.per_user_daily[user_id].append(now)
        
        is_premium = self.is_premium(user_id)
        premium_badge = "⭐ " if is_premium else ""
        logger.info(f"{premium_badge}Video processing recorded for user {user_id}")
    
    def _cleanup_old_entries(self, now: datetime):
        """Remove old entries to prevent memory bloat"""
        one_week_ago = now - timedelta(days=7)
        
        # Clean global hourly
        self.global_hourly['all'] = [
            t for t in self.global_hourly['all']
            if t > one_week_ago
        ]
        
        # Clean per-user entries
        for user_id in list(self.per_user_hourly.keys()):
            self.per_user_hourly[user_id] = [
                t for t in self.per_user_hourly[user_id]
                if t > one_week_ago
            ]
            if not self.per_user_hourly[user_id]:
                del self.per_user_hourly[user_id]
        
        for user_id in list(self.per_user_daily.keys()):
            self.per_user_daily[user_id] = [
                t for t in self.per_user_daily[user_id]
                if t > one_week_ago
            ]
            if not self.per_user_daily[user_id]:
                del self.per_user_daily[user_id]
    
    def get_stats(self, user_id: int) -> Dict:
        """Get rate limit stats for a user"""
        now = datetime.now()
        
        one_hour_ago = now - timedelta(hours=1)
        one_day_ago = now - timedelta(days=1)
        
        hourly_count = len([
            t for t in self.per_user_hourly.get(user_id, [])
            if t > one_hour_ago
        ])
        
        daily_count = len([
            t for t in self.per_user_daily.get(user_id, [])
            if t > one_day_ago
        ])
        
        is_premium = self.is_premium(user_id)
        multiplier = self.premium_multiplier if is_premium else 1.0
        
        return {
            'is_premium': is_premium,
            'hourly_usage': f"{hourly_count}/{int(self.per_user_limit * multiplier)}",
            'daily_usage': f"{daily_count}/{int(self.per_user_daily_limit * multiplier)}",
            'global_limit': f"{len(self.global_hourly['all'])}/{self.global_limit}",
        }


# Global instances
quality_presets = QUALITY_PRESETS
rate_limiter: Optional[RateLimiter] = None


async def init_rate_limiter() -> RateLimiter:
    """Initialize rate limiter"""
    global rate_limiter
    # For YouTubers with 2M+ subs: generous limits
    rate_limiter = RateLimiter(
        global_limit=100,          # 100 videos/hour global
        per_user_limit=20,         # 20 per user/hour
        per_user_daily_limit=200,  # 200 per user/day
        premium_multiplier=2.0,    # Premium users: 2x limit
    )
    return rate_limiter


async def get_rate_limiter() -> RateLimiter:
    """Get global rate limiter"""
    global rate_limiter
    if rate_limiter is None:
        rate_limiter = await init_rate_limiter()
    return rate_limiter
