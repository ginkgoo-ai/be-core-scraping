import asyncio
import json
import re
from app.models.schemas import PageType
from typing import Dict, Any, List
from app.core.logger import logger
from app.crawlers.base_crawler import BaseCrawler
from app.services.data_cleaning import DataCleaningService
from lxml import html
from app.models.data_model import PageType
from app.services.data_storage import DataStorageService
import aiohttp
import httpx 
from app.core.config import settings
from urllib.parse import urljoin

class CrawlerLawsociety(BaseCrawler):
    """HTML片段解析爬虫，处理不同类型页面的HTML片段"""
    source_name = "crawler_lawsociety"
    scrapy_id = "crawler_lawsociety"


    def __init__(self, db=None, scrapy_url: str = None, scrapy_params: dict = None):
        super().__init__(scrapy_url)
        self.db = db
        self.base_url = settings.LAWSOCIETY_BASE_URL
        self.scrapy_params = scrapy_params or {}
        self.page_type = self.scrapy_params.get('page_type')
        self.html_chunk = self.scrapy_params.get('html_chunk')
        self.results = {'companies': [], 'lawyers': []}
        self.parse_method_map = {
            PageType.COMPANY_LIST: self._parse_company_list,
            PageType.COMPANY_DETAIL: self._parse_company_detail,
            PageType.LAWYER_LIST: self._parse_lawyer_list,
            PageType.LAWYER_DETAIL: self._parse_lawyer_detail
        }
        raw_cookie = self.scrapy_params.get('cookies', '')
        self.cookies = self._filter_large_cookies(raw_cookie)
        
    
    
    
    async def crawl(self) -> Dict[str, Any]:
        """执行HTML解析并处理分页逻辑"""
        logger.info(f"开始解析页面，类型: {self.page_type}")

        # 验证输入参数
        if not self.html_chunk and not self.scrapy_url:
            logger.error("未提供HTML片段或初始URL")
            return self.results
        if not self.page_type:
            logger.error("未指定页面类型")
            return self.results

        # 获取解析方法
        parse_method = getattr(self, f"_parse_{self.page_type}", None)
        if not parse_method:
            logger.error(f"不支持的页面类型: {self.page_type}")
            return self.results

        try:
            # 根据页面类型选择处理方式
            if self.page_type in [PageType.COMPANY_LIST, PageType.LAWYER_LIST]:
                # 列表页启用分页爬取
                await self._handle_pagination(self.scrapy_url, parse_method)
            else:
                # 详情页直接解析HTML片段
                tree = html.fromstring(self.html_chunk)
                parse_method(tree)

            # 数据存储处理
            if self.db:
                if self.page_type == PageType.LAWYER_DETAIL:
                    # 提取并保存律师数据
                    lawyers = []
                    for company in self.results['companies']:
                        lawyers.extend(company.get('lawyers', []))
                    await DataStorageService.save_lawyers(
                        db=self.db,
                        source=self.source_name,
                        lawyers=lawyers
                    )
                else:
                    # 保存公司数据
                    await DataStorageService.save_crawled_data(
                        db=self.db,
                        source=self.source_name,
                        companies=self.results['companies']
                    )
                logger.info("数据已成功保存到数据库")
            else:
                logger.warning("数据库会话未提供，无法保存数据")

            logger.info(f"爬取完成，公司: {len(self.results['companies'])}, 律师: {len(self.results['lawyers'])}")
            return self.results

        except Exception as e:
            logger.error(f"爬取过程发生错误: {str(e)}", exc_info=True)
            return self.results
        
    def _filter_large_cookies(self, raw_cookie):
        """
        从原始Cookie中提取关键信息（仅保留fastoken）
        参考tests/api/test.py中的extract_essential_cookies实现
        """
        # 1. 解析Cookie（支持字符串和字典两种输入格式）
        cookie_dict = {}
        if isinstance(raw_cookie, str) and raw_cookie:
            for cookie in raw_cookie.split(';'):
                if '=' in cookie:
                    # 处理值中可能包含的'='符号
                    key, value = cookie.strip().split('=', 1)
                    cookie_dict[key] = value
        elif isinstance(raw_cookie, dict):
            cookie_dict = raw_cookie.copy()
        else:
            logger.warning("无效的Cookie格式，使用空Cookie")
            return {}

        # 2. 仅保留经过验证的关键Cookie（仅fastoken）
        essential_keys = [
            # 'ASP.NET_SessionId',
            # 'ARRAffinity',
            # 'ARRAffinitySameSite',
            # '__RequestVerificationToken',
            # 'fasST',
            'fastoken'
        ]
        # essential_key = 'fastoken'
        filtered_cookies = {
            key: cookie_dict[key] 
            for key in essential_keys 
            if key in cookie_dict
        }
        # 3. 验证结果并记录日志
        cookie_str = '; '.join([f'{k}={v}' for k, v in filtered_cookies.items()])
        logger.info(f"Cookie过滤完成，保留项: {list(filtered_cookies.keys())}, 总长度: {len(cookie_str)}字节")

        return filtered_cookies
    
    
    import httpx

    async def _fetch_page(self, url: str) -> str:
        """发送HTTP请求，使用过滤后的Cookie（httpx实现）"""
        try:
            # 将过滤后的Cookie转换为字符串
            cookie_str = '; '.join([f'{k}={v}' for k, v in self.cookies.items()])
            logger.info(f"请求URL: {url}, Cookie: {cookie_str}")

            # 配置请求头
            headers = {
                'Host': 'solicitors.lawsociety.org.uk',
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'accept-language': 'en,zh-CN;q=0.9,zh;q=0.8',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/138.0.0.0 Safari/537.36',
                'sec-fetch-dest': 'document',
                'sec-fetch-mode': 'navigate',
                'sec-fetch-site': 'same-origin',
                'upgrade-insecure-requests': '1',
                'Connection': 'keep-alive',
                'Cookie': cookie_str
            }

            # 创建httpx异步客户端，禁用默认Cookie管理
            async with httpx.AsyncClient(
                cookies=httpx.Cookies(),  # 空CookieJar，禁用自动Cookie处理
                timeout=30.0,
                limits=httpx.Limits(max_keepalive_connections=5),
                follow_redirects=True
            ) as client:
                response = await client.get(
                    url,
                    headers=headers
                )
                response.raise_for_status()
                return response.text

        except httpx.HTTPStatusError as e:
     
            if e.response.status_code == 503:
                # 针对503错误添加特殊处理逻辑
                raise ValueError(f"请求失败：服务器暂时不可用(503)，请更新Cookies")
            else:
                raise ValueError(f"请求失败：状态码{e.response.status_code}")
        except httpx.RequestError as e:
            # 网络层面错误保持不变
            raise ValueError(f"请求发生网络错误: {str(e)}")
    
            
    async def parse_html(self, page_type: PageType, html_chunk: str):
        """根据页面类型动态调用对应解析方法"""
        # 验证页面类型是否支持
        if page_type not in self.parse_method_map:
            raise ValueError(f"不支持的页面类型: {page_type}")

        # 解析HTML
        soup = self._parse_html(html_chunk)
        
        # 动态调用对应解析方法
        return await self.parse_method_map[page_type](soup)
    
    async def _handle_pagination(self, initial_url: str, parse_method) -> None:
        "处理分页逻辑，循环获取所有页面数据"
        current_url = initial_url
        page_num = 1
        
        while current_url:
            logger.info(f"正在爬取第 {page_num} 页: {current_url}")
            
            # 获取页面内容
            html_content = await self._fetch_page(current_url)
            tree = html.fromstring(html_content)
            
            # 调用解析方法处理当前页数据
            parse_method(tree)
            
            # 提取下一页URL
            next_page = self._extract_next_page_url(tree)
            current_url = urljoin(self.base_url, next_page) if next_page else None
            page_num += 1
           
    
    def _extract_next_page_url(self, tree: html.HtmlElement) -> str:
        "从页面中提取下一页URL"
        next_link = tree.xpath("//a[contains(text(), 'Next') or contains(@class, 'next-page')]/@href")
        return next_link[0] if next_link else None

    def _parse_company_list(self, tree: html.HtmlElement) -> None:
        """解析公司列表页面，提取公司基本信息"""
        # 获取所有公司条目
        company_elements = tree.xpath("//section[contains(@class, 'solicitor-outer')]")
        logger.info(f"找到 {len(company_elements)} 个公司条目")

        for elem in company_elements:
            # 提取公司名称
            name = DataCleaningService.safe_extract(elem, ".//a[@class='token']/text()").strip()
            if not name:
                logger.warning("未提取到公司名称，跳过此条目")
                continue

            # 提取地址信息
            address_elem = elem.xpath(".//li[contains(span/text(), 'Address')]")
            company_address = DataCleaningService.safe_extract(address_elem[0], "./text()[last()]") if address_elem else ""

            # 提取联系电话
            phone_elem = elem.xpath(".//li[contains(span/text(), 'Telephone')]")
            company_phone = DataCleaningService.safe_extract(phone_elem[0], "./text()[last()]") if phone_elem else ""

            # 提取邮箱地址（data-email属性）
            email_elem = elem.xpath(".//a[@class='show-email']")
            company_email = email_elem[0].get('data-email', '') if email_elem else ""

            # 提取网站域名
            website_elem = elem.xpath(".//li[contains(span/text(), 'Website')]/a")
            original_website = website_elem[0].get('href', '') if website_elem else None
            domains = DataCleaningService.extract_domain(original_website) if original_website else ''

            # 提取执业领域（Areas of practice）
            areas_panel = elem.xpath(".//div[contains(@class, 'info-panel') and .//span[contains(text(), 'Areas of practice')]]")
            areas_of_law = []
            if areas_panel:
                # 提取初始显示的领域
                initial_areas = areas_panel[0].xpath(".//ul[contains(@class, 'initial')]/li/text()")
                # 提取更多领域
                more_areas = areas_panel[0].xpath(".//div[contains(@class, 'more-holder')]/ul/li/text()")
                areas_of_law = initial_areas + more_areas

            # 提取认证信息（Accreditations）
            accreditations_panel = elem.xpath(".//div[contains(@class, 'info-panel') and .//span[contains(text(), 'Accreditations')]]")
            accreditations = []
            if accreditations_panel:
                accreditations = accreditations_panel[0].xpath(".//ul[contains(@class, 'initial')]/li/text()")

            # 提取办公室数量和律师数量
            more_info_list = elem.xpath(".//ul[contains(@class, 'more-info-list')]")
            office_num = 0
            total_solicitors_num = 0
            if more_info_list:
                # 提取办公室数量
                office_link = more_info_list[0].xpath(".//li[contains(.//i/@class, 'icon-office-blue')]/a/text()")
                if office_link:
                    office_num =  DataCleaningService.extract_number(office_link[0])

                # 提取律师数量
                solicitor_link = more_info_list[0].xpath(".//li[contains(.//i/@class, 'icon-people-blue')]/a/text()")
                if solicitor_link:
                    total_solicitors_num =  DataCleaningService.extract_number(solicitor_link[0])

            # 构建公司数据
            company_data = {
                'name': name,
                'company_email': company_email,
                'company_phone': company_phone,
                'company_address': company_address,
                'areas_of_law': areas_of_law,
                'total_solicitors': total_solicitors_num,
                'domains': domains,
                'redundant_info': {
                    'accreditations': accreditations,
                    'office_num': office_num
                },
                'source_name': self.source_name
            }
            self.results['companies'].append(company_data)

            # self.firm_data.append(company_data)
            logger.debug(f"已解析公司: {name}, 律师数量: {total_solicitors_num}")

    
    async def _parse_company_detail(self, soup):
        # 新增公司详情解析逻辑
        pass

    def _parse_lawyer_list(self, tree: html.HtmlElement) -> None:
        """解析律师列表页面"""
        # 实现律师列表解析逻辑
        lawyer_elements = tree.xpath("//div[contains(@class, 'lawyer-item')]")
        for elem in lawyer_elements:
            lawyer = {
                'name': DataCleaningService.safe_extract(elem, ".//h3[@class='lawyer-name']/text()"),
                'telephone': DataCleaningService.safe_extract(elem, ".//div[@class='phone']/text()"),
                'email_addresses': DataCleaningService.safe_extract(elem, ".//div[@class='email']/text()"),
                'practice_areas': DataCleaningService.safe_extract(elem, ".//div[@class='practice-areas']/text()").split(", "),
                'source_name': self.source_name
            }
            # 律师列表通常关联到公司，这里需要根据实际情况调整
            if not self.results['companies']:
                self.results['companies'].append({
                    'name': 'Unknown Company',
                    'source_name': self.source_name,
                    'lawyers': [lawyer]
                })
            else:
                self.results['companies'][0]['lawyers'].append(lawyer)

    def _parse_lawyer_detail(self, tree: html.HtmlElement) -> None:
        """解析律师详情页面"""
        # 提取律师姓名
        name = DataCleaningService.safe_extract(tree, "//h1/text()").strip()

        # 提取邮箱地址
        email_values = tree.xpath(
            "//dt[text()='Email']/following-sibling::dd[1]/a[starts-with(@href, 'mailto:')]/@href | "
            "//dt[text()='Email']/following-sibling::dd[1]/a/@data-email"
        )
        email_addresses = ''
        for value in email_values:
            if value.strip():
                # 移除mailto:前缀（如果存在）
                email_addresses = value.replace('mailto:', '').strip()
                break
        

        # 提取电话
        telephone = DataCleaningService.safe_extract(tree, "//dt[text()='Telephone']/following-sibling::dd[1]/text()").strip()

        # 提取地址
        address_parts = tree.xpath("//dd[@class='address']/text()[normalize-space()]")
        address = ', '.join([part.strip() for part in address_parts if part.strip()])

        # 提取执业领域
        areas_of_practice = []
        area_sections = tree.xpath("//section[.//h2[normalize-space(text())='Areas of practice']]//ul[@class='two-cols']/li/text()[normalize-space()]") #//ul[@class='three-cols']/li
        areas_of_practice = [text.strip() for text in area_sections if text.strip()]

        # 提取AdmissionDate
        admission_text = DataCleaningService.safe_extract(tree, "//p[contains(., 'Admitted as a solicitor:')]/span[@class='related']/text()")
        admission_date = re.search(r'(\d{2}/\d{2}/\d{2})', admission_text).group(1) if admission_text else ''
        # 转换为DD/MM/YYYY格式 (假设原格式是DD/MM/YY)
        if admission_date and len(admission_date) == 8:
            admission_date = admission_date[:6] + '20' + admission_date[6:]

        # 提取Roles
        roles = tree.xpath("//dl[@class='multi-line ul']/dd/ul/li/text()")
        roles = [role.strip() for role in roles if role.strip()]

        # 提取Languages
        languages = tree.xpath("//section[.//h2[normalize-space(text())='Languages spoken']]//ul[@class='three-cols']/li/text()")
        languages = [lang.strip() for lang in languages if lang.strip()]

        # 提取accreditations
        accreditations = tree.xpath("//em[@class='highlight' and text()='Accredited']/parent::li/text()")
        accreditations = [acc.strip().replace('\n', '').replace('  ', ' ') for acc in accreditations if acc.strip()]

        # 提取company_name
        company_name = DataCleaningService.safe_extract(tree, "//strong[contains(text(), 'at')]/following-sibling::a/text()").strip()

        # 构建律师数据
        lawyer = {
            'name': name,
            'email_addresses': email_addresses,
            'telephone': telephone,
            'address': address,
            'practice_areas': areas_of_practice,
            'source_name': self.source_name,
            'redundant_info': {
                'AdmissionDate': admission_date,
                'Roles': roles,
                'Languages': languages,
                'accreditations': accreditations,
                'company_name': company_name
            }
        }

        # 查找或创建公司
        company = next((c for c in self.results['companies'] if c['name'] == company_name), None)
        if not company:
            company = {
                'name': company_name,
                'source_name': self.source_name,
                'domains':[],
                'lawyers': []
            }
            self.results['companies'].append(company)
        company['lawyers'].append(lawyer)

