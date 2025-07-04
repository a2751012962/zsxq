"""
全局配置文件
"""
import os
import logging
import time
from typing import Optional
import glob
from datetime import datetime
import sys

# ==================== zsxq知识星球配置 ====================
# 🌟 如何切换不同的知识星球：
# 1. 修改 STAR_ID：在星球页面URL中找到，例如 https://wx.zsxq.com/group/48418411254128
# 2. 更新 COOKIE：登录后从浏览器开发者工具中获取最新的cookie
# 3. 其他API配置通常不需要修改

# 当前星球ID（从星球URL中获取）
STAR_ID = "48418411254128"

# 认证Cookie（从浏览器开发者工具中获取）
COOKIE = ""

# zsxq API配置（通常不需要修改）
API_BASE_URL = "https://api.zsxq.com/v2/topics"  # API基础URL
API_HOST = "api.zsxq.com"  # API主机地址
API_TIMEOUT = 15  # 请求超时时间（秒）
API_RETRY_TIMES = 5  # API重试次数
API_RETRY_DELAY = (3, 5)  # 重试延迟范围（秒）

# OpenAI API配置 (DeepSeek)
OPENAI_API_KEY = ""
OPENAI_API_BASE = "https://api.deepseek.com"
OPENAI_MODEL = "deepseek-chat"
TEMPERATURE = 0.4

# 股价获取器配置
USE_YFINANCE = True

# 日志配置
LOG_LEVEL = logging.INFO
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
LOG_DIR = "logs"

# ==================== 话题抓取参数 ====================
# 每次最多抓取多少页（每页60条，防止死循环）
MAX_TOPIC_PAGES = 100  # 默认最多抓取20页（1200条），如需更多可调整

def setup_logging() -> None:
    """
    统一配置日志系统，确保所有模块使用一致的日志格式
    同时清理旧的日志文件，只保留最新的30个
    """
    # 确保日志目录存在
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
    
    # 清理旧的日志文件，只保留最新的30个
    log_pattern = os.path.join(LOG_DIR, "extraction_*.log")
    log_files = glob.glob(log_pattern)
    
    if len(log_files) > 30:
        # 按文件修改时间排序，最新的在前
        log_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        
        # 删除多余的旧日志文件
        files_to_delete = log_files[30:]  # 保留前30个，删除其余的
        for file_path in files_to_delete:
            try:
                os.remove(file_path)
                print(f"🗑️ 删除旧日志文件: {os.path.basename(file_path)}")
            except Exception as e:
                print(f"⚠️ 删除日志文件失败 {file_path}: {e}")
        
        if files_to_delete:
            print(f"📋 日志清理完成，删除了 {len(files_to_delete)} 个旧文件，保留最新 30 个")
    
    # 生成日志文件名
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_filename = f"logs/extraction_{timestamp}.log"
    
    # 配置根日志记录器
    logging.basicConfig(
        level=LOG_LEVEL,
        format=LOG_FORMAT,
        handlers=[
            logging.FileHandler(log_filename, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ],
        force=True  # 强制重新配置，覆盖之前的配置
    )
    
    # 为特定的第三方库设置日志级别，减少噪音
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)

def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    获取带有模块名的日志器
    
    Args:
        name: 模块名，通常传入__name__
        
    Returns:
        Logger: 配置好的日志器
    """
    return logging.getLogger(name or __name__)
