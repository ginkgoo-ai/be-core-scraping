from fastapi import APIRouter, Depends, BackgroundTasks, Body
import time
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.schemas import SyncTriggerResponse, ScrapyTriggerResponse, ErrorResponse,SuccessResponse, SyncTriggerRequest
from app.services.sync_trigger import SyncTriggerService
from app.core.logger import logger

router = APIRouter()

@router.post("/sync-trigger", 
    responses={
        200: {"model": SuccessResponse[ScrapyTriggerResponse]},  # 200响应模型
        400: {"model": ErrorResponse}  # 400错误响应
    })
 

async def trigger_sync(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    request: SyncTriggerRequest = Body(..., description="CRM同步数据")
    
):
    """触发数据同步任务"""
    # 创建同步触发服务实例
    
    sync_service = SyncTriggerService(db)
    
    try:
        # 创建任务记录
        task_id = await sync_service.create_task(request.sync_source)
        logger.info(f"已创建同步任务，ID: {task_id}")
        
        # 添加后台任务执行同步
        background_tasks.add_task(
            sync_service.execute_task,
            task_id=task_id
        )   
    
        return SuccessResponse(
                data=SyncTriggerResponse(
                    task_id=task_id,
                    trigger_time=int(time.time()),
                    sync_source=request.sync_source
                    )
            )
    except Exception as e:
        logger.error(f"创建同步任务失败(sync_source={request.sync_source}): {str(e)}")
        return ErrorResponse(
            code=400,
            msg=str(f"创同步任务失败(sync_source={request.sync_source}): {str(e)}")
        ), 400