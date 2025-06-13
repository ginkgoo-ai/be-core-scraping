from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from app.crawlers.trigger_service import CrawlerTrigger
from app.core.database import get_db
from app.models.schemas import ScrapyResultResponse,LawyerScrapyRequest

router = APIRouter()

@router.post("/trigger/scrapy-lawyer", response_model=ScrapyResultResponse)
async def trigger_website_a(request: LawyerScrapyRequest,background_tasks: BackgroundTasks, db: Session = Depends(get_db)):

    """触发网站爬虫"""
    # 使用背景任务异步执行爬虫，避免API请求阻塞
    background_tasks.add_task(CrawlerTrigger.run_website_a, request.url, request.siteId,db)
    return {"message": "Crawler has been triggered"}
