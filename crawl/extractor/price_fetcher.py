"""
This module fetches stock prices from different sources.

⚠️ 重要提醒：TLS指纹伪装解决方案：
使用curl_cffi替代requests，通过浏览器TLS指纹伪装避免429 Rate Limit错误。
这比单纯升级yfinance更有效地解决反爬虫检测问题。

curl_cffi can impersonate browser TLS fingerprints to avoid detection.
"""
import re
import time
from typing import Optional

# 使用curl_cffi替代requests以避免TLS指纹检测
try:
    from curl_cffi import requests as cffi_requests
    import requests as std_requests
    TLS_IMPERSONATION_AVAILABLE = True
except ImportError:
    import requests as std_requests
    cffi_requests = None
    TLS_IMPERSONATION_AVAILABLE = False

import yfinance as yf

from config import USE_YFINANCE, get_logger

# 设置日志器
logger = get_logger(__name__)

def create_session():
    """
    创建带有TLS指纹伪装的会话对象
    
    Returns:
        Session: 配置了浏览器TLS指纹伪装的会话对象
    """
    if TLS_IMPERSONATION_AVAILABLE and cffi_requests:
        try:
            # 使用Chrome浏览器TLS指纹伪装 (curl_cffi特有功能)
            session = cffi_requests.Session(impersonate="chrome")
            logger.debug("成功创建Chrome TLS指纹伪装会话")
            return session
        except Exception as e:
            logger.warning(f"TLS指纹伪装失败，回退到普通session: {e}")
            return std_requests.Session()
    else:
        logger.warning("curl_cffi不可用，使用普通requests.Session")
        return std_requests.Session()

def get_currency_symbol(ticker: str) -> str:
    """
    根据股票代码获取对应的货币符号
    
    Args:
        ticker (str): 股票代码
        
    Returns:
        str: 货币符号
    """
    if re.match(r'^\d{6}$', ticker):
        # A股 - 人民币
        return "¥"
    elif re.match(r'^\d{4,5}\.HK$', ticker, re.IGNORECASE):
        # 港股 - 港币  
        return "HK$"
    elif re.match(r'^[A-Z]{1,5}$', ticker, re.IGNORECASE):
        # 美股 - 美元
        return "$"
    else:
        # 默认无货币符号
        return ""

def format_price_with_currency(price: float, ticker: str) -> str:
    """
    格式化价格并添加货币符号
    
    Args:
        price (float): 价格数值
        ticker (str): 股票代码
        
    Returns:
        str: 带货币符号的价格字符串
    """
    currency = get_currency_symbol(ticker)
    return f"{currency}{price:.2f}"

def get_price_from_yfinance(ticker: str) -> str:
    """
    Fetches the stock price from Yahoo Finance using curl_cffi session to avoid rate limits.

    Args:
        ticker (str): The stock ticker symbol.

    Returns:
        str: The formatted price string or "" if failed.
    """
    try:
        # 创建带有TLS指纹伪装的会话
        session = create_session()
        
        # Normalize ticker for yfinance
        if re.match(r'^\d{6}$', ticker):
            # A-shares, try both Shanghai (.SS) and Shenzhen (.SZ)
            stock = yf.Ticker(f"{ticker}.SS", session=session)
            history = stock.history(period="2d")
            if history.empty:
                stock = yf.Ticker(f"{ticker}.SZ", session=session)
                history = stock.history(period="2d")
        elif re.match(r'^\d{4,5}\.HK$', ticker, re.IGNORECASE):
            stock = yf.Ticker(ticker, session=session)
            history = stock.history(period="2d")
        elif re.match(r'^[A-Z]{1,5}$', ticker, re.IGNORECASE):
            stock = yf.Ticker(ticker, session=session)
            history = stock.history(period="2d")
        else:
            logger.warning(f"Invalid ticker format for yfinance: {ticker}")
            return ""

        if history.empty or len(history) < 2:
            logger.warning(f"No data found for ticker: {ticker} on yfinance")
            return ""

        # Get the last two days for price change calculation
        last_close = history['Close'].iloc[-1]
        prev_close = history['Close'].iloc[-2]

        price_change_pct = ((last_close - prev_close) / prev_close) * 100
        sign = "+" if price_change_pct >= 0 else ""
        
        return format_price_with_currency(last_close, ticker)

    except Exception as e:
        logger.error(f"Failed to fetch price for {ticker} from yfinance: {e}")
        return ""

def get_price_from_sina(ticker: str) -> str:
    """
    从新浪财经获取股价信息（备用数据源）
    
    Args:
        ticker (str): 股票代码
        
    Returns:
        str: 格式化的价格字符串 "货币符号+价格" 或 "" 如果失败
    """
    try:
        # 标准化ticker格式
        sina_ticker = ""
        if re.match(r'^\d{6}$', ticker):
            # A股：6开头是上海，0/3开头是深圳
            if ticker.startswith('6'):
                sina_ticker = f"sh{ticker}"
            else:
                sina_ticker = f"sz{ticker}"
        elif re.match(r'^\d{4,5}\.HK$', ticker, re.IGNORECASE):
            # 港股：去掉.HK后缀，加rt_hk前缀
            hk_code = ticker.split('.')[0].zfill(5)  # 补齐到5位
            sina_ticker = f"rt_hk{hk_code}"
        else:
            logger.warning(f"Unsupported ticker format for Sina API: {ticker}")
            return ""

        # 请求新浪财经API
        url = f"http://hq.sinajs.cn/list={sina_ticker}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        session = create_session()
        response = session.get(url, headers=headers, timeout=5)
        response.encoding = 'gbk'  # 新浪API使用GBK编码
        
        if response.status_code != 200:
            logger.error(f"Sina API request failed with status {response.status_code}")
            return ""
            
        # 解析返回数据
        content = response.text.strip()
        if not content or 'var hq_str_' not in content:
            logger.warning(f"No valid data from Sina API for {ticker}")
            return ""
            
        # 提取数据部分
        data_part = content.split('"')[1]
        data_fields = data_part.split(',')
        
        if len(data_fields) < 4:
            logger.warning(f"Insufficient data fields from Sina API for {ticker}")
            return ""
            
        # A股和港股的数据格式略有不同
        if sina_ticker.startswith(('sh', 'sz')):
            # A股格式
            current_price = float(data_fields[3])  # 当前价
            prev_close = float(data_fields[2])     # 昨收价
        elif sina_ticker.startswith('rt_hk'):
            # 港股格式  
            current_price = float(data_fields[6])  # 当前价
            prev_close = float(data_fields[3])     # 昨收价
        else:
            return ""
            
        # 计算涨跌幅
        if prev_close > 0:
            price_change_pct = ((current_price - prev_close) / prev_close) * 100
            sign = "+" if price_change_pct >= 0 else ""
            return format_price_with_currency(current_price, ticker)
        else:
            return format_price_with_currency(current_price, ticker)
            
    except Exception as e:
        logger.error(f"Failed to fetch price for {ticker} from Sina API: {e}")
        return ""

def get_price_from_163(ticker: str) -> str:
    """
    从网易财经获取股价信息（第二备用数据源）
    
    Args:
        ticker (str): 股票代码
        
    Returns:
        str: 格式化的价格字符串 "货币符号+价格" 或 "" 如果失败
    """
    try:
        # 标准化ticker格式
        if re.match(r'^\d{6}$', ticker):
            # A股
            if ticker.startswith('6'):
                api_ticker = f"0{ticker}"  # 上海
            else:
                api_ticker = f"1{ticker}"  # 深圳
        else:
            logger.warning(f"Unsupported ticker format for 163 API: {ticker}")
            return ""

        # 请求网易财经API
        url = f"http://api.money.126.net/data/feed/{api_ticker}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        session = create_session()
        response = session.get(url, headers=headers, timeout=5)
        
        if response.status_code != 200:
            logger.error(f"163 API request failed with status {response.status_code}")
            return ""
            
        # 解析JSON数据
        content = response.text.strip()
        if not content or not content.startswith('_ntes_quote_callback('):
            logger.warning(f"No valid data from 163 API for {ticker}")
            return ""
            
        # 提取JSON部分
        json_start = content.find('{')
        json_end = content.rfind('}') + 1
        json_str = content[json_start:json_end]
        
        import json
        data = json.loads(json_str)
        
        stock_data = data.get(api_ticker, {})
        if not stock_data:
            logger.warning(f"No stock data for {ticker} in 163 API response")
            return ""
            
        current_price = float(stock_data.get('price', 0))
        percent = float(stock_data.get('percent', 0))
        
        sign = "+" if percent >= 0 else ""
        return format_price_with_currency(current_price, ticker)
            
    except Exception as e:
        logger.error(f"Failed to fetch price for {ticker} from 163 API: {e}")
        return ""

def get_price_from_tencent(ticker: str) -> str:
    """
    从腾讯股票API获取股价信息（免费、稳定的备用数据源）
    
    Args:
        ticker (str): 股票代码
        
    Returns:
        str: 格式化的价格字符串 "货币符号+价格" 或 "" 如果失败
    """
    try:
        # 标准化ticker格式
        tencent_ticker = ""
        if re.match(r'^\d{6}$', ticker):
            # A股：6开头是上海，0/3开头是深圳
            if ticker.startswith('6'):
                tencent_ticker = f"sh{ticker}"
            else:
                tencent_ticker = f"sz{ticker}"
        elif re.match(r'^\d{4,5}\.HK$', ticker, re.IGNORECASE):
            # 港股：去掉.HK后缀，加hk前缀
            hk_code = ticker.split('.')[0].zfill(5)  # 补齐到5位
            tencent_ticker = f"hk{hk_code}"
        elif re.match(r'^[A-Z]{1,5}$', ticker, re.IGNORECASE):
            # 美股：不需要前缀，直接使用ticker
            tencent_ticker = f"{ticker.upper()}"
        else:
            logger.warning(f"Unsupported ticker format for Tencent API: {ticker}")
            return ""

        # 请求腾讯股票API
        url = f"http://qt.gtimg.cn/q={tencent_ticker}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        session = create_session()
        response = session.get(url, headers=headers, timeout=5)
        response.encoding = 'gbk'  # 腾讯API使用GBK编码
        
        if response.status_code != 200:
            logger.error(f"Tencent API request failed with status {response.status_code}")
            return ""
            
        # 解析返回数据
        content = response.text.strip()
        if not content or '~' not in content:
            logger.warning(f"No valid data from Tencent API for {ticker}")
            return ""
            
        # 提取数据部分（腾讯API返回格式：v_xxx="股票名~当前价~..."）
        data_part = content.split('"')[1]
        data_fields = data_part.split('~')
        
        if len(data_fields) < 4:
            logger.warning(f"Insufficient data fields from Tencent API for {ticker}")
            return ""
            
        # 获取当前价格（第3个字段）
        current_price = float(data_fields[3])
        return format_price_with_currency(current_price, ticker)
            
    except Exception as e:
        logger.error(f"Failed to fetch price for {ticker} from Tencent API: {e}")
        return ""

def get_price_with_fallback(ticker: str) -> str:
    """
    使用多个数据源获取股价，按优先级依次尝试
    
    Args:
        ticker (str): 股票代码
        
    Returns:
        str: 格式化的价格字符串 "价格" 或 "" 如果全部失败
    """
    if not ticker:
        return ""
    
    # 数据源优先级：yfinance -> 腾讯股票 -> 新浪财经 -> 网易财经  
    data_sources = [
        ("yfinance", get_price_from_yfinance),
        ("tencent", get_price_from_tencent),
        ("sina", get_price_from_sina),
        ("163", get_price_from_163)
    ]
    
    for source_name, fetch_func in data_sources:
        try:
            logger.info(f"尝试从{source_name}获取{ticker}的价格...")
            price = fetch_func(ticker)
            if price:
                logger.info(f"成功从{source_name}获取到价格: {price}")
                return price
            else:
                logger.warning(f"{source_name}未返回有效价格数据")
        except Exception as e:
            logger.error(f"从{source_name}获取价格时出错: {e}")
            
        # 在不同数据源之间添加短暂延迟，避免请求过于频繁
        time.sleep(0.5)
    
    logger.error(f"所有数据源都无法获取{ticker}的价格")
    return ""

def get_price(ticker: str) -> str:
    """
    Fetches the stock price based on the configuration in config.py.

    Args:
        ticker (str): The stock ticker symbol.

    Returns:
        str: The formatted price string "price/change%" or "" if failed.
    """
    if not ticker:
        return ""
        
    logger.info(f"Fetching price for ticker: {ticker}")
    
    if USE_YFINANCE:
        # 使用新的多数据源获取方式
        return get_price_with_fallback(ticker)
    else:
        logger.warning("Alternative price source not implemented")
        return ""
