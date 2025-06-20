 
# 律所信息爬取系统

## 1. 项目架构说明

### 1.1 系统架构图
```
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│   API层       │     │   服务层      │     │   数据层      │
│ (FastAPI)     │────▶│ (业务逻辑)    │────▶│ (数据库/爬虫) │
└───────────────┘     └───────────────┘     └───────────────┘
```

### 1.2 核心模块

#### 1.2.1 目录结构
```
app/
├── api/v1/           # API路由定义
│   ├── crawler_router.py  # 爬虫触发接口
│   ├── sync_router.py     # 同步触发接口
│   └── task_router.py     # 任务管理接口
├── core/             # 核心配置
│   ├── config.py     # 系统配置
│   ├── database.py   # 数据库连接
│   └── logger.py     # 日志配置
├── crawlers/         # 爬虫实现
│   ├── base_crawler.py    # 爬虫基类
│   ├── crawler_lawscot.py # 苏格兰律师协会爬虫
│   └── crawler_lawsocni.py # 北爱尔兰律师协会爬虫
├── models/           # 数据模型
│   ├── data_model.py # 数据库表模型
│   └── schemas.py    # API数据模型
└── services/         # 业务服务
    ├── crawler_trigger.py # 爬虫任务触发
    └── data_storage.py    # 数据存储服务
```

#### 1.2.2 核心功能
- **异步爬虫框架**：基于`BaseCrawler`实现多网站数据爬取
- **任务管理**：支持任务创建、执行、状态跟踪全生命周期管理
- **数据存储**：分批次提交机制，支持大规模数据高效入库
- **错误处理**：完善的异常捕获和日志记录
- **API接口**：RESTful API设计，支持爬虫触发、任务查询等功能

#### 1.2.3 数据模型
- **Company**：公司信息表，存储公司基本信息、联系方式等
- **Lawyer**：律师信息表，关联公司ID，存储律师个人信息
- **Task**：任务表，记录爬虫任务状态、进度和结果

## 2. 安装说明

### 2.1 环境要求
- Python 3.8+ 
- PostgreSQL 12+
- pip 20.0+

### 2.2 安装步骤

#### 2.2.1 克隆代码库
```bash
git clone <repository-url>
cd be-core-scraping
```

#### 2.2.3 安装依赖
```bash
pip install -r requirements.txt
```

#### 2.2.4 配置环境变量
创建`.env`文件，添加以下配置：
```
# 数据库配置
DATABASE_URL=postgresql://user:password@localhost:xxxx/dbname
DB_SCHEMA=customer

# 日志配置
LOG_LEVEL=INFO
LOG_PATH=./logs/app.log  


## 3. 使用说明

### 3.1 启动服务
```bash
python -m app.main
```
服务将运行在 http://localhost:8989

### 3.2 API文档
- Swagger UI: http://localhost:8989/api/v1/docs
- ReDoc: http://localhost:8989/api/v1/redoc

### 3.3 触发爬虫任务
#### 请求示例
```bash
curl -X POST "http://localhost:8989/api/v1/scrapy-trigger" \
  -H "Content-Type: application/json" \
  -d '{
    "scrapy_id": "crawler_lawsocni",
    "scrapy_url": "https://lawsoc-ni.org/using-a-solicitor/find-a-solicitor"
  }'
```

#### 请求参数
| 参数名 | 类型 | 描述 | 可选值 |
|--------|------|------|--------|
| scrapy_id | string | 爬虫ID | crawler_lawsocni, crawler_lawscot|
| scrapy_url | string | 爬取目标URL | 根据爬虫类型确定|

#### 响应示例
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "task_id": 1,
    "trigger_time": 1718901578,
    "scrapy_id": "crawler_lawsocni",
    "scrapy_url": "https://lawsoc-ni.org/using-a-solicitor/find-a-solicitor"
  }
}
```

### 3.4 查看任务状态
通过任务ID查询任务执行状态：
```bash
curl -X GET "http://localhost:8989/api/v1/tasks/{task_id}"
```

### 3.5 日志查看
日志文件位于 `logs/app.log`，包含详细的爬取过程和错误信息

### 3.6 数据存储说明
- 系统采用分批次提交机制，默认每30条公司数据提交一次
- 支持失败数据本地备份，备份文件位于 `app/failed_data/` 目录
- 已实现失败数据重试机制，可通过脚本手动触发重试
```
```
        