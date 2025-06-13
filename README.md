API触发的爬虫项目，使用FastAPI、PostgreSQL和OpenAI构建。

## 项目结构
{project_name}/
├── .gitignore
├── README.md
├── requirements.txt
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── crawler_router.py    # 爬虫触发接口
│   │       └── crm_router.py       # CRM数据接口
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py              # 配置管理
│   │   ├── database.py            # 数据库连接
│   │   └── ai_client.py           # AI服务客户端
│   ├── crawlers/
│   │   ├── __init__.py
│   │   ├── base_crawler.py        # 爬虫基类
│   │   ├── crawler_a.py           
│   │   ├── crawler_b.py
│   │   ├── crawler_c.py
│   │   └── trigger_service.py     # 爬虫触发服务
│   ├── models/
│   │   ├── __init__.py
│   │   ├── data_model.py          # SQLAlchemy模型
│   │   └── schemas.py             # Pydantic模型
│   └── services/
│       ├── __init__.py
│       ├── data_cleaning.py       # 数据清洗
│       ├── data_storage.py        # 数据存储
│       └── crm_integration.py     # CRM集成
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── api/
│   │   ├── test_crawler_api.py
│   │   └── test_crm_api.py
│   └── crawlers/
│       └── test_trigger_service.py
└── scripts/
    └── deploy_crawlers.py         # 部署脚本
## 初始化项目

1. 克隆仓库
2. 创建虚拟环境
3. 安装依赖: `pip install -r requirements.txt`
4. 配置环境变量
5. 运行应用: `python app/main.py`