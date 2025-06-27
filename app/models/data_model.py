from enum import Enum
from sqlalchemy import Column, Integer, String, Float, JSON, ForeignKey, BigInteger, Text
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
    company_phone = Column(String(100))
    source_name = Column(String(50))
    company_email = Column(String(100))
    company_address = Column(Text)
    scottish_partners = Column(Integer)
    total_solicitors = Column(Integer)
    areas_of_law = Column(JSON)
    team_count = Column(Integer)
    redundant_info = Column(JSON, default=lambda: {})
    update_date = Column(BigInteger, nullable=False, default=lambda: int(datetime.now().timestamp()))
    create_date = Column(BigInteger, nullable=False, default=lambda: int(datetime.now().timestamp()))
    lawyers = relationship(
        "Lawyer",
        back_populates="company",
        primaryjoin="Company.id == foreign(Lawyer.company_id)",
        viewonly=True  # 添加viewonly标记避免写入冲突
    )


    
class Lawyer(Base):
    __tablename__ = 'lawyer'
    __table_args__ = {'schema': settings.DB_SCHEMA} 

    id = Column(BigInteger, primary_key=True)
    company_id = Column(BigInteger, ForeignKey(f'{settings.DB_SCHEMA}.company.id'))
    email_addresses = Column(String(100))
    name = Column(String(100))
    practice_areas = Column(JSON)
    source_name = Column(String(50))
    address = Column(Text)
    telephone = Column(String(100))
    redundant_info = Column(JSON, default=lambda: {})
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
    scrapy_params = Column(JSON)
    scraped_company_count = Column(Integer)
    scraped_lawyer_count = Column(Integer)
    error_message = Column(Text)
    update_date = Column(BigInteger, nullable=False, default=lambda: int(datetime.now().timestamp()))
    create_date = Column(BigInteger, nullable=False, default=lambda: int(datetime.now().timestamp()))
    
# class ImmigrationAdviser(Base):
#     __tablename__ = "immigration_adviser"
#     __table_args__ = {'schema': settings.DB_SCHEMA}

#     id = Column(BigInteger, primary_key=True)
#     registration_number = Column(String(50), unique=True, comment='Organisation_Reference_Number__c')
#     business_name = Column(String(255), comment='BusinessName__c')
#     organisation_level = Column(String(50), comment='Level__c')
#     fee_type = Column(String(50), comment='Fee_Paying_Type__c')
#     categories = Column(JSON, comment='Categories__c')
#     phone = Column(String(50))
#     email = Column(String(100))
#     website = Column(String(255))
#     address = Column(JSON, comment='完整地址信息')
#     latitude = Column(Float)
#     longitude = Column(Float)
#     distance = Column(Float)
#     distance_from_location = Column(Float)
#     update_date = Column(BigInteger, nullable=False, default=lambda: int(datetime.now().timestamp()))
#     create_date = Column(BigInteger, nullable=False, default=lambda: int(datetime.now().timestamp()))
    
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
    SYNC_ALL = "sync_all"

# 该枚举类定义了同步操作的类型
class SyncType(str, Enum):
    COMPANY = "company"
    LAWYER = "lawyer"
    
class SourceName(str,Enum):
    CRAWLER_LAWSOCNI = "Law Society of Northern Ireland"
    CRAWLER_LAWSCOT = "Law Society of Scotland"
    CRAWLER_ADVISER_FINDER = "Immigration Advice Authority"
    
    
#定义scrapy的类型   
class ScrapyId(str, Enum):
    SCRAPY_A = "crawler_lawsocni"
    SCRAPY_B = "scrapy_b"
    SCRAPY_C = "crawler_lawscot"
    SCRAPY_ADVISER_FINDER = "crawler_adviser_finder"