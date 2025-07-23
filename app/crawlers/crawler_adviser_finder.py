import requests
import json
import time
import aiohttp
import random
import asyncio
from urllib.parse import urlencode
from typing import Optional, Dict, List,Any
from app.core.config import settings
from app.core.logger import logger
from app.crawlers.base_crawler import BaseCrawler
from app.services.data_cleaning import DataCleaningService

class CrawlerAdviserFinder(BaseCrawler):
    source_name = "crawler_adviser_finder" # Immigration Advice Authority 
    scrapy_id = "crawler_adviser_finder"
    
    def __init__(self, scrapy_url: str, scrapy_params: dict):
        super().__init__(scrapy_url)
        self.session = aiohttp.ClientSession()
              
        #获取基础配置 
        self.google_maps_api_key = settings.AF_GOOGLE_MAPS_API_KEY
        self.fwuid = settings.AF_FUID
        self.base_url = settings.AF_BASE_URL
        self.google_url =settings.AF_GOOGLE_BASE_URL
        # 获取参数，使用默认值如果未提供
        self.advisers: List[Dict[str, Any]] = []
        self.scrapy_params = scrapy_params or {}
        self.postcode = self.scrapy_params.get('postcode')
        self.distance = self.scrapy_params.get('distance', 50)
        self.fee_charging = self.scrapy_params.get('feeCharging', 'Both')
        self.type_of_advice = self.scrapy_params.get('typeOfAdvice', 'All Levels')
        self.asylum_or_immigration = self.scrapy_params.get('asylumOrImmigration', 'All Categories')
        self.action_id = self.scrapy_params.get('action_id', '131;a')
        
        
    async def crawl(self) -> Dict[str, Any]:
        """执行爬取操作，返回标准化的移民顾问数据"""
        logger.info(f"开始爬取{self.source_name}数据，postcode:{self.postcode}, 半径: {self.distance}英里")
        try:
            # 获取经纬度
            lat, lng = await self._get_lat_lng_from_postcode(self.postcode)
            if not lat or not lng:
                logger.error("无法获取经纬度，爬取终止")
                return {'advisers': []}

            # 发送API请求
            response_data = await self._fetch_adviser_list(lat, lng)
            if not response_data or 'actions' not in response_data or len(response_data['actions']) == 0:
                logger.warning("API响应为空或格式不正确")
                return {'advisers': []}
            
            # 获取API响应
            advisers = self._parse_adviser_list(response_data)
            logger.info(f"爬取完成，共找到 {len(advisers)} 条移民顾问数据")
            return {'companies': advisers}

        except Exception as e:
            logger.error(f"爬取过程发生错误: {str(e)}", exc_info=True)
            return {'advisers': [], 'error': str(e)}
            

    async def _get_lat_lng_from_postcode(self, postcode: str) -> tuple[Optional[float], Optional[float]]:
        """通过Google Maps Geocoding API获取邮编对应的经纬度"""
        if not self.google_maps_api_key:
            logger.error("未配置GOOGLE_MAPS_API_KEY环境变量")
            return None, None
        if not postcode:
            logger.error("Postcode parameter is required")
            return None, None
        params = {
            "address":postcode,
            "key": self.google_maps_api_key
        }
        try:
            async with self.session.get(self.google_url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    location = data['results'][0]['geometry']['location']
                    return float(location['lat']), float(location['lng'])
                logger.error(f"获取经纬度失败，状态码: {resp.status}")
                return None, None
        except (KeyError, IndexError, ValueError) as e:
            logger.error(f"解析经纬度失败: {str(e)}")
            return None, None
        finally:
            # 确保会话关闭
            if not self.session.closed:
                await self.session.close()

  


    async def _fetch_adviser_list(self, lat: float, lng: float) -> Optional[Dict[str, Any]]:
        """发送符合原始请求格式的POST请求"""
        message = {
            "actions": [{
                "id":self.action_id,
                "descriptor": "aura://ApexActionController/ACTION$execute",
                "callingDescriptor": "UNKNOWN",
                "params": {
                    "namespace": "",
                    "classname": "temporaryAdviserFinderController",
                    "method": "getOrganisationLTOA",
                    "params": {
                        "lat": lat,
                        "longi": lng,
                        "distance": self.distance,
                        "feeCharging": self.fee_charging,
                        "typeOfAdvice": self.type_of_advice,
                        "asylumOrImmigration": self.asylum_or_immigration
                    },
                    "cacheable": False,
                    "isContinuation": False
                }
            }]
        
        }
        # 构建Aura上下文
        aura_context = {
            "mode": "PROD",
            "fwuid": self.fwuid,
            "app": "siteforce:communityApp",
            "loaded": {
                "APPLICATION@markup://siteforce:communityApp": "1296_E-0fs7eMs-UxUK_92StDMQ"
            },
            "dn": [],
            "globals": {},
            "uad": True
        }

        # 构建POST数据
        post_data = {
            "message": json.dumps(message),
            "aura.context": json.dumps(aura_context),
            "aura.pageURI": f"/s/adviser-finder",  
            "aura.token": "null"
        }

        # 编码POST数据
        encoded_data = urlencode(post_data, safe='#')

        # 构建完整请求头
        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Accept-Language": "en",
            "origin": "https://portal.immigrationadviceauthority.gov.uk",
            "priority": "u=1, i",
            "Referer": f"{self.base_url}/s/adviser-finder",
            "Cache-Control": "no-cache",
            "X-Requested-With": "XMLHttpRequest"
        }

        # 构建API URL
        api_url = f"{self.base_url}/s/sfsites/aura?r=4&aura.ApexAction.execute=1"

        try:
            # 添加随机延迟
            await asyncio.sleep(random.uniform(0.1, 0.5))

            # 使用aiohttp发送异步POST请求
            async with aiohttp.ClientSession() as session:
                async with session.post(api_url, data=encoded_data, headers=headers) as response:
                    response.raise_for_status()
                    return await response.json()

        except aiohttp.ClientError as e:
            logger.error(f"API请求失败: {str(e)}")
        except json.JSONDecodeError:
            logger.error("API响应不是有效的JSON格式")
        except Exception as e:
            logger.error(f"请求处理发生错误: {str(e)}")
        return None



    def _parse_adviser_list(self, response_data: Dict[str, Any]) -> List[dict]:
        """解析API响应数据，提取顾问信息"""
        try:
            advisers = []
            # 遍历所有action节点
            if 'actions' in response_data:
                for action in response_data['actions']:
                    # 检查action是否包含非空的returnValue
                    if ('returnValue' in action and 
                        isinstance(action['returnValue'], dict) and
                        'returnValue' in action['returnValue'] and 
                        isinstance(action['returnValue']['returnValue'], list) and
                        len(action['returnValue']['returnValue']) > 0):
                        
                        # 遍历returnValue中的每个条目
                        for item in action['returnValue']['returnValue']:
                            try:
                                # 确保关键路径存在，避免KeyError
                                acc_obj = item.get('accObj', {})
                                loc_obj = item.get('locObj', {})
                                billing_address = acc_obj.get('BillingAddress', {})
                                primary_location_r = acc_obj.get('Primary_Location__r', {})
                                
                                # 提取并处理顾问信息
                                adviser = {
                                    # 基本信息
                                    'name': acc_obj.get('BusinessName__c'),
                                    'areas_of_law': [cat.strip() for cat in acc_obj.get('Categories__c', '').split(';')] if acc_obj.get('Categories__c') else [],
                                    
                                    # 联系方式
                                    'company_phone': acc_obj.get('Phone') or loc_obj.get('Phone_Number__c'),
                                    'company_email': primary_location_r.get('Primary_Email__c'),
                                    'domains': DataCleaningService.clean_domain(acc_obj.get('Website', '').strip()),
                                    'source_name':self.source_name,
                                    'company_address': billing_address.get('street') or loc_obj.get('Street__c'),
                                    
                                    # 其他信息
                                    'redundant_info': {
                                        # 平台索引信息
                                        'registration_number': acc_obj.get('Organisation_Reference_Number__c'),
                                        
                                        # 地理信息
                                        'latitude': loc_obj.get('Latitude__c'),
                                        'longitude': loc_obj.get('Longitude__c'),
                                        'distance': item.get('distance'),
                                        'distance_from_location': item.get('distanceFromLocation'),
                                        
                                        # 其他信息
                                        'organisation_level': acc_obj.get('Level__c'),
                                        'fee_type': acc_obj.get('Fee_Paying_Type__c'),
                                        
                                        # 地址信息
                                        'city': billing_address.get('city') or loc_obj.get('City__c'), 
                                        'state': billing_address.get('state'),
                                        'postal_code': billing_address.get('postalCode') or loc_obj.get('Postcode__c'),
                                    }
                                }
                                advisers.append(adviser)
                            except Exception as e:
                                logger.warning(f"Skipping invalid item: {str(e)}")
            
            logger.info(f"Successfully parsed {len(advisers)} adviser records")
            self.advisers = advisers  # 更新实例变量
            return advisers

        except Exception as e:
            logger.error(f"Error parsing API response: {str(e)}")
            return []


