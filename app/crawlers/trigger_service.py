import asyncio
from typing import Dict, Any
from sqlalchemy.orm import Session
from app.core.logger import logger
from app.models.data_model import Company, Lawyer
from app.crawlers.crawler_lawsocni import LawsocniSpider
from app.crawlers.scrapy_b import CrawlerB
from app.crawlers.crawler_c import CrawlerC
from app.services.data_cleaning import DataCleaningService
from app.services.data_storage import DataStorageService

# 管理具体服务实例，对外提供调用入口
class CrawlerTrigger:
    """爬虫触发服务，负责协调爬虫执行和数据处理"""
    
    @staticmethod
    async def run_website_a(db: Session) -> Dict[str, Any]:
        """运行网站A的爬虫"""
        crawler = LawsocniSpider()
        logger.info(f"开始爬取{ crawler.source_name }网站数据")
        raw_data = await crawler.crawl()
        logger.info(f"{ crawler.source_name }网站爬取完成，原始数据量: { len(raw_data) }条")
        
        # 清洗数据
        cleaning_service = DataCleaningService()
        cleaned_data = cleaning_service.clean_website_a_data(raw_data)
        logger.info(f"数据清洗完成，清洗后公司数据: { len(cleaned_data.get('companies', [])) }条, 律师数据: { len(cleaned_data.get('lawyers', [])) }条")
        
        # 存储数据
        storage_service = DataStorageService()
        # 按数据类型分别存储
        company_data = [Company(**item) for item in cleaned_data.get('companies', [])]
        lawyer_data = [Lawyer(**item) for item in cleaned_data.get('lawyers', [])]
        result = await storage_service.save_crawled_data(db, source=crawler.source_name, 
                                                       companies=company_data, lawyers=lawyer_data)
        logger.info(f"数据存储完成，成功保存公司: { result.get('company_count', 0) }条, 律师: { result.get('lawyer_count', 0) }条")
        
        return result
    
    @staticmethod
    async def run_website_b(db: Session) -> Dict[str, Any]:
        """运行网站B的爬虫"""
        crawler = CrawlerB()
        raw_data = await crawler.crawl()
        
        # 清洗数据
        cleaning_service = DataCleaningService()
        cleaned_data = cleaning_service.clean_website_b_data(raw_data)
        
        # 存储数据
        storage_service = DataStorageService()
        # 按数据类型分别存储
        company_data = [Company(**item) for item in cleaned_data.get('companies', [])]
        lawyer_data = [Lawyer(**item) for item in cleaned_data.get('lawyers', [])]
        result = await storage_service.save_crawled_data(db, source=crawler.source_name, 
                                                       companies=company_data, lawyers=lawyer_data)
        
        return result
    
    @staticmethod
    async def run_website_c(db: Session) -> Dict[str, Any]:
        """运行网站C的爬虫"""
        crawler = CrawlerC()
        raw_data = await crawler.crawl()
        
        # 清洗数据
        cleaning_service = DataCleaningService()
        cleaned_data = cleaning_service.clean_website_c_data(raw_data)
        
        # 存储数据
        storage_service = DataStorageService()
        # 按数据类型分别存储
        company_data = [Company(**item) for item in cleaned_data.get('companies', [])]
        lawyer_data = [Lawyer(**item) for item in cleaned_data.get('lawyers', [])]
        result = await storage_service.save_crawled_data(db, source=crawler.source_name, 
                                                       companies=company_data, lawyers=lawyer_data)
        
        return result
    @staticmethod
    async def run_sync(db: Session) -> Dict[str, Any]:
        """运行同步脚本"""