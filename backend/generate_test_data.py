#!/usr/bin/env python3
"""
生成测试数据脚本 - 用于验证 US_03 的 JSONL 备份功能
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path

# 配置
output_dir = Path(__file__).parent / "data"
output_dir.mkdir(exist_ok=True)

db_path = output_dir / "products.db"
jsonl_path = output_dir / f"products_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"

# 测试数据
test_products = [
    {
        "product_id": "123456789",
        "title": "iPhone 15 Pro Max 手机壳 透明防摔保护套",
        "price_min": 29.9,
        "price_max": 59.9,
        "sales": 1580,
        "supplier_name": "深圳数码配件厂",
        "supplier_level": "诚信通 8 年",
        "product_url": "https://detail.1688.com/offer/123456789.html",
        "main_image_url": "https://cbu01.alicdn.com/img/ibank/O1CN01xxx_!!123456789.jpg",
        "thumbnail_urls": '["https://cbu01.alicdn.com/img/ibank/O1CN01xxx_!!123456789-1.jpg", "https://cbu01.alicdn.com/img/ibank/O1CN01xxx_!!123456789-2.jpg"]',
        "collected_at": datetime.now().isoformat(),
        "is_latest": 1
    },
    {
        "product_id": "987654321",
        "title": "华为 Mate 60 Pro 手机壳 液态硅胶全包镜头保护",
        "price_min": 35.0,
        "price_max": 68.0,
        "sales": 2350,
        "supplier_name": "广州皮具制品厂",
        "supplier_level": "诚信通 5 年",
        "product_url": "https://detail.1688.com/offer/987654321.html",
        "main_image_url": "https://cbu01.alicdn.com/img/ibank/O1CN01yyy_!!987654321.jpg",
        "thumbnail_urls": '["https://cbu01.alicdn.com/img/ibank/O1CN01yyy_!!987654321-1.jpg"]',
        "collected_at": datetime.now().isoformat(),
        "is_latest": 1
    },
    {
        "product_id": "456789123",
        "title": "小米 14 Ultra 手机壳 碳纤维纹理散热保护套",
        "price_min": 25.5,
        "price_max": 45.0,
        "sales": 890,
        "supplier_name": "东莞电子配件公司",
        "supplier_level": "诚信通 3 年",
        "product_url": "https://detail.1688.com/offer/456789123.html",
        "main_image_url": "https://cbu01.alicdn.com/img/ibank/O1CN01zzz_!!456789123.jpg",
        "thumbnail_urls": '["https://cbu01.alicdn.com/img/ibank/O1CN01zzz_!!456789123-1.jpg", "https://cbu01.alicdn.com/img/ibank/O1CN01zzz_!!456789123-2.jpg", "https://cbu01.alicdn.com/img/ibank/O1CN01zzz_!!456789123-3.jpg"]',
        "collected_at": datetime.now().isoformat(),
        "is_latest": 1
    }
]

def create_test_data():
    """创建测试数据到 SQLite 和 JSONL"""
    print("=" * 60)
    print("生成 US_03 测试数据")
    print("=" * 60)
    
    # 1. 写入 SQLite
    print(f"\n📊 写入 SQLite 数据库：{db_path}")
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    for product in test_products:
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO products 
                (product_id, title, price_min, price_max, sales, supplier_name, 
                 supplier_level, product_url, main_image_url, thumbnail_urls, 
                 collected_at, is_latest)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                product["product_id"],
                product["title"],
                product["price_min"],
                product["price_max"],
                product["sales"],
                product["supplier_name"],
                product["supplier_level"],
                product["product_url"],
                product["main_image_url"],
                product["thumbnail_urls"],
                product["collected_at"],
                product["is_latest"]
            ))
            print(f"  ✅ 插入商品：{product['product_id']} - {product['title'][:30]}...")
        except Exception as e:
            print(f"  ❌ 插入失败：{e}")
    
    conn.commit()
    
    # 验证数据
    cursor.execute("SELECT COUNT(*) FROM products")
    count = cursor.fetchone()[0]
    print(f"  📊 数据库总记录数：{count}")
    
    cursor.execute("SELECT COUNT(*) FROM products WHERE is_latest = 1")
    latest_count = cursor.fetchone()[0]
    print(f"  📊 最新记录数 (is_latest=1): {latest_count}")
    
    conn.close()
    
    # 2. 写入 JSONL
    print(f"\n📄 写入 JSONL 备份：{jsonl_path}")
    with open(jsonl_path, 'w', encoding='utf-8') as f:
        for product in test_products:
            f.write(json.dumps(product, ensure_ascii=False) + '\n')
            print(f"  ✅ 写入 JSONL: {product['product_id']}")
    
    print(f"\n✅ 测试数据生成完成！")
    print(f"   - SQLite: {db_path} ({count} 条记录)")
    print(f"   - JSONL: {jsonl_path} ({len(test_products)} 条记录)")
    print("\n" + "=" * 60)

if __name__ == "__main__":
    create_test_data()
