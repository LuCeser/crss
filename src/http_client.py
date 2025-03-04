import logging
from typing import Dict

import requests

logger = logging.getLogger(__name__)


class HTTPClient:
    def __init__(self, target_api: str):
        self.target_api = target_api
        self.session = requests.Session()

    def send_item(self, title: str, url: str) -> bool:
        """
        发送处理后的内容到目标API
        
        Args:
            title: 文章标题
            url: 原始URL
        """

        # 构建基础请求体
        payload = {
            "type": "url",
            "content": url,
            "title": title,
            "folder": "RSS",
            "tags": []
        }

        try:
            response = self.session.post(
                self.target_api,
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            return True
        except requests.RequestException as e:
            logger.error(f"发送失败: {str(e)}, URL: {url}")
            return False

    def send_processed_item(self, title: str, link: str, analysis: Dict) -> bool:
        """发送处理后的RSS条目"""
        payload = {
            "type": "url",
            "title": title,
            "content": link,
            "folder": "RSS",
            "description": analysis.get('summary', ''),
            "tags": analysis.get('tags', ''),
        }

        try:
            response = self.session.post(
                self.target_api,
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            return True
        except requests.RequestException as e:
            logger.error(f"发送失败: {str(e)}, URL: {link}")
            return False
