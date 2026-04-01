#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
US_03 数据存储与去重 - 单元测试

测试场景：
1. 单次任务内去重（同一商品 ID 不重复保存）
2. 跨任务保留历史（新数据保留，旧数据 is_latest=0）
3. is_latest 标记正确性
4. JSONL 备份包含 is_latest 字段
"""

import json
import os
import sqlite3
import sys
import tempfile
from pathlib import Path
from datetime import datetime

# 添加父目录到路径以便导入 crawler
sys.path.insert(0, str(Path(__file__).parent))

from crawler import ProductCrawler


def test_deduplication_within_task():
    """测试 1: 单次任务内去重"""
    print("\n" + "="*60)
    print("测试 1: 单次任务内去重")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        crawler = ProductCrawler(keyword="test", limit=10, output_dir=tmpdir)
        
        # 模拟商品数据（包含重复的 product_id）
        crawler.products = [
            {
                'product_id': 'PROD_001',
                'title': '测试商品 1',
                'price_min': 10.0,
                'price_max': 20.0,
                'sales': 100,
                'supplier_name': '供应商 A',
                'supplier_level': '金牌',
                'product_url': 'https://example.com/1',
                'main_image_url': 'https://example.com/img1.jpg',
                'thumbnail_urls': ['https://example.com/thumb1.jpg'],
                'collected_at': datetime.now().isoformat()
            },
            {
                'product_id': 'PROD_001',  # 重复的 product_id
                'title': '测试商品 1（重复）',
                'price_min': 15.0,
                'price_max': 25.0,
                'sales': 150,
                'supplier_name': '供应商 A',
                'supplier_level': '金牌',
                'product_url': 'https://example.com/1',
                'main_image_url': 'https://example.com/img1.jpg',
                'thumbnail_urls': ['https://example.com/thumb1.jpg'],
                'collected_at': datetime.now().isoformat()
            },
            {
                'product_id': 'PROD_002',
                'title': '测试商品 2',
                'price_min': 30.0,
                'price_max': 40.0,
                'sales': 200,
                'supplier_name': '供应商 B',
                'supplier_level': '银牌',
                'product_url': 'https://example.com/2',
                'main_image_url': 'https://example.com/img2.jpg',
                'thumbnail_urls': ['https://example.com/thumb2.jpg'],
                'collected_at': datetime.now().isoformat()
            }
        ]
        
        # 保存到 SQLite
        count = crawler.save_to_sqlite()
        
        # 验证：应该只保存 2 条（PROD_001 和 PROD_002 各一条）
        assert count == 2, f"期望保存 2 条，实际保存 {count} 条"
        
        # 验证数据库内容
        conn = sqlite3.connect(crawler.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM products")
        db_count = cursor.fetchone()[0]
        conn.close()
        
        assert db_count == 2, f"数据库期望 2 条记录，实际 {db_count} 条"
        
        print("✅ 测试 1 通过：单次任务内去重功能正常")
        return True


def test_is_latest_flag():
    """测试 2: is_latest 标记正确性"""
    print("\n" + "="*60)
    print("测试 2: is_latest 标记正确性")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # 第一次爬取
        crawler1 = ProductCrawler(keyword="test", limit=10, output_dir=tmpdir)
        crawler1.products = [
            {
                'product_id': 'PROD_001',
                'title': '测试商品 v1',
                'price_min': 10.0,
                'price_max': 20.0,
                'sales': 100,
                'supplier_name': '供应商 A',
                'supplier_level': '金牌',
                'product_url': 'https://example.com/1',
                'main_image_url': 'https://example.com/img1.jpg',
                'thumbnail_urls': [],
                'collected_at': datetime.now().isoformat()
            }
        ]
        crawler1.save_to_sqlite()
        
        # 第二次爬取（同一商品，数据更新）
        crawler2 = ProductCrawler(keyword="test", limit=10, output_dir=tmpdir)
        crawler2.products = [
            {
                'product_id': 'PROD_001',
                'title': '测试商品 v2（更新）',
                'price_min': 12.0,
                'price_max': 22.0,
                'sales': 120,
                'supplier_name': '供应商 A',
                'supplier_level': '金牌',
                'product_url': 'https://example.com/1',
                'main_image_url': 'https://example.com/img1.jpg',
                'thumbnail_urls': [],
                'collected_at': datetime.now().isoformat()
            }
        ]
        crawler2.save_to_sqlite()
        
        # 验证数据库
        conn = sqlite3.connect(crawler2.db_path)
        cursor = conn.cursor()
        
        # 查询所有记录
        cursor.execute("SELECT product_id, title, sales, is_latest FROM products ORDER BY collected_at")
        rows = cursor.fetchall()
        
        print(f"数据库记录数：{len(rows)}")
        for row in rows:
            print(f"  {row}")
        
        # 验证：应该有 2 条记录
        assert len(rows) == 2, f"期望 2 条历史记录，实际 {len(rows)} 条"
        
        # 验证：第一条 is_latest=0，第二条 is_latest=1
        assert rows[0][3] == 0, f"第一条记录 is_latest 应为 0，实际 {rows[0][3]}"
        assert rows[1][3] == 1, f"第二条记录 is_latest 应为 1，实际 {rows[1][3]}"
        
        # 验证：最新记录的数据是更新后的
        assert rows[1][1] == '测试商品 v2（更新）', f"最新记录标题应为'测试商品 v2（更新）'，实际 {rows[1][1]}"
        assert rows[1][2] == 120, f"最新记录销量应为 120，实际 {rows[1][2]}"
        
        conn.close()
        
        print("✅ 测试 2 通过：is_latest 标记功能正常")
        return True


def test_jsonl_backup():
    """测试 3: JSONL 备份包含 is_latest 字段"""
    print("\n" + "="*60)
    print("测试 3: JSONL 备份包含 is_latest 字段")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        crawler = ProductCrawler(keyword="test", limit=10, output_dir=tmpdir)
        crawler.products = [
            {
                'product_id': 'PROD_001',
                'title': '测试商品 1',
                'price_min': 10.0,
                'price_max': 20.0,
                'sales': 100,
                'supplier_name': '供应商 A',
                'supplier_level': '金牌',
                'product_url': 'https://example.com/1',
                'main_image_url': 'https://example.com/img1.jpg',
                'thumbnail_urls': ['https://example.com/thumb1.jpg'],
                'collected_at': datetime.now().isoformat()
            }
        ]
        
        # 保存到 JSONL
        crawler.save_to_jsonl()
        
        # 读取 JSONL 文件验证
        jsonl_data = []
        with open(crawler.jsonl_path, 'r', encoding='utf-8') as f:
            for line in f:
                jsonl_data.append(json.loads(line))
        
        # 验证：包含 is_latest 字段
        assert len(jsonl_data) == 1, f"期望 1 条记录，实际 {len(jsonl_data)} 条"
        assert 'is_latest' in jsonl_data[0], "JSONL 记录缺少 is_latest 字段"
        assert jsonl_data[0]['is_latest'] == 1, f"is_latest 应为 1，实际 {jsonl_data[0]['is_latest']}"
        
        print(f"✅ 测试 3 通过：JSONL 备份包含 is_latest 字段")
        print(f"   JSONL 文件：{crawler.jsonl_path}")
        print(f"   记录内容：{json.dumps(jsonl_data[0], ensure_ascii=False, indent=2)}")
        return True


def test_query_latest_products():
    """测试 4: 查询最新数据（WHERE is_latest = 1）"""
    print("\n" + "="*60)
    print("测试 4: 查询最新数据")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建爬虫并保存多条数据
        crawler = ProductCrawler(keyword="test", limit=10, output_dir=tmpdir)
        crawler.products = [
            {
                'product_id': 'PROD_001',
                'title': '测试商品 v1',
                'price_min': 10.0,
                'price_max': 20.0,
                'sales': 100,
                'supplier_name': '供应商 A',
                'supplier_level': '金牌',
                'product_url': 'https://example.com/1',
                'main_image_url': 'https://example.com/img1.jpg',
                'thumbnail_urls': [],
                'collected_at': datetime.now().isoformat()
            },
            {
                'product_id': 'PROD_002',
                'title': '测试商品 2',
                'price_min': 30.0,
                'price_max': 40.0,
                'sales': 200,
                'supplier_name': '供应商 B',
                'supplier_level': '银牌',
                'product_url': 'https://example.com/2',
                'main_image_url': 'https://example.com/img2.jpg',
                'thumbnail_urls': [],
                'collected_at': datetime.now().isoformat()
            }
        ]
        crawler.save_to_sqlite()
        
        # 更新 PROD_001
        crawler.products = [
            {
                'product_id': 'PROD_001',
                'title': '测试商品 v2',
                'price_min': 15.0,
                'price_max': 25.0,
                'sales': 150,
                'supplier_name': '供应商 A',
                'supplier_level': '金牌',
                'product_url': 'https://example.com/1',
                'main_image_url': 'https://example.com/img1.jpg',
                'thumbnail_urls': [],
                'collected_at': datetime.now().isoformat()
            }
        ]
        crawler.save_to_sqlite()
        
        # 查询最新数据
        conn = sqlite3.connect(crawler.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT product_id, title, sales FROM products WHERE is_latest = 1")
        latest_products = cursor.fetchall()
        conn.close()
        
        print(f"最新产品数量：{len(latest_products)}")
        for prod in latest_products:
            print(f"  {prod}")
        
        # 验证：应该有 2 个最新产品（PROD_001 和 PROD_002）
        assert len(latest_products) == 2, f"期望 2 个最新产品，实际 {len(latest_products)} 个"
        
        # 验证：PROD_001 是最新版本
        prod_001 = [p for p in latest_products if p[0] == 'PROD_001'][0]
        assert prod_001[1] == '测试商品 v2', f"PROD_001 应为 v2，实际 {prod_001[1]}"
        assert prod_001[2] == 150, f"PROD_001 销量应为 150，实际 {prod_001[2]}"
        
        print("✅ 测试 4 通过：查询最新数据功能正常")
        return True


def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("US_03 数据存储与去重 - 单元测试")
    print("="*60)
    
    results = {
        'test_deduplication_within_task': False,
        'test_is_latest_flag': False,
        'test_jsonl_backup': False,
        'test_query_latest_products': False
    }
    
    try:
        results['test_deduplication_within_task'] = test_deduplication_within_task()
    except Exception as e:
        print(f"❌ 测试 1 失败：{e}")
    
    try:
        results['test_is_latest_flag'] = test_is_latest_flag()
    except Exception as e:
        print(f"❌ 测试 2 失败：{e}")
    
    try:
        results['test_jsonl_backup'] = test_jsonl_backup()
    except Exception as e:
        print(f"❌ 测试 3 失败：{e}")
    
    try:
        results['test_query_latest_products'] = test_query_latest_products()
    except Exception as e:
        print(f"❌ 测试 4 失败：{e}")
    
    # 汇总结果
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {test_name}: {status}")
    
    print(f"\n总计：{passed}/{total} 通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！US_03 功能实现正确。")
        return 0
    else:
        print(f"\n⚠️  有 {total - passed} 个测试失败，请检查代码。")
        return 1


if __name__ == '__main__':
    sys.exit(main())
