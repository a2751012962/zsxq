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
COOKIE = "zsxq_access_token=7F5314F2-F2B5-4249-AA83-C2FB4EE68219_29601D756BC25DAE; sensorsdata2015jssdkcross=%7B%22distinct_id%22%3A%2288441414221452%22%2C%22first_id%22%3A%221978be40064f2a-06a2ccf0c267ce-19525634-1296000-1978be4006510cf%22%2C%22props%22%3A%7B%22%24latest_traffic_source_type%22%3A%22%E7%9B%B4%E6%8E%A5%E6%B5%81%E9%87%8F%22%2C%22%24latest_search_keyword%22%3A%22%E6%9C%AA%E5%8F%96%E5%88%B0%E5%80%BC_%E7%9B%B4%E6%8E%A5%E6%89%93%E5%BC%80%22%2C%22%24latest_referrer%22%3A%22%22%7D%2C%22identities%22%3A%22eyIkaWRlbnRpdHlfY29va2llX2lkIjoiMTk3OGJlNDAwNjRmMmEtMDZhMmNjZjBjMjY3Y2UtMTk1MjU2MzQtMTI5NjAwMC0xOTc4YmU0MDA2NTEwY2YiLCIkaWRlbnRpdHlfbG9naW5faWQiOiI4ODQ0MTQxNDIyMTQ1MiJ9%22%2C%22history_login_id%22%3A%7B%22name%22%3A%22%24identity_login_id%22%2C%22value%22%3A%2288441414221452%22%7D%7D"  # 认证Cookie

# zsxq API配置
API_BASE_URL = "https://api.zsxq.com/v2/topics"
API_HOST = "api.zsxq.com"
API_TIMEOUT = 15  # 请求超时时间（秒）
API_RETRY_TIMES = 5  # API重试次数
API_RETRY_DELAY = (3, 5)  # 重试延迟范围（秒）
MAX_TOPIC_PAGES = 50 # 获取话题的最大页数，防止无限循环


# ==================== OpenAI API配置 ====================
# 请在此处填入您的真实API Key, 例如 "sk-..."
OPENAI_API_KEY = "sk-bb80108ed8104b08bf784feec4329e64"
# 推荐使用DeepSeek, 或者根据需要替换为 "https://api.openai.com/v1"
OPENAI_API_BASE = "https://api.deepseek.com"
OPENAI_MODEL = "deepseek-chat"
TEMPERATURE = 0.2  # 推荐0.2，平衡创意和准确性


# ==================== 日志配置 ====================
LOG_LEVEL = logging.INFO
MAX_LOG_FILES = 30  # 最多保留的日志文件数量 