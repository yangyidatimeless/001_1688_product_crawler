#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志管理模块 - US_05

功能：
- 独立日志文件（按日期命名）
- 多级别日志（DEBUG, INFO, WARNING, ERROR）
- 同时输出到文件和控制台
- 异常处理与重试机制
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
import time
import random


class CrawlerLogger:
    """爬虫日志管理器"""
    
    def __init__(self, log_dir: Optional[str] = None, level: str = 'INFO'):
        """
        初始化日志管理器
        
        Args:
            log_dir: 日志目录，默认 ./logs/
            level: 日志级别 (DEBUG, INFO, WARNING, ERROR)
        """
        self.log_dir = Path(log_dir) if log_dir else Path(__file__).parent / 'logs'
        self.log_dir.mkdir(exist_ok=True)
        
        # 按日期命名日志文件
        log_file = self.log_dir / f"crawler_{datetime.now().strftime('%Y%m%d')}.log"
        
        # 创建 logger
        self.logger = logging.getLogger('1688Crawler')
        self.logger.setLevel(getattr(logging, level.upper(), logging.INFO))
        
        # 清除现有 handlers
        self.logger.handlers.clear()
        
        # 日志格式
        log_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # 文件 Handler
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)  # 文件记录所有级别
        file_handler.setFormatter(log_format)
        self.logger.addHandler(file_handler)
        
        # 控制台 Handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
        console_handler.setFormatter(log_format)
        self.logger.addHandler(console_handler)
        
        self.log_file = log_file
        print(f"📝 日志文件：{log_file}")
    
    def debug(self, msg: str) -> None:
        """DEBUG 级别日志"""
        self.logger.debug(msg)
    
    def info(self, msg: str) -> None:
        """INFO 级别日志"""
        self.logger.info(msg)
    
    def warning(self, msg: str) -> None:
        """WARNING 级别日志"""
        self.logger.warning(msg)
    
    def error(self, msg: str, exc_info: bool = False) -> None:
        """ERROR 级别日志"""
        self.logger.error(msg, exc_info=exc_info)
    
    def get_logger(self) -> logging.Logger:
        """获取原生 logger 对象"""
        return self.logger


class RetryHandler:
    """重试处理器 - US_05 异常处理"""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 5.0, logger: Optional[CrawlerLogger] = None):
        """
        初始化重试处理器
        
        Args:
            max_retries: 最大重试次数
            base_delay: 基础延迟时间（秒）
            logger: 日志管理器
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.logger = logger
    
    def execute_with_retry(self, func, *args, **kwargs):
        """
        执行函数，失败时自动重试
        
        Args:
            func: 要执行的函数
            *args: 函数参数
            **kwargs: 函数关键字参数
            
        Returns:
            函数执行结果
            
        Raises:
            Exception: 重试失败后抛出异常
        """
        last_exception = None
        
        for attempt in range(1, self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                if self.logger:
                    self.logger.error(f"执行失败 (尝试 {attempt}/{self.max_retries}): {e}", exc_info=True)
                
                if attempt < self.max_retries:
                    # 指数退避 + 随机抖动
                    delay = self.base_delay * (2 ** (attempt - 1)) + random.uniform(0, 2)
                    if self.logger:
                        self.logger.warning(f"{delay:.1f}秒后重试...")
                    time.sleep(delay)
                else:
                    if self.logger:
                        self.logger.error(f"达到最大重试次数，放弃执行")
        
        # 所有重试都失败，抛出异常
        if last_exception:
            raise last_exception


def log_parse_error(logger: CrawlerLogger, url: str, html_snippet: str, error_message: str) -> None:
    """
    记录页面解析错误
    
    Args:
        logger: 日志管理器
        url: 出错的 URL
        html_snippet: HTML 片段
        error_message: 错误信息
    """
    logger.error(f"页面解析失败:")
    logger.error(f"  URL: {url}")
    logger.error(f"  错误：{error_message}")
    logger.error(f"  HTML 片段：{html_snippet[:200]}...")


def log_captcha_detected(logger: CrawlerLogger, url: str) -> None:
    """
    记录验证码检测
    
    Args:
        logger: 日志管理器
        url: 检测到验证码的 URL
    """
    logger.warning(f"⚠️ 检测到验证码!")
    logger.warning(f"  URL: {url}")
    logger.warning(f"  建议：使用代理或降低请求频率")


# 使用示例
if __name__ == '__main__':
    # 创建日志管理器
    logger = CrawlerLogger(level='DEBUG')
    logger.info("=== 日志系统测试开始 ===")
    
    # 测试各级别日志
    logger.debug("这是一条 DEBUG 日志")
    logger.info("这是一条 INFO 日志")
    logger.warning("这是一条 WARNING 日志")
    logger.error("这是一条 ERROR 日志")
    
    # 测试重试处理器
    print("\n=== 重试处理器测试 ===")
    retry_handler = RetryHandler(max_retries=3, base_delay=1.0, logger=logger)
    
    attempt_count = 0
    
    def failing_function():
        global attempt_count
        attempt_count += 1
        if attempt_count < 3:
            raise Exception(f"模拟失败 (第{attempt_count}次)")
        return "成功!"
    
    try:
        result = retry_handler.execute_with_retry(failing_function)
        logger.info(f"重试成功：{result}")
    except Exception as e:
        logger.error(f"重试失败：{e}")
    
    # 测试解析错误日志
    print("\n=== 解析错误日志测试 ===")
    log_parse_error(
        logger,
        "https://detail.1688.com/offer/123456.html",
        "<html>...</html>",
        "Unable to find product price"
    )
    
    # 测试验证码检测日志
    print("\n=== 验证码检测日志测试 ===")
    log_captcha_detected(logger, "https://detail.1688.com/offer/789.html")
    
    logger.info("=== 日志系统测试完成 ===")
    print(f"\n📄 日志文件位置：{logger.log_file}")
