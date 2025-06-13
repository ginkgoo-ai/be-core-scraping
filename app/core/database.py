from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import settings

# 创建数据库引擎
# engine = create_engine(
#     settings.DATABASE_URL,
#     pool_pre_ping=True,
#     pool_size=10,
#     max_overflow=20
# )
# engine = create_engine(settings.DATABASE_URL)  
engine = create_engine(
    str(settings.DATABASE_URL),  # 转换为字符串
    pool_pre_ping=True
)
# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基类模型
Base = declarative_base()

def get_db():
    """依赖注入函数，用于获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
