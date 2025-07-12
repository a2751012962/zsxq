import logging

# ==================== 功能开关配置 ====================
# FINANCE = False: 新版板块-标的对模式 (默认)
# FINANCE = True:  兼容旧版，包含价格抓取功能
FINANCE = False

# 当FINANCE=True时，此开关才生效
USE_YFINANCE = True  # 启用yfinance价格抓取

# 是否在生成CSV后自动转换为格式化的Excel文件
AUTO_CONVERT_TO_EXCEL = True


# ==================== zsxq知识星球配置 ====================
STAR_ID = "48418411254128"  # 星球ID
# 请在此处填入您的真实Cookie, 例如 "zsxq_access_token=ABC..."
COOKIE = "“ # 认证Cookie

# zsxq API配置
API_BASE_URL = "https://api.zsxq.com/v2/topics"
API_HOST = "api.zsxq.com"
API_TIMEOUT = 15  # 请求超时时间（秒）
API_RETRY_TIMES = 5  # API重试次数
API_RETRY_DELAY = (3, 5)  # 重试延迟范围（秒）
MAX_TOPIC_PAGES = 50 # 获取话题的最大页数，防止无限循环


# ==================== OpenAI API配置 ====================
# 请在此处填入您的真实API Key, 例如 "sk-..."
OPENAI_API_KEY = ""
# 推荐使用DeepSeek, 或者根据需要替换为 "https://api.openai.com/v1"
OPENAI_API_BASE = "https://api.deepseek.com"
OPENAI_MODEL = "deepseek-chat"
TEMPERATURE = 0.2  # 推荐0.2，平衡创意和准确性


# ==================== 日志配置 ====================
LOG_LEVEL = logging.INFO
MAX_LOG_FILES = 30  # 最多保留的日志文件数量 
