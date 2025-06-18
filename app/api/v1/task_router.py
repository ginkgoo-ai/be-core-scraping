from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.data_model import Task, TaskStatus
from app.models.schemas import TaskResponse,SuccessResponse,ErrorResponse
from app.core.logger import logger

# 配置日志
router = APIRouter(prefix="/tasks")

# @router.get("", response_model=TaskListResponse)
# async def get_task_list(
#     status: TaskStatus = None,
#     page: int = 1,
#     page_size: int = 20,
#     db: Session = Depends(get_db)
# ):
#     """获取任务列表，支持按状态筛选和分页"""
#     query = db.query(Task)
    
#     # 状态筛选
#     if status:
#         query = query.filter(Task.status == status)
    
#     # 分页处理
#     total = query.count()
#     tasks = query.order_by(Task.create_date.desc())
#                 .offset((page-1)*page_size)
#                 .limit(page_size)
#                 .all()
    
#     return TaskListResponse(
#         total=total,
#         page=page,
#         page_size=page_size,
#         tasks=[{
#             "id": task.id,
#             "status": task.status,
#             "type": task.type,
#             "scrapy_id": task.scrapy_id,
#             "create_time": task.create_date,
#             "start_time": task.start_time,
#             "completion_time": task.completion_time
#         } for task in tasks]
#     )

@router.get("/{task_id}",
    responses={
        200: {"model": SuccessResponse[TaskResponse]},  # 200响应模型
        400: {"model": ErrorResponse}  # 400错误响应
    })



async def get_task_detail(
    task_id: int,
    db: Session = Depends(get_db)
):
    """获取任务详细信息"""
    task = db.query(Task).filter(Task.id == task_id).first()
    
    if not task:
        logger.error(f"任务ID {task_id} 不存在")
        raise HTTPException(status_code=404, detail=f"任务ID {task_id} 不存在")
        
    
    logger.error(f"任务ID {task_id} 信息获取成功")
    return SuccessResponse(
        data=TaskResponse( 
            task_id=task.id,  
            start_time=task.create_date,  # 使用创建时间作为触发时间
            status=task.status,
            task_type=task.type,
            scrapy_id=task.scrapy_id,
            completion_time=task.completion_time,
            # 从元数据中获取统计信息
            scraped_company_count=task.scraped_company_count or 0,
            scraped_lawyer_count=task.scraped_lawyer_count or 0,
            # 错误信息存储在单独字段
            error_message=task.error_message
        ))
