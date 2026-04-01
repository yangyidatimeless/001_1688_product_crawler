#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
1688 商品爬虫 - 基础爬取功能 (US_01) + 反爬策略 (US_02) + 数据导出 (US_06)

功能：
- 输入关键词后自动抓取 1688 商品列表
- 支持命令行参数配置
- 数据保存到 SQLite、JSONL 和 CSV 格式
- 显示实时进度条
- 反爬策略：UA 轮换、频率限制、代理池、验证码检测

契约版本：
- US_01_Crawler_API.json v1.0
- US_02_AntiScrape.json v1.0
- US_06_Export.json v1.0
"""

import argparse
import csv
import json
import logging
import os
import sqlite3
import sys
import time
from datetime import datetime
from glob import glob
from pathlib import Path
from typing import Dict, List, Optional, Any

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from tqdm import tqdm

# 导入反爬策略模块 (US_02)
from anti_scrape import AntiScrapeManager, AntiScrapeConfig

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ProductCrawler:
    """1688 商品爬虫核心类"""
    
    def __init__(self, keyword: str, limit: int = 50, preview: bool = False, output_dir: str = "./data/", 
                 enable_anti_scrape: bool = True):
        """
        初始化爬虫
        
        Args:
            keyword: 搜索关键词
            limit: 抓取数量上限
            preview: 预览模式（只抓取前 5 条）
            output_dir: 输出目录路径
            enable_anti_scrape: 是否启用反爬策略 (US_02)
        """
        self.keyword = keyword
        self.limit = 5 if preview else limit
        self.preview = preview
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化反爬策略管理器 (US_02)
        self.enable_anti_scrape = enable_anti_scrape
        if enable_anti_scrape:
            self.anti_scrape_config = AntiScrapeConfig(
                min_delay_seconds=2.0,
                max_delay_seconds=5.0,
                max_retries=3,
                proxy_enabled=False,  # 默认关闭代理，可根据需要开启
                captcha_detection=True,
            )
            self.anti_scrape_manager = AntiScrapeManager(self.anti_scrape_config)
            logger = logging.getLogger(__name__)
            logger.info("✅ US_02 反爬策略已启用")
        else:
            self.anti_scrape_manager = None
        
        # 初始化 UA（兼容模式，如果不启用反爬）
        if not enable_anti_scrape:
            self.ua = UserAgent()
        
        # Session 配置（兼容模式）
        if not enable_anti_scrape:
            self.session = requests.Session()
            self.session.headers.update({
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
            })
        
        # 数据存储
        self.products: List[Dict[str, Any]] = []
        self.db_path = self.output_dir / "products.db"
        self.jsonl_path = self.output_dir / f"products_{keyword}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
        
        # CSV 导出配置 (US_06)
        self.exports_dir = self.output_dir.parent / "exports" if self.output_dir.name == "data" else self.output_dir / "exports"
        self.exports_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化数据库
        self._init_database()
    
    def _init_database(self) -> None:
        """初始化 SQLite 数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                product_id TEXT NOT NULL,
                title TEXT NOT NULL,
                price_min REAL NOT NULL,
                price_max REAL NOT NULL,
                sales REAL NOT NULL,
                supplier_name TEXT NOT NULL,
                supplier_level TEXT NOT NULL,
                product_url TEXT NOT NULL,
                main_image_url TEXT NOT NULL,
                thumbnail_urls TEXT NOT NULL,
                collected_at TEXT NOT NULL,
                PRIMARY KEY (product_id, collected_at)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        headers = self.session.headers.copy()
        headers['User-Agent'] = self.ua.random
        return headers
    
    def _parse_product_list(self, html: str) -> List[Dict[str, Any]]:
        """
        解析商品列表页
        
        Args:
            html: 页面 HTML 内容
            
        Returns:
            商品列表
        """
        soup = BeautifulSoup(html, 'lxml')
        products = []
        
        # 查找商品列表（根据实际 1688 页面结构调整选择器）
        # 注意：这是模拟实现，实际需要根据 1688 的 DOM 结构适配
        product_items = soup.select('.offer-item, .item, li[class*="offer"]')
        
        for item in product_items:
            try:
                product = self._parse_product_item(item)
                if product:
                    products.append(product)
            except Exception as e:
                print(f"解析商品项失败：{e}", file=sys.stderr)
                continue
        
        return products
    
    def _parse_product_item(self, item) -> Optional[Dict[str, Any]]:
        """
        解析单个商品项
        
        Args:
            item: BeautifulSoup 元素
            
        Returns:
            商品数据字典
        """
        try:
            # 提取商品 ID
            product_id = item.get('data-offer-id', '') or item.get('id', '')
            if not product_id:
                return None
            
            # 提取标题
            title_elem = item.select_one('.title, .product-title, a[class*="title"]')
            title = title_elem.get_text(strip=True) if title_elem else ''
            
            # 提取价格
            price_elem = item.select_one('.price, .product-price')
            price_text = price_elem.get_text(strip=True) if price_elem else '0'
            # 解析价格范围
            prices = self._parse_price(price_text)
            
            # 提取销量
            sales_elem = item.select_one('.sales, .month-sales')
            sales = self._parse_sales(sales_elem.get_text(strip=True) if sales_elem else '0')
            
            # 提取供应商信息
            supplier_elem = item.select_one('.supplier, .company-name')
            supplier_name = supplier_elem.get_text(strip=True) if supplier_elem else ''
            
            supplier_level_elem = item.select_one('.supplier-level, .company-level')
            supplier_level = supplier_level_elem.get_text(strip=True) if supplier_level_elem else ''
            
            # 提取链接
            link_elem = item.select_one('a[href*="offer"]')
            product_url = link_elem.get('href', '') if link_elem else ''
            
            # 提取图片
            img_elem = item.select_one('img')
            main_image_url = img_elem.get('src', '') or img_elem.get('data-src', '') if img_elem else ''
            
            # 缩略图（如果有）
            thumbnail_elems = item.select('.thumbnail img')
            thumbnail_urls = [img.get('src', '') or img.get('data-src', '') for img in thumbnail_elems if img.get('src') or img.get('data-src')]
            
            # 验证必填字段
            if not all([product_id, title, product_url]):
                return None
            
            return {
                'product_id': product_id,
                'title': title,
                'price_min': prices[0],
                'price_max': prices[1],
                'sales': sales,
                'supplier_name': supplier_name,
                'supplier_level': supplier_level,
                'product_url': product_url,
                'main_image_url': main_image_url,
                'thumbnail_urls': thumbnail_urls,
                'collected_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"解析单个商品项异常：{e}", file=sys.stderr)
            return None
    
    def _parse_price(self, price_text: str) -> tuple:
        """解析价格文本为数字范围"""
        import re
        prices = re.findall(r'[\d.]+', price_text)
        if len(prices) >= 2:
            return (float(prices[0]), float(prices[1]))
        elif len(prices) == 1:
            price = float(prices[0])
            return (price, price)
        return (0.0, 0.0)
    
    def _parse_sales(self, sales_text: str) -> float:
        """解析销量文本为数字"""
        import re
        match = re.search(r'[\d.]+', sales_text)
        if match:
            value = float(match.group())
            # 处理"万"单位
            if '万' in sales_text:
                value *= 10000
            return value
        return 0.0
    
    def search(self) -> List[Dict[str, Any]]:
        """
        执行搜索并抓取商品
        
        Returns:
            商品列表
        """
        print(f"🔍 开始搜索关键词：{self.keyword}")
        print(f"📊 抓取上限：{self.limit} 条")
        print(f"💾 输出目录：{self.output_dir}")
        if self.enable_anti_scrape:
            print(f"🛡️  反爬策略：已启用 (US_02)")
        print("-" * 50)
        
        # 构造搜索 URL（示例 URL，实际需要根据 1688 调整）
        search_url = f"https://s.1688.com/selloffer/offer_search.htm?keywords={self.keyword}"
        
        try:
            # 使用反爬管理器发起请求 (US_02)
            if self.enable_anti_scrape and self.anti_scrape_manager:
                response = self.anti_scrape_manager.get(search_url, timeout=30)
            else:
                # 兼容模式：使用原有的 retry_request
                response = retry_request(search_url, headers=self._get_headers(), timeout=30, max_retries=3)
            
            # 解析商品列表
            products = self._parse_product_list(response.text)
            
            # 限制数量
            products = products[:self.limit]
            
            print(f"✅ 成功抓取 {len(products)} 个商品")
            
            self.products = products
            return products
            
        except Exception as e:
            print(f"❌ 请求失败：{e}", file=sys.stderr)
            return []
    
    def save_to_sqlite(self) -> int:
        """
        保存数据到 SQLite
        
        Returns:
            保存的记录数
        """
        if not self.products:
            return 0
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        count = 0
        for product in self.products:
            try:
                cursor.execute('''
                    INSERT OR REPLACE INTO products 
                    (product_id, title, price_min, price_max, sales, supplier_name, 
                     supplier_level, product_url, main_image_url, thumbnail_urls, collected_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    product['product_id'],
                    product['title'],
                    product['price_min'],
                    product['price_max'],
                    product['sales'],
                    product['supplier_name'],
                    product['supplier_level'],
                    product['product_url'],
                    product['main_image_url'],
                    json.dumps(product['thumbnail_urls'], ensure_ascii=False),
                    product['collected_at']
                ))
                count += 1
            except Exception as e:
                print(f"保存商品 {product['product_id']} 失败：{e}", file=sys.stderr)
        
        conn.commit()
        conn.close()
        
        print(f"💾 SQLite 保存完成：{count} 条记录 → {self.db_path}")
        return count
    
    def save_to_jsonl(self) -> int:
        """
        保存数据到 JSONL 格式
        
        Returns:
            保存的记录数
        """
        if not self.products:
            return 0
        
        count = 0
        with open(self.jsonl_path, 'w', encoding='utf-8') as f:
            for product in self.products:
                try:
                    f.write(json.dumps(product, ensure_ascii=False) + '\n')
                    count += 1
                except Exception as e:
                    print(f"保存商品 {product['product_id']} 到 JSONL 失败：{e}", file=sys.stderr)
        
        print(f"📄 JSONL 保存完成：{count} 条记录 → {self.jsonl_path}")
        return count
    
    def save(self) -> Dict[str, int]:
        """
        保存数据到所有配置的格式
        
        Returns:
            各格式保存的记录数
        """
        return {
            'sqlite': self.save_to_sqlite(),
            'jsonl': self.save_to_jsonl()
        }
    
    def export_to_csv(self, keyword: Optional[str] = None, date_range: Optional[tuple] = None) -> str:
        """
        导出数据为 CSV 格式 (US_06)
        
        Args:
            keyword: 过滤关键词（可选）
            date_range: 日期范围 (start_date, end_date)（可选）
            
        Returns:
            导出的 CSV 文件路径
        """
        if not self.products:
            # 从数据库加载最新数据
            self._load_from_database()
        
        if not self.products:
            raise ValueError("没有可导出的数据")
        
        # CSV 列顺序（根据 US_06 契约）
        columns = [
            'product_id', 'title', 'price_min', 'price_max', 'sales',
            'supplier_name', 'supplier_level', 'product_url',
            'main_image_url', 'thumbnail_urls', 'collected_at', 'is_latest'
        ]
        
        # 生成文件名：products_{keyword}_{date}.csv
        export_keyword = keyword or self.keyword or "all"
        today = datetime.now().strftime('%Y-%m-%d')
        csv_filename = f"products_{export_keyword}_{today}.csv"
        csv_path = self.exports_dir / csv_filename
        
        # 过滤数据（只导出最新数据）
        export_data = self._filter_export_data(keyword, date_range)
        
        if not export_data:
            raise ValueError("过滤后没有可导出的数据")
        
        # 写入 CSV (UTF-8-sig 编码，Excel 兼容)
        with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(
                f,
                fieldnames=columns,
                delimiter=',',
                quotechar='"',
                quoting=csv.QUOTE_MINIMAL
            )
            
            writer.writeheader()
            
            for product in export_data:
                # 准备行数据
                row = {}
                for col in columns:
                    value = product.get(col, '')
                    
                    # 特殊处理：thumbnail_urls 是列表，转为 JSON 字符串
                    if col == 'thumbnail_urls' and isinstance(value, list):
                        value = json.dumps(value, ensure_ascii=False)
                    
                    # 特殊处理：is_latest 字段
                    elif col == 'is_latest':
                        value = product.get('is_latest', True)
                    
                    row[col] = value
                
                writer.writerow(row)
        
        print(f"📥 CSV 导出完成：{len(export_data)} 条记录 → {csv_path}")
        return str(csv_path)
    
    def _load_from_database(self) -> None:
        """从 SQLite 数据库加载产品数据"""
        if not self.db_path.exists():
            return
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM products')
        rows = cursor.fetchall()
        
        self.products = []
        for row in rows:
            product = dict(row)
            # 解析 thumbnail_urls JSON 字符串
            if isinstance(product.get('thumbnail_urls'), str):
                try:
                    product['thumbnail_urls'] = json.loads(product['thumbnail_urls'])
                except json.JSONDecodeError:
                    product['thumbnail_urls'] = []
            self.products.append(product)
        
        conn.close()
        print(f"📖 从数据库加载 {len(self.products)} 条记录")
    
    def _filter_export_data(self, keyword: Optional[str] = None, 
                            date_range: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """
        过滤要导出的数据
        
        Args:
            keyword: 关键词过滤
            date_range: 日期范围 (start_date, end_date)
            
        Returns:
            过滤后的产品列表
        """
        data = self.products.copy()
        
        # 标记最新数据（每个 product_id 只保留最新的）
        latest_products = {}
        for product in data:
            pid = product['product_id']
            collected_at = product.get('collected_at', '')
            
            if pid not in latest_products or collected_at > latest_products[pid].get('collected_at', ''):
                # 旧的标记为非最新
                if pid in latest_products:
                    latest_products[pid]['is_latest'] = False
                product['is_latest'] = True
                latest_products[pid] = product
        
        # 只导出最新数据
        result = [p for p in latest_products.values() if p.get('is_latest', True)]
        
        # 关键词过滤
        if keyword:
            result = [p for p in result if keyword.lower() in p.get('title', '').lower()]
        
        # 日期范围过滤
        if date_range and len(date_range) == 2:
            start_date, end_date = date_range
            result = [
                p for p in result
                if start_date <= p.get('collected_at', '')[:10] <= end_date
            ]
        
        return result


def main():
    """主函数 - CLI 入口点"""
    parser = argparse.ArgumentParser(
        description='1688 商品爬虫 - 基础爬取功能 + 数据导出',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  # 基础爬取
  python crawler.py --keyword "拖把" --limit 50
  python crawler.py --keyword "收纳盒" --preview
  python crawler.py --keyword "厨房用品" --output ./my_data/
  
  # 数据导出 (US_06)
  python crawler.py --keyword "拖把" --export
  python crawler.py --keyword "拖把" --export --format csv
  python crawler.py --keyword "拖把" --export --output ./exports/
        '''
    )
    
    parser.add_argument(
        '--keyword',
        type=str,
        required=True,
        help='搜索关键词，如"拖把"'
    )
    
    parser.add_argument(
        '--limit',
        type=int,
        default=50,
        help='抓取数量上限 (默认：50)'
    )
    
    parser.add_argument(
        '--preview',
        action='store_true',
        help='预览模式，只抓取前 5 条 (默认：False)'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        default='./data/',
        help='输出目录路径 (默认：./data/)'
    )
    
    # US_06 数据导出参数
    parser.add_argument(
        '--export',
        action='store_true',
        help='启用导出模式，将数据库中的数据导出为 CSV (默认：False)'
    )
    
    parser.add_argument(
        '--format',
        type=str,
        default='csv',
        choices=['csv', 'xlsx', 'json'],
        help='导出格式 (默认：csv)'
    )
    
    args = parser.parse_args()
    
    # 创建爬虫实例
    crawler = ProductCrawler(
        keyword=args.keyword,
        limit=args.limit,
        preview=args.preview,
        output_dir=args.output
    )
    
    # 导出模式 (US_06)
    if args.export:
        print("🚀 进入导出模式 (US_06)")
        print("=" * 50)
        
        try:
            # 从数据库加载数据并导出
            csv_path = crawler.export_to_csv(keyword=args.keyword)
            
            print("\n" + "=" * 50)
            print("📥 导出完成摘要")
            print("=" * 50)
            print(f"关键词：{args.keyword}")
            print(f"导出格式：{args.format}")
            print(f"导出路径：{csv_path}")
            print("=" * 50)
            
            return 0
            
        except ValueError as e:
            print(f"\n❌ 导出失败：{e}")
            return 1
        except Exception as e:
            print(f"\n❌ 导出异常：{e}")
            return 1
    
    # 爬取模式
    products = crawler.search()
    
    if products:
        # 保存数据
        results = crawler.save()
        
        # 输出摘要
        print("\n" + "=" * 50)
        print("📊 爬取完成摘要")
        print("=" * 50)
        print(f"关键词：{args.keyword}")
        print(f"抓取数量：{len(products)} 条")
        print(f"SQLite 保存：{results['sqlite']} 条")
        print(f"JSONL 保存：{results['jsonl']} 条")
        print(f"输出目录：{crawler.output_dir}")
        print("=" * 50)
        
        # 显示前 3 条预览
        print("\n📋 数据预览（前 3 条）:")
        for i, p in enumerate(products[:3], 1):
            print(f"\n{i}. {p['title']}")
            print(f"   价格：¥{p['price_min']:.2f} - ¥{p['price_max']:.2f}")
            print(f"   销量：{p['sales']}")
            print(f"   供应商：{p['supplier_name']}")
            print(f"   链接：{p['product_url'][:60]}...")
        
        return 0
    else:
        print("\n❌ 未抓取到任何商品数据")
        return 1


if __name__ == '__main__':
    sys.exit(main())
