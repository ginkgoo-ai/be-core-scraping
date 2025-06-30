from app.services.trigger_base import TriggerService
from app.models.data_model import Task, TaskType, TaskStatus, SyncType
from app.services.crm_integration import CRMIntegrationService
import time
from typing import Dict, Any
from app.core.logger import logger


class SyncTriggerService(TriggerService):
    async def create_task(self, sync_source: str) -> int:
        # 创建同步任务记录
        logger.info(f"创建同步任务: source={sync_source}")
        
        # 根据sync_source和sync_type确定任务类型
        new_task = Task(
            status=TaskStatus.IN_PROGRESS,
            type=TaskType.SYNC_COMPANY,
            scrapy_id=sync_source,
            start_time=int(time.time()),
            create_date=int(time.time())
        )
        self.db_session.add(new_task)
        self.db_session.commit()
        return new_task.id

    async def execute_task(self, task_id: int) -> Dict[str, Any]:
        # 执行同步任务
        task = self.db_session.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError(f"任务ID不存在: {task_id}")
         # 解析任务参数
        sync_source = task.scrapy_id
        # sync_service = CRMIntegrationService(self.db_session)
        # result = await sync_service.sync_companies(sync_source)
        async with CRMIntegrationService(self.db_session) as sync_service:
            try:
                logger.info(f"开始同步公司数据: {sync_source}") 
                result = await sync_service.sync_companies(sync_source)
                logger.info(f"同步任务执行完成: {result}") 
                task.status = TaskStatus.COMPLETED
                task.completion_time = int(time.time())
                self.db_session.commit()  # 确保状态变更持久化
                companies_count = result.get('company_count', 0)
                lawyers_count = result.get('lawyer_count', 0)
                logger.info(f"同步任务完成: {task_id}, 同步公司数量: {companies_count}, 同步律师数量: {lawyers_count}")
                return {
                    "task_id": task_id,
                    "status": "completed",
                    "result": {
                        "companies_synced": companies_count,
                        "lawyers_synced": lawyers_count
                    }
                }
            except Exception as e:
                logger.error(f"同步公司数据失败: {str(e)}", exc_info=True)  # 记录完整堆栈
                raise 

       
        # # 根据参数获取数据并同步
        # if sync_type == "all":
        #     company_result = await sync_service.sync_companies(sync_source)
        #     lawyer_result = await sync_service.sync_lawyers(sync_source)
        #     return {"companies_synced": len(company_result), "lawyers_synced": len(lawyer_result)}
        # elif sync_type == "company":
        #     result = await sync_service.sync_companies(sync_source)
        #     return {"companies_synced": len(result)}
        # else:
        #     result = await sync_service.sync_lawyers(sync_source)
        #     return {"lawyers_synced": len(result)}

    def _parse_sync_params(self, sync_id: str) -> [str]:
        # 从scrapy_id解析sync_source和sync_type
        _, sync_source = sync_id.split("_")
        return sync_source