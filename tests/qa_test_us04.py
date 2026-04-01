#!/usr/bin/env python3
"""
US_04 配置管理 - QA 验收测试脚本

项目：1688 商品爬虫开发 - 选品分析工具
任务 ID: T_US_04
执行者：少锋 (QA)
测试依据：US_04_Config.json v1.0
"""

import os
import sys
import yaml
import unittest
from pathlib import Path

# 添加 backend 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

from config_manager import ConfigManager


class TestUS04ConfigManagement(unittest.TestCase):
    """US_04 配置管理 QA 验收测试"""
    
    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        cls.project_root = Path(__file__).parent.parent
        cls.config_dir = cls.project_root / 'backend' / 'config'
        cls.config_file = cls.config_dir / 'config.yaml'
        print("\n" + "=" * 60)
        print("🧪 1688 商品爬虫 - US_04 QA 验收测试")
        print("=" * 60)
        print(f"测试人员：少锋 (QA)")
        print(f"测试时间：{Path(__file__).stat().st_mtime}")
        print(f"测试依据：US_04_Config.json v1.0")
        print("=" * 60)
    
    def test_01_config_file_exists(self):
        """测试 1: 配置文件存在性验证"""
        print("\n" + "=" * 60)
        print("测试 1: 配置文件存在性验证")
        print("=" * 60)
        
        # 验证配置文件存在
        self.assertTrue(self.config_file.exists(), f"配置文件不存在：{self.config_file}")
        print(f"✅ 配置文件存在：{self.config_file}")
        
        # 验证配置文件可读
        with open(self.config_file, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertGreater(len(content), 0, "配置文件为空")
        print(f"✅ 配置文件可读，内容长度：{len(content)} 字节")
    
    def test_02_config_schema_validation(self):
        """测试 2: 配置文件 Schema 验证"""
        print("\n" + "=" * 60)
        print("测试 2: 配置文件 Schema 验证")
        print("=" * 60)
        
        with open(self.config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 验证 crawler 配置
        self.assertIn('crawler', config, "缺少 crawler 配置")
        self.assertIn('keywords', config['crawler'], "缺少 crawler.keywords")
        self.assertIn('limit', config['crawler'], "缺少 crawler.limit")
        self.assertIn('preview_mode', config['crawler'], "缺少 crawler.preview_mode")
        print(f"✅ crawler 配置完整：keywords={config['crawler']['keywords']}, limit={config['crawler']['limit']}")
        
        # 验证 anti_scrape 配置
        self.assertIn('anti_scrape', config, "缺少 anti_scrape 配置")
        self.assertIn('use_proxy', config['anti_scrape'], "缺少 anti_scrape.use_proxy")
        self.assertIn('request_delay_min', config['anti_scrape'], "缺少 anti_scrape.request_delay_min")
        self.assertIn('request_delay_max', config['anti_scrape'], "缺少 anti_scrape.request_delay_max")
        print(f"✅ anti_scrape 配置完整：use_proxy={config['anti_scrape']['use_proxy']}, delay={config['anti_scrape']['request_delay_min']}-{config['anti_scrape']['request_delay_max']}s")
        
        # 验证 storage 配置
        self.assertIn('storage', config, "缺少 storage 配置")
        self.assertIn('sqlite_enabled', config['storage'], "缺少 storage.sqlite_enabled")
        self.assertIn('jsonl_enabled', config['storage'], "缺少 storage.jsonl_enabled")
        self.assertIn('data_dir', config['storage'], "缺少 storage.data_dir")
        print(f"✅ storage 配置完整：sqlite={config['storage']['sqlite_enabled']}, jsonl={config['storage']['jsonl_enabled']}, dir={config['storage']['data_dir']}")
        
        # 验证 logging 配置
        self.assertIn('logging', config, "缺少 logging 配置")
        self.assertIn('level', config['logging'], "缺少 logging.level")
        self.assertIn('file_enabled', config['logging'], "缺少 logging.file_enabled")
        self.assertIn('console_enabled', config['logging'], "缺少 logging.console_enabled")
        print(f"✅ logging 配置完整：level={config['logging']['level']}, file={config['logging']['file_enabled']}, console={config['logging']['console_enabled']}")
    
    def test_03_config_manager_load(self):
        """测试 3: ConfigManager 加载配置"""
        print("\n" + "=" * 60)
        print("测试 3: ConfigManager 加载配置")
        print("=" * 60)
        
        config = ConfigManager()
        
        # 验证配置加载
        keywords = config.get_crawler_keywords()
        self.assertIsInstance(keywords, list, "keywords 应该是列表")
        self.assertGreater(len(keywords), 0, "keywords 不应该为空")
        print(f"✅ 加载关键词：{keywords}")
        
        limit = config.get_crawler_limit()
        self.assertIsInstance(limit, int, "limit 应该是整数")
        self.assertGreater(limit, 0, "limit 应该大于 0")
        print(f"✅ 加载抓取数量限制：{limit}")
        
        preview_mode = config.is_preview_mode()
        self.assertIsInstance(preview_mode, bool, "preview_mode 应该是布尔值")
        print(f"✅ 加载预览模式：{preview_mode}")
        
        use_proxy = config.use_proxy()
        self.assertIsInstance(use_proxy, bool, "use_proxy 应该是布尔值")
        print(f"✅ 加载代理设置：use_proxy={use_proxy}")
        
        data_dir = config.get_data_dir()
        self.assertTrue(isinstance(data_dir, (str, Path)), "data_dir 应该是字符串或 Path")
        print(f"✅ 加载数据目录：{data_dir}")
        
        log_level = config.get_log_level()
        self.assertIsInstance(log_level, str, "log_level 应该是字符串")
        self.assertIn(log_level.upper(), ['DEBUG', 'INFO', 'WARNING', 'ERROR'], f"无效的日志级别：{log_level}")
        print(f"✅ 加载日志级别：{log_level}")
    
    def test_04_cli_override(self):
        """测试 4: 命令行参数覆盖配置"""
        print("\n" + "=" * 60)
        print("测试 4: 命令行参数覆盖配置")
        print("=" * 60)
        
        config = ConfigManager()
        original_keywords = config.get_crawler_keywords()
        original_limit = config.get_crawler_limit()
        original_preview = config.is_preview_mode()
        
        # 创建模拟命令行参数
        class MockArgs:
            keyword = '测试商品'
            limit = 10
            preview = True
            output = './test_output/'
            config = None
        
        # 应用覆盖
        config.apply_cli_override(MockArgs())
        
        # 验证覆盖结果
        new_keywords = config.get_crawler_keywords()
        self.assertEqual(new_keywords, ['测试商品'], f"关键词覆盖失败：期望 ['测试商品'], 实际 {new_keywords}")
        print(f"✅ 关键词覆盖：{original_keywords} → {new_keywords}")
        
        new_limit = config.get_crawler_limit()
        self.assertEqual(new_limit, 10, f"limit 覆盖失败：期望 10, 实际 {new_limit}")
        print(f"✅ limit 覆盖：{original_limit} → {new_limit}")
        
        new_preview = config.is_preview_mode()
        self.assertTrue(new_preview, f"preview_mode 覆盖失败：期望 True, 实际 {new_preview}")
        print(f"✅ 预览模式覆盖：{original_preview} → {new_preview}")
        
        new_output = config.get_data_dir()
        # Accept both string and Path, check that it ends with expected path
        self.assertTrue(str(new_output).endswith('test_output'), f"output 覆盖失败：期望包含 test_output, 实际 {new_output}")
        print(f"✅ 输出目录覆盖：./data/ → {new_output}")
    
    def test_05_preview_mode_config(self):
        """测试 5: 预览模式配置验证"""
        print("\n" + "=" * 60)
        print("测试 5: 预览模式配置验证")
        print("=" * 60)
        
        config = ConfigManager()
        
        # 验证 preview_limit 配置
        preview_limit = config.get_preview_limit()
        self.assertIsInstance(preview_limit, int, "preview_limit 应该是整数")
        self.assertEqual(preview_limit, 5, f"preview_limit 应该是 5, 实际 {preview_limit}")
        print(f"✅ 预览模式限制：{preview_limit} 条")
        
        # 验证预览模式开关
        preview_mode = config.is_preview_mode()
        self.assertIsInstance(preview_mode, bool, "preview_mode 应该是布尔值")
        print(f"✅ 预览模式开关：{preview_mode}")
    
    def test_06_default_values(self):
        """测试 6: 默认值验证"""
        print("\n" + "=" * 60)
        print("测试 6: 默认值验证")
        print("=" * 60)
        
        # 临时重命名配置文件以测试默认值
        backup_file = self.config_file.with_suffix('.yaml.bak')
        config_existed = self.config_file.exists()
        
        if config_existed:
            self.config_file.rename(backup_file)
        
        try:
            # 创建新的 ConfigManager（应该使用默认值）
            config = ConfigManager()
            
            # 验证默认值
            keywords = config.get_crawler_keywords()
            self.assertEqual(keywords, ['拖把'], f"默认关键词错误：期望 ['拖把'], 实际 {keywords}")
            print(f"✅ 默认关键词：{keywords}")
            
            limit = config.get_crawler_limit()
            self.assertEqual(limit, 50, f"默认 limit 错误：期望 50, 实际 {limit}")
            print(f"✅ 默认抓取数量：{limit}")
            
            preview_mode = config.is_preview_mode()
            self.assertFalse(preview_mode, f"默认预览模式错误：期望 False, 实际 {preview_mode}")
            print(f"✅ 默认预览模式：{preview_mode}")
            
            use_proxy = config.use_proxy()
            self.assertTrue(use_proxy, f"默认代理设置错误：期望 True, 实际 {use_proxy}")
            print(f"✅ 默认代理设置：use_proxy={use_proxy}")
            
            data_dir = config.get_data_dir()
            self.assertTrue(str(data_dir).endswith('data'), f"默认数据目录错误：期望包含 data, 实际 {data_dir}")
            print(f"✅ 默认数据目录：{data_dir}")
            
            log_level = config.get_log_level()
            self.assertEqual(log_level, 'INFO', f"默认日志级别错误：期望 INFO, 实际 {log_level}")
            print(f"✅ 默认日志级别：{log_level}")
            
        finally:
            # 恢复配置文件
            if config_existed:
                backup_file.rename(self.config_file)
    
    def test_07_config_validation(self):
        """测试 7: 配置有效性验证"""
        print("\n" + "=" * 60)
        print("测试 7: 配置有效性验证")
        print("=" * 60)
        
        config = ConfigManager()
        
        # 验证关键词列表非空
        keywords = config.get_crawler_keywords()
        self.assertGreater(len(keywords), 0, "关键词列表不能为空")
        print(f"✅ 关键词列表非空：{len(keywords)} 个关键词")
        
        # 验证 limit 为正数
        limit = config.get_crawler_limit()
        self.assertGreater(limit, 0, f"limit 必须大于 0, 实际 {limit}")
        print(f"✅ limit 为正数：{limit}")
        
        # 验证 request_delay_min < request_delay_max
        delay_min, delay_max = config.get_request_delay()
        self.assertLess(delay_min, delay_max, f"request_delay_min ({delay_min}) 必须小于 request_delay_max ({delay_max})")
        print(f"✅ 请求延迟配置有效：{delay_min}s - {delay_max}s")
        
        # 验证日志级别有效
        log_level = config.get_log_level()
        self.assertIn(log_level.upper(), ['DEBUG', 'INFO', 'WARNING', 'ERROR'], f"无效的日志级别：{log_level}")
        print(f"✅ 日志级别有效：{log_level}")


def run_tests():
    """运行所有测试"""
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestUS04ConfigManagement)
    
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
