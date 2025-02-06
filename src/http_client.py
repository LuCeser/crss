import requests
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class HTTPClient:
    def __init__(self, target_api: str):
        self.target_api = target_api
        self.session = requests.Session()

    def send_item(self, title: str, link: str) -> bool:
        """
        发送RSS条目到目标API
        
        Args:
            title: RSS条目标题
            link: RSS条目链接
        
        Returns:
            bool: 发送是否成功
        """
        payload = {
            "type": "url",
            "title": title,
            "content": link,
            "folder": "RSS"
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