from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any

class CrawledDataCreate(BaseModel):
    source: str
    raw_data: Dict[str, Any]
    
    class Config:
        from_attributes = True

class CrawledDataUpdate(BaseModel):
    cleaned_data: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True

class CrawledDataResponse(BaseModel):
    id: int
    source: str
    raw_data: Dict[str, Any]
    cleaned_data: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True

class CRMDataResponse(BaseModel):
    id: int
    crawled_data_id: int
    crm_id: Optional[str]
    sync_status: str
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
        
class LawyerScrapyRequest(BaseModel):
    url: str
    siteId: str = Field(..., min_length=6)

class ScrapyResultResponse(BaseModel):
    site: str
    total: int
    success: int
    task_status: str