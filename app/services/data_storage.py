import asyncio
from sqlalchemy.orm import Session
from app.models.data_model import CrawledData

class DataStorageService:
    """数据存储服务，负责将爬虫获取的数据保存到数据库"""
    
    async def save_crawled_data(self, db: Session, source: str, 
                               raw_data: dict, cleaned_data: dict) -> dict:
        """保存爬取的数据到数据库"""
        # 创建数据库记录
        db_data = CrawledData(
            source=source,
            raw_data=raw_data,
            cleaned_data=cleaned_data
        )
        
        # 保存到数据库
        db.add(db_data)
        db.commit()
        db.refresh(db_data)
        
        return {
            "success": True,
            "message": f"Data from {source} saved successfully",
            "data_id": db_data.id
        }
    
    async def get_latest_crawled_data(self, db: Session, limit: int = 10) -> list:
        """获取最新的爬取数据"""
        return db.query(CrawledData).order_by(CrawledData.created_at.desc()).limit(limit).all()
    
    async def get_crawled_data_by_id(self, db: Session, data_id: int) -> CrawledData:
        """根据ID获取爬取数据"""
        return db.query(CrawledData).filter(CrawledData.id == data_id).first()
