from sqlalchemy.exc import SQLAlchemyError
from app.models.data_model import Company, Lawyer, Task
from app.core.logger import logger

class DataStorageService:
    # 数据存储服务类
    # 负责将清洗后的爬虫数据存储到数据库

    @staticmethod
    async def save_crawled_data(db, source: str, companies: list = None, lawyers: list = None, batch_size: int = 30) -> dict:
        # 保存爬取数据到数据库（分批次提交版本）
       
        result = {
            'source': source,
            'company_success': 0,
            'company_failed': 0,
            'lawyer_success': 0,
            'lawyer_failed': 0,
            'batches_committed': 0 
        }

        if not companies:
            logger.warning(f"No company data to save from {source}")
            return result

        try:
            company_counter = 0  # 批次计数器
            # 逐个处理公司及其关联律师
            for company_data in companies:
                try:
                    # 1. 处理公司数据
                    lawyer_list = company_data.pop('lawyers', [])
                    
                    # 检查公司是否已存在（支持域名空值情况）
                    query = db.query(Company)
                    if company_data.get('domains'):
                        existing_company = query.filter(Company.domains == company_data['domains']).first()
                    else:
                        existing_company = query.filter(
                            Company.name == company_data['name'],
                            Company.company_address == company_data['company_address']
                        ).first()
                    
                    # 保存/更新公司
                    if existing_company:
                        logger.info(f"Updating existing company: {company_data['name']} (ID: {existing_company.id})")
                        for key, value in company_data.items():
                            if value is not None:
                                setattr(existing_company, key, value)
                        company_id = existing_company.id
                    else:
                        logger.info(f"Creating new company: {company_data['name']}")
                        new_company = Company(** company_data)
                        db.add(new_company)
                        db.flush()  # 刷新获取ID
                        company_id = new_company.id
                    
                    result['company_success'] += 1
                    company_counter += 1
                    
                    # 2. 处理该公司的律师数据
                    for lawyer_data in lawyer_list:
                        try:
                            lawyer_data['company_id'] = company_id
                            existing_lawyer = db.query(Lawyer).filter(
                                Lawyer.name == lawyer_data['name'],
                                Lawyer.company_id == company_id
                            ).first()
                            
                            if existing_lawyer:
                                for key, value in lawyer_data.items():
                                    if value is not None:
                                        setattr(existing_lawyer, key, value)
                            else:
                                new_lawyer = Lawyer(**lawyer_data)
                                db.add(new_lawyer)
                            
                            result['lawyer_success'] += 1
                        except Exception as e:
                            logger.error(f"Failed to save lawyer {lawyer_data.get('name')}: {str(e)}")
                            result['lawyer_failed'] += 1
                    
                    # 3. 批次提交逻辑
                    if company_counter % batch_size == 0:
                        db.commit()
                        db.flush()  # 清空会话缓存
                        result['batches_committed'] += 1
                        logger.info(f"Committed batch {result['batches_committed']} (total companies processed: {company_counter})")
                    
                except Exception as e:
                    logger.error(f"Failed to process company {company_data.get('name')}: {str(e)}")
                    result['company_failed'] += 1
                    continue  # 跳过当前公司

            # 4. 提交剩余未达批次的数据
            if company_counter % batch_size != 0:
                db.commit()
                result['batches_committed'] += 1
                logger.info(f"Committed final batch (remaining companies: {company_counter % batch_size})")
            
            logger.info(f"All data processed. Total batches: {result['batches_committed']}, Results: {result}")
            return result

        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Database error during batch commit: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during data save: {str(e)}")
            raise

    @staticmethod
    def update_task_metrics(db, task_id: int, metrics: dict):
        # 更新任务统计指标
        # 
        # Args:
        #     db: 数据库会话
        #     task_id: 任务ID
        #     metrics: 包含统计数据的字典
        try:
            task = db.query(Task).filter(Task.id == task_id).first()
            if not task:
                logger.warning(f"Task {task_id} not found for metrics update")
                return False

            # 更新任务指标
            if 'company_count' in metrics:
                task.scraped_company_count = metrics['company_count']
            if 'lawyer_count' in metrics:
                task.scraped_lawyer_count = metrics['lawyer_count']
            if 'status' in metrics:
                task.status = metrics['status']
            if 'error_message' in metrics:
                task.error_message = metrics['error_message']

            db.commit()
            return True

        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Failed to update task {task_id} metrics: {str(e)}")
            return False