"""
此模块负责从zsxq API获取话题数据
"""
import time
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
import random

import requests

from config import STAR_ID, COOKIE, API_BASE_URL, API_HOST, API_TIMEOUT, API_RETRY_TIMES, API_RETRY_DELAY, MAX_TOPIC_PAGES
from utils import get_logger

# 设置日志器
logger = get_logger(__name__)

def 获取今日时间范围():
    """
    获取今日的时间范围（开始和结束时间）
    返回 ISO 格式的时间字符串
    """
    # 获取当前时间（北京时间 UTC+8）
    北京时区 = timezone(timedelta(hours=8))
    现在 = datetime.now(北京时区)
    
    # 今日开始时间（00:00:00）
    今日开始 = 现在.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # 今日结束时间（23:59:59）
    今日结束 = 现在.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    return 今日开始.isoformat(), 今日结束.isoformat()

def 获取日期范围(起始日期: str):
    """
    获取从指定日期到现在的时间范围
    
    参数:
        起始日期 (str): 开始日期，格式为 YYYY-MM-DD
        
    返回:
        tuple: (开始时间ISO字符串, 结束时间ISO字符串)
    """
    北京时区 = timezone(timedelta(hours=8))
    
    # 解析开始日期
    try:
        开始日期 = datetime.strptime(起始日期, "%Y-%m-%d")
        开始时间 = 开始日期.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=北京时区)
    except ValueError:
        raise ValueError(f"无效的日期格式: {起始日期}. 应为 YYYY-MM-DD")
    
    # 结束时间为当前时间
    结束时间 = datetime.now(北京时区)
    
    return 开始时间.isoformat(), 结束时间.isoformat()

def 获取话题页面(结束时间: str = "", 仅今日: bool = True, 起始日期: str = "") -> Dict[str, Any]:
    """
    从zsxq API获取单页话题数据

    参数:
        结束时间 (str): 用于分页的结束时间，为空则获取最新话题
        仅今日 (bool): 是否只过滤今日话题（在客户端过滤）
        起始日期 (str): 过滤的开始日期 (YYYY-MM-DD格式)，为空则不使用（在客户端过滤）

    返回:
        Dict[str, Any]: API返回的JSON响应
    """
    # 生成时间戳（当前时间的Unix时间戳）
    import time as time_module
    timestamp = str(int(time_module.time()))
    
    请求头 = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Cookie": COOKIE,
        "Host": API_HOST,
        "Origin": "https://wx.zsxq.com",
        "Pragma": "no-cache",
        "Priority": "u=1, i",
        "Referer": "https://wx.zsxq.com/",
        "Sec-Ch-Ua": '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"macOS"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
        "X-Aduid": "f0185a8e3-7586-5bcf-7a8d-ebd0fdf0854",
        "X-Request-Id": f"req_{timestamp}_{hash(timestamp) % 100000:05d}",
        "X-Timestamp": timestamp,
        "X-Version": "2.77.0"
    }
    参数 = {
        "scope": "all",
        "count": 20,
    }
    
    # 只添加分页的结束时间，移除begin_time和end_time避免格式错误
    if 结束时间:
        参数["end_time"] = 结束时间

    网址 = API_BASE_URL.replace("/v2/topics", f"/v2/groups/{STAR_ID}/topics")

    for attempt in range(API_RETRY_TIMES):
        try:
            logger.debug(f"正在获取话题 (尝试 {attempt + 1}/{API_RETRY_TIMES})，URL: {网址}")
            logger.debug(f"请求参数: {参数}")
            
            响应 = requests.get(网址, headers=请求头, params=参数, timeout=API_TIMEOUT)
            
            # 永久性错误，直接失败，不重试
            if 响应.status_code in [401, 403]:
                logger.error(f"API请求失败，状态码: {响应.status_code}。请检查Cookie或权限。停止重试。")
                return {}

            # 其他客户端或服务器错误，触发重试
            响应.raise_for_status()
            
            # 成功获取响应
            json_data = 响应.json()
            if "resp_data" in json_data and "topics" in json_data["resp_data"]:
                topics_count = len(json_data["resp_data"]["topics"])
                logger.debug(f"成功获取API响应，包含 {topics_count} 个话题")
            return json_data

        except requests.exceptions.RequestException as e:
            logger.warning(f"获取话题时出错 (尝试 {attempt + 1}/{API_RETRY_TIMES}): {e}")
            
            if attempt < API_RETRY_TIMES - 1:
                sleep_time = random.uniform(*API_RETRY_DELAY)
                # 如果是429，则等待更长时间
                if isinstance(e, requests.exceptions.HTTPError) and e.response.status_code == 429:
                    sleep_time = 60
                    logger.warning(f"请求频率受限 (429)，将在 {sleep_time} 秒后重试...")
                else:
                    logger.info(f"将在 {sleep_time:.1f} 秒后重试...")
                
                time.sleep(sleep_time)
            else:
                logger.error(f"经过 {API_RETRY_TIMES} 次尝试后，获取话题失败。")

    return {}


def 获取所有今日话题(起始日期: str = "") -> List[Dict[str, Any]]:
    """
    获取所有今日话题（或指定日期范围的话题）
    持续获取直到遇到昨天或更早日期的话题为止

    参数:
        起始日期 (str): 过滤的开始日期 (YYYY-MM-DD格式)，为空则只获取今日话题

    返回:
        List[Dict[str, Any]]: 所有获取的话题列表
    """
    所有话题 = []
    结束时间 = ""
    页码 = 1  # 从第1页开始
    连续空响应次数 = 0  # 记录连续空响应的次数
    最大重试次数 = API_RETRY_TIMES     # 最多重试次数
    
    # 显著的分页开始日志
    logger.info("=" * 60)
    if 起始日期:
        logger.info(f"📅 开始获取从【{起始日期}】到现在的所有话题")
        目标日期 = 起始日期  # 获取从指定日期到现在的话题
    else:
        logger.info(f"📅 开始获取【今日所有话题】")
        今日开始, _ = 获取今日时间范围()
        目标日期 = 今日开始[:10]  # 获取今日日期 YYYY-MM-DD
    
    logger.info("📋 将持续获取直到遇到更早日期的话题")
    logger.info("=" * 60)
    
    while True:
        logger.info(f"🔍 正在获取第 【{页码}】 页话题...")
        
        数据 = 获取话题页面(结束时间, True, 起始日期)
        
        # 添加详细的调试信息
        logger.debug(f"API调用返回数据: {bool(数据)}")
        if 数据:
            logger.debug(f"数据结构: {list(数据.keys())}")
            if "resp_data" in 数据:
                resp_data = 数据["resp_data"]
                logger.debug(f"resp_data类型: {type(resp_data)}, 内容: {resp_data is not None}")
                if resp_data and isinstance(resp_data, dict):
                    logger.debug(f"resp_data键: {list(resp_data.keys())}")
                    if "topics" in resp_data:
                        topics = resp_data.get("topics")
                        logger.debug(f"topics类型: {type(topics)}, 长度: {len(topics) if topics else 'None'}")
        
        # 检查各个条件
        条件1 = not 数据
        条件2 = "resp_data" not in 数据 if 数据 else True
        条件3 = not 数据["resp_data"].get("topics") if 数据 and "resp_data" in 数据 else True
        
        logger.debug(f"停止条件检查: not数据={条件1}, no_resp_data={条件2}, no_topics={条件3}")
        
        # 🔄 新增重试逻辑：当API没有返回话题时，等待后重试
        if not 数据 or "resp_data" not in 数据 or not 数据["resp_data"].get("topics"):
            连续空响应次数 += 1
            logger.warning(f"⚠️  API没有返回更多话题 (第{连续空响应次数}/{最大重试次数}次)")
            
            if 连续空响应次数 >= 最大重试次数:
                logger.warning(f"🚫 连续{最大重试次数}次没有获取到话题，停止获取")
                break
            else:
                等待时间 = random.uniform(*API_RETRY_DELAY)  # 随机等待
                logger.info(f"⏰ 等待 {等待时间:.1f} 秒后重试...")
                time.sleep(等待时间)
                continue  # 重试当前页，页码不会增加
        
        # 成功获取数据后，重置计数器并处理数据
        连续空响应次数 = 0
        原始话题列表 = 数据["resp_data"]["topics"]
        原始数量 = len(原始话题列表)
        
        # 检查是否遇到更早的日期 - 这是新的关键逻辑
        遇到更早日期 = False
        符合条件话题 = []
        
        for 话题 in 原始话题列表:
            话题日期 = 话题.get("create_time", "")[:10]
            
            if 起始日期:
                # 指定日期范围：只要是指定日期或之后的都要
                if 话题日期 >= 起始日期:
                    符合条件话题.append(话题)
                else:
                    # 遇到比起始日期更早的话题，停止
                    logger.info(f"🔚 遇到更早日期话题: {话题日期} < {起始日期}，停止获取")
                    遇到更早日期 = True
                    break
            else:
                # 今日话题：只要今日的
                if 话题日期 == 目标日期:
                    符合条件话题.append(话题)
                elif 话题日期 < 目标日期:
                    # 遇到昨天或更早的话题，停止
                    logger.info(f"🔚 遇到昨天或更早话题: {话题日期} < {目标日期}，停止获取")
                    遇到更早日期 = True
                    break
                else:
                    # 未来日期，跳过但继续
                    logger.debug(f"跳过未来日期话题: {话题日期} > {目标日期}")
        
        logger.info(f"✅ 第{页码}页：从原始{原始数量}个话题中过滤出 【{len(符合条件话题)}个】 符合条件的话题")
        
        # 将符合条件的话题添加到结果中
        if 符合条件话题:
            所有话题.extend(符合条件话题)
            logger.info(f"🎯 累计获取到 【{len(所有话题)}个】 符合条件的话题")
        
        # 如果遇到更早日期，停止获取
        if 遇到更早日期:
            break
            
        # 获取下一页的结束时间，使用原始话题列表的最后一个话题时间
        if 原始话题列表:
            最后话题时间 = 原始话题列表[-1]["create_time"]
            # 将时间戳减去1毫秒避免重复
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(最后话题时间.replace('+0800', '+08:00'))
                dt = dt.replace(microsecond=dt.microsecond - 1000 if dt.microsecond >= 1000 else 999000)
                结束时间 = dt.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + '+0800'
            except:
                # 如果时间解析失败，直接使用原时间
                结束时间 = 最后话题时间
        else:
            结束时间 = ""
            
        # 成功处理完一页后，页码加1，准备获取下一页
        页码 += 1
            
        # 安全检查：如果页数过多，停止获取（防止无限循环）
        if 页码 > MAX_TOPIC_PAGES:
            logger.warning(f"⚠️  已获取{页码 - 1}页话题，达到最大页数限制({MAX_TOPIC_PAGES})，停止获取")
            break
            
        time.sleep(1)  # 对API友好

    # 显著的分页总结日志
    logger.info("=" * 60)
    logger.info(f"📊 话题获取完成！总共获取了 【{len(所有话题)}个】 符合条件的话题")
    logger.info(f"📋 共搜索了 【{页码 - 1}页】")
    logger.info("=" * 60)
    
    return 所有话题

# 保留原函数作为兼容性接口
def 获取所有话题(最大页数: int, 仅今日: bool = True, 起始日期: str = "") -> List[Dict[str, Any]]:
    """
    兼容性接口：保持原API不变，内部调用新的基于内容的获取逻辑
    """
    if 仅今日 and not 起始日期:
        return 获取所有今日话题()
    elif 起始日期:
        return 获取所有今日话题(起始日期)
    else:
        # 对于非今日话题，仍使用原逻辑（但现在很少使用）
        logger.warning("获取非今日话题，使用原始分页逻辑")
        return _获取所有话题_原逻辑(最大页数, 仅今日, 起始日期)

def _获取所有话题_原逻辑(最大页数: int, 仅今日: bool = True, 起始日期: str = "") -> List[Dict[str, Any]]:
    """
    原始的基于页数的获取逻辑（作为备用）
    """
    # 暂时返回空列表，这个函数现在很少使用
    logger.warning("使用原始分页逻辑，建议使用新的基于内容的获取方式")
    return []

if __name__ == '__main__':
    if not COOKIE or not STAR_ID:
        logger.error("必须在config.py中设置COOKIE和STAR_ID")
    else:
        # 测试获取今日话题
        今日话题 = 获取所有话题(最大页数=1, 仅今日=True)
        logger.info(f"成功获取{len(今日话题)}个今日话题")
        
        # 如果今日没有话题，尝试获取最近的话题
        if len(今日话题) == 0:
            logger.info("未找到今日话题，获取最近话题...")
            最近话题 = 获取所有话题(最大页数=1, 仅今日=False)
            logger.info(f"成功获取{len(最近话题)}个最近话题")
