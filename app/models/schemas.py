from pydantic import BaseModel, Field
from datetime import datetime,timezone
from typing import Optional, Dict, Any, Union
from pydantic import BaseModel
from typing import Generic, Optional, TypeVar
from app.models.data_model import SyncType, TaskStatus, TaskType, ScrapyId
from pydantic import BaseModel, field_validator



T = TypeVar("T") 
class TimeConvertMixin:
    @field_validator('*')
    def convert_timestamp(cls, value, info):
        if info.field_name.endswith('_time') and isinstance(value, int):
            return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()
        return value

class ScrapyTriggerRequest(BaseModel):
    scrapy_id: ScrapyId = Field(..., description="爬虫ID，支持lawsocni_spider/scrapy_b/scrapy_c")
    scrapy_url: str = Field(..., description="目标爬取URL")
    # priority: Optional[int] = Field(1, ge=1, le=5, description="任务优先级(1-5)")
class SyncTriggerRequest(BaseModel):
    sync_type: SyncType = Field(..., description="同步脚本，支持company/lawyer")
    # priority: Optional[int] = Field(1, ge=1, le=5, description="任务优先级(1-5)")

#  成功响应
class SuccessResponse(BaseModel,Generic[T]):
    code: int = 1
    msg: str = "success"
    data: Optional[T] = None
    model_config = {'arbitrary_types_allowed': True}
# 错误响应
class ErrorResponse(BaseModel):
    code: int
    msg: str

# scrapy-trigger 返回结构
class ScrapyTriggerResponse(BaseModel):
    task_id: int
    trigger_time: int  
    scrapy_id: str
    scrapy_url: str 
    
      
#  sync-trigger 返回结构
class SyncTriggerResponse(BaseModel):
    task_id: int
    trigger_time: int
    sync_type: SyncType

#  task 查询结构
class TaskResponse(BaseModel,TimeConvertMixin):
    task_id: int
    start_time: int
    status: TaskStatus
    task_type:TaskType
    scrapy_id: ScrapyId 
    scrapy_url: Optional[str] = None
    sync_type: Optional[SyncType] = None
    completion_time: Optional[int] = None
    scraped_company_count: Optional[int] = 0
    scraped_lawyer_count: Optional[int] = 0
    error_count: Optional[int] = 0


# 添加统一响应包装模型 

