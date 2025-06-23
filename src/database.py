import sqlite3
from datetime import datetime
import json
from contextlib import contextmanager
from typing import List, Dict, Optional

import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path):
        self.db_path = db_path
        self.init_db()

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def init_db(self):
        """初始化数据库表"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 创建扫描历史表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS scan_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    start_time TIMESTAMP NOT NULL,
                    end_time TIMESTAMP,
                    total_feeds INTEGER,
                    success_count INTEGER,
                    error_count INTEGER,
                    error_detail TEXT
                )
            ''')

            # 创建已处理项目表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS processed_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    feed_name TEXT NOT NULL,
                    item_link TEXT NOT NULL,
                    item_title TEXT NOT NULL,
                    link_hash CHAR(32) NOT NULL,
                    processed_time TIMESTAMP,
                    scan_history_id INTEGER,
                    status TEXT,
                    error_message TEXT,
                    UNIQUE(link_hash)
                )
            ''')
            
            # 创建每日摘要表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS daily_summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE NOT NULL,
                    summary_content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(date)
                )
            ''')
            
            conn.commit()

    def start_scan(self, total_feeds):
        """开始新的扫描记录"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO scan_history (start_time, total_feeds, success_count, error_count)
                VALUES (?, ?, 0, 0)
            ''', (datetime.now(), total_feeds))
            conn.commit()
            return cursor.lastrowid

    def end_scan(self, scan_id, success_count, error_count, error_detail):
        """更新扫描记录"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE scan_history
                SET end_time = ?, success_count = ?, error_count = ?, error_detail = ?
                WHERE id = ?
            ''', (datetime.now(), success_count, error_count, json.dumps(error_detail), scan_id))
            conn.commit()

    def is_processed(self, link_hash):
        """检查链接是否已处理"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT 1 FROM processed_items WHERE link_hash = ?', (link_hash,))
            return cursor.fetchone() is not None

    def add_processed_item(self, feed_name, item_link, item_title, link_hash, scan_history_id, status='success', error_message=None):
        """添加已处理项目"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    INSERT INTO processed_items 
                    (feed_name, item_link, item_title, link_hash, processed_time, scan_history_id, status, error_message)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (feed_name, item_link, item_title, link_hash, datetime.now(), scan_history_id, status, error_message))
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False

    def save_daily_summary(self, date: str, summary_content: str) -> bool:
        """保存每日摘要"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                INSERT OR REPLACE INTO daily_summaries (date, summary_content, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ''', (date, summary_content))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"保存每日摘要失败: {str(e)}")
            return False

    def get_daily_summary(self, date: str) -> Optional[str]:
        """获取指定日期的每日摘要"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                SELECT summary_content FROM daily_summaries
                WHERE date = ?
                ''', (date,))
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as e:
            logger.error(f"获取每日摘要失败: {str(e)}")
            return None

    def get_recent_items(self, days: int = 1) -> List[Dict]:
        """获取最近几天的文章条目"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                SELECT feed_name, item_title, item_link, processed_time
                FROM processed_items
                WHERE date(processed_time) >= date('now', ?)
                ORDER BY processed_time DESC
                ''', (f'-{days} days',))
                return [dict(zip(['feed_name', 'title', 'link', 'time'], row)) 
                       for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"获取最近文章失败: {str(e)}")
            return [] 