import logging
from typing import Dict, Optional

import feedparser

from .content_processor import ContentProcessor
from .database import Database
from .http_client import HTTPClient
from .utils import get_link_hash

logger = logging.getLogger(__name__)

class FeedProcessor:
    def __init__(self, database: Database, http_client: HTTPClient, content_processor: ContentProcessor):
        self.database = database
        self.http_client = http_client
        self.content_processor = content_processor

    def parse_feed(self, feed_url: str) -> Optional[feedparser.FeedParserDict]:
        """
        解析RSS源, 处理可能的编码问题
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
                        logger.info(f"已存在处理记录 {link}")
                        continue

                    content_type = self.content_processor.detect_content_type(link, {})
                    analyze_ret = self.content_processor.process_content(link, {}, content_type)

                    # 安全获取 summary
                    summary = ""
                    if analyze_ret.get('analysis') and isinstance(analyze_ret['analysis'], dict):
                        summary = analyze_ret['analysis'].get('summary', '')
                    # 如果 analysis 是 None 或没有 summary，summary 就是空字符串

                    # 发送到目标API
                    if self.http_client.send_item(title, link, summary):
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

    def process_entry(self, entry, feed_name: str, process_content: bool) -> Dict:
        """处理单个RSS条目"""
        analysis = {}
        if process_content:
            # 转换为Markdown
            markdown_content = self.content_processor.convert_to_markdown(entry.link)
            if markdown_content:
                # 分析内容
                analysis = self.content_processor.analyze_content(markdown_content)
                analysis['markdown_content'] = markdown_content

        return analysis 