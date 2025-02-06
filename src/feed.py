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

    def process_feed(self, feed_name: str, feed_url: str, scan_history_id: int) -> Dict[str, int]:
        """
        处理单个RSS源
        
        Returns:
            Dict[str, int]: 包含成功和失败计数的字典
        """
        result = {"success": 0, "error": 0}
        
        try:
            feed = feedparser.parse(feed_url)
            
            if feed.bozo:  # RSS解析错误
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