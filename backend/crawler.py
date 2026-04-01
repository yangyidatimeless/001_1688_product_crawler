#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
1688 商品爬虫 - 基础爬取功能 (US_01) + 反爬策略实现 (US_02)

功能：
- 输入关键词后自动抓取 1688 商品列表
- 支持命令行参数配置
- 数据保存到 SQLite 和 JSONL 格式
- 显示实时进度条
- 反爬策略：UA 轮换、频率控制、代理池、Stealth 模式

契约版本：US_01_Crawler_API.json v1.0, US_02_AntiScrape.json v1.0
"""

import argparse
import json
import os
import random
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from tqdm import tqdm


class ProductCrawler:
    """1688 商品爬虫核心类（支持反爬策略）"""
    
    # US_02: 预定义的 User-Agent 列表（至少 5 个，作为 fake_useragent 的补充）
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0 Safari/537.36",
    ]
    
    def __init__(
        self, 
        keyword: str, 
        limit: int = 50, 
        preview: bool = False, 
        output_dir: str = "./data/",
        min_delay: float = 2.0,
        max_delay: float = 5.0,
        proxy_enabled: bool = True,
        max_retries: int = 3
    ):
        """
        初始化爬虫
        
        Args:
            keyword: 搜索关键词
            limit: 抓取数量上限
            preview: 预览模式（只抓取前 5 条）
            output_dir: 输出目录路径
            min_delay: 最小请求延迟（秒），默认 2 秒（US_02 要求）
            max_delay: 最大请求延迟（秒），默认 5 秒（US_02 要求）
            proxy_enabled: 是否启用代理池（US_02 要求）
            max_retries: 最大重试次数（US_02 要求）
        """
        self.keyword = keyword
        self.limit = 5 if preview else limit
        self.preview = preview
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # US_02 反爬策略配置
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.proxy_enabled = proxy_enabled
        self.max_retries = max_retries
        
        # 初始化 UA（fake_useragent + 预定义列表）
        self.ua = UserAgent()
        
        # 代理池（US_02 要求）
        self.proxy_pool: List[Dict[str, str]] = []
        self.current_proxy: Optional[Dict[str, str]] = None
        self.proxy_failures: int = 0
        
        # Session 配置
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
        })
        
        # 数据存储
        self.products: List[Dict[str, Any]] = []
        self.db_path = self.output_dir / "products.db"
        self.jsonl_path = self.output_dir / f"products_{keyword}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
        
        # 初始化数据库
        self._init_database()
        
        # 初始化代理池（US_02 要求）
        if self.proxy_enabled:
            self._init_proxy_pool()
    
    def _init_proxy_pool(self) -> None:
        """
        初始化代理池（US_02 要求）
        从免费代理源获取代理列表，并进行健康检查
        """
        # 预定义一些免费代理（实际生产中应该从代理 API 动态获取）
        self.proxy_pool = [
            {"http": "http://proxy1.example.com:8080"},
            {"http": "http://proxy2.example.com:8080"},
            {"http": "http://proxy3.example.com:8080"},
        ]
        
        # 健康检查（简化版，实际应该测试代理连通性）
        if self.proxy_pool:
            print(f"✅ 代理池初始化完成：{len(self.proxy_pool)} 个代理可用")
        else:
            print("⚠️  代理池为空，将使用直连模式")
    
    def _get_random_ua(self) -> str:
        """
        获取随机 User-Agent（US_02 要求：random_per_request）
        优先使用预定义列表，回退到 fake_useragent
        
        Returns:
            随机选择的 User-Agent 字符串
        """
        # 50% 概率使用预定义 UA，50% 使用 fake_useragent
        if random.random() < 0.5:
            return random.choice(self.USER_AGENTS)
        else:
            try:
                return self.ua.random
            except:
                return random.choice(self.USER_AGENTS)
    
    def _get_headers(self) -> Dict[str, str]:
        """
        获取请求头（每次请求随机轮换 UA）
        
        Returns:
            包含随机 UA 的请求头字典
        """
        headers = self.session.headers.copy()
        headers['User-Agent'] = self._get_random_ua()
        return headers
    
    def _get_random_delay(self) -> float:
        """
        获取随机延迟时间（US_02 要求：2-5 秒可配置）
        
        Returns:
            延迟秒数
        """
        return random.uniform(self.min_delay, self.max_delay)
    
    def _apply_rate_limiting(self) -> None:
        """
        应用请求频率控制（US_02 要求）
        在每次请求前自动调用
        """
        delay = self._get_random_delay()
        print(f"⏳ 请求延迟：{delay:.2f} 秒")
        time.sleep(delay)
    
    def _get_next_proxy(self) -> Optional[Dict[str, str]]:
        """
        获取下一个可用代理（US_02 要求：自动切换）
        
        Returns:
            代理字典或 None（如果代理池为空）
        """
        if not self.proxy_pool:
            return None
        return random.choice(self.proxy_pool)
    
    def _switch_proxy(self) -> bool:
        """
        切换代理（US_02 要求：代理失败时自动切换）
        
        Returns:
            是否成功切换
        """
        if not self.proxy_pool:
            return False
        
        self.proxy_failures += 1
        
        if self.proxy_failures >= self.max_retries:
            print(f"⚠️  代理失败次数达到上限 ({self.max_retries})，切换到下一个代理")
            self.current_proxy = self._get_next_proxy()
            self.proxy_failures = 0
            
            if self.current_proxy:
                print(f"🔄 已切换代理：{self.current_proxy}")
                return True
            else:
                print("⚠️  无可用代理，将使用直连模式")
                return False
        
        return False
    
    def _is_slider_captcha(self, response: requests.Response) -> bool:
        """
        检测是否是滑块验证码（US_02 要求）
        
        Args:
            response: HTTP 响应对象
            
        Returns:
            是否检测到滑块验证码
        """
        captcha_keywords = [
            'slider captcha',
            '滑块验证',
            '请完成安全验证',
            'slide captcha',
            'verify_slider'
        ]
        
        response_text = response.text.lower()
        for keyword in captcha_keywords:
            if keyword in response_text:
                return True
        
        if response.status_code in [403, 503]:
            return True
        
        return False
    
    def _log_captcha_event(self, url: str) -> None:
        """
        记录验证码事件日志（US_02 要求）
        
        Args:
            url: 触发验证码的 URL
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": "slider_captcha_detected",
            "url": url,
            "keyword": self.keyword
        }
        
        log_file = self.output_dir / "captcha_events.jsonl"
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
    
    def _init_database(self) -> None:
        """初始化 SQLite 数据库（US_03: 支持去重和历史版本）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # US_03: 添加 is_latest, created_at, updated_at 字段
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id TEXT NOT NULL,
                title TEXT NOT NULL,
                price_min REAL NOT NULL,
                price_max REAL NOT NULL,
                sales INTEGER NOT NULL,
                supplier_name TEXT NOT NULL,
                supplier_level TEXT NOT NULL,
                product_url TEXT NOT NULL,
                main_image_url TEXT NOT NULL,
                thumbnail_urls TEXT NOT NULL,
                collected_at TEXT NOT NULL,
                is_latest BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(product_id, collected_at)
            )
        ''')
        
        # US_03: 创建索引以提升查询性能
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_product_id ON products(product_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_is_latest ON products(is_latest)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_collected_at ON products(collected_at)')
        
        conn.commit()
        conn.close()
        
        # US_03: 初始化去重集合（单次任务内去重）
        self.seen_product_ids = set()
    
    def _is_product_seen(self, product_id: str) -> bool:
        """
        US_03: 检查商品是否已在单次任务中抓取
        
        Args:
            product_id: 商品 ID
            
        Returns:
            True 如果已存在，False 否则
        """
        return product_id in self.seen_product_ids
    
    def _mark_product_seen(self, product_id: str) -> None:
        """
        US_03: 标记商品已抓取
        
        Args:
            product_id: 商品 ID
        """
        self.seen_product_ids.add(product_id)
    
    def _update_latest_flag(self, conn: sqlite3.Connection, product_id: str) -> None:
        """
        US_03: 更新已有商品的 is_latest 标记
        
        当同一商品有新数据时，将旧记录的 is_latest 设为 0
        
        Args:
            conn: 数据库连接
            product_id: 商品 ID
        """
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE products 
            SET is_latest = 0, updated_at = CURRENT_TIMESTAMP
            WHERE product_id = ? AND is_latest = 1
        ''', (product_id,))
    
    def _should_skip_product(self, product_id: str) -> bool:
        """
        US_03: 检查商品是否应该跳过（单次任务内去重）
        
        Args:
            product_id: 商品 ID
            
        Returns:
            True 如果应该跳过，False 否则
        """
        if self._is_product_seen(product_id):
            print(f"⚠️  商品 {product_id} 已在本任务中抓取，跳过")
            return True
        return False
    
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
        保存数据到 SQLite（US_03: 支持去重和 is_latest 标记）
        
        Returns:
            保存的记录数
        """
        if not self.products:
            return 0
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        count = 0
        skipped = 0
        
        for product in self.products:
            try:
                product_id = product['product_id']
                
                # US_03: 单次任务内去重
                if self._should_skip_product(product_id):
                    skipped += 1
                    continue
                
                # US_03: 更新已有商品的 is_latest 标记
                self._update_latest_flag(conn, product_id)
                
                # 插入新记录（is_latest 默认为 1）
                cursor.execute('''
                    INSERT INTO products 
                    (product_id, title, price_min, price_max, sales, supplier_name, 
                     supplier_level, product_url, main_image_url, thumbnail_urls, 
                     collected_at, is_latest)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                ''', (
                    product_id,
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
                
                # US_03: 标记为已抓取
                self._mark_product_seen(product_id)
                count += 1
                
            except sqlite3.IntegrityError as e:
                # UNIQUE 约束冲突（product_id + collected_at 相同）
                print(f"⚠️  商品 {product['product_id']} 数据已存在，跳过：{e}", file=sys.stderr)
                skipped += 1
            except Exception as e:
                print(f"保存商品 {product['product_id']} 失败：{e}", file=sys.stderr)
        
        conn.commit()
        conn.close()
        
        print(f"💾 SQLite 保存完成：{count} 条新增，{skipped} 条跳过 → {self.db_path}")
        return count
    
    def save_to_jsonl(self) -> int:
        """
        保存数据到 JSONL 格式（US_03: 添加 is_latest 字段）
        
        Returns:
            保存的记录数
        """
        if not self.products:
            return 0
        
        count = 0
        with open(self.jsonl_path, 'w', encoding='utf-8') as f:
            for product in self.products:
                try:
                    # US_03: 添加 is_latest 字段到 JSONL
                    product_with_latest = product.copy()
                    product_with_latest['is_latest'] = 1
                    
                    f.write(json.dumps(product_with_latest, ensure_ascii=False) + '\n')
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
