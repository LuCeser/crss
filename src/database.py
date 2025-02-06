import sqlite3
from datetime import datetime
import json
from contextlib import contextmanager

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