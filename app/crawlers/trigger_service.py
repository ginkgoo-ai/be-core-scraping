import asyncio
from typing import Dict, Any
from sqlalchemy.orm import Session
from app.models.data_model import CrawledData
from app.crawlers.crawler_a import CrawlerA
from app.crawlers.crawler_b import CrawlerB
from app.crawlers.crawler_c import CrawlerC
from app.services.data_cleaning import DataCleaningService
from app.services.data_storage import DataStorageService

class CrawlerTrigger:
    """爬虫触发服务，负责协调爬虫执行和数据处理"""
    
    @staticmethod
    async def run_website_a(db: Session) -> Dict[str, Any]:
        """运行网站A的爬虫"""
        crawler = CrawlerA()
        raw_data = await crawler.crawl()
        
        # 清洗数据
        cleaning_service = DataCleaningService()
        cleaned_data = cleaning_service.clean_website_a_data(raw_data)
        
        # 存储数据
        storage_service = DataStorageService()
        result = await storage_service.save_crawled_data(db, source=crawler.source_name, 
                                                       raw_data=raw_data, cleaned_data=cleaned_data)
        
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
        result = await storage_service.save_crawled_data(db, source=crawler.source_name, 
                                                       raw_data=raw_data, cleaned_data=cleaned_data)
        
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
        result = await storage_service.save_crawled_data(db, source=crawler.source_name, 
                                                       raw_data=raw_data, cleaned_data=cleaned_data)
        
        return result
