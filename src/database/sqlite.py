"""
Database module for Perplexo Bot using SQLite.
Handles user preferences, rate limiting, and analytics.
"""

import sqlite3
import json
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from contextlib import contextmanager


class Database:
    """SQLite database handler for Perplexo Bot."""
    
    def __init__(self, db_path: str = "data/perplexo.db"):
        self.db_path = db_path
        self._ensure_directory()
        self._init_tables()
    
    def _ensure_directory(self):
        """Ensure the database directory exists."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def _init_tables(self):
        """Initialize database tables."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # User preferences table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    user_id INTEGER PRIMARY KEY,
                    platform TEXT NOT NULL DEFAULT 'telegram',
                    model TEXT DEFAULT 'sonar',
                    focus TEXT DEFAULT 'web',
                    mode TEXT DEFAULT 'busca',
                    reasoning BOOLEAN DEFAULT 0,
                    return_citations BOOLEAN DEFAULT 1,
                    return_images BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Rate limiting table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rate_limits (
                    user_id INTEGER,
                    platform TEXT,
                    request_count INTEGER DEFAULT 1,
                    window_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, platform)
                )
            """)
            
            # Analytics/Logs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS query_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    platform TEXT,
                    query TEXT,
                    model TEXT,
                    focus TEXT,
                    response_time_ms INTEGER,
                    success BOOLEAN,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_query_logs_user_id 
                ON query_logs(user_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_query_logs_created_at 
                ON query_logs(created_at)
            """)
    
    # ==================== User Preferences ====================
    
    def get_user_config(self, user_id: int, platform: str = 'telegram') -> Dict[str, Any]:
        """Get user configuration or return defaults."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT model, focus, mode, reasoning, return_citations, return_images
                FROM user_preferences
                WHERE user_id = ? AND platform = ?
                """,
                (user_id, platform)
            )
            row = cursor.fetchone()
            
            if row:
                return {
                    'model': row['model'],
                    'focus': row['focus'],
                    'mode': row['mode'],
                    'reasoning': bool(row['reasoning']),
                    'return_citations': bool(row['return_citations']),
                    'return_images': bool(row['return_images'])
                }
            
            # Return defaults
            return {
                'model': 'sonar',
                'focus': 'web',
                'mode': 'busca',
                'reasoning': False,
                'return_citations': True,
                'return_images': True
            }
    
    def update_user_config(self, user_id: int, platform: str, config: Dict[str, Any]):
        """Update user configuration."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO user_preferences 
                (user_id, platform, model, focus, mode, reasoning, return_citations, return_images, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET
                    model = excluded.model,
                    focus = excluded.focus,
                    mode = excluded.mode,
                    reasoning = excluded.reasoning,
                    return_citations = excluded.return_citations,
                    return_images = excluded.return_images,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    user_id,
                    platform,
                    config.get('model', 'sonar'),
                    config.get('focus', 'web'),
                    config.get('mode', 'busca'),
                    config.get('reasoning', False),
                    config.get('return_citations', True),
                    config.get('return_images', True)
                )
            )
    
    def toggle_setting(self, user_id: int, platform: str, setting: str) -> bool:
        """Toggle a boolean setting for a user."""
        config = self.get_user_config(user_id, platform)
        
        if setting not in config:
            raise ValueError(f"Invalid setting: {setting}")
        
        config[setting] = not config[setting]
        self.update_user_config(user_id, platform, config)
        
        return config[setting]
    
    # ==================== Rate Limiting ====================
    
    def check_rate_limit(self, user_id: int, platform: str, 
                         max_requests: int = 20, window_seconds: int = 3600) -> tuple:
        """
        Check if user has exceeded rate limit.
        Returns (allowed: bool, remaining: int, reset_time: datetime)
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Get current rate limit record
            cursor.execute(
                """
                SELECT request_count, window_start
                FROM rate_limits
                WHERE user_id = ? AND platform = ?
                """,
                (user_id, platform)
            )
            row = cursor.fetchone()
            
            now = datetime.now()
            
            if row:
                window_start = datetime.fromisoformat(row['window_start'])
                request_count = row['request_count']
                
                # Check if window has expired
                if now - window_start > timedelta(seconds=window_seconds):
                    # Reset window
                    cursor.execute(
                        """
                        UPDATE rate_limits
                        SET request_count = 1, window_start = CURRENT_TIMESTAMP
                        WHERE user_id = ? AND platform = ?
                        """,
                        (user_id, platform)
                    )
                    remaining = max_requests - 1
                    reset_time = now + timedelta(seconds=window_seconds)
                    return True, remaining, reset_time
                
                # Check if under limit
                if request_count < max_requests:
                    cursor.execute(
                        """
                        UPDATE rate_limits
                        SET request_count = request_count + 1
                        WHERE user_id = ? AND platform = ?
                        """,
                        (user_id, platform)
                    )
                    remaining = max_requests - request_count - 1
                    reset_time = window_start + timedelta(seconds=window_seconds)
                    return True, remaining, reset_time
                else:
                    # Rate limit exceeded
                    reset_time = window_start + timedelta(seconds=window_seconds)
                    return False, 0, reset_time
            else:
                # New user
                cursor.execute(
                    """
                    INSERT INTO rate_limits (user_id, platform, request_count)
                    VALUES (?, ?, 1)
                    """,
                    (user_id, platform)
                )
                remaining = max_requests - 1
                reset_time = now + timedelta(seconds=window_seconds)
                return True, remaining, reset_time
    
    def get_rate_limit_info(self, user_id: int, platform: str, 
                            max_requests: int = 20, window_seconds: int = 3600) -> Dict[str, Any]:
        """Get rate limit information for a user."""
        allowed, remaining, reset_time = self.check_rate_limit(
            user_id, platform, max_requests, window_seconds
        )
        
        return {
            'allowed': allowed,
            'remaining': remaining,
            'reset_time': reset_time.isoformat(),
            'limit': max_requests
        }
    
    # ==================== Analytics ====================
    
    def log_query(self, user_id: int, platform: str, query: str, 
                  model: str, focus: str, response_time_ms: int = 0,
                  success: bool = True, error_message: Optional[str] = None):
        """Log a query for analytics."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO query_logs 
                (user_id, platform, query, model, focus, response_time_ms, success, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, platform, query, model, focus, response_time_ms, success, error_message)
            )
    
    def get_user_stats(self, user_id: int, platform: str) -> Dict[str, Any]:
        """Get statistics for a user."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Total queries
            cursor.execute(
                """
                SELECT COUNT(*) as total, 
                       SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful
                FROM query_logs
                WHERE user_id = ? AND platform = ?
                """,
                (user_id, platform)
            )
            row = cursor.fetchone()
            
            # Most used model
            cursor.execute(
                """
                SELECT model, COUNT(*) as count
                FROM query_logs
                WHERE user_id = ? AND platform = ?
                GROUP BY model
                ORDER BY count DESC
                LIMIT 1
                """,
                (user_id, platform)
            )
            model_row = cursor.fetchone()
            
            return {
                'total_queries': row['total'] or 0,
                'successful_queries': row['successful'] or 0,
                'favorite_model': model_row['model'] if model_row else 'N/A'
            }
    
    def get_global_stats(self) -> Dict[str, Any]:
        """Get global statistics."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    COUNT(DISTINCT user_id) as total_users,
                    COUNT(*) as total_queries,
                    AVG(response_time_ms) as avg_response_time
                FROM query_logs
            """)
            row = cursor.fetchone()
            
            return {
                'total_users': row['total_users'] or 0,
                'total_queries': row['total_queries'] or 0,
                'avg_response_time_ms': round(row['avg_response_time'] or 0, 2)
            }
    
    def cleanup_old_logs(self, days: int = 30):
        """Clean up logs older than specified days."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                DELETE FROM query_logs
                WHERE created_at < datetime('now', '-{} days')
                """.format(days)
            )
            return cursor.rowcount