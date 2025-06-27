from fastapi import APIRouter, Depends, BackgroundTasks, Body
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.schemas import ScrapyTriggerRequest, ScrapyTriggerResponse, ErrorResponse,SuccessResponse
from app.models.data_model import TaskType
from app.services.crawler_trigger import CrawlerTriggerService
import time
from app.core.logger import logger


router = APIRouter()

@router.post("/scrapy-trigger", 
    responses={
        200: {"model": SuccessResponse[ScrapyTriggerResponse]},  # 200响应模型
        400: {"model": ErrorResponse}  # 400错误响应
    })
async def trigger_scraping(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    request: ScrapyTriggerRequest = Body(..., description="爬虫任务参数")
):
    """触发网站爬虫任务"""
    # 创建爬虫触发服务实例
    crawler_service = CrawlerTriggerService(db_session=db)
    
    try:
        # 创建任务记录
        task_id = await crawler_service.create_task(request.scrapy_id, request.scrapy_url,request.scrapy_params)
        
        logger.info(f"已创建爬虫任务，ID: {task_id}")
        
        # 添加后台任务执行爬虫
        background_tasks.add_task(
            crawler_service.execute_task,
            task_id=task_id
        )
        
        return SuccessResponse(
            data=ScrapyTriggerResponse(
                task_id=task_id,
                trigger_time=int(time.time()),
                scrapy_id=request.scrapy_id,
                scrapy_url=request.scrapy_url
                )
        )
    except Exception as e:
        logger.error(f"创建爬虫任务失败(scrapy_id={request.scrapy_id}): {str(e)}")
        return ErrorResponse(
            code=400,
            msg=str(f"创建爬虫任务失败(scrapy_id={request.scrapy_id}): {str(e)}")
        ), 400