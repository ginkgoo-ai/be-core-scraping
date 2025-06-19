import logging
from logging.handlers import RotatingFileHandler
from app.core.config import settings
import os

class WatchfilesFilter(logging.Filter):
    def filter(self, record):
        # 过滤 watchfiles.main 的 INFO 级日志
        return not (
            record.name == "watchfiles.main" and
            record.levelno == logging.INFO and
            "change detected" in record.getMessage()
        )
        
  # 初始化根日志记录器
def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(settings.LOG_LEVEL)
    #创建日志文件
    log_dir = os.path.dirname(settings.LOG_PATH)
    os.makedirs(log_dir, exist_ok=True)

    # 统一日志格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
     # 添加过滤器到处理器
    console_handler.addFilter(WatchfilesFilter())

    # 文件处理器（自动轮转）
    file_handler = RotatingFileHandler(
        settings.LOG_PATH,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    file_handler.addFilter(WatchfilesFilter()) 

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    return logger
    
    # 创建并导出logger实例
logger = setup_logging()