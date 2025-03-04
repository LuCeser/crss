import logging
import os
import time

import schedule

from src.config import Config
from src.content_processor import ContentProcessor
from src.database import Database
from src.feed import FeedProcessor
from src.http_client import HTTPClient
from src.utils import setup_logging


class RSSMonitor:
    def __init__(self, config_path: str):
        # 加载配置
        self.config = Config(config_path)
        
        # 设置日志
        self.logger = setup_logging(self.config.log_file)
        
        # 初始化组件
        self.database = Database(self.config.database)
        self.http_client = HTTPClient(self.config.target_api)
        
        # 初始化内容处理器
        self.content_processor = ContentProcessor(
            llm_config=self.config.llm_config
        )
        
        # 初始化Feed处理器
        self.feed_processor = FeedProcessor(
            database=self.database,
            http_client=self.http_client,
            content_processor=self.content_processor
        )

    def scan_feeds(self):
        """执行一次完整的扫描"""
        self.logger.info("开始扫描RSS源")
        
        # 重新加载配置
        self.config.load_config()
        feeds = self.config.feeds
        
        # 创建新的扫描记录
        scan_id = self.database.start_scan(len(feeds))
        total_success = 0
        total_error = 0
        error_details = []

        # 处理每个RSS源
        for feed in feeds:
            try:
                self.logger.info(f"处理RSS源: {feed['name']}")
                
                result = self.feed_processor.process_feed(
                    feed_name=feed['name'],
                    feed_url=feed['url'],
                    scan_history_id=scan_id,
                )
                
                total_success += result['success']
                total_error += result['error']
                
            except Exception as e:
                error_msg = f"处理RSS源 {feed['name']} 时发生错误: {str(e)}"
                self.logger.error(error_msg)
                error_details.append(error_msg)
                total_error += 1

        # 更新扫描记录
        self.database.end_scan(
            scan_id=scan_id,
            success_count=total_success,
            error_count=total_error,
            error_detail=error_details
        )
        
        self.logger.info(f"扫描完成 - 成功: {total_success}, 错误: {total_error}")

    def run(self):
        """启动监控程序"""
        self.logger.info("crss启动")
        
        # 立即执行一次扫描
        self.scan_feeds()
        
        # 设置定时任务
        schedule.every(self.config.interval).seconds.do(self.scan_feeds)
        
        # 主循环
        while True:
            try:
                schedule.run_pending()
                time.sleep(1)
            except KeyboardInterrupt:
                self.logger.info("程序被用户中断")
                break
            except Exception as e:
                self.logger.error(f"发生错误: {str(e)}")
                # 继续运行，不中断程序
                continue

def main():
    # 获取配置文件路径
    config_path = os.getenv('RSS_CONFIG', 'config/config.yaml')
    
    try:
        monitor = RSSMonitor(config_path)
        monitor.run()
    except Exception as e:
        logging.error(f"程序启动失败: {str(e)}")
        raise

if __name__ == "__main__":
    main() 