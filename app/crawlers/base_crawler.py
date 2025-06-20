import time
import random
from typing import Optional, Dict, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
from app.core.logger import logger

class BaseCrawler:
    def __init__(self, scrapy_url: str):
        # 核心属性初始化
        self.scrapy_url = scrapy_url
        self.logger = logger
        
        # 创建带重试机制的Session
        self.session = requests.Session()
        retry_strategy = Retry(
            total=5,  # 总重试次数
            backoff_factor=1,  # 退避因子（1s, 2s, 4s...）
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    async def crawl(self) -> Dict[str, Any]:
        """执行爬取操作，返回原始数据（需子类实现）"""
        raise NotImplementedError("子类必须实现crawl方法")

    def _get_page_content(self, url: str, headers: Optional[Dict[str, str]] = None) -> str:
        """获取网页内容，带重试和反反爬机制"""
        # 设置默认请求头
        if headers is None:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }

        max_retries = 3
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                # 使用带重试机制的session发送请求
                response = self.session.get(url, headers=headers, timeout=15)
                response.raise_for_status()
                
                # 随机延迟避免被反爬
                time.sleep(random.uniform(0.5, 1.0))
                return response.text
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                if attempt < max_retries - 1:
                    self.logger.warning(f"请求失败（{attempt+1}/{max_retries}）: {str(e)}，将重试...")
                    time.sleep(retry_delay * (2 **attempt))  # 指数退避
                    continue
                self.logger.error(f"请求最终失败：{str(e)}")
                raise
            except Exception as e:
                self.logger.error(f"请求异常：{str(e)}")
                raise
        return None

    def _parse_html(self, html_content: str) -> BeautifulSoup:
        """解析HTML内容"""
        return BeautifulSoup(html_content, "html.parser")

    def handle_error(self, failure):
        """统一错误处理"""
        request = failure.request
        self.logger.error(
            f"请求失败: URL={request.url}, "
            f"状态码={failure.value.response.status if hasattr(failure.value, 'response') else 'N/A'}"
        )