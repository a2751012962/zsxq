import logging
import os
import time
from logging.handlers import RotatingFileHandler
from typing import Optional

from config import LOG_LEVEL, MAX_LOG_FILES

def _cleanup_logs(log_dir: str, max_files: int):
    """清理旧的日志文件，只保留最新的 max_files 个文件"""
    if not os.path.exists(log_dir):
        return
    
    try:
        files = [os.path.join(log_dir, f) for f in os.listdir(log_dir) if f.endswith('.log')]
        if len(files) <= max_files:
            return

        # 按修改时间排序，最旧的在前
        files.sort(key=lambda x: os.path.getmtime(x))

        # 删除多余的旧文件
        files_to_delete = files[:-max_files]
        for f in files_to_delete:
            os.remove(f)
            # 使用 print 因为此时 logger 可能还未完全设置好
            print(f"Removed old log file: {f}")
    except Exception as e:
        print(f"Error cleaning up log files: {e}")

def setup_logging() -> Optional[str]:
    """
    配置全局日志系统，包括文件输出和自动清理。
    
    Returns:
        Optional[str]: 日志文件的路径，如果设置失败则返回 None。
    """
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)

    # 在设置新的 handler 之前执行清理
    _cleanup_logs(log_dir, MAX_LOG_FILES)

    log_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)'
    )
    
    # 构造带时间戳的日志文件名
    log_filename = f"extraction_{time.strftime('%Y%m%d_%H%M%S')}.log"
    log_filepath = os.path.join(log_dir, log_filename)

    # 文件处理器
    file_handler = RotatingFileHandler(
        log_filepath, maxBytes=5*1024*1024, backupCount=5, encoding='utf-8'
    )
    file_handler.setFormatter(log_formatter)

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)

    # 配置根 logger
    root_logger = logging.getLogger()
    root_logger.setLevel(LOG_LEVEL)
    
    # 清除已有处理器，避免重复记录
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
        
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    logging.info(f"日志系统设置完成，日志将记录到: {log_filepath}")
    return log_filepath

def get_logger(name: str) -> logging.Logger:
    """
    获取一个指定名称的 logger 实例。
    
    Args:
        name (str): logger 的名称，通常是 __name__。
        
    Returns:
        logging.Logger: logger 实例。
    """
    return logging.getLogger(name) 