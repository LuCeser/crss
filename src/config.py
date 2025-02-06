import yaml
import os
from typing import List, Dict, Any

class Config:
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.config_data = {}
        self.load_config()

    def load_config(self) -> None:
        """加载配置文件"""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            self.config_data = yaml.safe_load(f)

    @property
    def interval(self) -> int:
        """获取扫描间隔时间（秒）"""
        return int(self.config_data.get('interval', 300))

    @property
    def database(self) -> str:
        """获取数据库路径"""
        return self.config_data.get('database', 'feeds.db')

    @property
    def log_file(self) -> str:
        """获取日志文件路径"""
        return self.config_data.get('log_file', 'logs/rss.log')

    @property
    def target_api(self) -> str:
        """获取目标API地址"""
        return self.config_data.get('target_api', '')

    @property
    def feeds(self) -> List[Dict[str, str]]:
        """获取RSS源列表"""
        return self.config_data.get('feeds', []) 