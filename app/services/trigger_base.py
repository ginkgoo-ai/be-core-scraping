from abc import ABC, abstractmethod
from typing import Dict, Any
from sqlalchemy.orm import Session

class TriggerService(ABC):
    # 任务触发服务抽象基类
    def __init__(self, db_session: Session):
        self.db_session = db_session

    @abstractmethod
    async def create_task(self, task_id: str) -> int:
        # 创建任务记录(抽象方法)
        pass

    @abstractmethod
    async def execute_task(self, task_id: int) -> Dict[str, Any]:
        # 执行任务(抽象方法)
        pass

    async def run(self, task_id: str) -> Dict[str, Any]:
        # 统一执行入口(模板方法)
        task_db_id = await self.create_task(task_id)
        return await self.execute_task(task_db_id)