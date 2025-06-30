import requests
import traceback
import aiohttp
from app.core.config import settings
from app.core.logger import logger
from app.models.data_model import Company, Lawyer,SourceName
import json
from asyncio import gather


class CRMIntegrationService:
    def __init__(self, db_session):
        self.db_session = db_session
        self.session = aiohttp.ClientSession() 
        self.attio_api_base = settings.CRM_URL
        self.attio_token = settings.CRM_API_KEY
        self.headers = {
            "Authorization": f"Bearer {self.attio_token}",
            "Content-Type": "application/json"
        }
        self.company_api_success = 0
        self.company_api_failure = 0
        self.lawyer_api_success = 0
        self.lawyer_api_failure = 0
    #定义session 上下文管理器
    async def __aenter__(self):
        return self
    async def __aexit__(self, exc_type, exc, tb):
        await self.session.close()
    
    #定义attio请求方法
    async def send_attio_request(self, endpoint, data, method='post'):
        url = f"{self.attio_api_base}/{endpoint}"
        
        try:
            if method.lower() not in ['put', 'post']:
                logger.error(f"CRM API请求方式不对: 实际请求：{method}，仅支持put/post")
                raise ValueError(f"Unsupported HTTP method: {method}")
            if method.lower() == 'put':
                response = await self.session.put(url, headers=self.headers, json=data)
            else:
                response = await self.session.post(url, headers=self.headers, json=data)
           
            response.raise_for_status()
            return await response.json()
        except requests.exceptions.RequestException as e:
            if 'response' in locals():
                logger.error(f"CRM API请求体: {json.dumps(data, indent=2, ensure_ascii=False)}")
                logger.error(f"CRM API请求失败: 状态码{response.status_code}, 响应内容{response.text}")
            else:
                logger.error(f"CRM API请求失败: {str(e)}")
            return None
        
    async def get_company_data(self, sync_source: str):
        # 根据sync_source查询公司数据
        query = self.db_session.query(Company)
        if sync_source != "all":
            query = query.filter(Company.source_name == sync_source)
        return query.all()

    async def get_lawyer_data(self, sync_source: str):
        # 根据sync_source查询律师数据
        query = self.db_session.query(Lawyer)
        if sync_source != "all":
            query = query.filter(Lawyer.source_name == sync_source)
        return query.all()
    
    def _build_company_data(self, company):
        field_mapping = settings.CRM_COMPANY_FIELD_MAPPING
        if not company.areas_of_law:
            areas_of_law = ""
        else:
            try:
                # 尝试解析JSON数组格式（如：["Level 1 Immigration", ...]
                parsed = json.loads(company.areas_of_law)
                if isinstance(parsed, list):
                    # 数组格式：转换为逗号分隔字符串
                    areas_of_law = ", ".join(parsed)
                else:
                    # JSON但非数组：直接转为字符串
                    areas_of_law = str(parsed)
            except json.JSONDecodeError:
                # 非JSON格式：视为已有的逗号分隔字符串
                areas_of_law = company.areas_of_law
        return {
        "data": {
            "values": {
                field_mapping.get("name", "name"): company.name,
                field_mapping.get("domains", "domains"): [company.domains] if company.domains else [],
                field_mapping.get("company_email", "company_email"): company.company_email if company.company_email else "",
                field_mapping.get("company_phone", "company_phone"): company.company_phone if company.company_phone else "",
                field_mapping.get("areas_of_law", "areas_of_law"): areas_of_law,
                field_mapping.get("total_solicitors", "total_solicitors"): company.total_solicitors or 0,
                field_mapping.get("scottish_partners", "scottish_partners"): company.scottish_partners or 0,
                field_mapping.get("regulated_body", "regulated_body"): SourceName[company.source_name.upper()].value,
                field_mapping.get("team_count", "team_count"): self.db_session.query(Lawyer).filter(Lawyer.company_id == company.id).count(),
            }
        }
    }
        

    def _build_lawyer_data(self, lawyer, crm_company_id):
        field_mapping = settings.CRM_LAWYER_FIELD_MAPPING
        return {
        "data": {
            "values": {
                field_mapping.get("name", "name"): [{ "first_name": "","last_name": "","full_name": lawyer.name}],
                field_mapping.get("email", "email"): [lawyer.email_addresses] if lawyer.email_addresses else [],
                field_mapping.get("phone", "Telephone"): lawyer.telephone if lawyer.telephone else "",
                field_mapping.get("address", "address"): lawyer.address if lawyer.address else "",
                field_mapping.get("regulated_body", "regulated_body"): SourceName[lawyer.source_name.upper()].value,
                field_mapping.get("company", "company"): [{
                        "target_object": "companies",
                        "target_record_id": crm_company_id
                    }]
                
            }
        }
    }
        
        # return {
        #     "data": {
        #         "values": {
        #             "name": lawyer.name,
        #             "email": lawyer.email_addresses,
        #             "phone": lawyer.phone,
        #             "address": lawyer.address,
        #             "regulated_body": SourceName[lawyer.source_name.upper()].value,
        #             "company": [{
        #                 "target_object": "companies",
        #                 "target_record_id": crm_company_id
        #             }]
        #         }
        #     }
        # }    

    async def sync_companies(self, sync_source: str):
        companies = await self.get_company_data(sync_source)
        
        results = []
        for company in companies:
            try:
                company_endpoint = "objects/companies/records"
                method = 'put' if company.domains else 'post'  #依赖attio更新方式增加去重校验
                endpoint = f"{company_endpoint}?matching_attribute=domains" if method == 'put' else company_endpoint
                response = await self.send_attio_request(
                    endpoint,
                    self._build_company_data(company),
                    method=method
                )
                if response:
                    self.company_api_success += 1
                    results.append(response)
                    logger.info(f"公司 {company.name} 同步成功")
                    crm_company_id = response.get("data", {}).get("id", {}).get("record_id") #获取company在CRM的 id
                    if not crm_company_id:
                        logger.error(f"公司 {company.name} 未获取到CRM ID")
                        continue
                    lawyers = self.db_session.query(Lawyer).filter(Lawyer.company_id == company.id).all()
                    if not lawyers:
                        logger.info(f"公司 {company.name} 没有关联律师，跳过律师同步")
                        continue
                    for lawyer in lawyers:
                        lawyer_endpoint = "objects/people/records"
                        lawyer_data = self._build_lawyer_data(lawyer, crm_company_id)
                        method = 'put' if lawyer.email_addresses else 'post'        #依赖attio更新方式增加去重校验
                        endpoint = f"{lawyer_endpoint}?matching_attribute=email_addresses" if method == 'put' else lawyer_endpoint
                        response = await self.send_attio_request(
                            endpoint,
                            lawyer_data,
                            method=method
                        )
                        
                        
                        if response:
                            self.lawyer_api_success += 1
                            results.append(response)
                            logger.info(f"律师 {lawyer.name} 同步成功")
                        else:
                            self.lawyer_api_failure += 1
                            logger.error(f"律师 {lawyer.name} 同步失败")
                            logger.error(f"律师API请求 {lawyer_data}")
                            logger.error(f"律师API返回 {response.text}")
                else:
                    self.company_api_failure += 1
                    logger.error(f"公司 {company.name} 同步失败")
            except Exception as e:
                logger.error(f"公司 {company.name} 同步失败: {str(e)}，详细堆栈: {traceback.format_exc()}")
                self.company_api_failure += 1
        return {
            'company_count': self.company_api_success,
            'lawyer_count': self.lawyer_api_success,
            'results': results
        }
    

    # async def sync_lawyers(self, sync_source: str):
    #     lawyers = await self.get_lawyer_data(sync_source)
    #     results = []
    #     for lawyer in lawyers:
    #         lawyer_data = {
    #             "data": {
    #                 "values": {
    #                     "name": lawyer.name,
    #                     "email": lawyer.email,
    #                     "phone": lawyer.phone,
    #                     "address": lawyer.full_address,
    #                     "practice_areas": lawyer.practice_areas,
    #                     "company": [{
    #                         "target_object": "companies",
    #                         "target_record_id": lawyer.company_id
    #                     }]
    #                 }
    #             }
    #         }
    #         response =await self.send_attio_request("objects/people/records", lawyer_data)
    #         if response:
    #             self.lawyer_api_success += 1
    #             results.append(response)
    #             logger.info(f"律师 {lawyer.id} 同步成功")
    #         else:
    #             self.lawyer_api_failure += 1
    #             logger.error(f"律师 {lawyer.id} 同步失败")
    #     return results