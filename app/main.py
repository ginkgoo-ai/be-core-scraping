from fastapi import FastAPI
from app.api.v1.crawler_router import router as crawler_router
from app.api.v1.sync_router import router as sync_router
from app.api.v1.task_router import router as task_router
from app.core.config import settings
from app.core.logger import setup_logging
from app.core.exception_handler import http_exception_handler
from starlette.exceptions import HTTPException as StarletteHTTPException
import uvicorn

# 创建数据库表
# 数据库表迁移请使用Alembic工具
# 初始化命令: alembic init alembic
# 修改alembic.ini配置后执行: alembic revision --autogenerate -m "init" && alembic upgrade head

# 初始化FastAPI应用
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="API Triggered Crawler with CRM Integration",
    docs_url="/api/v1/docs",  # 自定义Swagger UI路径
    redoc_url="/api/v1/redoc"   # 自定义ReDoc路径
)

# 挂载路由
app.include_router(crawler_router, prefix="/api/v1")
app.include_router(sync_router, prefix="/api/v1")
app.include_router(task_router, prefix="/api/v1")

# 注册自定义异常处理器
app.add_exception_handler(StarletteHTTPException, http_exception_handler)

@app.get("/")
async def root():
    return {"message": "Welcome to the API Triggered Crawler"}

if __name__ == "__main__":
    setup_logging()
   
    uvicorn.run(
        app="app.main:app",
        host="0.0.0.0",
        port=8989,  # ← 此处直接指定端口
        reload=True
    
    )