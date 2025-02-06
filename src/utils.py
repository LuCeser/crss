from hashlib import blake2b
from urllib.parse import urlparse, urlunparse
import logging
from datetime import datetime
import os

def setup_logging(log_file):
    """设置日志"""
    log_dir = os.path.dirname(log_file)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def normalize_url(url):
    """规范化URL"""
    parsed = urlparse(url)
    normalized = parsed._replace(
        netloc=parsed.netloc.lower(),
        fragment=''
    )
    return urlunparse(normalized)

def get_link_hash(url):
    """获取规范化URL的哈希值"""
    normalized_url = normalize_url(url)
    return blake2b(normalized_url.encode(), digest_size=16).hexdigest() 