import re
import asyncio
from lxml import html
from typing import Dict, Any, List
from urllib.parse import urlparse 
from app.core.logger import logger
from app.crawlers.base_crawler import BaseCrawler
import urllib.parse

class CrawlerLawsocni(BaseCrawler):
    """Lawsocni网站爬虫实现，遵循项目标准爬虫接口"""
    source_name = "crawler_lawsocni" #Law Society of Northern lreland
    scrapy_id = "crawler_lawsocni"


    def __init__(self, scrapy_url: str, scrapy_params: dict = None):
        super().__init__(scrapy_url)
        self.scrapy_params = scrapy_params or {}
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
       
        
        parsed_url = urllib.parse.urlparse(self.scrapy_url)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        
        # 严格判断是否存在limit参数
        
        try:
            if 'limit' not in query_params:
            # 构建新参数
                query_params['limit'] = ['9999']
                new_query = urllib.parse.urlencode(query_params, doseq=True)
                # 重构完整URL（自动处理?和&的拼接）
                modified_url = urllib.parse.urlunparse(
                    (parsed_url.scheme, parsed_url.netloc, parsed_url.path,
                    parsed_url.params, new_query, parsed_url.fragment)
                )
                self.logger.info(f"Added limit=9999 to URL: {modified_url}")
            else:
                modified_url = self.scrapy_url
                self.logger.info(f"URL already contains limit parameter: {modified_url}")
            # 获取搜索页面内容
            logger.info(f"开始爬取 {self.source_name} 请求网站，URL: {self.scrapy_url}，实际请求：{modified_url}")
            html_content = self._get_page_content(modified_url)
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
        firm_names = tree.xpath("//div[contains(@class, 'section-heading')]/h1/span/text()")
        firm_name = firm_names[0].strip() if firm_names else ""
        if not firm_name:
            logger.warning(f"无法提取公司名称，URL: {firm_url}")
            return {}

        # 提取联系信息
        firm_email = self._extract_email(tree)
        firm_phone = self._extract_phone(tree)
        firm_website = self._extract_website(tree)
        firm_address, city = self._extract_address(tree)
        solicitors = self._extract_solicitors(tree)
        areas_of_expertise = self._extract_expertise(tree)
        

        return {
            'name': firm_name,
            'email': firm_email,
            'phone': firm_phone,
            'website': firm_website,
            'address': firm_address,
            'solicitors': solicitors,
            'areas_of_expertise': areas_of_expertise,
            'city': city  # 添加城市信息
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
                'source_name':self.source_name,
                'redundant_info': {
                    'city': firm['city']  # 添加城市信息
                },
                'lawyers': [{
                    'name': lawyer_name,
                    'practice_areas': firm['areas_of_expertise'],
                    'source_name':self.source_name
                    
                }  for lawyer_name in firm['solicitors'] if lawyer_name.strip()]
            }
            companies.append(company)
            logger.info(f"格式化公司数据: {company['name']}, 律师数量: {len(company['lawyers'])}")
        logger.info(f"数据格式化完成，共 {len(companies)} 家公司，{sum(len(c['lawyers']) for c in companies)} 名律师")
        return {'companies': companies}


    # 辅助提取方法
    def _safe_extract(self, tree: html.HtmlElement, xpath: str) -> str:
        """安全提取单个元素文本"""
        elements = tree.xpath(xpath)
        if elements:
            return elements[0].strip() if isinstance(elements[0], str) else elements[0].text.strip()
        return ''
    
    def _extract_website(self, tree: html.HtmlElement) -> str:
        """提取网站地址"""
        try:
            links = tree.xpath("//a[contains(., 'Visit the Website')]/@href")
            if links:
                return links[0].strip()
            return ''
        except Exception as e:
            self.logger.error(f"提取网站链接失败: {str(e)}")
            return ''
    def _extract_email(self, tree: html.HtmlElement) -> str:
        """提取邮箱地址"""
        mailto_links = tree.xpath("//a[contains(., 'Send Enquiry')]/@href")
        if mailto_links:
            mailto_link = mailto_links[0]
            return mailto_link.split(':', 1)[-1].strip()
        return ''

    def _extract_phone(self, tree: html.HtmlElement) -> str:
        """使用XPath提取电话"""
        tel_links = tree.xpath("//a[contains(., 'Call Now')]/@href")
        if tel_links:
            return tel_links[0].split(':', 1)[1] if ':' in tel_links[0] else ""
        return ''

    def _extract_address(self, tree: html.HtmlElement) -> str:
        """使用XPath提取地址并清理格式"""
        try:
            import re
            address_elements = tree.xpath("//address/text()")
            # 合并文本节点并移除所有空白字符（包括换行和制表符）
            address_parts = [re.sub(r'\s+', ' ', elem.strip()) for elem in address_elements if elem.strip()]
            address = ' '.join(address_parts)
            # 处理逗号前后的空格
            address = re.sub(r'\s*,\s*', ', ', address)
            # 处理连字符前后的空格（保留数字间的空格）
            address = re.sub(r'(?<!\d)\s+-\s+(?!\d)', '-', address)
            city = self._extract_city_from_address(address)
            return address, city
        except Exception as e:
            self.logger.error(f"提取地址失败: {str(e)}")
            return ''
    def _extract_city_from_address(self, address: str) -> str:
        """从地址字符串中提取城市名"""
        if not address:
            return ''
        # 按逗号分割地址并清洗空格
        address_parts = [part.strip() for part in address.split(',') if part.strip()]
        # 检测是否包含郡信息(不区分大小写)
        has_county = any("county" in part.lower() for part in address_parts)
        
        # 根据地址格式确定城市位置
        if len(address_parts) >= 2:
            # 带郡格式取倒数第三位，否则取倒数第二位
            city_index = -3 if (has_county and len(address_parts)>=3) else -2
            city = address_parts[city_index]
            
            # 特殊情况处理：如果提取到的是郡则降级取前一位
            if "county" in city.lower() and len(address_parts) > abs(city_index):
                city = address_parts[city_index-1]
            return city
        return ''
    def _extract_solicitors(self, tree: html.HtmlElement) -> List[str]:
        """提取律师列表"""
        elements = tree.xpath("//span[@class='font-bold ']/text()") #这里Xpath的空格要保留，源站就是这样的
        # 该网站律师名字返回的全大写，进行调整以提高可读
        formatted_names = []
        for elem in elements:
            raw_name = elem.strip()
            if not raw_name:
                continue  
            # 正则匹配名字和后缀（支持多种格式："NAME SUFFIX", "NAME, SUFFIX", "NAME (SUFFIX)"）
            match = re.match(
            r'^(?P<name>[\w\s\-\']+?)(?:\s+|\,|\()(?P<suffix>[A-Z]{2,4}(?:\s+[A-Z]{2,4})?)?\)?$',
            raw_name
        )
            if match:
                name_parts = match.group('name').split()
                suffix = match.group('suffix') or ""
                # 格式化名字
                formatted_name = " ".join([part.capitalize() for part in name_parts])
                # 追加后缀（去空格并保留原始格式）
                if suffix:
                    formatted_name += f" {suffix.strip()}"  
                formatted_names.append(formatted_name)
    
        return [name for name in formatted_names if name]
       

    def _extract_expertise(self, tree: html.HtmlElement) -> List[str]:
        """提取专业领域列表"""
        elements = tree.xpath("//span[contains(@class, 'font-bold') and contains(@class, 'leading-[24px]')]/text()")
        return [elem.strip() for elem in elements if elem.strip()]