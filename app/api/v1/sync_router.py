from fastapi import APIRouter, Depends, BackgroundTasks, Body
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.schemas import SyncTriggerResponse, ErrorResponse
from app.models.data_model import SyncType
from app.services.sync_trigger import SyncTriggerService
from app.core.logger import logger


router = APIRouter(prefix="/sync-trigger")

@router.post("", response_model=SyncTriggerResponse)
async def trigger_sync(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    sync_type: SyncType = Body(..., description="同步类型: COMPANY或LAWYER"),
    
):
    """触发数据同步任务"""
    # 创建同步触发服务实例
    sync_service = SyncTriggerService(db)
    
    try:
        # 创建任务记录
        task_id = await sync_service.create_task(sync_type.value)
        logger.info(f"已创建同步任务，ID: {task_id}")
        
        # 添加后台任务执行同步
        background_tasks.add_task(
            sync_service.execute_task,
            task_id=task_id
        )
        
        return SyncTriggerResponse(
            task_id=task_id,
            status="IN_PROGRESS",
            task_type=f"SYNC_{sync_type.value}"
        )
    except Exception as e:
        logger.error(f"创建同步任务失败: {str(e)}")
        return ErrorResponse(message=str(e)), 400