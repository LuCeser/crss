import feedparser
from typing import Dict, List, Optional, Generator
import logging
from datetime import datetime
from .utils import get_link_hash
from .database import Database
from .http_client import HTTPClient

logger = logging.getLogger(__name__)

class FeedProcessor:
    def __init__(self, database: Database, http_client: HTTPClient):
        self.database = database
        self.http_client = http_client

    def parse_feed(self, feed_url: str) -> Optional[feedparser.FeedParserDict]:
        """
        解析RSS源，处理可能的编码问题
        """
        try:
            # 首先尝试直接解析
            feed = feedparser.parse(feed_url)
            
            # 如果发现编码错误，尝试使用不同的编码重新解析
            if feed.bozo and isinstance(feed.bozo_exception, feedparser.CharacterEncodingOverride):
                # 获取原始内容
                import requests
                response = requests.get(feed_url, timeout=10)
                
                # 尝试使用 UTF-8 编码
                response.encoding = 'utf-8'
                feed = feedparser.parse(response.text)
                
                # 如果还是失败，尝试其他常见编码
                if feed.bozo:
                    for encoding in ['gb2312', 'gbk', 'iso-8859-1']:
                        response.encoding = encoding
                        feed = feedparser.parse(response.text)
                        if not feed.bozo:
                            break
            
            return feed
        except Exception as e:
            logger.error(f"RSS解析失败: {str(e)}")
            return None

    def process_feed(self, feed_name: str, feed_url: str, scan_history_id: int) -> Dict[str, int]:
        """
        处理单个RSS源
        
        Returns:
            Dict[str, int]: 包含成功和失败计数的字典
        """
        result = {"success": 0, "error": 0}
        
        try:
            feed = self.parse_feed(feed_url)
            
            if feed is None:
                logger.error(f"无法解析RSS源 {feed_name}")
                return result
            
            if feed.bozo and not isinstance(feed.bozo_exception, feedparser.CharacterEncodingOverride):
                logger.error(f"RSS解析错误 {feed_name}: {feed.bozo_exception}")
                return result
            
            for entry in feed.entries:
                try:
                    link = entry.link
                    title = entry.title
                    link_hash = get_link_hash(link)
                    
                    # 检查是否已处理
                    if self.database.is_processed(link_hash):
                        continue
                    
                    # 发送到目标API
                    if self.http_client.send_item(title, link):
                        self.database.add_processed_item(
                            feed_name=feed_name,
                            item_link=link,
                            item_title=title,
                            link_hash=link_hash,
                            scan_history_id=scan_history_id,
                            status='success'
                        )
                        result["success"] += 1
                    else:
                        self.database.add_processed_item(
                            feed_name=feed_name,
                            item_link=link,
                            item_title=title,
                            link_hash=link_hash,
                            scan_history_id=scan_history_id,
                            status='failed',
                            error_message='HTTP发送失败'
                        )
                        result["error"] += 1
                
                except Exception as e:
                    logger.error(f"处理条目错误 {feed_name}: {str(e)}")
                    result["error"] += 1
                    
        except Exception as e:
            logger.error(f"处理RSS源错误 {feed_name}: {str(e)}")
            
        return result 