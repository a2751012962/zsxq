"""
文本提取器模块：从zsxq话题数据中提取结构化信息
"""
import re
from typing import Dict, Any, Optional

from config import get_logger

# 设置日志器
logger = get_logger(__name__)

class TextExtractor:
    """
    从zsxq话题对象中提取结构化数据的类
    """

    def __init__(self, topic: Dict[str, Any]):
        self.topic = topic
        self.text = self._get_text()
        logger.debug(f"初始化TextExtractor，文本长度: {len(self.text)}")

    def _get_text(self) -> str:
        """安全地从话题中获取主要文本内容"""
        return self.topic.get("talk", {}).get("text", "").strip()

    def extract_title(self) -> str:
        """提取标题，优先使用talk.title，否则使用文本第一行"""
        title = self.topic.get("talk", {}).get("title")
        if title:
            return title.strip()
        return self.text.split('\n')[0].strip()

    def extract_date(self) -> str:
        """从话题中提取创建日期"""
        return self.topic.get("create_time", "")[:10]

    def extract_summary(self) -> str:
        """返回完整的清理后文本内容，用于传递给LLM处理"""
        # 清理HTML标签和特殊字符，但保留完整内容
        clean_text = re.sub(r'<[^>]+>', '', self.text)  # 移除HTML标签
        clean_text = re.sub(r'&[a-zA-Z]+;', '', clean_text)  # 移除HTML实体
        clean_text = re.sub(r'\s+', ' ', clean_text)  # 标准化空白字符
        return clean_text.strip()

    def is_content_valid(self, min_length: int = 50) -> bool:
        """检查内容是否有效（只统计中文字符长度是否足够）"""
        summary = self.extract_summary()
        # 只统计中文字符（Unicode范围：\u4e00-\u9fff）
        chinese_chars = re.findall(r'[\u4e00-\u9fff]', summary)
        chinese_char_count = len(chinese_chars)
        is_valid = chinese_char_count >= min_length
        logger.debug(f"内容有效性检查: 中文字符数={chinese_char_count}, 最小要求={min_length}, 结果={is_valid}")
        return is_valid

    def extract_all(self) -> Optional[Dict[str, Any]]:
        """运行所有提取方法并返回结构化字典，如果内容太短则返回None"""
        # 先检查内容是否有效
        if not self.is_content_valid():
            # 显示完整的话题内容，方便查看为什么被跳过
            title = self.extract_title()
            summary = self.extract_summary()
            chinese_chars = re.findall(r'[\u4e00-\u9fff]', summary)
            chinese_char_count = len(chinese_chars)
            
            logger.info(f"话题内容太短，跳过处理 (中文字符数: {chinese_char_count}/50)")
            logger.info(f"跳过话题标题: {title}")
            logger.info(f"跳过话题内容: {summary}")
            logger.info("=" * 80)
            return None
        
        title = self.extract_title()
        date = self.extract_date()
        summary = self.extract_summary()
        
        logger.debug(f"提取完成 - 标题: {title[:30]}..., 日期: {date}, 摘要长度: {len(summary)}")
        
        return {
            "title": title,
            "date": date,
            "summary": summary,
        }

if __name__ == '__main__':
    # 简单测试
    mock_topic = {
        "create_time": "2023-10-27T10:00:00.123+0800",
        "talk": {
            "text": "【新能源汽车】这是一个测试话题，包含足够的中文内容进行分析。TSLA 值得关注，市场前景良好，建议关注相关投资机会。"
        }
    }
    extractor = TextExtractor(mock_topic)
    result = extractor.extract_all()
    print("提取结果:", result)
    print("中文字符数:", len(re.findall(r'[\u4e00-\u9fff]', result['summary'])) if result else 0)
