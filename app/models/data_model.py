from enum import Enum
from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, BigInteger, Index, Text
from sqlalchemy.orm import relationship
from app.core.config import settings
from datetime import datetime
from app.core.database import Base
from app.core.logger import logger
from sqlalchemy.ext.declarative import declarative_base




class Company(Base):
    __tablename__ = "company"
    __table_args__ = {'schema': settings.DB_SCHEMA}

    id = Column(BigInteger, primary_key=True)
    domains = Column(String(255), unique=True)
    name = Column(String(255))
    company_phone = Column(String(20))
    company_email = Column(String(100))
    company_address = Column(Text)
    scottish_partners = Column(Integer)
    total_solicitors = Column(Integer)
    areas_of_law = Column(JSON)
    team_count = Column(Integer)
    update_date = Column(BigInteger, nullable=False, default=lambda: int(datetime.now().timestamp()))
    create_date = Column(BigInteger, nullable=False, default=lambda: int(datetime.now().timestamp()))
    lawyers = relationship(
        "Lawyer",
        back_populates="company",
        primaryjoin="Company.id == foreign(Lawyer.company_id)",
        viewonly=True  # 添加viewonly标记避免写入冲突
    )

    # 与CRM数据的关联
    # crm_data = relationship("CRMData", back_populates="crawled_data", uselist=False)
     # AFTER (V2 syntax):
    
class Lawyer(Base):
    __tablename__ = 'lawyer'
    __table_args__ = {'schema': settings.DB_SCHEMA} 

    id = Column(BigInteger, primary_key=True)
    company_id = Column(BigInteger, ForeignKey(f'{settings.DB_SCHEMA}.company.id'))
    email_addresses = Column(String(100))
    name = Column(String(100))
    practice_areas = Column(JSON)
    address = Column(Text)
    telephone = Column(String(20))
    update_date = Column(BigInteger, nullable=False, default=lambda: int(datetime.now().timestamp()))
    create_date = Column(BigInteger, nullable=False, default=lambda: int(datetime.now().timestamp()))
    company = relationship(
        "Company",
        back_populates="lawyers",
        primaryjoin="Company.id == foreign(Lawyer.company_id)"
    )
    
    
 
class Task(Base):
    __tablename__ = 'task'
    __table_args__ = {'schema': settings.DB_SCHEMA} 

    id = Column(BigInteger, primary_key=True)
    status = Column(String(20))
    type = Column(String(30))
    scrapy_id = Column(String(50))
    start_time = Column(BigInteger)
    completion_time = Column(BigInteger, nullable=True) 
    scrapy_url = Column(String(255))
    scraped_company_count = Column(Integer)
    scraped_lawyer_count = Column(Integer)
    error_message = Column(Text)
    update_date = Column(BigInteger, nullable=False, default=lambda: int(datetime.now().timestamp()))
    create_date = Column(BigInteger, nullable=False, default=lambda: int(datetime.now().timestamp()))

  
class TaskStatus(str, Enum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"

class TaskType(str, Enum):
    SCRAPY_COMPANY = "scrapy_company"
    SCRAPY_LAWYER = "scrapy_lawyer"
    SYNC_COMPANY = "sync_company"
    SYNC_LAWYER = "sync_lawyer"

class SyncType(str, Enum):
    COMPANY = "company"
    LAWYER = "lawyer"
    
class ScrapyId(str, Enum):
    SCRAPY_A = "crawler_lawsocni"
    SCRAPY_B = "scrapy_b"
    SCRAPY_C = "scrapy_c"
