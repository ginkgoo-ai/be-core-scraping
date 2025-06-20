import asyncio
import json
import re
from urllib.parse import urlparse
from lxml import html
from typing import Dict, Any, List
from app.core.logger import logger
from app.services.data_storage import DataStorageService
from app.crawlers.base_crawler import BaseCrawler


class CrawlerLawscot(BaseCrawler):
    """Lawscot网站爬虫实现，遵循项目标准爬虫接口"""
    source_name = "crawler_lawscot"
    scrapy_id = "crawler_lawscot"
    base_url = "https://www.lawscot.org.uk/umbraco/surface/Imis"

    def __init__(self, scrapy_url: str):
        super().__init__(scrapy_url)
        self.firm_data: List[Dict[str, Any]] = []


    def _parse_html(self, html_content: str) -> html.HtmlElement:
        """使用lxml解析HTML内容，返回HtmlElement对象"""
        if not html_content:
            logger.error("空的HTML内容，无法解析")
            raise ValueError("HTML content cannot be empty")
        return html.fromstring(html_content)

    def _safe_extract(self, tree: html.HtmlElement, xpath: str) -> str:
        """安全提取单个元素文本"""
        elements = tree.xpath(xpath)
        if elements:
            return elements[0].strip() if isinstance(elements[0], str) else elements[0].text.strip()
        return ''

    async def crawl(self) -> Dict[str, Any]:
        """执行爬取操作，返回标准化的爬取结果
        符合BaseCrawler抽象方法要求，返回格式为{
            'companies': [...],
            'lawyers': [...]}
        """
        logger.info(f"开始爬取 {self.source_name} 网站，URL: {self.scrapy_url}")
        try:
            # 获取搜索页面内容
            html_content = await self._fetch_page_content(self.scrapy_url)
            tree = self._parse_html(html_content)

            # 提取公司ID
            firm_ids = self._extract_firm_ids(tree)
            if not firm_ids:
                logger.warning("未提取到任何公司ID，爬取终止")
                return {'companies': [], 'lawyers': []}

            logger.info(f"成功提取到 {len(firm_ids)} 个公司ID，开始异步爬取详情页")
            # 创建任务列表并并发执行
            tasks = [self._fetch_and_parse_detail(firm_id) for firm_id in firm_ids]
            await asyncio.gather(*tasks)
            logger.info(f"{self.source_name} 网站爬取完成，共获取 {len(self.firm_data)} 家公司数据")
            
            result = self._format_output()
            total_lawyers = sum(len(company.get('lawyers', [])) for company in result['companies'])
            logger.info(f"爬取结果：{len(result['companies'])}家公司，{total_lawyers}名律师准备存储")
            return result

        except Exception as e:
            logger.error(f"爬取过程发生错误: {str(e)}", exc_info=True)
            raise

    async def _fetch_page_content(self, url: str) -> str:
        """异步获取页面内容"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._get_page_content, url
        )

    def _extract_firm_ids(self, tree: html.HtmlElement) -> List[str]:
        """使用XPath提取公司ID"""
        if tree is None or len(tree) == 0:
            self.logger.warning("无法从页面提取公司ID，树结构为空")
            return []
        xpath_expr = "//button[contains(@class, 'print')]/@data-list-item-id"
        return tree.xpath(xpath_expr)

    async def _fetch_and_parse_detail(self, firm_id: str) -> None:
        """异步获取并解析公司详情页"""
        try:
            url = f"{self.base_url}/GetLegalFirmDetail?id={firm_id}"
            content = await self._fetch_page_content(url)
            data = json.loads(content)
            await self._parse_firm_data(data, firm_id)
        except json.JSONDecodeError:
            logger.error(f"公司ID {firm_id} 响应不是有效的JSON")
        except Exception as e:
            logger.error(f"处理公司ID {firm_id} 失败: {str(e)}")

    async def _parse_firm_data(self, data: Dict[str, Any], firm_id: str) -> None:
        """解析公司JSON数据并提取信息"""
        # 提取公司基本信息
        total_solicitors = data.get('TotalSolicitorCount')
        total_solicitors_num = int(total_solicitors) if total_solicitors is not None else 0

        scottish_partners = data.get('ScottishPartnerCount')
        scottish_partners_num = int(scottish_partners) if scottish_partners is not None else 0

        # 提取原始 Website 和 Email
        original_website = data.get('Website')
        email = data.get('Email')

        # 优化 Website 逻辑
        public_domains = {'gmail.com', 'me.com', 'yahoo.com', 'hotmail.com', 'msn.com','hotmail.co.uk','outlook.com'}
        if not original_website and email and '@' in email:
            email_suffix = email.split('@')[-1].lower()
            if email_suffix not in public_domains:
                original_website = email_suffix

        # 构建公司数据
        company_data = {
            'name': data.get('Company'),
            'company_email': email,
            'company_phone': data.get('Telephone'),
            'company_address': data.get('FullAddress', '').replace('\r', ', '),
            'areas_of_law': ", ".join([
                c.get('Parent', {}).get('PublicDescription')
                for c in data.get('CategoriesOfWork', [])
                if c.get('Parent', {}).get('PublicDescription')
            ]),
            'total_solicitors': total_solicitors_num,
            'scottish_partners': scottish_partners_num,
            'domains': original_website  # 修正为字符串类型
        }

        # 提取律师ID并异步处理
        solicitors = data.get('SolicitorsAtOffice', [])
        lawyer_ids = [s.get('Id') for s in solicitors if s.get('Id')]

        # 收集公司数据
        firm_entry = {
            'firm_id': firm_id,
            'base_info': company_data,
            'parsed_solicitors': [],
            'expected_solicitors': len(lawyer_ids)
        }
        self.firm_data.append(firm_entry)
        logger.debug(f"公司 {firm_id} 的 律师列表：{lawyer_ids}")
        # 异步处理律师数据
        if lawyer_ids:
            logger.info(f"开始处理公司 {firm_id} 的 {len(lawyer_ids)} 个律师数据")
            lawyer_tasks = [
                asyncio.create_task(self._fetch_and_parse_lawyer(firm_id, lawyer_id))
                for lawyer_id in lawyer_ids
            ]
            await asyncio.gather(*lawyer_tasks)
            logger.info(f"公司 {firm_id} 的律师数据处理完成")
                    

    async def _fetch_and_parse_lawyer(self, firm_id: str, lawyer_id: str) -> None:    
        """获取并解析律师详情"""
        try:
            logger.debug(f"开始异步获取律师 {lawyer_id} 详情")
            url = f"{self.base_url}/GetSolicitorDetail?id={lawyer_id}"
            # 使用异步HTTP客户端而非同步方法
            content = await self._fetch_page_content(url)
            if not content:
                logger.error(f"律师 {lawyer_id} 详情页为空")
                return
            
            data = json.loads(content)
            self._parse_lawyer_data(data, firm_id)
            logger.debug(f"律师 {lawyer_id} 解析成功")
        except Exception as e:
            logger.error(f"律师 {lawyer_id} 处理失败: {str(e)}", exc_info=True)

    def _parse_lawyer_data(self, data: Dict[str, Any], firm_id: str) -> None:
        """解析律师JSON数据并提取信息"""
        try:
            # 查找对应公司条目
            firm_entry = next((f for f in self.firm_data if f['firm_id'] == firm_id), None)
            if not firm_entry:
                logger.error(f"找不到公司 {firm_id} 的条目，律师数据无法关联")
                return
             # 解析律师详细信息
            lawyer_info = {
                'name': data.get('Name'),
                'email_addresses': data.get('Email'),
                'telephone': data.get('Telephone'),
                'address': data.get('FullAddress', '').replace('\r', ', '),
                'practice_areas': [
                    c.get('Parent', {}).get('PublicDescription')
                    for c in data.get('CategoriesOfWork', [])
                    if c.get('Parent', {}).get('PublicDescription')
                ]
            }
            logger.info(f"解析到律师数据: {lawyer_info['name']} (公司ID: {firm_id})")

            # 关联到公司
            firm_entry['parsed_solicitors'].append(lawyer_info)
            logger.info(f"律师 {data.get('Id')} 数据已关联到公司 {firm_id}，当前律师数量: {len(firm_entry['parsed_solicitors'])}")
        except Exception as e:
            logger.error(f"解析律师数据失败: {str(e)}，公司ID: {firm_id}", exc_info=True)

    def _format_output(self) -> Dict[str, List[Dict[str, Any]]]:
        """格式化输出为项目标准格式"""
        companies = []
        for firm in self.firm_data:
            # 处理域名格式
            domain = firm['base_info']['domains'] or ''
            if domain:
                parsed_url = urlparse(domain)
                domain = parsed_url.netloc or parsed_url.path.split('/')[0]
                domain = domain.lstrip('www.')

            company = {
                'name': firm['base_info']['name'],
                'company_email': firm['base_info']['company_email'],
                'company_phone': firm['base_info']['company_phone'],
                'company_address': firm['base_info']['company_address'],
                'domains': domain,
                'areas_of_law': firm['base_info']['areas_of_law'],
                'total_solicitors': firm['base_info']['total_solicitors'],
                'scottish_partners': firm['base_info']['scottish_partners'],
                'lawyers': firm['parsed_solicitors']
            }
            companies.append(company)
        logger.info(f"数据格式化完成，共 {len(companies)} 家公司，{sum(len(c['lawyers']) for c in companies)} 名律师")

        return {'companies': companies}

   