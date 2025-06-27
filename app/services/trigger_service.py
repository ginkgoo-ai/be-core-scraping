from app.services.crawler_trigger import CrawlerTriggerService
from app.services.sync_trigger import SyncTriggerService
from sqlalchemy.orm import Session
from typing import Dict, Any

class TriggerServiceManager:
    # 管理具体服务实例，对外提供统一调用入口
    @staticmethod
    def get_crawler_trigger(db_session: Session) -> CrawlerTriggerService:
        # 获取爬虫触发器实例
        return CrawlerTriggerService(db_session)

    @staticmethod
    def get_sync_trigger(db_session: Session) -> SyncTriggerService:
        # 获取同步触发器实例
        return SyncTriggerService(db_session)

    @staticmethod
    async def run_crawler(db_session: Session, scrapy_id: str) -> Dict[str, Any]:
        # 快捷调用：运行爬虫任务
        trigger = CrawlerTriggerService(db_session)
        return await trigger.run(scrapy_id)
    
    @staticmethod
    async def run_sync(db_session: Session, sync_source: str, sync_type: str) -> Dict[str, Any]:
        # 快捷调用：运行同步任务
        trigger = SyncTriggerService(db_session)
        return await trigger.run(sync_source, sync_type)