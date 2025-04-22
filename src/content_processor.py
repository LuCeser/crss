import logging
import re
from enum import Enum
from typing import Dict, Optional
from urllib.parse import urlparse

import markitdown
import requests

logger = logging.getLogger(__name__)

class ContentType(Enum):
    ARTICLE = "article"
    YOUTUBE = "youtube"
    PODCAST = "podcast"
    OTHER = "other"

class ContentProcessor:
    def __init__(self, llm_config: Dict):
        self.llm_config = llm_config
        self.md = markitdown.MarkItDown()
        self.headers = {
            "Authorization": f"Bearer {llm_config['api_key']}",
            "Content-Type": "application/json"
        }

    def detect_content_type(self, url: str, entry: Dict) -> ContentType:
        """检测内容类型"""
        domain = urlparse(url).netloc.lower()
        
        # YouTube 视频检测
        if any(yt_domain in domain for yt_domain in ['youtube.com', 'youtu.be']):
            return ContentType.YOUTUBE
        
        # Podcast 检测 (检查 enclosures 和 media 标签)
        if hasattr(entry, 'enclosures') and entry.enclosures:
            for enclosure in entry.enclosures:
                if 'audio' in enclosure.get('type', ''):
                    return ContentType.PODCAST
                    
        if hasattr(entry, 'media_content'):
            for media in entry.media_content:
                if 'audio' in media.get('type', ''):
                    return ContentType.PODCAST
        
        # 默认作为文章处理
        return ContentType.ARTICLE

    def process_content(self, url: str, entry: Dict, content_type: ContentType) -> Dict:
        """根据内容类型进行处理"""
        try:
            if content_type == ContentType.ARTICLE:
                return self._process_article(url)
            elif content_type == ContentType.YOUTUBE:
                return self._process_youtube(url, entry)
            elif content_type == ContentType.PODCAST:
                return self._process_podcast(url, entry)
            else:
                return self._process_other(url, entry)
        except Exception as e:
            logger.error(f"内容处理失败: {str(e)}")
            return {}

    def _process_article(self, url: str) -> Dict:
        """处理文章内容"""
        try:
            markdown_content = self.md.convert_url(url)
            if markdown_content:
                return {
                    'type': 'article',
                    'markdown_content': markdown_content,
                    'analysis': self._analyze_with_llm(markdown_content.text_content)
                }
        except Exception as e:
            logger.error(f"文章处理失败: {str(e)}")
        return {'type': 'article'}

    def _process_youtube(self, url: str, entry: Dict) -> Dict:
        """处理YouTube视频"""
        video_id = self._extract_youtube_id(url)
        return {
            'type': 'youtube',
            'video_id': video_id,
            'thumbnail': f'https://img.youtube.com/vi/{video_id}/maxresdefault.jpg',
            'duration': entry.get('media_content', [{}])[0].get('duration', ''),
            'original_url': url
        }

    def _process_podcast(self, url: str, entry: Dict) -> Dict:
        """处理播客内容"""
        audio_url = ''
        duration = ''
        
        # 尝试从 enclosures 获取音频 URL
        if hasattr(entry, 'enclosures') and entry.enclosures:
            for enclosure in entry.enclosures:
                if 'audio' in enclosure.get('type', ''):
                    audio_url = enclosure.get('href', '')
                    break
        
        # 尝试获取时长
        if hasattr(entry, 'itunes_duration'):
            duration = entry.itunes_duration
        
        return {
            'type': 'podcast',
            'audio_url': audio_url,
            'duration': duration,
            'original_url': url
        }

    def _process_other(self, url: str, entry: Dict) -> Dict:
        """处理其他类型内容"""
        return {
            'type': 'other',
            'original_url': url
        }

    def _extract_youtube_id(self, url: str) -> Optional[str]:
        """提取YouTube视频ID"""
        youtube_regex = (
            r'(?:youtube(?:-nocookie)?\.com/(?:[^/]+/.+/|(?:v|e(?:mbed)?)/|.*[?&]v=)|youtu\.be/)'
            r'([^"&?/ ]{11})'
        )
        match = re.search(youtube_regex, url)
        return match.group(1) if match else None

    def _analyze_with_llm(self, content: str) -> Dict:
        """使用LLM分析文章内容"""
        try:
            # 获取摘要作为描述
            summary_prompt = ("作为一名资深编辑，阅读以下文章内容并输出\n"
                              "1. 一句话核心摘要\n"
                              "2. 文章结构（列出 3～5个小标题或段落主题）\n"
                              "3. 建议：是否值得阅读全文？请简要说明理由（20字以内）")
            summary = self._get_llm_response(summary_prompt + "\n\n" + content)

            # 获取标签，要求返回数组格式
            # tags_prompt = "请为这篇文章提供3-5个标签，直接返回标签数组，用逗号分隔："
            # tags = self._get_llm_response(tags_prompt + "\n\n" + content)

            return {
                'summary': summary.strip(),
            }
        except Exception as e:
            logger.error(f"LLM分析失败: {str(e)}")
            return {}

    def _get_llm_response(self, prompt: str) -> str:
        """调用LLM API获取响应"""
        try:
            response = requests.post(
                self.llm_config['api_url'],
                headers=self.headers,
                json={
                    "model": self.llm_config['model'],
                    "messages": [
                        {"role": "system", "content": "你是一个专业的文章分析助手，请简洁直接地回答问题。"},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": self.llm_config['temperature'],
                    "max_tokens": self.llm_config['max_tokens']
                }
            )
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']
        except Exception as e:
            logger.error(f"LLM API调用失败: {str(e)}")
            return ""

    def convert_to_markdown(self, url: str) -> Optional[str]:
        """将文章转换为Markdown格式"""
        try:
            # 使用 markitdown 转换内容
            markdown_content = markitdown.parse_article(url)
            return markdown_content
        except Exception as e:
            logger.error(f"转换Markdown失败: {str(e)}")
            return None

    def analyze_content(self, content: str, prompts: Dict) -> Dict:
        """使用LLM分析内容"""
        try:
            results = {}
            
            # 获取摘要
            results['summary'] = self._get_llm_response(
                prompts['summary'] + "\n\n" + content
            )
            
            # 获取标签
            results['tags'] = self._get_llm_response(
                prompts['tags'] + "\n\n" + content
            )
            
            # 判断是否值得读
            results['worth_reading'] = self._get_llm_response(
                prompts['worth_reading'] + "\n\n" + content
            )
            
            return results
        except Exception as e:
            logger.error(f"内容分析失败: {str(e)}")
            return {} 