import asyncio
import requests
from sqlalchemy.orm import Session
from app.models.data_model import CrawledData, CRMData
from app.core.config import settings

class CRMIntegrationService:
    """CRM集成服务，负责将爬取的数据同步到CRM系统"""
    
    def __init__(self):
        self.api_url = settings.CRM_API_URL
        self.api_key = settings.CRM_API_KEY.get_secret_value()
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def sync_data_to_crm(self, db: Session, data_id: int) -> dict:
        """将指定ID的爬取数据同步到CRM系统"""
        # 获取爬取的数据
        crawled_data = db.query(CrawledData).filter(CrawledData.id == data_id).first()
        if not crawled_data:
            return {
                "success": False,
                "message": f"Data with ID {data_id} not found"
            }
        
        # 创建CRM数据记录
        crm_data = CRMData(
            crawled_data_id=crawled_data.id,
            sync_status="pending"
        )
        db.add(crm_data)
        db.commit()
        db.refresh(crm_data)
        
        try:
            # 准备要发送到CRM的数据
            data_for_crm = self._prepare_data_for_crm(crawled_data)
            
            # 发送数据到CRM
            response = requests.post(
                f"{self.api_url}/api/leads",
                json=data_for_crm,
                headers=self.headers
            )
            response.raise_for_status()
            
            # 更新同步状态
            crm_data.crm_id = response.json().get("id")
            crm_data.sync_status = "success"
            db.commit()
            
            return {
                "success": True,
                "message": f"Data synced to CRM successfully",
                "crm_id": crm_data.crm_id
            }
            
        except Exception as e:
            # 更新同步状态为失败
            crm_data.sync_status = "failed"
            crm_data.error_message = str(e)
            db.commit()
            
            return {
                "success": False,
                "message": f"Failed to sync data to CRM: {str(e)}"
            }
    
    def _prepare_data_for_crm(self, crawled_data: CrawledData) -> dict:
        """根据CRM系统的要求准备数据"""
        # 这里是示例转换逻辑，实际项目中需要根据CRM系统的API要求编写转换逻辑
        source = crawled_data.source
        cleaned_data = crawled_data.cleaned_data or {}
        
        # 根据不同来源准备不同的数据结构
        if source == "website_a":
            # 网站A的数据转换为CRM线索
            if cleaned_data.get("products"):
                first_product = cleaned_data["products"][0]
                return {
                    "name": first_product.get("name", "Unknown Product"),
                    "description": f"From {source} - {first_product.get('price', 'N/A')}",
                    "lead_source": source,
                    "custom_fields": {
                        "original_data_id": crawled_data.id,
                        "price": first_product.get("price")
                    }
                }
        
        elif source == "website_b":
            # 网站B的数据转换为CRM线索
            if cleaned_data.get("articles"):
                first_article = cleaned_data["articles"][0]
                return {
                    "name": first_article.get("title", "Unknown Article"),
                    "description": first_article.get("content", "")[:200] + "...",
                    "lead_source": source,
                    "custom_fields": {
                        "original_data_id": crawled_data.id,
                        "source_article_id": first_article.get("id")
                    }
                }
        
        elif source == "website_c":
            # 网站C的数据转换为CRM线索
            if cleaned_data.get("events"):
                first_event = cleaned_data["events"][0]
                return {
                    "name": first_event.get("title", "Unknown Event"),
                    "description": f"Event on {first_event.get('date', 'N/A')}",
                    "lead_source": source,
                    "custom_fields": {
                        "original_data_id": crawled_data.id,
                        "event_date": first_event.get("date")
                    }
                }
        
        # 默认转换
        return {
            "name": f"Data from {source}",
            "description": f"Imported from {source} on {crawled_data.created_at}",
            "lead_source": source,
            "custom_fields": {
                "original_data_id": crawled_data.id,
                "source_type": source
            }
        }
