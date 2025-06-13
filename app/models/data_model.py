from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class CrawledData(Base):
    __tablename__ = "crawled_data"
    class Config:
        from_attributes = True
    
    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, index=True)  # 来源网站标识
    raw_data = Column(JSON)  # 原始爬取数据
    cleaned_data = Column(JSON)  # 清洗后的数据
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 与CRM数据的关联
    crm_data = relationship("CRMData", back_populates="crawled_data", uselist=False)
     # AFTER (V2 syntax):
    

class CRMData(Base):
    __tablename__ = "crm_data"
    
    id = Column(Integer, primary_key=True, index=True)
    crawled_data_id = Column(Integer, ForeignKey("crawled_data.id"))
    crm_id = Column(String, index=True)  # CRM系统中的记录ID
    sync_status = Column(String, default="pending")  # pending, success, failed
    error_message = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    crawled_data = relationship("CrawledData", back_populates="crm_data")
