#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
US_06 数据导出功能 - QA 验收测试脚本

测试人员：少锋 (QA)
测试类型：独立验收测试 (Independent QA Testing)
测试依据：US_06_Export.json v1.0 验收标准

验收标准：
1. 支持导出指定关键词的抓取数据
2. CSV 包含所有必填字段
3. CSV 文件命名包含日期和关键词
4. 导出时自动处理特殊字符（避免 CSV 格式错误）
5. 支持 UTF-8 编码（Excel 兼容）
"""

import sys
import os
import json
import sqlite3
import csv
import subprocess
from pathlib import Path
from datetime import datetime

# 添加 backend 目录到路径
BACKEND_DIR = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from crawler import ProductCrawler

# 测试结果记录
test_results = []
bug_list = []


def log_test(name, success, details=""):
    """记录测试结果"""
    test_results.append({
        "name": name,
        "success": success,
        "details": details,
        "timestamp": datetime.now().isoformat()
    })
    status = "✅" if success else "❌"
    print(f"{status} {name}: {details}")


def log_bug(bug_id, title, severity, steps, expected, actual):
    """记录 Bug"""
    bug = {
        "bug_id": bug_id,
        "title": title,
        "severity": severity,
        "steps": steps,
        "expected": expected,
        "actual": actual
    }
    bug_list.append(bug)
    print(f"🐛 [{bug_id}] {title} - 严重等级：{severity}")


def create_test_data(crawler: ProductCrawler, reset_db: bool = True) -> int:
    """创建测试数据
    
    Args:
        crawler: 爬虫实例
        reset_db: 是否重置数据库表结构（添加 is_latest 字段）
    """
    # 确保数据库表结构正确
    if reset_db:
        conn = sqlite3.connect(crawler.db_path)
        cursor = conn.cursor()
        
        # 检查 is_latest 列是否已存在
        cursor.execute("PRAGMA table_info(products)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'is_latest' not in columns:
            cursor.execute('''
                ALTER TABLE products
                ADD COLUMN is_latest INTEGER DEFAULT 1
            ''')
            conn.commit()
            print(f"✅ 已添加 is_latest 列到数据库：{crawler.db_path}")
        
        conn.close()
    
    test_products = [
        {
            'product_id': 'US06_TEST001',
            'title': '测试 - 家用拖把免手洗旋转干湿两用',
            'price_min': 29.9,
            'price_max': 59.9,
            'sales': 15000,
            'supplier_name': '义乌市清洁用品厂',
            'supplier_level': '诚信通 5 年',
            'product_url': 'https://detail.1688.com/offer/US06_TEST001.html',
            'main_image_url': 'https://cbu01.alicdn.com/img/ibank/us06_test001.jpg',
            'thumbnail_urls': ['https://cbu01.alicdn.com/img/ibank/us06_test001_1.jpg', 'https://cbu01.alicdn.com/img/ibank/us06_test001_2.jpg'],
            'collected_at': datetime.now().isoformat(),
        },
        {
            'product_id': 'US06_TEST002',
            'title': '测试 - 收纳盒塑料整理箱衣物储物盒',
            'price_min': 15.8,
            'price_max': 35.8,
            'sales': 8500,
            'supplier_name': '台州市家居用品公司',
            'supplier_level': '诚信通 3 年',
            'product_url': 'https://detail.1688.com/offer/US06_TEST002.html',
            'main_image_url': 'https://cbu01.alicdn.com/img/ibank/us06_test002.jpg',
            'thumbnail_urls': ['https://cbu01.alicdn.com/img/ibank/us06_test002_1.jpg'],
            'collected_at': datetime.now().isoformat(),
        },
        {
            'product_id': 'US06_TEST003',
            'title': '测试 - 厨房用品神器家用大全实用小百货',
            'price_min': 9.9,
            'price_max': 19.9,
            'sales': 25000,
            'supplier_name': '广州市厨具有限公司',
            'supplier_level': '诚信通 8 年',
            'product_url': 'https://detail.1688.com/offer/US06_TEST003.html',
            'main_image_url': 'https://cbu01.alicdn.com/img/ibank/us06_test003.jpg',
            'thumbnail_urls': [],
            'collected_at': datetime.now().isoformat(),
        },
    ]
    
    conn = sqlite3.connect(crawler.db_path)
    cursor = conn.cursor()
    
    for product in test_products:
        cursor.execute('''
            INSERT OR REPLACE INTO products 
            (product_id, title, price_min, price_max, sales, supplier_name, 
             supplier_level, product_url, main_image_url, thumbnail_urls, collected_at, is_latest)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            product['collected_at'],
            1
        ))
    
    conn.commit()
    conn.close()
    
    crawler.products = test_products
    return len(test_products)


# ============================================================
# 测试 1: CSV 导出基本功能
# ============================================================
def test_csv_export_basic():
    """测试 CSV 导出基本功能"""
    print("\n" + "=" * 60)
    print("测试 1: CSV 导出基本功能")
    print("=" * 60)
    
    crawler = ProductCrawler(
        keyword="测试",
        limit=50,
        preview=False,
        output_dir="./data/"
    )
    
    # 创建测试数据
    count = create_test_data(crawler)
    log_test("测试数据创建", True, f"创建 {count} 条测试数据")
    
    # 执行导出
    try:
        csv_path = crawler.export_to_csv(keyword="测试")
        log_test("CSV 导出执行", True, f"导出成功：{csv_path}")
    except Exception as e:
        log_test("CSV 导出执行", False, f"导出失败：{e}")
        return False
    
    # 验证文件存在
    if not os.path.exists(csv_path):
        log_test("CSV 文件存在", False, f"文件不存在：{csv_path}")
        return False
    log_test("CSV 文件存在", True, f"{csv_path}")
    
    return True


# ============================================================
# 测试 2: CSV 列名验证
# ============================================================
def test_csv_columns():
    """测试 CSV 列名是否符合契约要求"""
    print("\n" + "=" * 60)
    print("测试 2: CSV 列名验证")
    print("=" * 60)
    
    expected_columns = [
        'product_id', 'title', 'price_min', 'price_max', 'sales',
        'supplier_name', 'supplier_level', 'product_url',
        'main_image_url', 'thumbnail_urls', 'collected_at', 'is_latest'
    ]
    
    crawler = ProductCrawler(
        keyword="测试",
        limit=50,
        preview=False,
        output_dir="./data/"
    )
    
    csv_path = crawler.export_to_csv(keyword="测试")
    
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        
        if reader.fieldnames != expected_columns:
            log_test("CSV 列名验证", False, f"列名不匹配")
            print(f"   期望：{expected_columns}")
            print(f"   实际：{reader.fieldnames}")
            return False
        
        log_test("CSV 列名验证", True, f"所有 {len(expected_columns)} 列正确")
        return True


# ============================================================
# 测试 3: 文件命名规范
# ============================================================
def test_file_naming():
    """测试 CSV 文件命名是否符合规范"""
    print("\n" + "=" * 60)
    print("测试 3: 文件命名规范")
    print("=" * 60)
    
    crawler = ProductCrawler(
        keyword="拖把",
        limit=50,
        preview=False,
        output_dir="./data/"
    )
    
    create_test_data(crawler)
    csv_path = crawler.export_to_csv(keyword="拖把")
    
    # 验证文件名格式：products_{keyword}_{date}.csv
    filename = os.path.basename(csv_path)
    today = datetime.now().strftime("%Y-%m-%d")
    expected_pattern = f"products_拖把_{today}.csv"
    
    if expected_pattern not in filename:
        log_test("文件命名规范", False, f"期望包含 '{expected_pattern}', 实际：{filename}")
        return False
    
    log_test("文件命名规范", True, f"{filename}")
    return True


# ============================================================
# 测试 4: 特殊字符处理
# ============================================================
def test_special_characters():
    """测试特殊字符（逗号、引号、换行）是否正确处理"""
    print("\n" + "=" * 60)
    print("测试 4: 特殊字符处理")
    print("=" * 60)
    
    crawler = ProductCrawler(
        keyword="测试",
        limit=50,
        preview=False,
        output_dir="./data/"
    )
    
    # 添加包含特殊字符的测试数据
    special_product = {
        'product_id': 'US06_SPECIAL',
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
         supplier_level, product_url, main_image_url, thumbnail_urls, collected_at, is_latest)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        special_product['collected_at'],
        1
    ))
    conn.commit()
    conn.close()
    
    crawler.products.append(special_product)
    csv_path = crawler.export_to_csv(keyword="测试")
    
    # 验证 CSV 能否正确读取（如果特殊字符未正确处理，csv 模块会报错）
    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            special_row = next((r for r in rows if r['product_id'] == 'US06_SPECIAL'), None)
            
            if not special_row:
                log_test("特殊字符处理", False, "未找到特殊字符测试数据")
                return False
            
            # 验证特殊字符内容是否正确保留
            if '逗号' in special_row['title'] and '引号' in special_row['title']:
                log_test("特殊字符处理", True, "逗号、引号、换行符处理正确")
                return True
            else:
                log_test("特殊字符处理", False, "特殊字符内容丢失")
                return False
                
    except Exception as e:
        log_test("特殊字符处理", False, f"CSV 解析失败：{e}")
        return False


# ============================================================
# 测试 5: UTF-8 编码验证 (Excel 兼容)
# ============================================================
def test_utf8_encoding():
    """测试 CSV 文件是否为 UTF-8-SIG 编码（Excel 兼容）"""
    print("\n" + "=" * 60)
    print("测试 5: UTF-8 编码验证")
    print("=" * 60)
    
    crawler = ProductCrawler(
        keyword="测试",
        limit=50,
        preview=False,
        output_dir="./data/"
    )
    
    create_test_data(crawler)
    csv_path = crawler.export_to_csv(keyword="测试")
    
    # 检查 BOM 头（UTF-8-SIG 的标志）
    with open(csv_path, 'rb') as f:
        bom = f.read(3)
        if bom == b'\xef\xbb\xbf':
            log_test("UTF-8-SIG 编码", True, "包含 BOM 头，Excel 兼容")
            return True
        else:
            log_test("UTF-8-SIG 编码", False, "缺少 BOM 头，Excel 可能乱码")
            return False


# ============================================================
# 测试 6: 关键词过滤功能
# ============================================================
def test_keyword_filter():
    """测试按关键词过滤导出功能"""
    print("\n" + "=" * 60)
    print("测试 6: 关键词过滤功能")
    print("=" * 60)
    
    crawler = ProductCrawler(
        keyword="拖把",
        limit=50,
        preview=False,
        output_dir="./data/"
    )
    
    # 创建不同关键词的测试数据
    conn = sqlite3.connect(crawler.db_path)
    cursor = conn.cursor()
    
    # 添加"收纳盒"关键词数据
    cursor.execute('''
        INSERT OR REPLACE INTO products 
        (product_id, title, price_min, price_max, sales, supplier_name, 
         supplier_level, product_url, main_image_url, thumbnail_urls, collected_at, is_latest)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        'US06_STORAGE',
        '收纳盒塑料整理箱',
        15.8,
        35.8,
        8500,
        '台州市家居用品公司',
        '诚信通 3 年',
        'https://detail.1688.com/offer/storage.html',
        'https://example.com/storage.jpg',
        json.dumps([], ensure_ascii=False),
        datetime.now().isoformat(),
        1
    ))
    conn.commit()
    conn.close()
    
    # 导出"拖把"关键词
    csv_path = crawler.export_to_csv(keyword="拖把")
    
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        
        # 验证只包含"拖把"相关数据
        has_storage = any('收纳盒' in row['title'] for row in rows)
        
        if has_storage:
            log_test("关键词过滤", False, "导出了非拖把关键词的数据")
            return False
        else:
            log_test("关键词过滤", True, "正确过滤出拖把关键词数据")
            return True


# ============================================================
# 主测试流程
# ============================================================
def main():
    """执行所有 QA 验收测试"""
    print("=" * 60)
    print("🧪 US_06 数据导出功能 - QA 验收测试")
    print("测试人员：少锋")
    print("测试依据：US_06_Export.json v1.0")
    print("=" * 60)
    
    tests = [
        ("CSV 导出基本功能", test_csv_export_basic),
        ("CSV 列名验证", test_csv_columns),
        ("文件命名规范", test_file_naming),
        ("特殊字符处理", test_special_characters),
        ("UTF-8 编码验证", test_utf8_encoding),
        ("关键词过滤功能", test_keyword_filter),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            if result:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            log_test(test_name, False, f"异常：{e}")
            failed += 1
    
    # 输出测试统计
    print("\n" + "=" * 60)
    print("📊 测试统计")
    print("=" * 60)
    print(f"总用例：{len(tests)}")
    print(f"通过：{passed}")
    print(f"失败：{failed}")
    print(f"通过率：{passed/len(tests)*100:.1f}%")
    
    # 生成测试结论
    if failed == 0:
        print("\n✅ 测试结论：通过 - 所有验收标准满足")
    else:
        print(f"\n❌ 测试结论：不通过 - {failed} 个用例失败，需要修复")
    
    # 返回测试结果
    return {
        "total": len(tests),
        "passed": passed,
        "failed": failed,
        "pass_rate": f"{passed/len(tests)*100:.1f}%",
        "conclusion": "通过" if failed == 0 else "不通过",
        "bug_list": bug_list
    }


if __name__ == '__main__':
    result = main()
    
    # 如果有 Bug，输出 Bug 列表
    if bug_list:
        print("\n" + "=" * 60)
        print("🐛 Bug 列表")
        print("=" * 60)
        for bug in bug_list:
            print(f"[{bug['bug_id']}] {bug['title']}")
            print(f"  严重等级：{bug['severity']}")
            print(f"  复现步骤：{bug['steps']}")
            print(f"  期望：{bug['expected']}")
            print(f"  实际：{bug['actual']}")
            print()
    
    sys.exit(0 if result['failed'] == 0 else 1)
