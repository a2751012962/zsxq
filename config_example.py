"""
知识星球配置示例文件
复制并重命名为 config.py，然后修改相应的配置

🌟 如何切换到不同的知识星球：
1. 获取星球ID：在星球页面URL中找到，例如 https://wx.zsxq.com/group/12345678901234
2. 获取Cookie：登录后从浏览器开发者工具的Network标签页中获取
3. 修改下面的STAR_ID和COOKIE配置
"""

# ==================== zsxq知识星球配置 ====================
# 🌟 如何切换不同的知识星球：
# 1. 修改 STAR_ID：在星球页面URL中找到，例如 https://wx.zsxq.com/group/48418411254128
# 2. 更新 COOKIE：登录后从浏览器开发者工具中获取最新的cookie
# 3. 其他API配置通常不需要修改

# 示例1：投资类星球
STAR_ID_INVESTMENT = "48418411254128"
COOKIE_INVESTMENT = "你的投资星球cookie"

# 示例2：技术类星球  
STAR_ID_TECH = "12345678901234"
COOKIE_TECH = "你的技术星球cookie"

# 示例3：财经类星球
STAR_ID_FINANCE = "98765432109876"
COOKIE_FINANCE = "你的财经星球cookie"

# 当前使用的配置（修改这里切换星球）
STAR_ID = STAR_ID_INVESTMENT  # 改为其他星球ID
COOKIE = COOKIE_INVESTMENT    # 改为对应的cookie

# zsxq API配置（通常不需要修改）
API_BASE_URL = "https://api.zsxq.com/v2/topics"  # API基础URL
API_HOST = "api.zsxq.com"  # API主机地址
API_TIMEOUT = 15  # 请求超时时间（秒）
API_RETRY_TIMES = 5  # API重试次数
API_RETRY_DELAY = (3, 5)  # 重试延迟范围（秒）

# ==================== 其他配置保持不变 ====================
# OpenAI API配置 (DeepSeek)
OPENAI_API_KEY = "sk-your-api-key"
OPENAI_API_BASE = "https://api.deepseek.com"
OPENAI_MODEL = "deepseek-chat"
TEMPERATURE = 0.2

# 股价获取器配置
USE_YFINANCE = True

# 日志配置
import logging
LOG_LEVEL = logging.INFO
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
LOG_DIR = "logs"

# 其他必要的函数定义...
def setup_logging():
    pass

def get_logger(name=None):
    import logging
    return logging.getLogger(name or __name__) 