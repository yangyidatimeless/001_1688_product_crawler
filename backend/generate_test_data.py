#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成 US_01 测试数据

用于 QA 测试的 Mock 数据，模拟 1688 商品爬取结果
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path


def generate_mock_products():
    """生成模拟商品数据"""
    products = [
        {
            'product_id': 'TB001',
            'title': '家用拖把免手洗旋转干湿两用懒人拖地神器',
            'price_min': 29.9,
            'price_max': 59.9,
            'sales': 15000,
            'supplier_name': '义乌市清洁用品厂',
            'supplier_level': '诚信通 5 年',
            'product_url': 'https://detail.1688.com/offer/TB001.html',
            'main_image_url': 'https://cbu01.alicdn.com/img/ibank/TB001.jpg',
            'thumbnail_urls': [
                'https://cbu01.alicdn.com/img/ibank/TB001_1.jpg',
                'https://cbu01.alicdn.com/img/ibank/TB001_2.jpg',
                'https://cbu01.alicdn.com/img/ibank/TB001_3.jpg'
            ],
            'collected_at': datetime.now().isoformat()
        },
        {
            'product_id': 'TB002',
            'title': '加厚平板拖把商用大号尘推排拖',
            'price_min': 45.0,
            'price_max': 88.0,
            'sales': 8500,
            'supplier_name': '临沂市家居用品公司',
            'supplier_level': '诚信通 3 年',
            'product_url': 'https://detail.1688.com/offer/TB002.html',
            'main_image_url': 'https://cbu01.alicdn.com/img/ibank/TB002.jpg',
            'thumbnail_urls': [
                'https://cbu01.alicdn.com/img/ibank/TB002_1.jpg',
                'https://cbu01.alicdn.com/img/ibank/TB002_2.jpg'
            ],
            'collected_at': datetime.now().isoformat()
        },
        {
            'product_id': 'TB003',
            'title': '电动拖把无线充电式自动旋转拖地机',
            'price_min': 128.0,
            'price_max': 198.0,
            'sales': 3200,
            'supplier_name': '深圳市智能家电有限公司',
            'supplier_level': '诚信通 7 年',
            'product_url': 'https://detail.1688.com/offer/TB003.html',
            'main_image_url': 'https://cbu01.alicdn.com/img/ibank/TB003.jpg',
            'thumbnail_urls': [
                'https://cbu01.alicdn.com/img/ibank/TB003_1.jpg',
                'https://cbu01.alicdn.com/img/ibank/TB003_2.jpg',
                'https://cbu01.alicdn.com/img/ibank/TB003_3.jpg',
                'https://cbu01.alicdn.com/img/ibank/TB003_4.jpg'
            ],
            'collected_at': datetime.now().isoformat()
        },
        {
            'product_id': 'TB004',
            'title': '一次性拖把替换布干湿两用除尘纸',
            'price_min': 9.9,
            'price_max': 19.9,
            'sales': 50000,
            'supplier_name': '杭州市日用品批发商行',
            'supplier_level': '诚信通 2 年',
            'product_url': 'https://detail.1688.com/offer/TB004.html',
            'main_image_url': 'https://cbu01.alicdn.com/img/ibank/TB004.jpg',
            'thumbnail_urls': [
                'https://cbu01.alicdn.com/img/ibank/TB004_1.jpg'
            ],
            'collected_at': datetime.now().isoformat()
        },
        {
            'product_id': 'TB005',
            'title': '不锈钢杆拖把工厂食堂专用大拖把',
            'price_min': 35.0,
            'price_max': 55.0,
            'sales': 2800,
            'supplier_name': '广州市清洁工具厂',
            'supplier_level': '诚信通 4 年',
            'product_url': 'https://detail.1688.com/offer/TB005.html',
            'main_image_url': 'https://cbu01.alicdn.com/img/ibank/TB005.jpg',
            'thumbnail_urls': [
                'https://cbu01.alicdn.com/img/ibank/TB005_1.jpg',
                'https://cbu01.alicdn.com/img/ibank/TB005_2.jpg'
            ],
            'collected_at': datetime.now().isoformat()
        }
    ]
    return products


def save_to_jsonl(products, output_path):
    """保存数据到 JSONL 文件"""
    with open(output_path, 'w', encoding='utf-8') as f:
        for product in products:
            f.write(json.dumps(product, ensure_ascii=False) + '\n')
    print(f"✅ JSONL 文件已生成：{output_path}")


def save_to_sqlite(products, db_path):
    """保存数据到 SQLite 数据库"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 创建表
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
    
    # 插入数据
    for product in products:
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
    print(f"✅ SQLite 数据库已更新：{db_path}")


def main():
    """主函数"""
    # 确保 data 目录存在
    data_dir = Path(__file__).parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # 生成测试数据
    print("🔧 生成 US_01 测试数据...")
    products = generate_mock_products()
    print(f"📦 生成了 {len(products)} 条模拟商品数据")
    
    # 保存到 JSONL
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    jsonl_path = data_dir / f"products_测试商品_{timestamp}.jsonl"
    save_to_jsonl(products, jsonl_path)
    
    # 保存到 SQLite
    db_path = data_dir / "products.db"
    save_to_sqlite(products, db_path)
    
    print("\n" + "=" * 50)
    print("✅ 测试数据生成完成")
    print("=" * 50)
    print(f"数据目录：{data_dir}")
    print(f"JSONL 文件：{jsonl_path.name}")
    print(f"SQLite 文件：{db_path.name}")
    print("=" * 50)


if __name__ == '__main__':
    main()
