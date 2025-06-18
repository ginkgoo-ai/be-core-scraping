import re
import asyncio
from lxml import html
from typing import Dict, Any, List
from urllib.parse import urlparse 
from app.core.logger import logger
from app.crawlers.base_crawler import BaseCrawler

class CrawlerLawsocni(BaseCrawler):
    """Lawsocni网站爬虫实现，遵循项目标准爬虫接口"""
    source_name = "crawler_lawsocni"
    scrapy_id = "crawler_lawsocni"

    def __init__(self, scrapy_url: str):
        super().__init__(scrapy_url)
        self.firm_data: List[Dict[str, Any]] = []
    
    def _parse_html(self, html_content: str) -> html.HtmlElement:
        """使用lxml解析HTML内容，返回HtmlElement对象"""
        if not html_content:
            logger.error("空的HTML内容，无法解析")
            raise ValueError("HTML content cannot be empty")
        return html.fromstring(html_content)

    async def crawl(self) -> Dict[str, Any]:
        """执行爬取操作，返回标准化的爬取结果
        符合BaseCrawler抽象方法要求，返回格式为{
            'companies': [...],
            'lawyers': [...]
        }
        """
        logger.info(f"开始爬取 {self.source_name} 网站，URL: {self.scrapy_url}")
        try:
            # 获取搜索页面内容
            html_content = self._get_page_content(self.scrapy_url)
            tree = self._parse_html(html_content)

            # 提取公司详情页URL
            firm_urls = self._extract_firm_urls(tree)
            if not firm_urls:
                logger.warning("未提取到任何公司URL，爬取终止")
                return {'companies': [], 'lawyers': []}

            logger.info(f"成功提取到 {len(firm_urls)} 个公司URL，开始异步爬取详情页")
            # 创建任务列表并并发执行
            tasks = [self._fetch_and_parse_detail(url) for url in firm_urls]
            await asyncio.gather(*tasks)

            logger.info(f"{self.source_name} 网站爬取完成，共获取 {len(self.firm_data)} 家公司数据")
            return self._format_output()

        except Exception as e:
            logger.error(f"爬取过程发生错误: {str(e)}", exc_info=True)
            raise

    def _extract_firm_urls(self, tree: html.HtmlElement) -> List[str]:
        """使用XPath提取公司详情页URL"""
        if tree is None or len(tree) == 0:
            self.logger.warning("无法从页面提取公司URL，树结构为空")
            return []
        xpath_expr = "//a[contains(@class, 'print')]/@href"
        return tree.xpath(xpath_expr)

    async def _fetch_and_parse_detail(self, firm_url: str) -> None:
        """异步获取并解析公司详情页"""
        try:
            # 使用线程池执行同步的网络请求，避免阻塞事件循环
            loop = asyncio.get_event_loop()
            html_content = await loop.run_in_executor(
                None, self._get_page_content, firm_url
            )
            tree = self._parse_html(html_content)
            firm_info = self._parse_detail_page(tree, firm_url)
            if firm_info:
                self.firm_data.append(firm_info)
        except Exception as e:
            logger.error(f"处理详情页 {firm_url} 失败: {str(e)}")

    def _parse_detail_page(self, tree, firm_url: str) -> Dict[str, Any]:
        """解析公司详情页数据"""
        # 提取公司基本信息
        firm_names = self._safe_extract(tree, "//div[contains(@class, 'section-heading')]/h1/span/text()")
        firm_name = firm_names[0].strip() if firm_names else ""
        if not firm_name:
            logger.warning(f"无法提取公司名称，URL: {firm_url}")
            return {}

        # 提取联系信息
        
        firm_email = self._extract_email(tree)
        firm_phone = self._extract_phone(tree)
        firm_website = self._extract_website(tree)
        firm_address = self._extract_address(tree)

        # 提取人员和专业领域信息
        solicitors = self._extract_solicitors(tree)
        areas_of_expertise = self._extract_expertise(tree)

        return {
            'name': firm_name,
            'email': firm_email,
            'phone': firm_phone,
            'website': firm_website,
            'address': firm_address,
            'solicitors': solicitors,
            'areas_of_expertise': areas_of_expertise
        }

    def _format_output(self) -> Dict[str, List[Dict[str, Any]]]:
        """格式化输出为项目标准格式"""
        companies = []
        # lawyers = []

        for firm in self.firm_data:
            website = firm['website']
            domain = ""
            if website:
                parsed_url = urlparse(website)
                domain = parsed_url.netloc or parsed_url.path.split('/')[0]
                domain = domain.lstrip('www.')
            # 公司数据
            company = {
                'name': firm['name'],
                'company_email': firm['email'],
                'company_phone': firm['phone'],
                'company_address': firm['address'],
                'domains': domain,
                'areas_of_law': firm['areas_of_expertise'],
                'lawyers': [{
                    'name': lawyer_name,
                    'practice_areas': firm['areas_of_expertise'],
                    'source': self.source_name
                } for lawyer_name in firm['solicitors']]
            }
            companies.append(company)

            # 律师数据
            # for lawyer_name in firm['solicitors']:
            #     lawyer = {
            #         'name': lawyer_name,
            #         'company_id': None,  # 将由存储服务关联
            #         'practice_areas': firm['areas_of_expertise'],
            #         'source': self.source_name
            #     }
            #     lawyers.append(lawyer)

        return {'companies': companies}

    # 辅助提取方法
    def _safe_extract(self, tree: html.HtmlElement, xpath: str) -> str:
        """安全提取单个元素文本"""
        elements = tree.xpath(xpath)
        if elements:
            return elements[0].strip() if isinstance(elements[0], str) else elements[0].text.strip()
        return ''
    def _extract_website(self, tree: html.HtmlElement) -> str:
        try:
            # 使用 lxml 正确的属性获取方式
            links = tree.xpath("//a[@target='_blank' and contains(@href, 'http')]")
            if links and isinstance(links[0], html.HtmlElement):
                # 直接使用 .get() 方法，无需 .attrs
                return links[0].get('href', '').strip()
            return ''
        except Exception as e:
            self.logger.error(f"提取网站链接失败: {str(e)}")
            return ''
    def _extract_email(self, tree: html.HtmlElement) -> str:
        """提取邮箱地址"""
        mailto_links = tree.xpath("//a[contains(@href, 'mailto')]/@href")
        if mailto_links:
            mailto_link = mailto_links[0]
            return mailto_link.split(':', 1)[-1].strip()
        return ''

    def _extract_phone(self, tree: html.HtmlElement) -> str:
        """使用XPath提取电话"""
        tel_links = tree.xpath("//a[contains(@href, 'tel')]/@href")
        if tel_links:
            return tel_links[0].split(':', 1)[1] if ':' in tel_links[0] else ""
        return ''

    def _extract_address(self, tree: html.HtmlElement) -> str:
        try:
            address_elements = tree.xpath("//div[contains(@class, 'address')]")
            if address_elements and isinstance(address_elements[0], html.HtmlElement):
                # 修复：使用 .get() 替代 .attrs.get()
                address = address_elements[0].get('content', '').strip()
                return address
            return ''
        except Exception as e:
            self.logger.error(f"提取地址失败: {str(e)}")
            return ''

    def _extract_solicitors(self, tree: html.HtmlElement) -> List[str]:
        """提取律师列表"""
        elements = tree.xpath("//span[@class='font-bold ']/text()")
        return [elem.strip() for elem in elements if elem.strip()]

    def _extract_expertise(self, tree: html.HtmlElement) -> List[str]:
        """提取专业领域列表"""
        elements = tree.xpath("//span[contains(@class, 'font-bold') and contains(@class, 'leading-[24px]')]/text()")
        return [elem.strip() for elem in elements if elem.strip()]