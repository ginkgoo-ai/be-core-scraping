from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from app.services.crm_integration import CRMIntegrationService
from app.services.data_storage import DataStorageService
from app.core.database import get_db
from app.models.schemas import CrawledDataResponse, CRMDataResponse

router = APIRouter()

@router.post("/sync/{data_id}", response_model=CRMDataResponse)
async def sync_data_to_crm(
    data_id: int, 
    background_tasks: BackgroundTasks, 
    db: Session = Depends(get_db)
):
    """将指定ID的爬取数据同步到CRM系统"""
    # 使用背景任务异步执行同步，避免API请求阻塞
    crm_service = CRMIntegrationService()
    background_tasks.add_task(crm_service.sync_data_to_crm, db, data_id)
    return {"message": f"Syncing data {data_id} to CRM has been scheduled"}
