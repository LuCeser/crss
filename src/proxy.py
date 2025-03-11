import os
from typing import Dict, Optional, List
from urllib.parse import urlparse


class ProxyManager:
    def __init__(self, proxy_config: Optional[Dict] = None):
        """
        初始化代理管理器
        
        Args:
            proxy_config: 代理配置字典，格式如下：
            {
                'http': 'http://proxy:port',
                'https': 'http://proxy:port',
                'no_proxy': ['localhost', '127.0.0.1']
            }
        """
        self.proxy_config = proxy_config or {}
        self._setup_proxy_env()
    
    def _setup_proxy_env(self):
        """设置系统环境变量中的代理"""
        if self.proxy_config:
            if 'http' in self.proxy_config:
                os.environ['HTTP_PROXY'] = self.proxy_config['http']
            if 'https' in self.proxy_config:
                os.environ['HTTPS_PROXY'] = self.proxy_config['https']
            if 'no_proxy' in self.proxy_config:
                os.environ['NO_PROXY'] = ','.join(self.proxy_config['no_proxy'])
    
    def get_session_proxies(self) -> Dict[str, str]:
        """获取用于requests.Session的代理配置"""
        proxies = {}
        if self.proxy_config:
            if 'http' in self.proxy_config:
                proxies['http'] = self.proxy_config['http']
            if 'https' in self.proxy_config:
                proxies['https'] = self.proxy_config['https']
        return proxies
    
    def should_use_proxy(self, url: str) -> bool:
        """
        判断给定URL是否应该使用代理
        
        Args:
            url: 目标URL
            
        Returns:
            bool: 是否应该使用代理
        """
        if not self.proxy_config or 'no_proxy' not in self.proxy_config:
            return True
            
        hostname = urlparse(url).hostname
        if not hostname:
            return False
            
        return not any(
            no_proxy in hostname 
            for no_proxy in self.proxy_config['no_proxy']
        ) 