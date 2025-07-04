from typing import Dict, Any, Optional
from app.core.ai_client import AIClient
from lxml import html 
from urllib.parse import urlparse
import re

class DataCleaningService:
    """数据清洗服务，负责处理爬虫获取的原始数据"""
    
    def __init__(self):
        self.ai_client = AIClient()
    
    @staticmethod
    def extract_number(text: str) -> int:
        """从文本中提取数字（公共方法）
        Args:
            text: 包含数字的文本字符串
        Returns:
            提取到的整数，无数字时返回0
        """
        match = re.search(r'\d+', text)
        return int(match.group()) if match else 0

    @staticmethod
    def extract_domain(url: str) -> str:
        """从URL中提取域名（公共方法）
        Args:
            url: 完整URL字符串
        Returns:
            纯域名（不带协议和路径），空URL返回空字符串
        """
        if not url:
            return ''
        # 使用urllib.parse解析URL（更健壮）
        parsed_url = urlparse(url.lower())
        # 处理无协议的URL情况
        domain = parsed_url.netloc or parsed_url.path.split('/')[0]
        return domain
    
    @staticmethod
    def safe_extract(tree: html.HtmlElement, xpath: str) -> str:
        """安全提取单个元素文本

        Args:
            tree: lxml HTML元素对象
            xpath: XPath表达式

        Returns:
            提取到的文本内容或空字符串
        """
        elements = tree.xpath(xpath)
        if elements:
            return elements[0].strip() if isinstance(elements[0], str) else elements[0].text.strip()
        return ''
    
    
    def clean_website_a_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """清洗网站A的数据"""
        # 这里是示例清洗逻辑，实际项目中需要根据数据结构编写清洗逻辑
        cleaned_data = {
            "products": [],
            "categories": []
        }
        
        # 清洗产品数据
        for product in raw_data.get("data", {}).get("products", []):
            cleaned_product = {
                "id": product.get("id"),
                "name": self._clean_text(product.get("name", "")),
                "price": float(product.get("price", 0))
            }
            cleaned_data["products"].append(cleaned_product)
        
        # 清洗分类数据
        for category in raw_data.get("data", {}).get("categories", []):
            cleaned_data["categories"].append(self._clean_text(category))
        
        return cleaned_data
    
    def clean_website_b_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """清洗网站B的数据"""
        # 这里是示例清洗逻辑，实际项目中需要根据数据结构编写清洗逻辑
        cleaned_data = {
            "articles": [],
            "authors": []
        }
        
        # 清洗文章数据
        for article in raw_data.get("data", {}).get("articles", []):
            cleaned_article = {
                "id": article.get("id"),
                "title": self._clean_text(article.get("title", "")),
                "content": self._clean_text(article.get("content", ""))
            }
            cleaned_data["articles"].append(cleaned_article)
        
        # 清洗作者数据
        for author in raw_data.get("data", {}).get("authors", []):
            cleaned_data["authors"].append(self._clean_text(author))
        
        return cleaned_data
    
    def clean_website_c_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """清洗网站C的数据"""
        # 这里是示例清洗逻辑，实际项目中需要根据数据结构编写清洗逻辑
        cleaned_data = {
            "events": [],
            "locations": []
        }
        
        # 清洗事件数据
        for event in raw_data.get("data", {}).get("events", []):
            cleaned_event = {
                "id": event.get("id"),
                "title": self._clean_text(event.get("title", "")),
                "date": self._clean_date(event.get("date", ""))
            }
            cleaned_data["events"].append(cleaned_event)
        
        # 清洗位置数据
        for location in raw_data.get("data", {}).get("locations", []):
            cleaned_data["locations"].append(self._clean_text(location))
        
        return cleaned_data
    
    def _clean_text(self, text: str) -> str:
        """清洗文本数据，去除多余空格和特殊字符"""
        # 简单的文本清洗
        cleaned = text.strip()
        # 可以使用AI进行更复杂的文本清洗
        # cleaned = self.ai_client.enhance_text(cleaned)
        return cleaned
    
    def _clean_date(self, date_str: str) -> str:
        """清洗日期数据"""
        # 简单的日期格式检查
        # 可以使用AI进行更复杂的日期解析
        return date_str
