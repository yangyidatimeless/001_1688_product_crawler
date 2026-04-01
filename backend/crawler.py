#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
1688 商品爬虫 - 基础爬取功能 (US_01)

功能：
- 输入关键词后自动抓取 1688 商品列表
- 支持命令行参数配置
- 数据保存到 SQLite 和 JSONL 格式
- 显示实时进度条

契约版本：US_01_Crawler_API.json v1.0
"""

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from tqdm import tqdm


class ProductCrawler:
    """1688 商品爬虫核心类"""
    
    def __init__(self, keyword: str, limit: int = 50, preview: bool = False, output_dir: str = "./data/"):
        """
        初始化爬虫
        
        Args:
            keyword: 搜索关键词
            limit: 抓取数量上限
            preview: 预览模式（只抓取前 5 条）
            output_dir: 输出目录路径
        """
        self.keyword = keyword
        self.limit = 5 if preview else limit
        self.preview = preview
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化 UA
        self.ua = UserAgent()
        
        # Session 配置
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
        print("-" * 50)
        
        # 构造搜索 URL（示例 URL，实际需要根据 1688 调整）
        search_url = f"https://s.1688.com/selloffer/offer_search.htm?keywords={self.keyword}"
        
        try:
            response = self.session.get(search_url, headers=self._get_headers(), timeout=30)
            response.raise_for_status()
            
            # 解析商品列表
            products = self._parse_product_list(response.text)
            
            # 限制数量
            products = products[:self.limit]
            
            print(f"✅ 成功抓取 {len(products)} 个商品")
            
            self.products = products
            return products
            
        except requests.RequestException as e:
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


def main():
    """主函数 - CLI 入口点"""
    parser = argparse.ArgumentParser(
        description='1688 商品爬虫 - 基础爬取功能',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  python crawler.py --keyword "拖把" --limit 50
  python crawler.py --keyword "收纳盒" --preview
  python crawler.py --keyword "厨房用品" --output ./my_data/
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
    
    args = parser.parse_args()
    
    # 创建爬虫实例
    crawler = ProductCrawler(
        keyword=args.keyword,
        limit=args.limit,
        preview=args.preview,
        output_dir=args.output
    )
    
    # 执行爬取
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
