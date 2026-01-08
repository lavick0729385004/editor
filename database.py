"""
Database Persistence Layer for Production Analytics and Job History
SQLite-based for easy deployment, no external dependencies
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class ProductionDatabase:
    """
    SQLite database for persistent storage of:
    - Video processing jobs
    - User statistics
    - Processing history
    - Performance analytics
    """
    
    def __init__(self, db_path: str = "data/video_editor.db"):
        self.db_path = db_path
        self._ensure_db_exists()
        logger.info(f"✓ Database initialized: {db_path}")
    
    def _ensure_db_exists(self):
        """Create database and tables if they don't exist"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Jobs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                status TEXT NOT NULL,
                priority TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                duration_seconds REAL,
                attempts INTEGER DEFAULT 0,
                max_retries INTEGER DEFAULT 3,
                progress REAL DEFAULT 0,
                status_message TEXT,
                output_file TEXT,
                error_message TEXT,
                input_size_mb REAL,
                output_size_mb REAL,
                preset TEXT,
                INDEX idx_user (user_id),
                INDEX idx_status (status),
                INDEX idx_created (created_at)
            )
        ''')
        
        # User stats table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_stats (
                user_id INTEGER PRIMARY KEY,
                total_videos INTEGER DEFAULT 0,
                total_processing_time_seconds REAL DEFAULT 0,
                avg_processing_time_seconds REAL DEFAULT 0,
                success_count INTEGER DEFAULT 0,
                failure_count INTEGER DEFAULT 0,
                success_rate REAL DEFAULT 0,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP,
                total_input_mb REAL DEFAULT 0,
                total_output_mb REAL DEFAULT 0,
                is_premium INTEGER DEFAULT 0,
                storage_used_mb REAL DEFAULT 0,
                INDEX idx_success_rate (success_rate)
            )
        ''')
        
        # Processing history table (for analytics)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS processing_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metric_name TEXT NOT NULL,
                metric_value REAL,
                tags TEXT,
                INDEX idx_timestamp (timestamp),
                INDEX idx_metric (metric_name)
            )
        ''')
        
        # Rate limit tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rate_limits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                action TEXT,
                INDEX idx_user_timestamp (user_id, timestamp)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def record_job(self, job_data: Dict[str, Any]) -> bool:
        """Record a job in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO jobs (
                    job_id, user_id, status, priority, created_at,
                    started_at, completed_at, duration_seconds, attempts,
                    max_retries, progress, status_message, output_file,
                    error_message, input_size_mb, output_size_mb, preset
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                job_data.get('job_id'),
                job_data.get('user_id'),
                job_data.get('status'),
                job_data.get('priority'),
                job_data.get('created_at'),
                job_data.get('started_at'),
                job_data.get('completed_at'),
                job_data.get('duration_seconds'),
                job_data.get('attempts'),
                job_data.get('max_retries'),
                job_data.get('progress'),
                job_data.get('status_message'),
                job_data.get('output_file'),
                job_data.get('error_message'),
                job_data.get('input_size_mb'),
                job_data.get('output_size_mb'),
                job_data.get('preset'),
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Failed to record job: {e}")
            return False
    
    def update_user_stats(self, user_id: int, job_data: Dict[str, Any]):
        """Update user statistics based on completed job"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            duration = job_data.get('duration_seconds', 0)
            success = job_data.get('status') == 'completed'
            input_mb = job_data.get('input_size_mb', 0)
            output_mb = job_data.get('output_size_mb', 0)
            
            # Get current stats
            cursor.execute('SELECT * FROM user_stats WHERE user_id = ?', (user_id,))
            row = cursor.fetchone()
            
            if row:
                # Update existing
                cursor.execute('''
                    UPDATE user_stats SET
                        total_videos = total_videos + 1,
                        total_processing_time_seconds = total_processing_time_seconds + ?,
                        success_count = success_count + ?,
                        failure_count = failure_count + ?,
                        total_input_mb = total_input_mb + ?,
                        total_output_mb = total_output_mb + ?,
                        last_seen = CURRENT_TIMESTAMP,
                        storage_used_mb = storage_used_mb + ?
                    WHERE user_id = ?
                ''', (
                    duration,
                    1 if success else 0,
                    0 if success else 1,
                    input_mb,
                    output_mb,
                    output_mb,
                    user_id
                ))
            else:
                # Insert new
                cursor.execute('''
                    INSERT INTO user_stats (
                        user_id, total_videos, total_processing_time_seconds,
                        success_count, failure_count, total_input_mb, total_output_mb,
                        storage_used_mb
                    ) VALUES (?, 1, ?, ?, ?, ?, ?, ?)
                ''', (
                    user_id,
                    duration,
                    1 if success else 0,
                    0 if success else 1,
                    input_mb,
                    output_mb,
                    output_mb
                ))
            
            # Update success rate and avg time
            cursor.execute('''
                UPDATE user_stats SET
                    avg_processing_time_seconds = CASE
                        WHEN success_count > 0 THEN total_processing_time_seconds / success_count
                        ELSE 0
                    END,
                    success_rate = CASE
                        WHEN total_videos > 0 THEN (success_count * 100.0 / total_videos)
                        ELSE 0
                    END
                WHERE user_id = ?
            ''', (user_id,))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to update user stats: {e}")
    
    def get_user_stats(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM user_stats WHERE user_id = ?', (user_id,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))
            return None
        except Exception as e:
            logger.error(f"Failed to get user stats: {e}")
            return None
    
    def get_job_history(self, user_id: Optional[int] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get job history"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if user_id:
                cursor.execute('''
                    SELECT * FROM jobs WHERE user_id = ?
                    ORDER BY created_at DESC LIMIT ?
                ''', (user_id, limit))
            else:
                cursor.execute('''
                    SELECT * FROM jobs
                    ORDER BY created_at DESC LIMIT ?
                ''', (limit,))
            
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            conn.close()
            
            return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get job history: {e}")
            return []
    
    def record_metric(self, metric_name: str, value: float, tags: Optional[Dict] = None):
        """Record a performance metric"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            tags_json = json.dumps(tags) if tags else None
            
            cursor.execute('''
                INSERT INTO processing_history (metric_name, metric_value, tags)
                VALUES (?, ?, ?)
            ''', (metric_name, value, tags_json))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to record metric: {e}")
    
    def get_analytics(self, hours: int = 24) -> Dict[str, Any]:
        """Get analytics for the last N hours"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            time_filter = datetime.now() - timedelta(hours=hours)
            
            # Total jobs
            cursor.execute('''
                SELECT COUNT(*) FROM jobs WHERE created_at > ?
            ''', (time_filter,))
            total_jobs = cursor.fetchone()[0]
            
            # Success rate
            cursor.execute('''
                SELECT COUNT(*) FROM jobs WHERE status = 'completed' AND created_at > ?
            ''', (time_filter,))
            successful = cursor.fetchone()[0]
            
            # Average processing time
            cursor.execute('''
                SELECT AVG(duration_seconds) FROM jobs
                WHERE status = 'completed' AND created_at > ?
            ''', (time_filter,))
            avg_duration = cursor.fetchone()[0] or 0
            
            # Unique users
            cursor.execute('''
                SELECT COUNT(DISTINCT user_id) FROM jobs WHERE created_at > ?
            ''', (time_filter,))
            unique_users = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'period_hours': hours,
                'total_jobs': total_jobs,
                'successful_jobs': successful,
                'success_rate': f"{(successful/total_jobs*100):.1f}%" if total_jobs > 0 else "0%",
                'avg_processing_seconds': f"{avg_duration:.1f}",
                'unique_users': unique_users,
            }
        except Exception as e:
            logger.error(f"Failed to get analytics: {e}")
            return {}
    
    def cleanup_old_data(self, days: int = 30):
        """Remove old data to prevent database bloat"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cutoff_time = datetime.now() - timedelta(days=days)
            
            cursor.execute('DELETE FROM jobs WHERE completed_at < ?', (cutoff_time,))
            cursor.execute('DELETE FROM processing_history WHERE timestamp < ?', (cutoff_time,))
            cursor.execute('DELETE FROM rate_limits WHERE timestamp < ?', (cutoff_time,))
            
            deleted = cursor.total_changes
            
            conn.commit()
            conn.close()
            
            logger.info(f"🧹 Cleaned up {deleted} old records")
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")


# Global instance
db: Optional[ProductionDatabase] = None


async def init_database(db_path: str = "data/video_editor.db") -> ProductionDatabase:
    """Initialize the database"""
    global db
    db = ProductionDatabase(db_path)
    return db


async def get_database() -> ProductionDatabase:
    """Get the global database instance"""
    global db
    if db is None:
        db = await init_database()
    return db
