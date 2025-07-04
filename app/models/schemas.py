from pydantic import BaseModel, Field
from datetime import datetime,timezone
from typing import Optional, Dict, Any, Union
from pydantic import BaseModel
from typing import Generic, Optional, TypeVar
from app.models.data_model import SyncType, TaskStatus, TaskType, ScrapyId,PageType
from pydantic import BaseModel, field_validator



T = TypeVar("T") 
class TimeConvertMixin:
    @field_validator('*')
    def convert_timestamp(cls, value, info):
        if info.field_name.endswith('_time') and isinstance(value, int):
            return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()
        return value

class ScrapyTriggerRequest(BaseModel):
    scrapy_id: ScrapyId = Field(..., description="爬虫ID，支持lawsocni_spider/crawler_lawscot")
    scrapy_url: str = Field(..., description="目标爬取URL")
    scrapy_params: Optional[Dict[str, Any]] = Field(None, description="可选爬虫参数")

class SyncTriggerRequest(BaseModel):
    sync_source: str = Field("all", description="同步数据源，支持crawler_lawsocni/crawler_lawscot/crawler_adviser_finder/all")
    # sync_type: str = Field("all", description="同步类型，支持company/lawyer/all")


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
    sync_source:str

class HtmlParseRequest(BaseModel):
    scrapy_id: ScrapyId = Field(..., description="爬虫ID，支持lawsocni_spider/crawler_lawscot")
    page_type: PageType = Field(..., description="页面类型: company_list, lawyer_detail, lawyer_list")
    crawler_engine: str = Field(..., description="爬虫引擎，支持scrapy/ai")
    html_chunk: str = Field(..., description="HTML片段内容")
#  task 查询结构
class TaskResponse(BaseModel,TimeConvertMixin):
    task_id: int
    start_time: int
    status: TaskStatus
    task_type:TaskType
    scrapy_id: ScrapyId 
    scrapy_url: Optional[str] = None
    completion_time: Optional[int] = None
    scraped_company_count: Optional[int] = 0
    scraped_lawyer_count: Optional[int] = 0
    error_count: Optional[int] = 0


# 添加统一响应包装模型 

