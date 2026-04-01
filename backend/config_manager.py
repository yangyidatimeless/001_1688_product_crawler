#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理模块 - US_04

功能：
- 加载 config.yaml 配置文件
- 支持命令行参数覆盖配置
- 提供默认值
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional


class ConfigManager:
    """配置管理器"""
    
    # 默认配置值
    DEFAULT_CONFIG = {
        'crawler': {
            'keywords': ['拖把'],
            'limit': 50,
            'preview_mode': False,
            'preview_limit': 5
        },
        'anti_scrape': {
            'use_proxy': True,
            'proxy_source': 'free',
            'request_delay_min': 2,
            'request_delay_max': 5,
            'user_agent_count': 5
        },
        'storage': {
            'sqlite_enabled': True,
            'jsonl_enabled': True,
            'data_dir': './data/'
        },
        'logging': {
            'level': 'INFO',
            'file_enabled': True,
            'console_enabled': True
        }
    }
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            config_path: 配置文件路径，默认使用 ./config/config.yaml
        """
        if config_path:
            self.config_path = Path(config_path)
        else:
            # 默认配置文件路径
            self.config_path = Path(__file__).parent / 'config' / 'config.yaml'
        
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """
        加载配置文件
        
        Returns:
            配置字典（已合并默认值）
        """
        # 从默认配置开始
        config = self._deep_copy(self.DEFAULT_CONFIG)
        
        # 如果配置文件存在，加载并合并
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    file_config = yaml.safe_load(f)
                    if file_config:
                        config = self._merge_config(config, file_config)
                print(f"✅ 配置文件已加载：{self.config_path}")
            except Exception as e:
                print(f"⚠️ 配置文件加载失败：{e}，使用默认配置")
        else:
            print(f"ℹ️ 配置文件不存在：{self.config_path}，使用默认配置")
        
        return config
    
    def _deep_copy(self, obj: Any) -> Any:
        """深度复制字典"""
        if isinstance(obj, dict):
            return {k: self._deep_copy(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._deep_copy(item) for item in obj]
        else:
            return obj
    
    def _merge_config(self, base: Dict, override: Dict) -> Dict:
        """
        深度合并配置字典
        
        Args:
            base: 基础配置
            override: 覆盖配置
            
        Returns:
            合并后的配置
        """
        result = self._deep_copy(base)
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key_path: 配置键路径，如 'crawler.limit' 或 'anti_scrape.request_delay_min'
            default: 默认值
            
        Returns:
            配置值
        """
        keys = key_path.split('.')
        value = self.config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def get_crawler_keywords(self) -> list:
        """获取爬虫关键词列表"""
        return self.get('crawler.keywords', ['拖把'])
    
    def get_crawler_limit(self) -> int:
        """获取爬虫数量限制"""
        return self.get('crawler.limit', 50)
    
    def is_preview_mode(self) -> bool:
        """是否为预览模式"""
        return self.get('crawler.preview_mode', False)
    
    def get_preview_limit(self) -> int:
        """获取预览模式数量限制"""
        return self.get('crawler.preview_limit', 5)
    
    def use_proxy(self) -> bool:
        """是否使用代理"""
        return self.get('anti_scrape.use_proxy', True)
    
    def get_request_delay(self) -> tuple:
        """获取请求延迟范围 (min, max)"""
        return (
            self.get('anti_scrape.request_delay_min', 2),
            self.get('anti_scrape.request_delay_max', 5)
        )
    
    def get_data_dir(self) -> Path:
        """获取数据目录"""
        data_dir = self.get('storage.data_dir', './data/')
        # 如果是相对路径，相对于项目根目录
        if not os.path.isabs(data_dir):
            data_dir = Path(__file__).parent / data_dir
        return Path(data_dir)
    
    def is_sqlite_enabled(self) -> bool:
        """是否启用 SQLite 存储"""
        return self.get('storage.sqlite_enabled', True)
    
    def is_jsonl_enabled(self) -> bool:
        """是否启用 JSONL 存储"""
        return self.get('storage.jsonl_enabled', True)
    
    def get_log_level(self) -> str:
        """获取日志级别"""
        return self.get('logging.level', 'INFO')
    
    def is_log_file_enabled(self) -> bool:
        """是否启用日志文件"""
        return self.get('logging.file_enabled', True)
    
    def is_log_console_enabled(self) -> bool:
        """是否启用控制台日志"""
        return self.get('logging.console_enabled', True)
    
    def apply_cli_override(self, args: Any) -> None:
        """
        应用命令行参数覆盖配置
        
        Args:
            args: argparse 解析后的参数对象
        """
        if hasattr(args, 'keyword') and args.keyword:
            self.config['crawler']['keywords'] = [args.keyword]
            print(f"📝 命令行覆盖：keywords = [{args.keyword}]")
        
        if hasattr(args, 'limit') and args.limit != 50:
            self.config['crawler']['limit'] = args.limit
            print(f"📝 命令行覆盖：limit = {args.limit}")
        
        if hasattr(args, 'preview') and args.preview:
            self.config['crawler']['preview_mode'] = True
            print(f"📝 命令行覆盖：preview_mode = True")
        
        if hasattr(args, 'output') and args.output:
            self.config['storage']['data_dir'] = args.output
            print(f"📝 命令行覆盖：data_dir = {args.output}")
    
    def print_config(self) -> None:
        """打印当前配置（用于调试）"""
        print("\n" + "=" * 50)
        print("📋 当前配置")
        print("=" * 50)
        print(f"关键词：{self.get_crawler_keywords()}")
        print(f"抓取上限：{self.get_crawler_limit()}")
        print(f"预览模式：{self.is_preview_mode()}")
        print(f"使用代理：{self.use_proxy()}")
        print(f"请求延迟：{self.get_request_delay()}")
        print(f"数据目录：{self.get_data_dir()}")
        print(f"SQLite 启用：{self.is_sqlite_enabled()}")
        print(f"JSONL 启用：{self.is_jsonl_enabled()}")
        print(f"日志级别：{self.get_log_level()}")
        print("=" * 50 + "\n")


def main():
    """测试配置管理器"""
    config = ConfigManager()
    config.print_config()
    
    print("\n配置值测试:")
    print(f"crawler.keywords: {config.get('crawler.keywords')}")
    print(f"crawler.limit: {config.get('crawler.limit')}")
    print(f"anti_scrape.use_proxy: {config.get('anti_scrape.use_proxy')}")
    print(f"storage.data_dir: {config.get('storage.data_dir')}")


if __name__ == '__main__':
    main()
