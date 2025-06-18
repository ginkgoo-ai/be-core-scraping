from app.services.trigger_base import TriggerService
from app.models.data_model import Task, TaskType, TaskStatus, SyncType
from app.services.crm_integration import CRMIntegrationService
import time
from typing import Dict, Any
from app.core.logger import logger



class SyncTriggerService(TriggerService):
    # 同步任务触发服务
    async def create_task(self, sync_type: str) -> int:
        # 创建同步任务记录
        logger.info(f"创建同步任务: {sync_type}")
        task_type = TaskType.SYNC_COMPANY if sync_type == SyncType.COMPANY else TaskType.SYNC_LAWYER
        new_task = Task(
            status=TaskStatus.IN_PROGRESS,
            type=task_type,
            scrapy_id=f"sync_{sync_type.lower()}",
            start_time=int(time.time()),
            create_date=int(time.time())
        )
        self.db_session.add(new_task)
        self.db_session.commit()
        self.db_session.refresh(new_task)
        logger.info(f"同步任务创建成功，ID: {new_task.id}")
        return new_task.id

    async def execute_task(self, task_id: int) -> Dict[str, Any]:
        # 执行同步任务
        logger.info(f"开始执行同步任务: {task_id}")
        task = self.db_session.query(Task).filter(Task.id == task_id).first()
        if not task:
            logger.error(f"任务ID不存在: {task_id}")
            raise ValueError(f"任务ID不存在: {task_id}")

        try:
            # 执行CRM同步
            sync_service = CRMIntegrationService(self.db_session)
            if 'company' in task.scrapy_id:
                result = await sync_service.sync_companies()
                logger.info(f"公司数据同步完成，同步数量: {len(result)}")
            else:
                result = await sync_service.sync_lawyers()
                logger.info(f"律师数据同步完成，同步数量: {len(result)}")

            task.status = TaskStatus.COMPLETED
            task.completion_time = int(time.time())
            return {"task_id": task_id, "status": "completed", "synced_count": len(result)}

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            task.completion_time = int(time.time())
            logger.error(f"同步任务失败: {task_id}, 错误: {str(e)}", exc_info=True)
            raise
        finally:
            self.db_session.commit()