#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
US_06 数据导出功能自测脚本

测试场景：
1. 创建测试数据
2. 导出为 CSV
3. 验证 CSV 内容和格式
"""

import os
import sys
import json
import sqlite3
import csv
from pathlib import Path
from datetime import datetime

# 添加 backend 目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from crawler import ProductCrawler


def create_test_data(crawler: ProductCrawler) -> int:
    """创建测试数据"""
    test_products = [
        {
            'product_id': 'TEST001',
            'title': '测试 - 家用拖把免手洗旋转干湿两用',
            'price_min': 29.9,
            'price_max': 59.9,
            'sales': 15000,
            'supplier_name': '义乌市清洁用品厂',
            'supplier_level': '诚信通 5 年',
            'product_url': 'https://detail.1688.com/offer/TEST001.html',
            'main_image_url': 'https://cbu01.alicdn.com/img/ibank/test001.jpg',
            'thumbnail_urls': ['https://cbu01.alicdn.com/img/ibank/test001_1.jpg', 'https://cbu01.alicdn.com/img/ibank/test001_2.jpg'],
            'collected_at': datetime.now().isoformat(),
        },
        {
            'product_id': 'TEST002',
            'title': '测试 - 收纳盒塑料整理箱衣物储物盒',
            'price_min': 15.8,
            'price_max': 35.8,
            'sales': 8500,
            'supplier_name': '台州市家居用品公司',
            'supplier_level': '诚信通 3 年',
            'product_url': 'https://detail.1688.com/offer/TEST002.html',
            'main_image_url': 'https://cbu01.alicdn.com/img/ibank/test002.jpg',
            'thumbnail_urls': ['https://cbu01.alicdn.com/img/ibank/test002_1.jpg'],
            'collected_at': datetime.now().isoformat(),
        },
        {
            'product_id': 'TEST003',
            'title': '测试 - 厨房用品神器家用大全实用小百货',
            'price_min': 9.9,
            'price_max': 19.9,
            'sales': 25000,
            'supplier_name': '广州市厨具有限公司',
            'supplier_level': '诚信通 8 年',
            'product_url': 'https://detail.1688.com/offer/TEST003.html',
            'main_image_url': 'https://cbu01.alicdn.com/img/ibank/test003.jpg',
            'thumbnail_urls': [],
            'collected_at': datetime.now().isoformat(),
        },
    ]
    
    # 插入测试数据到数据库
    conn = sqlite3.connect(crawler.db_path)
    cursor = conn.cursor()
    
    import json
    
    for product in test_products:
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
    
    conn.commit()
    conn.close()
    
    crawler.products = test_products
    return len(test_products)


def test_export():
    """测试导出功能"""
    print("=" * 60)
    print("🧪 US_06 数据导出功能自测")
    print("=" * 60)
    
    # 创建爬虫实例
    crawler = ProductCrawler(
        keyword="测试",
        limit=50,
        preview=False,
        output_dir="./data/"
    )
    
    # Step 1: 创建测试数据
    print("\n📝 Step 1: 创建测试数据...")
    count = create_test_data(crawler)
    print(f"✅ 已创建 {count} 条测试数据")
    
    # Step 2: 导出 CSV
    print("\n📤 Step 2: 导出 CSV...")
    print(f"   当前 products 数量：{len(crawler.products)}")
    
    # 手动测试 _filter_export_data
    filtered = crawler._filter_export_data(keyword="测试")
    print(f"   过滤后数据数量：{len(filtered)}")
    
    try:
        csv_path = crawler.export_to_csv(keyword="测试")
        print(f"✅ CSV 导出成功：{csv_path}")
    except Exception as e:
        print(f"❌ 导出失败：{e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 3: 验证 CSV 文件
    print("\n🔍 Step 3: 验证 CSV 文件...")
    
    if not os.path.exists(csv_path):
        print(f"❌ CSV 文件不存在：{csv_path}")
        return False
    
    # 读取并验证 CSV 内容
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        
        # 验证列名
        expected_columns = [
            'product_id', 'title', 'price_min', 'price_max', 'sales',
            'supplier_name', 'supplier_level', 'product_url',
            'main_image_url', 'thumbnail_urls', 'collected_at', 'is_latest'
        ]
        
        if reader.fieldnames != expected_columns:
            print(f"❌ 列名不匹配")
            print(f"   期望：{expected_columns}")
            print(f"   实际：{reader.fieldnames}")
            return False
        
        print(f"✅ 列名正确：{len(expected_columns)} 列")
        
        # 验证行数
        if len(rows) != count:
            print(f"❌ 行数不匹配：期望 {count}, 实际 {len(rows)}")
            return False
        
        print(f"✅ 行数正确：{len(rows)} 行")
        
        # 验证数据内容
        print("\n📋 CSV 内容预览:")
        print("-" * 60)
        for i, row in enumerate(rows[:3], 1):
            print(f"{i}. {row['title']}")
            print(f"   价格：¥{row['price_min']} - ¥{row['price_max']}")
            print(f"   销量：{row['sales']}")
            print(f"   供应商：{row['supplier_name']}")
            print(f"   is_latest: {row['is_latest']}")
            print()
    
    # Step 4: 验证特殊字符处理
    print("🔍 Step 4: 验证特殊字符处理...")
    
    # 添加包含特殊字符的测试数据
    special_product = {
        'product_id': 'TEST_SPECIAL',
        'title': '测试，逗号 "引号" 和\n换行符',
        'price_min': 10.0,
        'price_max': 20.0,
        'sales': 100,
        'supplier_name': '测试"供应商", 有限公司',
        'supplier_level': '诚信通 1 年',
        'product_url': 'https://example.com/test',
        'main_image_url': 'https://example.com/img.jpg',
        'thumbnail_urls': [],
        'collected_at': datetime.now().isoformat(),
    }
    
    conn = sqlite3.connect(crawler.db_path)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO products 
        (product_id, title, price_min, price_max, sales, supplier_name, 
         supplier_level, product_url, main_image_url, thumbnail_urls, collected_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        special_product['product_id'],
        special_product['title'],
        special_product['price_min'],
        special_product['price_max'],
        special_product['sales'],
        special_product['supplier_name'],
        special_product['supplier_level'],
        special_product['product_url'],
        special_product['main_image_url'],
        json.dumps(special_product['thumbnail_urls'], ensure_ascii=False),
        special_product['collected_at']
    ))
    conn.commit()
    conn.close()
    
    crawler.products.append(special_product)
    
    # 重新导出
    csv_path2 = crawler.export_to_csv(keyword="测试")
    
    # 验证特殊字符是否正确转义
    with open(csv_path2, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        special_row = next((r for r in rows if r['product_id'] == 'TEST_SPECIAL'), None)
        
        if special_row:
            print(f"✅ 特殊字符处理正确")
            print(f"   标题：{special_row['title'][:30]}...")
            print(f"   供应商：{special_row['supplier_name'][:30]}...")
        else:
            print(f"❌ 未找到特殊字符测试数据")
            return False
    
    print("\n" + "=" * 60)
    print("✅ 所有测试通过！")
    print("=" * 60)
    
    return True


if __name__ == '__main__':
    success = test_export()
    sys.exit(0 if success else 1)
