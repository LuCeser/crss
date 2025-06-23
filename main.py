import logging
import os
import time
from datetime import datetime
import pytz

import schedule

from src.config import Config
from src.content_processor import ContentProcessor
from src.database import Database
from src.feed import FeedProcessor
from src.http_client import HTTPClient
from src.utils import setup_logging
from src.summary_generator import SummaryGenerator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RSSMonitor:
    def __init__(self, config_path: str):
        # 加载配置
        self.config = Config(config_path)
        
        # 设置时区
        self.timezone = pytz.timezone(getattr(self.config, 'timezone', 'Asia/Shanghai'))
        os.environ['TZ'] = self.timezone.zone
        time.tzset()  # 更新系统时区
        self.logger = setup_logging(self.config.log_file)
        self.logger.info(f"使用时区: {self.timezone.zone}")

        self.schedule_times = self.config.schedule_times

        # 获取代理配置
        proxy_config = getattr(self.config, 'proxy', None)
        if proxy_config:
            self.logger.info(f"使用代理配置: HTTP={proxy_config.get('http', 'None')}, "
                           f"HTTPS={proxy_config.get('https', 'None')}")
        
        # 初始化组件
        self.database = Database(self.config.database)
        self.http_client = HTTPClient(self.config.target_api, proxy_config)
        
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
        current_time = datetime.now(self.timezone).strftime('%Y-%m-%d %H:%M:%S %Z')
        self.logger.info(f"开始扫描RSS源 - 当前时间: {current_time}")
        
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
        
        # 设置定时任务 - 为每个配置的时间点创建调度
        for time_str in self.schedule_times:
            schedule.every().day.at(time_str).do(self.scan_feeds)
            self.logger.info(f"已设置每日 {time_str} ({self.timezone.zone}) 运行扫描任务")
        
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

def process_feeds():
    """处理所有RSS源"""
    try:
        # 初始化组件
        config = Config()
        db = Database(config.get('database'))
        http_client = HTTPClient(config.get('target_api'))
        content_processor = ContentProcessor(config.get('llm'))
        feed_processor = FeedProcessor(db, http_client, content_processor)
        
        # 处理RSS源
        feed_processor.process_all_feeds()
        
        # 生成每日摘要
        summary_generator = SummaryGenerator(content_processor, db, config.get('llm'))
        summary = summary_generator.generate_daily_summary()
        
        # 推送摘要
        if summary and summary != "今天没有新的文章。":
            http_client.send_message({
                "type": "summary",
                "title": f"每日摘要 - {datetime.now().strftime('%Y-%m-%d')}",
                "content": summary,
                "folder": "RSS Summary"
            })
            
    except Exception as e:
        logger.error(f"处理RSS源时发生错误: {str(e)}")

def main():
    """主函数"""
    config = Config()
    schedule_times = config.get('schedule_times', ['09:00', '12:00', '18:00'])
    
    # 设置定时任务
    for time_str in schedule_times:
        schedule.every().day.at(time_str).do(process_feeds)
    
    logger.info(f"已设置定时任务: {schedule_times}")
    
    # 运行定时任务
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    main() 