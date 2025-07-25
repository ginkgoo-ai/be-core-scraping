from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError  
from sqlalchemy.orm import load_only
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from app.models.data_model import Company, Lawyer, Task
from app.core.logger import logger
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

class DataStorageService:
    # 数据存储服务类，负责将清洗后的爬虫数据存储到数据库，增强了错误处理和性能优化


    @staticmethod   
    @retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def _commit_batch(db, batch_size, company_counter, result):
        if db is None:
            logger.error("数据库会话对象为None，无法提交事务")
            raise ValueError(" DB session object 'db' cannot be None")
        try:
            db.commit()
            result['batches_committed'] += 1
            logger.info(f"Committed batch with {batch_size} records...")
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"提交事务失败: {str(e)}")
            raise

    
    @staticmethod
    async def save_crawled_data(
        db, 
        source: str, 
        companies: list = None, 
        lawyers: list = None, 
        batch_size: int = 30
        ) -> dict:
        """
        保存爬取数据到数据库（优化后的分批次提交版本）
        
        参数:
            db: 数据库会话对象
            source: 数据来源标识
            companies: 公司数据列表
            lawyers: 律师数据列表（未使用，保留接口兼容性）
            batch_size: 批量提交大小
            
        返回:
            包含操作结果的字典
        """
        
        result = {
            'source': source,
            'company_success': 0,
            'company_failed': 0,
            'company_new': 0,     
            'company_update': 0,
            'lawyer_new': 0,      
            'lawyer_update': 0,  
            'lawyer_success': 0,
            'lawyer_failed': 0,
            'batches_committed': 0,
            'total_companies': 0
        }
        if db is None:
            raise ValueError("Database session 'db' cannot be None. Check session injection.")
        if not companies:
            logger.warning(f"No company data to save from {source}")
            return result

        result['total_companies'] = len(companies)
        company_counter = 0
        current_batch = []  # 用于收集当前批次的公司对象
        
        try:
            for company_data in companies:
                try:
                    # 提取律师数据并处理
                    lawyer_list = company_data.pop('lawyers', [])
                    stmt = select(Company).where(
                        (Company.domains == company_data.get('domains')) |
                        ((Company.name == company_data.get('name')) & 
                         (Company.company_address == company_data.get('company_address')))
                    ) #同一个公司会有不同地址，不同地址办公室的律师不同，所以需要用地址区分
                    query_result = db.execute(stmt)
                    existing_company = query_result.scalars().first()

                    # 保存/更新公司（使用批量操作优化）
                    if existing_company:
                        result['company_update'] += 1
                        logger.info(f"Updating existing company: {company_data.get('name')} (ID: {existing_company.id})")
                        for key, value in company_data.items():
                            if value is not None:
                                setattr(existing_company, key, value)
                        existing_company.update_date = int(datetime.now().timestamp())
                        company_id = existing_company.id
                        current_batch.append(existing_company)
                    else:
                        result['company_new'] += 1
                        logger.info(f"Creating new company: {company_data.get('name')}")
                        new_company = Company(**company_data)
                        db.add(new_company)
                        db.flush()
                        company_id = new_company.id
                        current_batch.append(new_company)
                    
                    result['company_success'] += 1
                    
                    
                    # 处理律师数据（使用批量添加优化）
                    lawyer_objs = []
                    for lawyer_data in lawyer_list:
                        try:
                            lawyer_data['company_id'] = company_id
                            # 优化律师查询
                            stmt = select(Lawyer).where(
                                Lawyer.name == lawyer_data.get('name'),
                                Lawyer.company_id == company_id
                            )
                            query_result =  db.execute(stmt)
                            existing_lawyer = query_result.scalars().first()                         
                            
                            if existing_lawyer:
                                result['lawyer_update'] += 1
                                logger.info(f"Updating existing lawyer: {lawyer_data.get('name')} (ID: {existing_lawyer.id})")
                                for key, value in lawyer_data.items():
                                    if value is not None:
                                        setattr(existing_lawyer, key, value)
                                lawyer_objs.append(existing_lawyer)
                            else:
                                result['lawyer_new'] += 1
                                logger.info(f"Creating new lawyer: {lawyer_data.get('name')}")
                                new_lawyer = Lawyer(**lawyer_data)
                                lawyer_objs.append(new_lawyer)
                            
                            result['lawyer_success'] += 1
                        except Exception as e:
                            logger.error(f"Failed to process lawyer {lawyer_data.get('name')}: {str(e)}", exc_info=True)
                            result['lawyer_failed'] += 1
                    
                    if lawyer_objs:
                        db.add_all(lawyer_objs)
                    
                    # 批次提交逻辑（带重试机制）
                    result['batches_committed'] += 1
                    company_counter += 1
                    if company_counter % batch_size == 0:
                        await DataStorageService._commit_batch(db, batch_size, company_counter, result)
                        current_batch.clear()  # 使用 clear() 替代重新赋值
                    
                except IntegrityError as e:
                    db.rollback()  # 回滚事务
                    logger.error(f"Integrity error for company {company_data.get('name')}: {str(e)}", exc_info=True)
                    result['company_failed'] += 1
                    continue
                except SQLAlchemyError as e:
                    db.rollback()  # 回滚事务
                    logger.error(f"Database error processing company {company_data.get('name')}: {str(e)}", exc_info=True)
                    result['company_failed'] += 1
                    continue
                except Exception as e:
                    db.rollback()
                    logger.error(f"Unexpected error processing company {company_data.get('name')}: {str(e)}", exc_info=True)
                    result['company_failed'] += 1
   
            # 提交剩余未达批次的数据
            if current_batch:
               await DataStorageService._commit_batch(db, batch_size, company_counter, result)

            logger.info(f"Data storage completed. Source: {source}, Results: {result}")
            return result

        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Database error during batch commit: {str(e)}", exc_info=True)
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Unexpected error during data save: {str(e)}", exc_info=True)
            raise


    @staticmethod
    async def save_lawyers(
        db,
        source: str,
        lawyers: list = None,
        batch_size: int = 30
    ) -> dict:
        """
        单独保存律师数据到数据库，自动关联或创建公司
        参数:
            db: 数据库会话对象
            source: 数据来源标识
            lawyers: 律师数据列表
            batch_size: 批量提交大小
        返回:
            包含操作结果的字典
        """
        result = {
            'source': source,
            'company_success': 0,
            'company_failed': 0,
            'lawyer_success': 0,
            'lawyer_failed': 0,
            'batches_committed': 0,
            'total_lawyers': len(lawyers) if lawyers else 0
        }

        if db is None:
            raise ValueError("Database session 'db' cannot be None")
        if not lawyers:
            logger.warning(f"No lawyer data to save from {source}")
            return result

        current_batch = []
        lawyer_counter = 0

        try:
            for lawyer_data in lawyers:
                try:
                    # 1. 提取公司信息并查找/创建公司
                    company_name = lawyer_data.get('redundant_info', {}).get('company_name')
                    if not company_name:
                        logger.error("Missing company_name in lawyer data")
                        result['lawyer_failed'] += 1
                        continue

                    # 2. 查找公司（优先按名称，可扩展其他字段）
                    stmt = select(Company).where(Company.name == company_name)
                    query_result = db.execute(stmt)
                    company = query_result.scalars().first()

                    # 3. 公司不存在则创建（最小化字段集）
                    
                    if not company:
                        logger.info(f"Creating new company for lawyer: {company_name}")
                        company = Company(
                            name=company_name,
                            source_name=source,
                            domains=['auto-created'],
                            redundant_info={'auto_created': True}  # 标记自动创建
                        )
                        logger.debug(f"新增公司信息: {company}")
                        db.add(company)
                        db.flush()  # 获取company.id
                        result['company_success'] += 1
                    else:
                        logger.debug(f"Found existing company: {company_name} (ID: {company.id})")

                    # 4. 准备律师数据（添加公司关联）
                    lawyer_data['company_id'] = company.id
                    lawyer_data['source_name'] = source

                    # 5. 查找现有律师
                    stmt = select(Lawyer).where(
                        Lawyer.name == lawyer_data.get('name'),
                        Lawyer.company_id == company.id
                    )
                    existing_lawyer = db.execute(stmt).scalars().first()

                    # 6. 更新或创建律师
                    if existing_lawyer:
                        logger.info(f"Updating lawyer: {lawyer_data['name']} (ID: {existing_lawyer.id})")
                        for key, value in lawyer_data.items():
                            if value is not None:
                                setattr(existing_lawyer, key, value)
                        current_batch.append(existing_lawyer)
                    else:
                        logger.info(f"Creating lawyer: {lawyer_data['name']}")
                        new_lawyer = Lawyer(** lawyer_data)
                        current_batch.append(new_lawyer)

                    result['lawyer_success'] += 1
                    lawyer_counter += 1

                    # 7. 批次提交
                    if lawyer_counter % batch_size == 0:
                        await DataStorageService._commit_batch(db, batch_size, lawyer_counter, result)
                        current_batch.clear()

                except IntegrityError as e:
                    db.rollback()
                    logger.error(f"Integrity error for lawyer {lawyer_data.get('name')}: {str(e)}")
                    result['lawyer_failed'] += 1
                except SQLAlchemyError as e:
                    db.rollback()
                    logger.error(f"Database error for lawyer {lawyer_data.get('name')}: {str(e)}")
                    result['lawyer_failed'] += 1
                except Exception as e:
                    db.rollback()
                    logger.error(f"Unexpected error for lawyer {lawyer_data.get('name')}: {str(e)}")
                    result['lawyer_failed'] += 1

            # 提交剩余数据
            if current_batch:
                await DataStorageService._commit_batch(db, batch_size, lawyer_counter, result)

            logger.info(f"Lawyer storage completed. Results: {result}")
            return result

        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Batch commit failed: {str(e)}")
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Data save failed: {str(e)}")
            raise
