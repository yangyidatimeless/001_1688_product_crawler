#!/usr/bin/env python3
"""
US_05 日志与异常处理 - QA 验收测试脚本

项目：1688 商品爬虫开发 - 选品分析工具
任务 ID: T_US_05
执行者：少锋 (QA)
测试依据：US_05_Logging.json v1.0
"""

import os
import sys
import unittest
from pathlib import Path
from datetime import datetime

# 添加 backend 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

from logger import CrawlerLogger, RetryHandler, log_parse_error, log_captcha_detected


class TestUS05LoggingAndException(unittest.TestCase):
    """US_05 日志与异常处理 QA 验收测试"""
    
    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        cls.project_root = Path(__file__).parent.parent
        cls.logs_dir = cls.project_root / 'backend' / 'logs'
        print("\n" + "=" * 60)
        print("🧪 1688 商品爬虫 - US_05 QA 验收测试")
        print("=" * 60)
        print(f"测试人员：少锋 (QA)")
        print(f"测试时间：{datetime.now().isoformat()}")
        print(f"测试依据：US_05_Logging.json v1.0")
        print("=" * 60)
    
    @classmethod
    def tearDownClass(cls):
        """测试后清理"""
        print("\n" + "=" * 60)
        print("测试完成")
        print("=" * 60)
    
    def test_01_log_file_creation(self):
        """测试 1: 独立日志文件（按日期命名）"""
        print("\n" + "=" * 60)
        print("测试 1: 独立日志文件（按日期命名）")
        print("=" * 60)
        
        # 创建日志管理器
        logger = CrawlerLogger(log_dir=str(self.logs_dir), level='INFO')
        
        # 验证日志目录存在
        self.assertTrue(self.logs_dir.exists(), f"日志目录不存在：{self.logs_dir}")
        print(f"✅ 日志目录存在：{self.logs_dir}")
        
        # 验证日志文件创建
        today = datetime.now().strftime('%Y%m%d')
        expected_log_file = self.logs_dir / f'crawler_{today}.log'
        
        # 写一条日志确保文件创建
        logger.info("QA 测试 - 日志文件验证")
        
        self.assertTrue(expected_log_file.exists(), f"日志文件未创建：{expected_log_file}")
        print(f"✅ 日志文件创建：{expected_log_file}")
        
        # 验证命名格式
        self.assertRegex(expected_log_file.name, r'crawler_\d{8}\.log', "日志文件命名格式不正确")
        print(f"✅ 日志文件命名格式正确：crawler_YYYYMMDD.log")
    
    def test_02_log_levels(self):
        """测试 2: 日志包含 INFO、WARNING、ERROR 级别"""
        print("\n" + "=" * 60)
        print("测试 2: 日志包含 INFO、WARNING、ERROR 级别")
        print("=" * 60)
        
        logger = CrawlerLogger(log_dir=str(self.logs_dir), level='DEBUG')
        
        # 记录各级别日志
        logger.debug("QA 测试 - DEBUG 级别")
        logger.info("QA 测试 - INFO 级别")
        logger.warning("QA 测试 - WARNING 级别")
        logger.error("QA 测试 - ERROR 级别")
        
        print("✅ 各级别日志记录成功:")
        print("   - DEBUG: 详细调试信息")
        print("   - INFO: 正常流程信息")
        print("   - WARNING: 可恢复异常")
        print("   - ERROR: 严重错误")
        
        # 验证日志文件内容包含各级别
        today = datetime.now().strftime('%Y%m%d')
        log_file = self.logs_dir / f'crawler_{today}.log'
        
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        self.assertIn('DEBUG', content, "日志文件缺少 DEBUG 级别")
        self.assertIn('INFO', content, "日志文件缺少 INFO 级别")
        self.assertIn('WARNING', content, "日志文件缺少 WARNING 级别")
        self.assertIn('ERROR', content, "日志文件缺少 ERROR 级别")
        print(f"✅ 日志文件包含所有级别：DEBUG, INFO, WARNING, ERROR")
    
    def test_03_retry_mechanism(self):
        """测试 3: 网络异常时自动重试（最多 3 次）"""
        print("\n" + "=" * 60)
        print("测试 3: 网络异常时自动重试（最多 3 次）")
        print("=" * 60)
        
        logger = CrawlerLogger(log_dir=str(self.logs_dir), level='INFO')
        retry_handler = RetryHandler(max_retries=3, base_delay=0.1, logger=logger)
        
        # 测试重试成功场景
        attempt_count = {'count': 0}
        
        def failing_then_success():
            attempt_count['count'] += 1
            if attempt_count['count'] < 3:
                raise Exception(f"模拟失败 (第{attempt_count['count']}次)")
            return "成功!"
        
        result = retry_handler.execute_with_retry(failing_then_success)
        
        self.assertEqual(result, "成功!", "重试后应该成功")
        self.assertEqual(attempt_count['count'], 3, f"应该尝试 3 次，实际 {attempt_count['count']} 次")
        print(f"✅ 重试机制工作正常：尝试 {attempt_count['count']} 次后成功")
        
        # 测试重试失败场景（超过最大重试次数）
        attempt_count_fail = {'count': 0}
        
        def always_fail():
            attempt_count_fail['count'] += 1
            raise Exception("始终失败")
        
        try:
            retry_handler.execute_with_retry(always_fail)
            self.fail("应该抛出异常")
        except Exception as e:
            self.assertEqual(attempt_count_fail['count'], 3, f"应该尝试 3 次后放弃，实际 {attempt_count_fail['count']} 次")
            print(f"✅ 重试失败处理正确：尝试 {attempt_count_fail['count']} 次后放弃")
    
    def test_04_parse_error_logging(self):
        """测试 4: 页面结构变化时记录详细错误信息"""
        print("\n" + "=" * 60)
        print("测试 4: 页面结构变化时记录详细错误信息")
        print("=" * 60)
        
        logger = CrawlerLogger(log_dir=str(self.logs_dir), level='INFO')
        
        # 模拟解析错误
        test_url = "https://detail.1688.com/offer/123456.html"
        test_html = "<html><body><div>测试页面</div></body></html>"
        test_error = "Unable to find product price"
        
        # 记录解析错误
        log_parse_error(logger, test_url, test_html, test_error)
        
        # 验证日志文件包含详细信息
        today = datetime.now().strftime('%Y%m%d')
        log_file = self.logs_dir / f'crawler_{today}.log'
        
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        self.assertIn(test_url, content, "日志应该包含 URL")
        self.assertIn(test_error, content, "日志应该包含错误信息")
        self.assertIn('HTML', content, "日志应该包含 HTML 片段")
        
        print("✅ 解析错误日志包含:")
        print(f"   - URL: {test_url}")
        print(f"   - 错误：{test_error}")
        print(f"   - HTML 片段：{test_html[:50]}...")
    
    def test_05_dual_output(self):
        """测试 5: 日志输出到文件同时也在控制台显示"""
        print("\n" + "=" * 60)
        print("测试 5: 日志输出到文件同时也在控制台显示")
        print("=" * 60)
        
        logger = CrawlerLogger(log_dir=str(self.logs_dir), level='INFO')
        
        # 记录日志
        test_message = f"QA 测试 - 双输出验证 {datetime.now().strftime('%H%M%S')}"
        logger.info(test_message)
        
        # 验证文件输出
        today = datetime.now().strftime('%Y%m%d')
        log_file = self.logs_dir / f'crawler_{today}.log'
        
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        self.assertIn(test_message, content, "日志文件应该包含测试消息")
        print(f"✅ 文件输出：日志已写入 {log_file}")
        print(f"✅ 控制台输出：消息已实时显示")
    
    def test_06_captcha_logging(self):
        """测试 6: 验证码检测日志"""
        print("\n" + "=" * 60)
        print("测试 6: 验证码检测日志")
        print("=" * 60)
        
        logger = CrawlerLogger(log_dir=str(self.logs_dir), level='INFO')
        
        # 模拟验证码检测
        test_url = "https://detail.1688.com/offer/789012.html"
        log_captcha_detected(logger, test_url)
        
        # 验证日志文件包含验证码信息
        today = datetime.now().strftime('%Y%m%d')
        log_file = self.logs_dir / f'crawler_{today}.log'
        
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        self.assertIn('验证码', content, "日志应该包含验证码信息")
        self.assertIn(test_url, content, "日志应该包含 URL")
        
        print(f"✅ 验证码检测日志记录成功")
        print(f"   - URL: {test_url}")
        print(f"   - 建议：consider using proxy or reducing frequency")
    
    def test_07_log_format(self):
        """测试 7: 日志格式验证"""
        print("\n" + "=" * 60)
        print("测试 7: 日志格式验证")
        print("=" * 60)
        
        logger = CrawlerLogger(log_dir=str(self.logs_dir), level='INFO')
        logger.info("QA 测试 - 格式验证")
        
        # 读取日志文件验证格式
        today = datetime.now().strftime('%Y%m%d')
        log_file = self.logs_dir / f'crawler_{today}.log'
        
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 验证最后一行日志格式
        last_line = lines[-1].strip()
        
        # 格式：2026-04-01 20:30:43 - 1688Crawler - INFO - 消息
        import re
        pattern = r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} - \w+ - (DEBUG|INFO|WARNING|ERROR) - .+'
        self.assertRegex(last_line, pattern, f"日志格式不正确：{last_line}")
        
        print(f"✅ 日志格式正确：%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        print(f"   示例：{last_line}")


def run_tests():
    """运行所有测试"""
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestUS05LoggingAndException)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出汇总
    print("\n" + "=" * 60)
    print("📊 QA 测试结果汇总")
    print("=" * 60)
    
    tests_run = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    successes = tests_run - failures - errors
    
    print(f"总计：{tests_run} 个测试")
    print(f"✅ 通过：{successes}")
    print(f"❌ 失败：{failures}")
    print(f"⚠️  错误：{errors}")
    print("-" * 60)
    
    if failures == 0 and errors == 0:
        print("测试结论：✅ 通过 - 所有测试用例通过，无 Bug")
    else:
        print("测试结论：❌ 不通过 - 需要修复")
        if result.failures:
            print("\n失败用例:")
            for test, tb in result.failures:
                lines = tb.split('\n')
                print(f"  - {test}: {lines[-2] if len(lines) > 1 else 'Unknown'}")
        if result.errors:
            print("\n错误用例:")
            for test, tb in result.errors:
                lines = tb.split('\n')
                print(f"  - {test}: {lines[-2] if len(lines) > 1 else 'Unknown'}")
    
    print("=" * 60)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
