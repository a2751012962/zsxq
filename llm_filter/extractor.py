"""
LLM智能信息提取器模块：使用OpenAI API从文本中提取投资相关信息
"""
import json
from typing import Dict, Optional, List, Tuple, Union, Any

from openai import OpenAI
from config import OPENAI_API_KEY, OPENAI_API_BASE, OPENAI_MODEL, TEMPERATURE, FINANCE
from utils import get_logger

# 设置日志器
logger = get_logger(__name__)

# 初始化OpenAI客户端（支持DeepSeek API）
客户端 = None
if OPENAI_API_KEY:
    try:
        客户端 = OpenAI(
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_API_BASE
        )
        logger.info(f"API客户端初始化成功 - Base URL: {OPENAI_API_BASE}, Model: {OPENAI_MODEL}")
    except Exception as e:
        logger.error(f"API客户端初始化失败: {e}")
        客户端 = None
else:
    logger.warning("未找到OPENAI_API_KEY，LLM提取功能将被禁用")

# 兼容：旧版本系统提示词（FINANCE=True时使用）
旧版系统提示词_TEMPLATE = """
你是一位专业的金融分析师AI助手。请从以下文本中提取投资相关信息。

**重要：如果文本中明确提及任何公司或股票名称作为投资机会（即使是"建议关注"、"相关标的"等），就必须提取。只有在完全没有提及任何公司或股票时，才返回null。**

**多标的处理：如果文章推荐多个标的，请按推荐强弱排序（最强推荐在前），用逗号分隔。**

提取要求：
1. 标的（target）：
   - 提取文章明确推荐或提及的、可供投资的具体公司或股票名称（如：特斯拉、爱美客、海尔智家、德业股份、固德威等）。
   - **即使是"建议关注"、"相关标的包括"等措辞，也应视为有效推荐并提取。**
   - 使用公司的常用简称，不要包含"股份"、"有限公司"等后缀。
   - 如果有多个标的，按推荐强弱排序，用逗号分隔（最多3个）。
   - 如果文本中完全没有提及任何公司或股票，返回null。

2. 行业板块（sector）：
   - 使用简洁的中文描述受益板块（如：新能源汽车、半导体、消费电子、医美、军工、房地产、固态电池等）
   - 基于最主要推荐标的的行业领域判断
   - 避免过于宽泛的描述，尽量具体

3. 简洁摘要（brief）：
   - 🎯 关键要求：用50-100字高度概括核心投资要点
   - 包含：标的+核心事件/技术/业绩
   - 格式示例："铂力特3D打印技术助力火箭发动机，成本降低75%"
   - 📝 字数严格控制在100字以内，突出核心价值

4. 推荐理由（reason）：
   - 提取文章中支撑投资建议的核心逻辑和理由
   - 包括基本面分析、技术面分析、政策利好、业绩预期等
   - 用简洁的中文总结，60-100字

5. 文章预期（expectation）：
   - 提取对股价、业绩、行业发展的具体预期和目标
   - 包括价格目标、业绩预测、时间节点等具体详细量化信息
   - 用简洁的中文描述，不超过100字

6. 如果文本内容是纯信息性质（如新闻资讯、政策解读）而非投资建议，所有字段返回null

请严格按照JSON格式返回，包含"target"、"sector"、"brief"、"reason"、"expectation"五个字段，不要包含任何其他文字说明。
"""

新版系统提示词_TEMPLATE = f"""你是一位专业的金融分析师AI助手。请从以下文本中提取**所有投资标的，并按行业板块归类**，每个板块下可有多个标的，无数量上限。

【提取规则】
1. 只要出现公司、股票、ETF、基金名，都算标的。必须全提取。
2. 对每个标的，判断其主要所属行业板块。板块用简洁中文命名，如 新能源、半导体、AI、医药、军工……
3. 输出JSON（必须严格结构化）：
   - sector_targets: 数组。每元素形如 {{"sector":"新能源", "targets":"宁德时代,阳光电源"}}
   - brief: 50-100字高度浓缩摘要（含板块、核心事件、主要标的）
   - reason: 60-100字提炼推荐理由
   - expectation: ≤100字，列出股价/业绩/趋势等具体可量化预期
4. 若全文无任何标的，sector_targets返回[]，其他字段留空即可。

【输出示例】
{{
  "sector_targets":[
    {{"sector":"新能源", "targets":"宁德时代,阳光电源"}},
    {{"sector":"半导体", "targets":"中芯国际"}}
  ],
  "brief":"宁德时代固态电池突破，带动新能源产业链整体受益。",
  "reason":"固态电池进展快，技术落地驱动多公司增长。",
  "expectation":"年内新能源板块整体有望上涨10%以上。"
}}

【待分析文本】：
"""

def get_system_prompt() -> str:
    """
    根据FINANCE配置获取对应的静态系统提示词
    """
    if FINANCE:
        return 旧版系统提示词_TEMPLATE
    else:
        return 新版系统提示词_TEMPLATE

def parse_llm_result(content: str) -> dict:
    """
    根据FINANCE配置解析LLM返回结果
    
    Args:
        content (str): LLM返回的JSON字符串
        
    Returns:
        dict: 解析后的结果字典
    """
    try:
        结果 = json.loads(content)
        
        if FINANCE:
            # 兼容：旧版逻辑，返回target等字段
            return {
                "target": 结果.get("target"),
                "sector": 结果.get("sector"),
                "brief": 结果.get("brief"),
                "reason": 结果.get("reason"), 
                "expectation": 结果.get("expectation")
            }
        else:
            # 新版本：解析sector_targets并返回sector_pairs
            sector_targets = 结果.get("sector_targets", [])
            sector_pairs = [(item["sector"], item["targets"]) for item in sector_targets if isinstance(item, dict) and "sector" in item and "targets" in item]
                    
            return {
                "sector_pairs": sector_pairs,
                "brief": 结果.get("brief", ""),
                "reason": 结果.get("reason", ""),
                "expectation": 结果.get("expectation", "")
            }
            
    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"解析LLM结果时出错: {e}")
        if FINANCE:
            return {"target": None, "sector": None, "brief": None, "reason": None, "expectation": None}
        else:
            return {"sector_pairs": [], "brief": "", "reason": "", "expectation": ""}

def 提取股票信息(文本: str) -> Union[Dict[str, Optional[str]], Dict[str, Union[str, List[Tuple[str, str]]]]]:
    """
    使用OpenAI的LLM从文本中提取标的、行业板块、简洁摘要、推荐理由和预期信息
    
    参数:
        文本 (str): 需要分析的输入文本
        
    返回:
        Dict: 根据FINANCE配置返回不同格式的字典
    """
    if not 客户端:
        logger.error("OpenAI客户端未初始化，跳过LLM提取")
        if FINANCE:
            return {"target": None, "sector": None, "brief": None, "reason": None, "expectation": None}
        else:
            return {"sector_pairs": [], "brief": "", "reason": "", "expectation": ""}

    try:
        # 1. 获取静态系统提示词
        系统提示词 = get_system_prompt()
        
        # 2. 构建优化的消息结构
        # 将静态提示词和动态文本分开
        响应 = 客户端.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": 系统提示词},
                {"role": "user", "content": 文本} # 只把动态文本放在这里
            ],
            temperature=TEMPERATURE,
            response_format={"type": "json_object"},
            max_tokens=600
        )
        
        # 3. 记录缓存命中情况
        if 响应.usage:
            hit_tokens = getattr(响应.usage, 'prompt_cache_hit_tokens', 0) or 0
            total_prompt = getattr(响应.usage, 'prompt_tokens', 0) or 0
            if total_prompt > 0:
                hit_rate = (hit_tokens / total_prompt) * 100
                logger.info(f"🧠 DeepSeek缓存命中: {hit_tokens}/{total_prompt} tokens ({hit_rate:.1f}%)")
            else:
                 logger.info("🧠 DeepSeek缓存: prompt_tokens为0，无法计算命中率")
        
        # 4. 解析结果
        结果字符串 = 响应.choices[0].message.content
        if not 结果字符串:
            if FINANCE:
                return {"target": None, "sector": None, "brief": None, "reason": None, "expectation": None}
            else:
                return {"sector_pairs": [], "brief": "", "reason": "", "expectation": ""}
            
        return parse_llm_result(结果字符串)

    except Exception as e:
        logger.error(f"使用LLM提取信息时出错: {e}")
        if FINANCE:
            return {"target": None, "sector": None, "brief": None, "reason": None, "expectation": None}
        else:
            return {"sector_pairs": [], "brief": "", "reason": "", "expectation": ""}

# 保持向后兼容的函数名
def extract_stock_info(文本: str) -> Union[Dict[str, Optional[str]], Dict[str, Union[str, List[Tuple[str, str]]]]]:
    """
    向后兼容函数，调用新的提取股票信息函数
    """
    return 提取股票信息(文本)

def extract_sector_and_ticker(文本: str) -> Dict[str, Optional[str]]:
    """
    向后兼容函数，现在只返回sector，ticker将由程序通过公司名称查询
    """
    结果 = 提取股票信息(文本)
    if FINANCE:
        # FINANCE=True时，结果包含sector字段
        return {"ticker": None, "sector": 结果.get("sector")}  # type: ignore
    else:
        # 新模式下不返回单独的sector，而是返回sector_pairs
        return {"ticker": None, "sector": None}

if __name__ == '__main__':
    from utils import setup_logging
    setup_logging()
    
    # 测试用例1: 有明确推荐标的
    测试文本1 = "【3D打印】铂力特为巧龙一号火箭发动机打印20余项核心零部件，涡轮泵成本从20万元降至5万元，制造周期从3个月缩短至45天。技术突破明显，航天需求增长。"
    信息1 = 提取股票信息(测试文本1)
    logger.info(f"有推荐标的测试: {信息1}")
    
    # 测试用例2: 纯信息性质，无推荐标的
    测试文本2 = "彭博社：欧盟寻求私人融资以推动量子技术发展。据报道，欧盟正在制定新的政策框架。"
    信息2 = 提取股票信息(测试文本2)
    logger.info(f"无推荐标的测试: {信息2}")
    
    # 测试用例3: 空内容
    测试文本3 = "今天天气不错"
    信息3 = 提取股票信息(测试文本3)
    logger.info(f"空内容测试: {信息3}") 