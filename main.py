"""
主程序：运行话题提取处理流程

此脚本从zsxq获取话题数据，提取相关信息，
获取股价，生成摘要，并将结果保存到CSV和JSON文件。
"""
import argparse
import json
import logging
import os
import time
from typing import List, Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import pandas as pd
from tqdm import tqdm

from config import COOKIE, STAR_ID, setup_logging, get_logger
from extractor.client import 获取所有今日话题 as fetch_all_today_topics, 获取所有话题 as fetch_all_topics
from extractor.price_fetcher import get_price
from extractor.text_extractor import TextExtractor
from llm_filter.extractor import extract_stock_info
from extractor.ticker_mapper import map_targets_to_tickers

# --- 配置 ---
输出目录 = "output"

# 设置日志系统
logger = get_logger(__name__)

def 保存结果(结果列表: List[dict], 仅今日: bool, 起始日期: str = ""):
    """将结果保存到CSV和JSON文件，使用优化的命名方式"""
    os.makedirs(输出目录, exist_ok=True)
    
    # 生成当前时间戳 (修复时间错误)
    时间戳 = time.strftime('%Y%m%d_%H%M%S')
    当前日期 = time.strftime('%Y-%m-%d')
    
    # 确定文件命名后缀（使用会议纪要格式）
    年月日 = time.strftime('%y.%m.%d')  # YY.MM.DD 格式
    文件描述 = f"会议纪要_{年月日}"
    
    # 转换数据格式为中文字段名，支持多个投资标的
    转换后结果 = []
    for 数据 in 结果列表:
        # 解析投资标的（可能有多个）
        标的列表 = []
        价格列表 = []
        
        if isinstance(数据.get('target'), str) and 数据['target']:
            # 分割多个标的（可能用逗号、分号等分隔）
            import re
            targets = re.split(r'[,，;；、\s]+', 数据['target'].strip()) if 数据['target'] else []
            tickers = re.split(r'[,，;；、\s]+', 数据.get('ticker', '').strip()) if 数据.get('ticker') else []
            prices = re.split(r'[,，;；、\s]+', str(数据.get('price', '')).strip()) if 数据.get('price') else []
            
            # 确保至少有3个位置
            while len(targets) < 3:
                targets.append('')
            while len(prices) < 3:
                prices.append('')
                
            标的列表 = [t.strip() for t in targets[:3]]
            价格列表 = [p.strip() for p in prices[:3]]
        else:
            标的列表 = ['', '', '']
            价格列表 = ['', '', '']
        
        # 转换日期格式为时分
        日期时分 = ''
        try:
            # 优先使用已提取的时分信息
            日期时分 = 数据.get('时分', '')
            
            # 如果没有时分信息，尝试从create_time提取
            if not 日期时分:
                原始时间 = 数据.get('create_time', '')
                if 原始时间 and 'T' in 原始时间:
                    时间部分 = 原始时间.split('T')[1]
                    if ':' in 时间部分:
                        日期时分 = 时间部分[:5]  # HH:MM
            
            # 如果仍然没有，尝试从date字段获取
            if not 日期时分:
                date_value = 数据.get('date', '')
                if date_value and ':' in date_value:
                    日期时分 = date_value[:5] if len(date_value) >= 5 else date_value
        except Exception as e:
            logging.debug(f"解析时间失败: {e}")
            日期时分 = ''
        
        转换后数据 = {
            '标题': 数据.get('title', ''),
            '日期': 日期时分,
            '板块': 数据.get('sector', ''),
            '标的1': 标的列表[0],
            '价格1': 价格列表[0],
            '标的2': 标的列表[1], 
            '价格2': 价格列表[1],
            '标的3': 标的列表[2],
            '价格3': 价格列表[2],
            '简述': 数据.get('brief', ''),
            '推荐理由': 数据.get('reason', ''),
            '预期': 数据.get('expectation', ''),
            '原文': 数据.get('原文', '')
        }
        转换后结果.append(转换后数据)
    
    df = pd.DataFrame(转换后结果)
    
    # 保存带详细信息的历史文件
    csv文件名 = f"{文件描述}.csv"
    csv路径 = os.path.join(输出目录, csv文件名)
    df.to_csv(csv路径, index=False, encoding='utf-8-sig')
    logger.info(f"历史结果已保存到 {csv路径}")

    json文件名 = f"{文件描述}.json"
    json路径 = os.path.join(输出目录, json文件名)
    with open(json路径, 'w', encoding='utf-8') as f:
        json.dump(结果列表, f, indent=2, ensure_ascii=False)
    logger.info(f"历史结果已保存到 {json路径}")

    # 保存最新文件（覆盖），保持简单命名以便程序调用
    csv简单文件 = os.path.join(输出目录, "result.csv")
    json简单文件 = os.path.join(输出目录, "result.json")
    df.to_csv(csv简单文件, index=False, encoding='utf-8-sig')
    with open(json简单文件, 'w', encoding='utf-8') as f:
        json.dump(结果列表, f, indent=2, ensure_ascii=False)
    logger.info(f"最新结果已更新到 result.csv 和 result.json")
    
    # 输出命名说明
    logger.info(f"文件命名规则说明:")
    logger.info(f"  - 历史文件: {文件描述}")
    logger.info(f"  - 格式说明: 会议纪要_YY.MM.DD")
    logger.info(f"  - 数据统计: 共处理{len(结果列表)}条投资话题")

def 处理单个话题(话题: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    处理单个话题的完整流程：文本提取 + LLM分析 + 股价获取
    
    参数:
        话题 (Dict[str, Any]): 话题数据
        
    返回:
        Optional[Dict[str, Any]]: 处理后的结果，如果无效则返回None
    """
    try:
        # 1. 文本提取
        提取器 = TextExtractor(话题)
        结构化数据 = 提取器.extract_all()
        
        if not 结构化数据:
            # 获取话题标题用于日志
            话题标题 = 话题.get("talk", {}).get("title", "")
            话题文本 = 话题.get("talk", {}).get("text", "")
            if not 话题标题:
                话题标题 = 话题文本.split('\n')[0][:50] if 话题文本 else "无标题"
            
            logger.debug(f"话题内容太短，跳过: {话题标题} (topic_id: {话题.get('topic_id', 'unknown')})")
            return None
        
        logger.debug(f"开始LLM分析话题: {结构化数据['title'][:50]}...")
        
        # 2. LLM信息提取
        数据 = extract_stock_info(结构化数据["summary"])
        
        if not 数据:
            logger.debug(f"LLM未能提取到有效信息: {结构化数据['title'][:30]}...")
            logger.info(f"跳过话题 (LLM未提取到信息): {结构化数据['title']}")
            logger.info(f"话题内容: {结构化数据['summary']}")
            logger.info("=" * 80)
            return None
        
        # 如果没有找到投资标的，跳过此话题
        if not 数据['target'] or 数据['target'] in ['', 'null', None]:
            logger.debug(f"话题中未找到投资标的: {数据.get('title', '未知')}")
            logger.info(f"跳过话题 (未找到投资标的): {结构化数据['title']}")
            logger.info(f"话题内容: {结构化数据['summary']}")
            logger.info("=" * 80)
            return None
        
        # 2.5. 根据标的名称查询股票代码
        ticker_mappings = map_targets_to_tickers(数据['target'])
        logger.debug(f"股票代码映射: {数据['target']} -> {ticker_mappings}")
        
        # 提取ticker列表
        ticker_list = [ticker for _, ticker in ticker_mappings if ticker]
        数据['ticker'] = ','.join(ticker_list) if ticker_list else ""
        
        # 3. 股价获取
        if ticker_list:
            price_list = []
            
            for ticker in ticker_list[:3]:  # 最多处理3个ticker
                if ticker:
                    logger.debug(f"正在获取股价: {ticker}")
                    price = get_price(ticker)
                    if price:
                        price_list.append(price)
                        logger.debug(f"获取到价格: {price}")
                    else:
                        price_list.append("")
                        logger.debug(f"未能获取到{ticker}的价格")
                else:
                    price_list.append("")
            
            # 将价格列表组合成字符串
            数据['price'] = ','.join(price_list) if price_list else ""
        else:
            数据['price'] = ""
        
        # 合并结构化数据和LLM提取的数据
        数据.update(结构化数据)
        
        # 📝 从原始话题提取时间信息到数据中
        原始时间 = 话题.get('create_time', '')
        if 原始时间 and 'T' in 原始时间:
            时间部分 = 原始时间.split('T')[1]
            if ':' in 时间部分:
                数据['时分'] = 时间部分[:5]  # HH:MM
        
        # 添加原文内容
        数据['原文'] = 话题.get("talk", {}).get("text", "").strip()
        
        标题 = 数据.get('title', 结构化数据.get('title', '未知标题')) or '未知标题'
        标的 = 数据.get('target', '未知标的') or '未知标的'
        logger.info(f"✅ 处理完成: {标题[:50]}... | 标的: {标的}")
        return 数据
        
    except Exception as e:
        logger.error(f"处理话题时出错: {e}")
        return None

def 并发处理话题列表(话题列表: List[Dict[str, Any]], 最大工作线程: int = 5) -> List[Dict[str, Any]]:
    """
    并发处理话题列表
    
    参数:
        话题列表 (List[Dict[str, Any]]): 要处理的话题列表
        最大工作线程 (int): 最大并发线程数
        
    返回:
        List[Dict[str, Any]]: 处理成功的结果列表
    """
    结果列表 = []
    
    logger.info("=" * 60)
    logger.info(f"🚀 开始并发处理 {len(话题列表)} 个话题，使用 {最大工作线程} 个线程")
    logger.info("=" * 60)
    
    with ThreadPoolExecutor(max_workers=最大工作线程) as executor:
        # 提交所有任务
        future_to_topic = {executor.submit(处理单个话题, 话题): 话题 for 话题 in 话题列表}
        
        # 收集结果
        已完成 = 0
        for future in as_completed(future_to_topic):
            话题 = future_to_topic[future]
            已完成 += 1
            
            try:
                结果 = future.result()
                if 结果:
                    结果列表.append(结果)
                    标题 = 结果.get('title', '未知标题')
                    logger.info(f"📊 进度: {已完成}/{len(话题列表)} | ✅ 成功: {标题[:30]}...")
                else:
                    # 显示跳过话题的信息
                    话题标题 = 话题.get("talk", {}).get("title", "")
                    话题文本 = 话题.get("talk", {}).get("text", "")
                    
                    if not 话题标题:
                        # 如果没有标题，从文本中获取第一行作为标题
                        话题标题 = 话题文本.split('\n')[0][:50] if 话题文本 else "无标题"
                    
                    logger.info(f"📊 进度: {已完成}/{len(话题列表)} | ⏭️  跳过话题: {话题标题[:30]}...")
            except Exception as e:
                logger.error(f"📊 进度: {已完成}/{len(话题列表)} | ❌ 处理失败: {e}")
    
    logger.info("=" * 60)
    logger.info(f"🎯 并发处理完成！成功处理 {len(结果列表)} 个话题")
    logger.info("=" * 60)
    
    return 结果列表

def main():
    """运行提取和处理流程的主函数"""
    # 设置统一日志系统
    log_file = setup_logging()
    logger.info(f"开始运行投资话题提取系统，日志文件: {log_file}")

    解析器 = argparse.ArgumentParser(description="从zsxq获取和处理话题")
    解析器.add_argument("--pages", type=int, default=3, help="最大获取页数（用于兼容性，新逻辑会自动获取所有符合条件的话题）")
    解析器.add_argument("--today", action="store_true", default=True, help="过滤今日话题（默认）")
    解析器.add_argument("--from-date", type=str, help="从指定日期(YYYY-MM-DD)到现在获取话题，覆盖--today选项")
    参数 = 解析器.parse_args()

    # 确定时间过滤策略
    if 参数.from_date:
        起始日期 = 参数.from_date
        时间过滤信息 = f"从{起始日期}到现在的话题"
        logger.info(f"开始提取{时间过滤信息}")
        话题列表 = fetch_all_today_topics(起始日期)
    else:
        时间过滤信息 = "今日话题"
        logger.info(f"开始提取{时间过滤信息}")
        话题列表 = fetch_all_today_topics()

    if not COOKIE or not STAR_ID:
        logging.error("必须在config.py中设置COOKIE和STAR_ID")
        return
    
    if not 话题列表:
        if 参数.from_date:
            logging.warning(f"未找到从{参数.from_date}到现在的话题")
        else:
            logging.warning("未找到今日话题。请尝试使用--from-date指定更早的日期")
        return

    logging.info(f"找到{len(话题列表)}个话题需要处理")

    结果列表 = 并发处理话题列表(话题列表)

    if not 结果列表:
        logging.warning("没有话题被成功处理")
        return

    保存结果(结果列表, not 参数.from_date, 参数.from_date or "")
    logging.info(f"总结: 从{时间过滤信息}中处理了{len(结果列表)}个话题")

if __name__ == "__main__":
    main()
