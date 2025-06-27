import time
import random
from typing import Optional, Dict, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
from app.core.logger import logger
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import requests.exceptions as requests_exceptions

class BaseCrawler:
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((requests_exceptions.Timeout, requests_exceptions.ConnectionError, requests_exceptions.HTTPError))
    )
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

    def _get_page_content(self, url: str, headers: Optional[Dict[str, str]] = None, connect_timeout: int = 10, read_timeout: int = 20) -> str:
        """获取网页内容，带重试和反反爬机制

        参数:
            url: 目标网页URL
            headers: 请求头字典（可选）
            connect_timeout: 连接超时时间(秒)
            read_timeout: 读取超时时间(秒)

        返回:
            网页HTML内容字符串

        异常:
            requests.exceptions.RequestException: 请求失败时抛出
        """
        # 设置默认请求头
        if headers is None:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }

        try:
            # 发送请求（使用合并的超时参数）
            response = self.session.get(
                url,
                headers=headers,
                timeout=(connect_timeout, read_timeout)  # 分别设置连接和读取超时
            )
            response.raise_for_status()  # 触发HTTP错误状态码异常

            # 随机延迟避免反爬（0.5-2秒）
            time.sleep(random.uniform(0.5, 2.0))
            return response.text

        except requests.exceptions.HTTPError as e:
            self.logger.error(f"HTTP错误: {str(e)}，状态码: {response.status_code}")
            raise
        except requests.exceptions.RequestException as e:
            self.logger.error(f"请求失败: {str(e)}")
            raise

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