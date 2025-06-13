from fastapi import FastAPI
from app.api.v1.crawler_router import router as crawler_router
from app.api.v1.crm_router import router as crm_router
from app.core.config import settings
from app.models.data_model import Base
from app.core.database import engine

# 创建数据库表
# Base.metadata.create_all(bind=engine)

# 初始化FastAPI应用
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="API Triggered Crawler with CRM Integration"
)

# 挂载路由
app.include_router(crawler_router, prefix="/api/v1")
app.include_router(crm_router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "Welcome to the API Triggered Crawler"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app="app.main:app",
        host="0.0.0.0",
        port=8989,  # ← 此处直接指定端口
        reload=True
    )