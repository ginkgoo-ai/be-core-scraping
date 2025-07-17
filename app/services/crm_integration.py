
import aiohttp 
from app.core.config import settings
from app.core.logger import logger
from app.models.data_model import Company, Lawyer,SourceName
import json
from asyncio import gather
import asyncio
import datetime
from datetime import timezone
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from concurrent.futures import ThreadPoolExecutor
import asyncio
from app.services.data_cleaning import DataCleaningService

class CRMIntegrationService:
    def __init__(self, db_session):
        self.db_session = db_session
        self.executor = ThreadPoolExecutor(max_workers=5)  # 初始化线程池
        self.session = None
        #attio API限制请求频次25/s
        self.company_semaphore = asyncio.Semaphore(15)  # company级并发控制
        self.lawyer_semaphore = asyncio.Semaphore(15)     # lawyer级并发控制
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
        
    @retry(
        stop=stop_after_attempt(5),  # 最大重试次数
        wait=wait_exponential(multiplier=1, min=1, max=10),  # 指数退避
        retry=retry_if_exception_type((ValueError, aiohttp.ClientError)),
    )
    #定义session 上下文管理器
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    async def __aexit__(self, exc_type, exc, tb):
        self.executor.shutdown(wait=True)
        if self.session:
            await self.session.close()
        
    #429重试逻辑    
    def _parse_retry_after(self, retry_after_header):
        try:
            return int(retry_after_header)
        except (ValueError, TypeError):
            pass
        if isinstance(retry_after_header, str):
            try:
                # 解析日期字符串并添加UTC时区信息
                retry_datetime = datetime.datetime.strptime(
                    retry_after_header, '%a, %d %b %Y %H:%M:%S GMT'
                ).replace(tzinfo=timezone.utc)
                # 获取当前UTC时间
                now = datetime.datetime.now(timezone.utc)
                # 计算时间差并转换为秒数
                time_diff = retry_datetime - now
                seconds = int(time_diff.total_seconds())
                # 确保等待时间不为负（服务器时间可能比本地快）
                return max(seconds, 1)
            except ValueError:
                pass

        # 所有解析失败时返回默认值
        return 1


    
    #定义attio请求方法
    async def send_attio_request(self, endpoint, data, method='post'):
        """
        发送Attio API请求，包含速率限制和错误重试机制
        :param endpoint: API端点路径（如'/objects/people/records'）
        :param data: 请求数据（JSON对象）
        :param method: HTTP方法（默认为'post'）
        :return: API响应JSON数据
        """
        timeout = aiohttp.ClientTimeout(total=30)
        full_url = f"{self.attio_api_base}/{endpoint}"
        method_lower = method.lower()
        max_retries = 5
        retry_count = 0
        if method.lower() not in ['put', 'post']:
                    logger.error(f"CRM API请求方式不对: 实际请求：{method}，仅支持put/post")
                    raise ValueError(f"Unsupported HTTP method: {method}")
        try:
            session_method = getattr(self.session, method_lower)
            while retry_count < max_retries:   
                async with session_method(full_url, json=data, headers=self.headers,timeout=timeout) as response:
                    if response.status == 429:   # 处理429速率限制错误
                        retry_after = self._parse_retry_after(response.headers.get('Retry-After', '1'))
                        logger.warning(f"API速率限制触发，将在{retry_after}秒后重试(第{retry_count+1}次)")
                        await asyncio.sleep(retry_after)
                        retry_count += 1
                        continue
                        
                    if response.status >= 400:
                        error_details = await response.text()
                        logger.error(f"API请求失败: {response.status}，详情: {error_details}")
                        response.raise_for_status() 
                    return await response.json()
            raise aiohttp.ClientError(f"达到最大重试次数{max_retries}次，API请求仍然失败")
        
        except aiohttp.ClientResponseError as e:
            response_text = await e.response.text() if e.response else "无响应内容"
            logger.error(
                f"API请求失败: 状态码={e.status}, 原因={e.message}, "
                f"响应内容={response_text}",  
                exc_info=True
            )
            raise 
        except asyncio.TimeoutError:
                logger.error(f"Attio API请求超时: {full_url}")
                raise  # 重新抛出以让上层处理
        except aiohttp.ClientError as e:
                logger.error(f"Attio API请求失败: {str(e)}")
                raise
        except Exception as e:
            logger.error(f"请求发生异常: {str(e)}", exc_info=True)
            
            
           
    async def get_company_data(self, sync_source: str):
        # 根据sync_source查询公司数据
        def sync_query():
            query = self.db_session.query(Company)
            if sync_source != "all":
                query = query.filter(Company.source_name == sync_source) 
            return query.all()

        # 提交同步任务到线程池执行
        return await asyncio.get_event_loop().run_in_executor(
            self.executor,
            sync_query  # 传递函数对象，而非执行结果
        )
       
                
    async def get_company_lawyers(self, company_id):
        def sync_query():
            return self.db_session.query(Lawyer).filter(
                Lawyer.company_id == company_id
            ).all()
    
        return await asyncio.get_running_loop().run_in_executor(
            self.executor, sync_query
        )
    
    def _build_company_data(self, company):
        try:
            # 获取字段映射配置，处理配置缺失情况
            field_mapping = settings.CRM_COMPANY_FIELD_MAPPING
            if not isinstance(field_mapping, dict):
                logger.warning("CRM_COMPANY_FIELD_MAPPING配置格式错误，使用默认映射")
                field_mapping = {}

            # 处理法律领域数据
            if not company.areas_of_law:
                areas_of_law = ""
            else:
                try:
                    parsed = json.loads(company.areas_of_law)
                    if isinstance(parsed, list):
                        areas_of_law = ", ".join(parsed)
                    else:
                        areas_of_law = str(parsed)
                except json.JSONDecodeError:
                    areas_of_law = company.areas_of_law
                except Exception as e:
                    logger.error(f"解析areas_of_law时发生意外错误: {str(e)}")
                    areas_of_law = ""

            # 处理regulated_body枚举映射
            try:
                source_name = company.source_name.upper()
                regulated_body_value = [SourceName[source_name].value]
            except KeyError:
                logger.error(f"无效的source_name: {company.source_name}，无法映射到SourceName枚举")
                regulated_body_value = []
            except AttributeError:
                logger.error(f"company对象缺少source_name属性")
                regulated_body_value = []

            # 构建并返回数据
            return {
                "data": {
                    "values": {
                        field_mapping.get("name", "name"): company.name,
                        field_mapping.get("domains", "domains"): [company.domains] if company.domains else [],
                        field_mapping.get("company_email", "company_email"): company.company_email or "",
                        field_mapping.get("company_phone", "company_phone"): company.company_phone or "",
                        field_mapping.get("areas_of_law", "areas_of_law"): areas_of_law,
                        field_mapping.get("total_solicitors", "total_solicitors"): company.total_solicitors or 0,
                        field_mapping.get("scottish_partners", "scottish_partners"): company.scottish_partners or 0,
                        field_mapping.get("regulated_body", "regulated_body"): regulated_body_value,
                        field_mapping.get("company_address", "company_address"): company.company_address or "",
                        field_mapping.get('city'): DataCleaningService.extract_value_from_redundant_info(company.redundant_info, 'city'),
                    }
                }
            }

        except AttributeError as e:
            logger.error(f"环境变量配置错误: 缺少必要的配置项 - {str(e)}")
            raise ValueError(f"构建公司数据失败: 配置不完整") from e
        except Exception as e:
            logger.error(f"构建公司数据时发生未预期错误: {str(e)}", exc_info=True)
            raise ValueError(f"构建公司数据失败: {str(e)}") from e


    def _build_lawyer_data(self, lawyer, crm_company_id):
        try:
            # 获取字段映射配置，处理配置缺失情况
            field_mapping = settings.CRM_LAWYER_FIELD_MAPPING
            if not isinstance(field_mapping, dict):
                logger.warning("CRM_LAWYER_FIELD_MAPPING配置格式错误，使用默认映射")
                field_mapping = {}

            # 验证公司ID有效性
            if not crm_company_id:
                logger.error("crm_company_id为空，无法关联公司")
                raise ValueError("构建律师数据失败：缺少公司ID")

            # 构建并返回数据
            return {
                "data": {
                    "values": {
                        field_mapping.get("name", "name"): [{ "first_name": "","last_name": "","full_name": lawyer.name}],
                        field_mapping.get("email", "email"): [lawyer.email_addresses] if lawyer.email_addresses else [],
                        field_mapping.get("phone", "Telephone"): lawyer.telephone if lawyer.telephone else "",
                        field_mapping.get("address", "address"): lawyer.address if lawyer.address else "",
                        field_mapping.get("company", "company"): [{
                            "target_object": "companies",
                            "target_record_id": crm_company_id
                        }]
                    }
                }
            }

        except AttributeError as e:
            logger.error(f"环境变量或对象属性错误: {str(e)}", exc_info=True)
            raise ValueError(f"构建律师数据失败: 缺少必要配置或属性") from e
        except KeyError as e:
            logger.error(f"枚举或映射键错误: {str(e)}", exc_info=True)
            raise ValueError(f"构建律师数据失败: 无效的映射键") from e
        except Exception as e:
            logger.error(f"构建律师数据时发生未预期错误: {str(e)}", exc_info=True)
            raise ValueError(f"构建律师数据失败: {str(e)}") from e  

    #同步单个公司信息   
    async def _sync_single_company(self, company):
        try:
            async with self.company_semaphore:
                company_endpoint = "objects/companies/records"
                method = 'put' if company.domains else 'post'
                endpoint = f"{company_endpoint}?matching_attribute=domains" if method == 'put' else company_endpoint
                response = await self.send_attio_request(
                    endpoint,
                    self._build_company_data(company),
                    method=method
                )
                if response:
                    crm_company_id = response.get("data", {}).get("id", {}).get("record_id")
                    if not crm_company_id:
                        logger.error(f"公司 {company.name} 未获取到CRM ID")
                        return None

                    # 同步公司关联的律师
                    # lawyers = self.db_session.query(Lawyer).filter(Lawyer.company_id == company.id).all()
                    await self._sync_company_lawyers(company.id, crm_company_id)
                    # if lawyers:
                    #     await self._sync_company_lawyers(lawyers, crm_company_id)
                    # else:
                    #    logger.info(f"公司 {company.name} 没有关联律师，跳过律师同步")
                   
                    logger.info(f"公司 {company.name} 同步成功")
                    return response
                return None
        except Exception as e:
            logger.error(f"公司 {company.name} 同步失败: {str(e)}", exc_info=True)
            raise
        
    #同步单个律师信息 
    async def _sync_single_lawyer(self, lawyer, crm_company_id):
        try:
            async with self.lawyer_semaphore:  # 使用律师专用信号量
                lawyer_endpoint = "objects/people/records"
                lawyer_data = self._build_lawyer_data(lawyer, crm_company_id)
                method = 'put' if lawyer.email_addresses else 'post'
                endpoint = f"{lawyer_endpoint}?matching_attribute=email_addresses" if method == 'put' else lawyer_endpoint
                return await self.send_attio_request(endpoint, lawyer_data, method=method)
        except Exception as e:
            logger.error(f"同步律师 {lawyer.name} 时发生异常", exc_info=True)
            raise
     #同步律师列表 
    async def _sync_company_lawyers(self, company_id, crm_company_id):
        try:
            lawyers = await self.get_company_lawyers(company_id)  
            if not lawyers:
                logger.info(f"公司ID {company_id} 没有关联律师，跳过律师同步")
                return
            logger.info(f"开始同步公司ID {company_id} 的 {len(lawyers)} 名律师")
            lawyer_tasks = [
                self._sync_single_lawyer(lawyer, crm_company_id)
            for lawyer in lawyers
        ]
            results = await asyncio.gather(*lawyer_tasks, return_exceptions=True)
            success_count = 0
            for i, result in enumerate(results):
                lawyer = lawyers[i]
                if isinstance(result, Exception):
                    self.lawyer_api_failure += 1
                    logger.error(f"律师 {lawyer.name} (ID:{lawyer.id}) 同步失败: {str(result)}")
                else:
                    success_count += 1
                    self.lawyer_api_success += 1
                    logger.info(f"律师 {lawyer.name} 同步成功")
        
            logger.info(f"公司ID {company_id} 律师同步完成: 成功 {success_count}/{len(lawyers)} 名")
            return success_count
        
        except Exception as e:
            logger.error(f"同步公司ID {company_id} 的律师时发生错误: {str(e)}", exc_info=True)
            return 0
            
            
    #批量同步信息            
    async def sync_companies(self, sync_source: str):  
        try:  
            companies = await self.get_company_data(sync_source)
            logger.info(f"获取到 {len(companies)} 家公司数据需要同步")
            if not companies:
                logger.info("没有需要同步的公司数据")
                return {'company_count': 0, 'lawyer_count': 0, 'results': []}
            # 创建公司同步任务列表
            company_tasks = [self._sync_single_company(company) for company in companies]
            company_results = await gather(*company_tasks, return_exceptions=True)

            results = []
            for i, result in enumerate(company_results):
                company = companies[i]
                if isinstance(result, Exception):
                    self.company_api_failure += 1
                    # 记录详细异常信息，包括公司名称和异常堆栈
                    logger.error(f"公司 {company.name} 同步任务失败: {str(result)}", exc_info=True)
                elif result is not None:
                    
                    self.company_api_success += 1
                    results.append(result)

            return {
                'company_count': self.company_api_success,
                'lawyer_count': self.lawyer_api_success,
                'results': results
            }
        except Exception as e:
            # 捕获整个同步过程中的未预料异常
            logger.critical(f"公司同步流程发生致命错误: {str(e)}", exc_info=True)
            # 可以选择重新抛出异常或返回错误状态
            raise
                
