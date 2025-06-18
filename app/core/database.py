from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base,sessionmaker
from .config import settings

# 创建数据库引擎
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
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
