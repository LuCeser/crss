# crss

一个简单的 RSS 监控工具，用于定时扫描 RSS 源并将新内容推送到指定的 HTTP 接口。

## 项目目标

- 定时扫描配置的 RSS 源
- 检测新内容并通过 HTTP 请求推送
- 避免重复推送相同内容
- 记录处理历史和错误信息

## 技术架构

### 目录结构

```
rss_monitor/
├── config/
│ └── config.yaml # 配置文件
├── src/
│ ├── init.py
│ ├── config.py # 配置加载
│ ├── database.py # 数据库操作
│ ├── feed.py # RSS处理
│ ├── http_client.py # HTTP请求
│ └── utils.py # 工具函数
├── logs/ # 日志目录
├── requirements.txt # 依赖包
└── main.py # 主程序
```

### 核心组件

1. **配置管理 (config.py)**
   - 加载 YAML 配置文件
   - 提供配置项访问接口
   - 支持运行时重新加载

2. **数据库 (database.py)**
   - 使用 SQLite 存储数据
   - 表结构：
     - scan_history：记录扫描操作历史
     - processed_items：记录已处理的条目

3. **RSS处理 (feed.py)**
   - 解析 RSS 源
   - 提取文章信息
   - 处理重复检查

4. **HTTP客户端 (http_client.py)**
   - 发送 POST 请求到目标 API
   - 统一的错误处理

### 数据结构

1. scan_history 表

```sql
CREATE TABLE scan_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    total_feeds INTEGER,
    success_count INTEGER,
    error_count INTEGER,
    error_detail TEXT
);
```

2. processed_items 表
```sql
CREATE TABLE processed_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    feed_name TEXT NOT NULL,
    item_link TEXT NOT NULL,
    item_title TEXT NOT NULL,
    link_hash CHAR(32) NOT NULL,
    processed_time TIMESTAMP,
    scan_history_id INTEGER,
    status TEXT,
    error_message TEXT,
    UNIQUE(link_hash)
);
```

### 配置文件格式

```yaml
interval: 300              # 扫描间隔（秒）
database: "feeds.db"       # 数据库文件路径
log_file: "logs/rss.log"  # 日志文件路径
target_api: "http://api.example.com/webhook"  # 推送接口

feeds:
  - name: "源名称"
    url: "RSS源URL"
```

### HTTP 推送格式

```json
{
    "type": "url",
    "title": "文章标题",
    "content": "文章链接",
    "folder": "RSS"
}
```

## 特性

1. **URL 去重**
   - 使用 Blake2b 哈希算法
   - URL 规范化处理
   - 通过数据库唯一索引保证

2. **错误处理**
   - 详细的日志记录
   - 单个源错误不影响整体运行
   - 支持错误重试

3. **运行时更新**
   - 支持动态更新 RSS 源配置
   - 每次扫描前重新加载配置

## 使用方法

1. 安装依赖：
```bash
pip install -r requirements.txt
```

2. 配置：
   - 复制并修改 config.yaml
   - 设置 RSS 源和目标 API

3. 运行：
```bash
python main.py
```

## 开发状态

- [x] 基础框架搭建
- [x] 配置管理
- [x] 数据库设计
- [x] RSS 处理
- [x] HTTP 推送
- [x] 错误处理
- [x] 日志系统

## 未来改进

1. 可能的优化方向：
   - 添加命令行参数支持
   - 支持多种推送方式
   - 添加 Web 管理界面
   - 支持更多的 RSS 格式

