from app.services.trigger_base import TriggerService
from app.crawlers.base_crawler import BaseCrawler
from typing import Dict, Any
import importlib
from app.models.data_model import Task, TaskType, TaskStatus
from app.services.data_storage import DataStorageService
import time
from app.core.database import get_db
from app.core.logger import logger
from sqlalchemy import select



class CrawlerTriggerService(TriggerService):
    
    # 爬虫任务触发服务
    async def create_task(self, scrapy_id: str, scrapy_url: str, scrapy_params: dict) -> int:
        # 创建爬虫任务记录
        logger.info(f"创建爬虫任务: {scrapy_id}, URL: {scrapy_url}")
        try:
            new_task = Task(
                status=TaskStatus.IN_PROGRESS,
                type=TaskType.SCRAPY_COMPANY,
                scrapy_id=scrapy_id,
                scrapy_url=scrapy_url,
                scrapy_params=scrapy_params,
                start_time=int(time.time()),
                create_date=int(time.time())
            )
            self.db_session.add(new_task)
            self.db_session.commit()
            self.db_session.refresh(new_task)
            logger.info(f"爬虫任务创建成功，ID: {new_task.id}")
            return new_task.id
            
            
        except Exception as e:
            logger.error(f"创建爬虫任务失败: {str(e)}")
            raise 
        

    async def execute_task(self, task_id: int) -> Dict[str, Any]:
        """
            执行爬虫任务并管理生命周期
            - 任务状态流转: pending → running → completed/failed
            - 记录开始/完成时间
            - 异常捕获与错误记录
        """
        # 执行爬虫任务
        logger.info(f"开始执行爬虫任务，task_id: {task_id}")
        task = self.db_session.query(Task).filter(Task.id == task_id).first()
        if not task:
            logger.error(f"任务ID不存在: {task_id}")
            raise ValueError(f"任务ID不存在: {task_id}")

        try:
            # 动态加载爬虫
            logger.info(f"动态加载爬虫模块: {task.scrapy_id}")
            crawler_module = importlib.import_module(f"app.crawlers.{task.scrapy_id}")
            if '_' in task.scrapy_id:
                class_name = "Crawler" + "".join(part.capitalize() for part in task.scrapy_id.split('_')[1:])
            else:
                class_name = f"Crawler{task.scrapy_id.capitalize()}"
            crawler_class = getattr(crawler_module, class_name)
            crawler = crawler_class(scrapy_url=task.scrapy_url,scrapy_params=task.scrapy_params)

            # 执行爬取
            result = await crawler.crawl()
            
            logger.info(f"待存储company: {len(result.get('companies', []))}条")
            #数据存储：
            if self.db_session is None:
                logger.error("CrawlerTriggerService数据库会话未初始化")
                raise RuntimeError("数据库会话未初始化")
            storage_service = DataStorageService()
            storage_result = await storage_service.save_crawled_data(
                self.db_session,
                source=task.scrapy_id,
                companies=result.get('companies', [])
            )
            logger.info(f"数据存储完成: {storage_result}")
            
            task.scraped_company_count = storage_result.get('company_success', 0)
            task.scraped_lawyer_count = storage_result.get('lawyer_success', 0)
            task.scrapy_url = result.get('scrapy_url', task.scrapy_url)
            task.status = TaskStatus.COMPLETED
            task.completion_time = int(time.time())
            logger.info(f"爬虫任务完成: {task_id}")
            return {"task_id": task_id, "status": "completed", "result": result}

        except Exception as e:
            self.db_session.rollback() 
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            task.completion_time = int(time.time())
            logger.error(f"爬虫任务失败: {task_id}, 错误: {str(e)}", exc_info=True)
            raise
        finally:
            self.db_session.commit()