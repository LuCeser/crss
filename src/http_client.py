import logging
from typing import Dict, Any, Optional

import requests

from .proxy import ProxyManager

logger = logging.getLogger(__name__)


class HTTPClient:
    def __init__(self, target_api: str, proxy_config: Optional[Dict] = None):
        """
        初始化HTTP客户端
        
        Args:
            target_api: 目标API地址
            proxy_config: 代理配置
        """
        self.target_api = target_api
        self.proxy_manager = ProxyManager(proxy_config)
        
        # 创建session并配置代理
        self.session = requests.Session()
        self.session.proxies.update(self.proxy_manager.get_session_proxies())

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

    def post(self, data: Dict[str, Any]) -> Dict:
        """
        发送POST请求
        
        Args:
            data: 要发送的数据
            
        Returns:
            Dict: 响应数据
        """
        if not self.proxy_manager.should_use_proxy(self.target_api):
            # 如果目标API不需要代理，临时禁用代理
            original_proxies = self.session.proxies
            self.session.proxies = {}
            try:
                response = self.session.post(self.target_api, json=data)
                response.raise_for_status()
                return response.json()
            finally:
                self.session.proxies = original_proxies
        else:
            # 使用配置的代理
            response = self.session.post(self.target_api, json=data)
            response.raise_for_status()
            return response.json()
