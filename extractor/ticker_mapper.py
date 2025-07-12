"""
智能股票代码映射模块
使用akshare获取完整的A股和港股清单，实现智能搜索匹配
"""

import re
import json
import os
from typing import Optional, List, Dict, Tuple
from difflib import SequenceMatcher
import time

import akshare as ak
import pandas as pd

from utils import get_logger

logger = get_logger(__name__)

class StockDatabase:
    """股票数据库类，负责获取和管理股票清单"""
    
    def __init__(self, cache_file: str = "data/stock_cache.json"):
        self.cache_file = cache_file
        self.stock_data: Dict[str, Dict] = {}
        self.last_update: float = 0
        self.cache_expire_hours = 24  # 缓存24小时
        
        # 确保数据目录存在
        os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
        
        # 加载缓存
        self._load_cache()
        
        # 如果缓存过期或为空，更新数据
        if self._is_cache_expired() or not self.stock_data:
            self.update_stock_data()
    
    def _load_cache(self) -> None:
        """从缓存文件加载股票数据"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    self.stock_data = cache_data.get('stock_data', {})
                    self.last_update = cache_data.get('last_update', 0)
                logger.info(f"从缓存加载了 {len(self.stock_data)} 只股票数据")
        except Exception as e:
            logger.warning(f"缓存加载失败: {e}")
            self.stock_data = {}
            self.last_update = 0
    
    def _save_cache(self) -> None:
        """保存股票数据到缓存文件"""
        try:
            cache_data = {
                'stock_data': self.stock_data,
                'last_update': self.last_update
            }
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            logger.info(f"已保存 {len(self.stock_data)} 只股票数据到缓存")
        except Exception as e:
            logger.error(f"缓存保存失败: {e}")
    
    def _is_cache_expired(self) -> bool:
        """检查缓存是否过期"""
        if self.last_update == 0:
            return True
        
        hours_passed = (time.time() - self.last_update) / 3600
        return hours_passed > self.cache_expire_hours
    
    def update_stock_data(self) -> None:
        """更新股票数据（A股+港股）"""
        logger.info("开始更新股票数据...")
        self.stock_data = {}
        
        # 获取A股数据
        self._fetch_a_shares()
        
        # 获取港股数据  
        self._fetch_hk_shares()
        
        # 更新时间戳并保存缓存
        self.last_update = time.time()
        self._save_cache()
        
        logger.info(f"股票数据更新完成，共 {len(self.stock_data)} 只股票")
    
    def _fetch_a_shares(self) -> None:
        """获取A股列表"""
        try:
            logger.info("正在获取A股列表...")
            # 获取沪深股票基本信息
            df_a = ak.stock_info_a_code_name()
            
            for _, row in df_a.iterrows():
                code = str(row['code']).zfill(6)  # 确保6位代码
                name = str(row['name']).strip()
                
                # 清理名称（去除ST、*ST等前缀）
                clean_name = self._clean_company_name(name)
                
                self.stock_data[code] = {
                    'code': code,
                    'name': name,
                    'clean_name': clean_name,
                    'market': 'A',
                    'exchange': 'SH' if code.startswith(('60', '68', '51')) else 'SZ'
                }
            
            logger.info(f"获取到 {len([k for k, v in self.stock_data.items() if v['market'] == 'A'])} 只A股")
            
        except Exception as e:
            logger.error(f"获取A股数据失败: {e}")
    
    def _fetch_hk_shares(self) -> None:
        """获取港股列表"""
        try:
            logger.info("正在获取港股列表...")
            
            # 尝试多个港股数据源以获取完整列表
            hk_data_sources = [
                ('stock_hk_spot_em', 'ak.stock_hk_spot_em()'),  # 东财港股主板实时行情
                ('stock_hk_spot', 'ak.stock_hk_spot()'),       # 东财港股实时行情
            ]
            
            df_hk = None
            for func_name, func_desc in hk_data_sources:
                try:
                    logger.info(f"尝试使用 {func_desc}")
                    if func_name == 'stock_hk_spot_em':
                        df_hk = ak.stock_hk_spot_em()
                    elif func_name == 'stock_hk_spot':
                        df_hk = ak.stock_hk_spot()
                    
                    if df_hk is not None and not df_hk.empty:
                        logger.info(f"成功使用 {func_desc} 获取到 {len(df_hk)} 条港股数据")
                        break
                    else:
                        logger.warning(f"{func_desc} 返回空数据")
                        
                except Exception as e:
                    logger.warning(f"{func_desc} 调用失败: {e}")
                    continue
            
            if df_hk is not None and not df_hk.empty:
                logger.info(f"开始处理 {len(df_hk)} 条港股数据...")
                
                # 打印列信息以便调试
                logger.info(f"港股数据列: {list(df_hk.columns)}")
                
                # 根据不同的数据源处理不同的列结构
                if 'symbol' in df_hk.columns and 'name' in df_hk.columns:
                    # 使用 symbol 和 name 列
                    symbol_col, name_col = 'symbol', 'name'
                elif '代码' in df_hk.columns and '名称' in df_hk.columns:
                    # 中文列名
                    symbol_col, name_col = '代码', '名称'
                elif 'Symbol' in df_hk.columns and 'Name' in df_hk.columns:
                    # 英文大写列名
                    symbol_col, name_col = 'Symbol', 'Name'
                else:
                    # 尝试使用第一列和第二列
                    columns = list(df_hk.columns)
                    if len(columns) >= 2:
                        symbol_col, name_col = columns[0], columns[1]
                        logger.info(f"使用默认列映射: 代码列={symbol_col}, 名称列={name_col}")
                    else:
                        logger.error(f"无法确定港股数据的列结构: {columns}")
                        return
                
                processed_count = 0
                for _, row in df_hk.iterrows():
                    try:
                        # 港股代码通常是5位数字
                        code = str(row[symbol_col]).strip()
                        name = str(row[name_col]).strip()
                        
                        # 跳过无效数据
                        if not code or not name or code in ['nan', 'None'] or name in ['nan', 'None']:
                            continue
                        
                        # 清理名称
                        clean_name = self._clean_company_name(name)
                        
                        # 港股代码格式：原代码.HK
                        hk_code = f"{code}.HK"
                        
                        self.stock_data[hk_code] = {
                            'code': hk_code,
                            'name': name,
                            'clean_name': clean_name,
                            'market': 'HK',
                            'exchange': 'HK'
                        }
                        processed_count += 1
                        
                    except Exception as e:
                        logger.warning(f"处理港股数据行失败: {e}")
                        continue
                
                logger.info(f"成功处理 {processed_count} 只港股")
            else:
                logger.warning("所有港股数据源都无法获取到数据")
            
        except Exception as e:
            logger.error(f"获取港股数据失败: {e}")
        
        # 统计并记录港股数量
        hk_count = len([k for k, v in self.stock_data.items() if v['market'] == 'HK'])
        logger.info(f"最终获取到 {hk_count} 只港股")
    
    def _clean_company_name(self, name: str) -> str:
        """清理公司名称，去除特殊标记和后缀"""
        # 去除ST、*ST、N、C等前缀
        cleaned = re.sub(r'^(\*?ST|N|C)', '', name).strip()
        
        # 去除常见后缀
        suffixes = ['股份有限公司', '有限公司', '集团', '控股', '科技', '股份', '公司', 
                   '集团有限公司', '科技有限公司', '控股有限公司']
        for suffix in suffixes:
            if cleaned.endswith(suffix):
                cleaned = cleaned[:-len(suffix)].strip()
                break
        
        return cleaned

class SmartTickerMapper:
    """智能股票代码映射器"""
    
    def __init__(self):
        self.db = StockDatabase()
        logger.info(f"智能映射器初始化完成，股票数据库包含 {len(self.db.stock_data)} 只股票")
    
    def find_ticker(self, company_name: str) -> Optional[str]:
        """智能查找股票代码"""
        if not company_name or not company_name.strip():
            return None
        
        company_name = company_name.strip()
        
        # 1. 精确匹配（原名称）
        exact_match = self._exact_match(company_name)
        if exact_match:
            return exact_match
        
        # 2. 精确匹配（清理后名称）
        clean_match = self._clean_name_match(company_name)
        if clean_match:
            return clean_match
        
        # 3. 包含匹配
        contain_match = self._contain_match(company_name)
        if contain_match:
            return contain_match
        
        # 4. 模糊匹配
        fuzzy_match = self._fuzzy_match(company_name)
        if fuzzy_match:
            return fuzzy_match
        
        logger.warning(f"未找到匹配的股票代码: {company_name}")
        return None
    
    def _exact_match(self, company_name: str) -> Optional[str]:
        """精确匹配（原名称）"""
        for code, info in self.db.stock_data.items():
            if info['name'] == company_name:
                return code
        return None
    
    def _clean_name_match(self, company_name: str) -> Optional[str]:
        """清理名称匹配"""
        cleaned_input = self.db._clean_company_name(company_name)
        
        for code, info in self.db.stock_data.items():
            if info['clean_name'] == cleaned_input:
                return code
        return None
    
    def _contain_match(self, company_name: str) -> Optional[str]:
        """包含匹配"""
        candidates = []
        
        # 优先匹配：股票清理名称包含输入
        for code, info in self.db.stock_data.items():
            if company_name in info['clean_name'] or company_name in info['name']:
                candidates.append((code, info, 1))  # 高优先级
        
        # 次优匹配：输入包含股票清理名称  
        for code, info in self.db.stock_data.items():
            if info['clean_name'] in company_name and len(info['clean_name']) >= 2:
                candidates.append((code, info, 2))  # 低优先级
        
        if candidates:
            # 按优先级和名称长度排序
            candidates.sort(key=lambda x: (x[2], -len(x[1]['clean_name'])))
            return candidates[0][0]
        
        return None
    
    def _fuzzy_match(self, company_name: str, threshold: float = 0.6) -> Optional[str]:
        """模糊匹配，使用相似度算法"""
        best_match = None
        best_score = 0
        
        cleaned_input = self.db._clean_company_name(company_name)
        
        for code, info in self.db.stock_data.items():
            # 计算与清理名称的相似度
            score1 = SequenceMatcher(None, cleaned_input, info['clean_name']).ratio()
            score2 = SequenceMatcher(None, cleaned_input, info['name']).ratio()
            
            score = max(score1, score2)
            
            if score > best_score and score >= threshold:
                best_score = score
                best_match = code
        
        return best_match

# 全局映射器实例
_mapper_instance: Optional[SmartTickerMapper] = None

def get_ticker_mapper() -> SmartTickerMapper:
    """获取全局映射器实例（单例模式）"""
    global _mapper_instance
    if _mapper_instance is None:
        _mapper_instance = SmartTickerMapper()
    return _mapper_instance

def get_ticker_by_company_name(company_name: str) -> Optional[str]:
    """根据公司名称获取股票代码（向后兼容的接口）"""
    mapper = get_ticker_mapper()
    return mapper.find_ticker(company_name)

def map_targets_to_tickers(targets: str) -> List[Tuple[str, Optional[str]]]:
    """将多个投资标的映射为股票代码（向后兼容的接口）"""
    if not targets:
        return []
    
    mapper = get_ticker_mapper()
    results = []
    
    # 分割多个标的
    target_list = [t.strip() for t in targets.split(',') if t.strip()]
    
    for target in target_list:
        ticker = mapper.find_ticker(target)
        results.append((target, ticker))
    
    return results

if __name__ == '__main__':
    # 测试代码
    from utils import setup_logging
    setup_logging()
    
    mapper = SmartTickerMapper()
    
    # 测试用例
    test_cases = [
        "铂力特",      # 完整名称
        "宏工科技",    # 完整名称  
        "立讯精密",    # 完整名称
        "立讯",        # 部分名称
        "中国平安",    # 完整名称
        "平安",        # 部分名称
        "腾讯",        # 港股
        "阿里巴巴",    # 港股
    ]
    
    logger.info("=== 智能股票代码映射测试 ===")
    for case in test_cases:
        ticker = mapper.find_ticker(case)
        if ticker:
            info = mapper.db.stock_data[ticker]
            logger.info(f"✅ {case} -> {ticker} ({info['name']}) [{info['market']}股]")
        else:
            logger.warning(f"❌ {case} -> 未找到")
