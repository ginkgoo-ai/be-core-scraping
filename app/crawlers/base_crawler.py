import abc
import requests
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup
from app.core.logger import logger

class BaseCrawler(abc.ABC):
    """爬虫基类，定义所有爬虫必须实现的方法"""
    
    def __init__(self, scrapy_url: str):
        self.scrapy_url = scrapy_url
        self.logger = logger
    
    @abc.abstractmethod
    async def crawl(self) -> Dict[str, Any]:
        """执行爬取操作，返回原始数据"""
        pass
    
    def _get_page_content(self, url: str, headers: Optional[Dict[str, str]] = None) -> str:
        """获取网页内容的辅助方法"""
        if headers is None:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.text
    
    def _parse_html(self, html_content: str) -> BeautifulSoup:
        """解析HTML内容的辅助方法"""
        return BeautifulSoup(html_content, "html.parser")
    
    def handle_error(self, failure):
        """统一错误处理方法"""
        request = failure.request
        self.logger.error(
            f"请求失败: URL={request.url}, "
            f"状态码={failure.value.response.status if hasattr(failure.value, 'response') else 'N/A'}"
        )