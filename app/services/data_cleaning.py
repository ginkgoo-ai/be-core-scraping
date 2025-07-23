from typing import Dict, Any, Optional
from app.core.ai_client import AIClient
from lxml import html 
from urllib.parse import urlparse
import re
import json
from pathlib import Path
import csv
from app.core.logger import logger

class DataCleaningService:
    """数据清洗服务，负责处理爬虫获取的原始数据"""
    
    def __init__(self):
        # self.ai_client = AIClient()
        self.company_area_mapping = DataCleaningService._load_area_of_law_mapping('app/models/company_area_of_law_mapping.csv')
        self.lawyer_area_mapping = DataCleaningService._load_area_of_law_mapping('app/models/lawyer_area_of_law_mapping.csv')
    
    @staticmethod
    def _load_area_of_law_mapping(file_path, column_mapping=None):
        """加载法律领域映射表（优化版）
        参数:
            file_path (str): CSV映射文件路径
            column_mapping (dict, optional): 列名映射（兼容不同CSV格式），如{"old": "old_value", "new": "new_value"}
                                            默认为{"old": "old_value", "new": "new_value", "slug": "slug_id"}
        返回:
            dict: 标准化old_value为键，值为{"new_value": ..., "slug_id": ...}的映射字典
        """
        # 1. 初始化列名映射（兼容大小写和自定义列名）
        default_col_map = {"old": "old_value", "new": "new_value", "slug": "slug_id"}
        col_map = {**default_col_map,** (column_mapping or {})}
        # 列名标准化（转为小写，兼容CSV列名大小写差异）
        normalized_col_names = {k: v.lower() for k, v in col_map.items()}

        mapping = {}  # 最终映射：key为标准化后的old_value，value为{new_value, slug_id}
        normalized_keys = set()  # 用于去重的标准化键集合
        total_rows = 0
        valid_rows = 0
        duplicate_rows = 0
        invalid_rows = 0

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                # 标准化CSV表头（转为小写），方便后续匹配
                reader.fieldnames = [f.lower() for f in reader.fieldnames] if reader.fieldnames else []

                for row_num, row in enumerate(reader, start=2):  # 行号从2开始（表头为1）
                    total_rows += 1
                    try:
                        # 2. 提取并标准化列值（兼容列名大小写）
                        # 从CSV行中提取old_value/new_value/slug_id（列名标准化后匹配）
                        old_val = row.get(normalized_col_names["old"], "").strip()
                        new_val = row.get(normalized_col_names["new"], "").strip()
                        slug_id = row.get(normalized_col_names["slug"], "").strip()

                        # 3. 统一标准化规则（移除所有空白字符+大小写折叠）
                        # 与查询时的normalized_key = re.sub(r'\s+', '', str(key)).casefold()保持一致
                        normalized_old = re.sub(r'\s+', '', old_val).casefold()

                        # 4. 校验核心映射有效性（仅要求old_value和new_value非空）
                        if not normalized_old:  # old_value标准化后为空（如纯空白），视为无效
                            invalid_rows += 1
                            logger.warning(f"行{row_num}：old_value为空或仅含空白字符，跳过")
                            continue
                        if not new_val:  # new_value为空，视为无效
                            invalid_rows += 1
                            logger.warning(f"行{row_num}：new_value为空，跳过")
                            continue

                        # 5. 处理重复映射（保留最后出现的有效映射）
                        if normalized_old in normalized_keys:
                            duplicate_rows += 1
                            logger.info(
                                f"行{row_num}：old_value标准化后重复（{normalized_old}），覆盖为最新映射"
                            )
                        # 更新映射和去重集合
                        mapping[normalized_old] = {
                            "new_value": new_val,
                            "slug_id": slug_id  # 允许slug_id为空（非核心字段）
                        }
                        normalized_keys.add(normalized_old)
                        valid_rows += 1

                    except Exception as e:
                        invalid_rows += 1
                        logger.error(f"行{row_num}处理失败：{str(e)}，跳过该行")
                        continue

            # 6. 加载结果日志（增强可追溯性）
            logger.info(
                f"映射表加载完成：共{total_rows}行，有效{valid_rows}行，重复{duplicate_rows}行，无效{invalid_rows}行"
            )
            return mapping

        except FileNotFoundError:
            logger.error(f"法律领域映射文件不存在：{file_path}")
        except Exception as e:
            logger.error(f"映射文件整体加载失败（非单行错误）：{str(e)}")
        return {}
    
        
    @staticmethod   
    def _load_area_of_law_mapping_old(file_path):
        """加载法律领域映射表
        Args:
            file_path: CSV映射文件路径
        Returns:
            dict: 旧值到新值的映射字典
        """
        mapping = {}
        # 用于跟踪已标准化的键，防止重复
        normalized_keys = set()
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    old_value = row['old_value'].strip()
                    new_value = row['new_value'].strip()
                    slug_id = row.get('slug_id', '').strip()
                    if old_value and new_value and slug_id:
                        # 标准化键用于查重（去空格+casefold）
                        normalized_key = old_value.strip().casefold()
                        # 仅保留首次出现的映射
                        if normalized_key not in normalized_keys:
                            mapping[old_value] = {
                                'new_value': new_value,
                                'slug_id': slug_id
                            }
                            normalized_keys.add(normalized_key)
                        else:
                            logger.warning(f"CSV文件中发现重复映射: {old_value}，已保留首次出现的映射关系")
            return mapping
        except FileNotFoundError:
            logger.error(f"法律领域映射文件不存在: {file_path}")
        except Exception as e:
            logger.error(f"加载法律领域映射文件失败: {str(e)}")
        return {}
    
    def get_area_ids(self, areas, entity_type):
        """获取领域对应的CRM ID列表
        Args:
            areas (list): 清洗后的new_value列表
            entity_type (str): 'company'或'lawyer'
        Returns:
            list: 对应的slug_id列表
        """
        mapping = self.company_area_mapping if entity_type == 'company' else self.lawyer_area_mapping
        # 反转映射: new_value -> slug_id (处理可能的多对一映射)
        value_to_id = {v['new_value'].casefold(): v['slug_id'] for v in mapping.values()}
        return [value_to_id[area.casefold()] for area in areas if area.casefold() in value_to_id]
    
    def clean_company_areas_of_law(self, areas, default_unmapped=None):
        """清洗公司法律领域数据
        Args:
            areas: 原始法律领域数据（JSON字符串或列表）
        Returns:
            list: 清洗后的法律领域列表
        """
        return self._apply_area_mapping(areas, self.company_area_mapping, 
                                      entity_type="company", 
                                      default_unmapped=default_unmapped)
        
    def clean_lawyer_areas_of_law(self, areas, default_unmapped=None):
        """清洗律师法律领域数据
        Args:
            areas: 原始法律领域数据（JSON字符串或列表
        Returns:
            list: 清洗后的法律领域列表
        """
        return self._apply_area_mapping(areas, self.lawyer_area_mapping, 
                                      entity_type="lawyer", 
                                      default_unmapped=default_unmapped)
          
    def _apply_area_mapping(self, areas, mapping, entity_type, default_unmapped=None):
        """应用领域映射转换并过滤未匹配值
        将输入的法律领域列表根据映射表进行转换（完全大小写不敏感），
        对未匹配值使用默认值或直接过滤，并优化日志记录。
        
        参数:
            areas (list or str): 原始法律领域列表或单个领域字符串
            mapping (dict): 领域映射表，键为原始值，值为目标映射值
            entity_type (str): 实体类型，用于日志记录（如"lawyer"或"company"）
            default_unmapped (any, optional): 未匹配值的默认替换值，默认为None
                                            当为None时，未匹配值将被过滤不返回
        返回:
            list: 转换后的法律领域列表，已去重并保持原始顺序
                未匹配且无默认值的项将被排除
        异常:
            任何异常发生时会记录错误日志，并返回原始输入（列表形式）或空列表
        """
        try:
            # 构建大小写不敏感的映射字典（预处理提升性能）
            casefold_mapping = {}
            if mapping:
                for key, value in mapping.items():
                    # 使用casefold进行标准化处理（比lower更彻底）
                    # normalized_key = str(key).strip().casefold()
                    normalized_key = re.sub(r'\s+', '', str(key)).casefold()
                    # 保留原始映射值（不修改大小写）
                    casefold_mapping[normalized_key] = value

            # 处理空输入
            if not areas:
                logger.info(f"No areas provided for {entity_type} mapping")
                return []
            
            if isinstance(areas, str):
                try:
                    areas = json.loads(areas)
                except json.JSONDecodeError:
                    areas = [area.strip() for area in areas.split(',') if area.strip()]

            # 统一输入为列表格式
            areas_list = [areas] if isinstance(areas, str) else areas or []
            result = []
            # 跟踪已记录的未映射值（避免重复日志）
            logged_unmapped = set()

            for raw_area in areas_list:
                if not raw_area or not str(raw_area).strip():
                    continue

                # 标准化当前值用于匹配
                current_area = str(raw_area).strip()
                area_key = re.sub(r'\s+', '', current_area).casefold()

                # 1. 成功找到映射值
                if area_key in casefold_mapping:
                    # result.append(casefold_mapping[area_key])
                    # result.append(casefold_mapping[area_key]['new_value'])
                    result.append({
                        'new_value': casefold_mapping[area_key]['new_value'],
                        'slug_id': casefold_mapping[area_key]['slug_id']
                    })
                    continue

                # 2. 未匹配但使用默认值
                if default_unmapped is not None:
                    result.append({
                        'new_value': default_unmapped,
                        'slug_id': None  
                    })
                    # 避免重复记录相同值的日志
                    if area_key not in logged_unmapped:
                        logger.info(
                            f"Unmapped {entity_type} area: {current_area}, using default",
                            extra={"entity_type": entity_type, "unmapped_value": current_area}
                        )
                        logged_unmapped.add(area_key)
                    continue

                # 3. 未匹配且需过滤（仅记录首次出现的未映射值）
                if area_key not in logged_unmapped:
                    logger.warning(
                        f"Unmapped {entity_type} area: {current_area}, filtered out",
                        extra={"entity_type": entity_type, "unmapped_value": current_area}
                    )
                    logged_unmapped.add(area_key)
            # return list(dict.fromkeys(result))
            seen = set()
            unique_result = []
            for item in result:
                # 将字典转换为可哈希的元组
                item_tuple = tuple(sorted(item.items()))
                if item_tuple not in seen:
                    seen.add(item_tuple)
                    unique_result.append(item)
            return unique_result

        except Exception as e:
            logger.error(
                f"Error applying area mapping for {entity_type}: {str(e)}",
                exc_info=True,
                extra={"entity_type": entity_type, "error_details": str(e)}
            )
            # 异常时安全返回：原始值（列表形式）或空列表
            if isinstance(areas, list):
                return areas
            return [areas] if areas else []
     
    
    @staticmethod
    def extract_number(text: str) -> int:
        """从文本中提取数字（公共方法）
        Args:
            text: 包含数字的文本字符串
        Returns:
            提取到的整数，无数字时返回0
        """
        match = re.search(r'\d+', text)
        return int(match.group()) if match else 0

    @staticmethod
    def extract_domain(url: str) -> str:
        """从URL中提取域名（公共方法）
        Args:
            url: 完整URL字符串
        Returns:
            纯域名（不带协议和路径），空URL返回空字符串
        """
        if not url:
            return ''
        # 使用urllib.parse解析URL
        parsed_url = urlparse(url.lower())
        # 处理无协议的URL情况
        domain = parsed_url.netloc or parsed_url.path.split('/')[0]
        return DataCleaningService.clean_domain(domain)
    
    @staticmethod
    def safe_extract(tree: html.HtmlElement, xpath: str) -> str:
        """安全提取单个元素文本

        Args:
            tree: lxml HTML元素对象
            xpath: XPath表达式

        Returns:
            提取到的文本内容或空字符串
        """
        elements = tree.xpath(xpath)
        if elements:
            return elements[0].strip() if isinstance(elements[0], str) else elements[0].text.strip()
        return ''
    
    
    def clean_website_a_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """清洗网站A的数据"""
        # 这里是示例清洗逻辑，实际项目中需要根据数据结构编写清洗逻辑
        cleaned_data = {
            "products": [],
            "categories": []
        }
        
        # 清洗产品数据
        for product in raw_data.get("data", {}).get("products", []):
            cleaned_product = {
                "id": product.get("id"),
                "name": self._clean_text(product.get("name", "")),
                "price": float(product.get("price", 0))
            }
            cleaned_data["products"].append(cleaned_product)
        
        # 清洗分类数据
        for category in raw_data.get("data", {}).get("categories", []):
            cleaned_data["categories"].append(self._clean_text(category))
        
        return cleaned_data
    
    def clean_website_b_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """清洗网站B的数据"""
        # 这里是示例清洗逻辑，实际项目中需要根据数据结构编写清洗逻辑
        cleaned_data = {
            "articles": [],
            "authors": []
        }
        
        # 清洗文章数据
        for article in raw_data.get("data", {}).get("articles", []):
            cleaned_article = {
                "id": article.get("id"),
                "title": self._clean_text(article.get("title", "")),
                "content": self._clean_text(article.get("content", ""))
            }
            cleaned_data["articles"].append(cleaned_article)
        
        # 清洗作者数据
        for author in raw_data.get("data", {}).get("authors", []):
            cleaned_data["authors"].append(self._clean_text(author))
        
        return cleaned_data
    
    def clean_website_c_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """清洗网站C的数据"""
        # 这里是示例清洗逻辑，实际项目中需要根据数据结构编写清洗逻辑
        cleaned_data = {
            "events": [],
            "locations": []
        }
        
        # 清洗事件数据
        for event in raw_data.get("data", {}).get("events", []):
            cleaned_event = {
                "id": event.get("id"),
                "title": self._clean_text(event.get("title", "")),
                "date": self._clean_date(event.get("date", ""))
            }
            cleaned_data["events"].append(cleaned_event)
        
        # 清洗位置数据
        for location in raw_data.get("data", {}).get("locations", []):
            cleaned_data["locations"].append(self._clean_text(location))
        
        return cleaned_data
    
    def _clean_text(self, text: str) -> str:
        """清洗文本数据，去除多余空格和特殊字符"""
        # 简单的文本清洗
        cleaned = text.strip()
        # 可以使用AI进行更复杂的文本清洗
        # cleaned = self.ai_client.enhance_text(cleaned)
        return cleaned
    
    def _clean_date(self, date_str: str) -> str:
        """清洗日期数据"""
        # 简单的日期格式检查
        # 可以使用AI进行更复杂的日期解析
        return date_str
    
    @staticmethod
    def extract_value_from_redundant_info(
    redundant_info: Optional[Any], 
    key: str, 
    case_sensitive: bool = False   
) -> Optional[str]:
        """从冗余信息中提取指定key的值
        Args:
            redundant_info: 可能包含目标值的冗余数据（字典或JSON字符串）
            key: 要提取的节点键名
        Returns:
            提取到的字符串值（自动去除首尾空格）或None
        """
        if not redundant_info or not key:
            return ""

        # 处理JSON字符串格式的冗余信息
        if isinstance(redundant_info, str):
            try:
                redundant_info = json.loads(redundant_info)
            except json.JSONDecodeError:
                return ""

        # 确保是字典类型
        if not isinstance(redundant_info, dict):
            return ""
        
        # 大小写不敏感查询逻辑
        if case_sensitive:
            value = redundant_info.get(key)
        else:
            # 构建小写键映射
            lower_key = key.lower()
            value = next((v for k, v in redundant_info.items() if k.lower() == lower_key), None)

        # 提取并验证值
        value = redundant_info.get(key)
        return value.strip() if isinstance(value, str) and value.strip() else ""
    
    @staticmethod
    def clean_domain(website):
        """标准化URL域名格式
        Args:
            website (str): 原始网站URL或域名
        Returns:
            str: 标准化后的域名，若输入无效则返回空字符串
        """
        if not isinstance(website, str) or not website.strip():  # 处理空字符串和空白字符串
            logger.warning("无效的网站URL输入: %s", website)
            return ""
        website = re.sub(r'^(https?:)/([^/])', r'\1//\2', website)
        # 补充协议以确保urlparse正确解析
        if not website.startswith(('http://', 'https://')):
            website = f'http://{website}'
        try:
            parsed_url = urlparse(website)
            domain = parsed_url.netloc
            # 移除所有www前缀变体(www., www2., wwwww.等)
            domain = re.sub(r'^www\d*\.', '', domain, flags=re.IGNORECASE)
            # 移除端口号
            domain = domain.split(':')[0].lower()
            return domain if domain else ""
        except Exception as e:
            logger.error(f"域名解析失败: {str(e)}", exc_info=True)
            return ""
        
 
 