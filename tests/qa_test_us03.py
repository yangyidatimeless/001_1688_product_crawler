#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
1688 商品爬虫 - US_03 QA 验收测试脚本

测试人员：少锋 (QA)
测试类型：独立验收测试 (Independent QA Testing)
测试依据：US_03_DataStorage.json v1.0 验收标准

测试覆盖：
1. 数据库 Schema 验证 - 联合唯一键、索引、is_latest 字段
2. 单次任务内去重 - 同一商品 ID 不重复保存
3. 跨任务保留历史 - 新数据保留，旧数据 is_latest=0
4. JSONL 备份验证 - 包含 is_latest 字段
5. 查询最新数据 - WHERE is_latest = 1 功能验证
6. 数据完整性 - 字段完整性、数据合理性
"""

import sys
import os
import json
import sqlite3
import subprocess
from pathlib import Path
from datetime import datetime

# 项目路径
PROJECT_DIR = Path("/app/dev_project/001_1688_product_crawler")
BACKEND_DIR = PROJECT_DIR / "backend"
DATA_DIR = BACKEND_DIR / "data"  # 数据在 backend/data 目录
TESTS_DIR = PROJECT_DIR / "tests"

# 添加 backend 目录到路径
sys.path.insert(0, str(BACKEND_DIR))

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


def log_bug(bug_id, title, severity, steps, expected, actual, impact=""):
    """记录 Bug"""
    bug = {
        "bug_id": bug_id,
        "title": title,
        "severity": severity,
        "steps": steps,
        "expected": expected,
        "actual": actual,
        "impact": impact
    }
    bug_list.append(bug)
    print(f"🐛 [{bug_id}] {title} - 严重等级：{severity}")


# ============================================================
# 测试 1: 数据库 Schema 验证
# ============================================================
def test_database_schema():
    """测试 1: 验证数据库 Schema 是否符合契约要求"""
    print("\n" + "=" * 60)
    print("测试 1: 数据库 Schema 验证")
    print("=" * 60)
    
    db_path = DATA_DIR / "products.db"
    
    if not db_path.exists():
        log_test("数据库文件存在", False, "products.db 不存在")
        return False
    
    log_test("数据库文件存在", True, f"{db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='products'")
        if not cursor.fetchone():
            log_test("products 表存在", False, "表不存在")
            conn.close()
            return False
        log_test("products 表存在", True, "表存在")
        
        # 检查表结构
        cursor.execute("PRAGMA table_info(products)")
        columns = {row[1]: {"type": row[2], "notnull": row[3], "default": row[4]} for row in cursor.fetchall()}
        
        # 契约要求的字段
        required_columns = {
            'id': 'INTEGER',
            'product_id': 'TEXT',
            'title': 'TEXT',
            'price_min': 'REAL',
            'price_max': 'REAL',
            'sales': 'INTEGER',
            'supplier_name': 'TEXT',
            'supplier_level': 'TEXT',
            'product_url': 'TEXT',
            'main_image_url': 'TEXT',
            'thumbnail_urls': 'TEXT',
            'collected_at': 'DATETIME',
            'is_latest': 'BOOLEAN',
            'created_at': 'DATETIME',
            'updated_at': 'DATETIME'
        }
        
        missing_columns = [c for c in required_columns if c not in columns]
        if missing_columns:
            log_test("字段完整性", False, f"缺少字段：{missing_columns}")
            log_bug("BUG_US03_001", "数据库字段缺失", "高",
                   "检查数据库表结构",
                   f"包含所有字段：{list(required_columns.keys())}",
                   f"缺少字段：{missing_columns}",
                   "影响数据存储和查询功能")
            conn.close()
            return False
        log_test("字段完整性", True, f"所有 {len(required_columns)} 个字段存在")
        
        # 检查 is_latest 默认值
        if columns['is_latest']['default'] != '1':
            log_test("is_latest 默认值", False, f"默认值应为 1，实际：{columns['is_latest']['default']}")
            conn.close()
            return False
        log_test("is_latest 默认值", True, "默认值为 1")
        
        # 检查联合唯一约束
        cursor.execute("PRAGMA index_list(products)")
        indexes = cursor.fetchall()
        
        # 查找唯一约束
        has_unique_constraint = False
        for idx in indexes:
            cursor.execute(f"PRAGMA index_info({idx[1]})")
            index_info = cursor.fetchall()
            index_columns = [info[2] for info in index_info]
            if 'product_id' in index_columns and 'collected_at' in index_columns:
                has_unique_constraint = True
                break
        
        if not has_unique_constraint:
            log_test("联合唯一约束", False, "未找到 product_id + collected_at 联合唯一约束")
            log_bug("BUG_US03_002", "缺少联合唯一约束", "高",
                   "检查数据库索引",
                   "UNIQUE(product_id, collected_at) 约束",
                   "未找到联合唯一约束",
                   "可能导致重复数据")
            conn.close()
            return False
        log_test("联合唯一约束", True, "product_id + collected_at 联合唯一约束已配置")
        
        # 检查索引
        expected_indexes = ['idx_product_id', 'idx_is_latest', 'idx_collected_at']
        index_names = [idx[1] for idx in indexes]
        
        missing_indexes = [idx for idx in expected_indexes if idx not in index_names]
        if missing_indexes:
            log_test("索引完整性", False, f"缺少索引：{missing_indexes}")
            conn.close()
            return False
        log_test("索引完整性", True, f"所有索引已创建：{expected_indexes}")
        
        # 检查记录数
        cursor.execute("SELECT COUNT(*) FROM products")
        count = cursor.fetchone()[0]
        log_test("数据记录数", True, f"{count} 条记录")
        
        conn.close()
        return True
        
    except Exception as e:
        log_test("数据库 Schema 验证", False, f"验证异常：{e}")
        return False


# ============================================================
# 测试 2: 单次任务内去重验证
# ============================================================
def test_deduplication_within_task():
    """测试 2: 验证单次任务内去重功能"""
    print("\n" + "=" * 60)
    print("测试 2: 单次任务内去重验证")
    print("=" * 60)
    
    db_path = DATA_DIR / "products.db"
    
    if not db_path.exists():
        log_test("数据库存在", False, "products.db 不存在")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 查询是否有重复的 product_id 在同一 collected_at 时间
        cursor.execute("""
            SELECT product_id, collected_at, COUNT(*) as cnt
            FROM products
            GROUP BY product_id, collected_at
            HAVING cnt > 1
        """)
        duplicates = cursor.fetchall()
        
        if duplicates:
            log_test("单次任务去重", False, f"发现 {len(duplicates)} 组重复记录")
            for dup in duplicates[:3]:
                log_bug("BUG_US03_003", "单次任务内数据重复", "高",
                       f"检查 product_id={dup[0]}, collected_at={dup[1]}",
                       "同一 collected_at 时间不应有重复 product_id",
                       f"发现 {dup[2]} 条重复记录",
                       "影响数据准确性")
            conn.close()
            return False
        
        log_test("单次任务去重", True, "无重复记录，去重功能正常")
        
        # 验证去重逻辑：检查是否有相同 product_id 但不同 collected_at 的记录（这是允许的，用于历史追踪）
        cursor.execute("""
            SELECT product_id, COUNT(*) as cnt
            FROM products
            GROUP BY product_id
            HAVING cnt > 1
        """)
        historical_records = cursor.fetchall()
        
        if historical_records:
            log_test("历史记录保留", True, f"{len(historical_records)} 个商品有多条历史记录（符合预期）")
        else:
            log_test("历史记录保留", True, "暂无历史重复商品（正常）")
        
        conn.close()
        return True
        
    except Exception as e:
        log_test("去重验证", False, f"验证异常：{e}")
        return False


# ============================================================
# 测试 3: is_latest 标记验证
# ============================================================
def test_is_latest_flag():
    """测试 3: 验证 is_latest 标记正确性"""
    print("\n" + "=" * 60)
    print("测试 3: is_latest 标记验证")
    print("=" * 60)
    
    db_path = DATA_DIR / "products.db"
    
    if not db_path.exists():
        log_test("数据库存在", False, "products.db 不存在")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查 is_latest 字段值
        cursor.execute("SELECT DISTINCT is_latest FROM products")
        is_latest_values = [row[0] for row in cursor.fetchall()]
        
        # 验证 is_latest 只能是 0 或 1
        invalid_values = [v for v in is_latest_values if v not in [0, 1]]
        if invalid_values:
            log_test("is_latest 值有效性", False, f"发现无效值：{invalid_values}")
            conn.close()
            return False
        log_test("is_latest 值有效性", True, "所有值为 0 或 1")
        
        # 检查每个 product_id 是否只有一个 is_latest=1 的记录
        cursor.execute("""
            SELECT product_id, COUNT(*) as cnt
            FROM products
            WHERE is_latest = 1
            GROUP BY product_id
            HAVING cnt > 1
        """)
        multiple_latest = cursor.fetchall()
        
        if multiple_latest:
            log_test("is_latest 唯一性", False, f"{len(multiple_latest)} 个商品有多个 is_latest=1 的记录")
            for ml in multiple_latest[:3]:
                log_bug("BUG_US03_004", "is_latest 标记重复", "高",
                       f"检查 product_id={ml[0]}",
                       "每个商品只能有一个 is_latest=1 的记录",
                       f"发现 {ml[1]} 条 is_latest=1 的记录",
                       "影响最新数据查询")
            conn.close()
            return False
        log_test("is_latest 唯一性", True, "每个商品只有一个 is_latest=1 的记录")
        
        # 检查有历史记录的 product_id，是否旧记录的 is_latest=0
        cursor.execute("""
            SELECT product_id, COUNT(*) as cnt
            FROM products
            GROUP BY product_id
            HAVING cnt > 1
        """)
        historical_products = cursor.fetchall()
        
        if historical_products:
            for hp in historical_products:
                cursor.execute("""
                    SELECT COUNT(*) FROM products
                    WHERE product_id = ? AND is_latest = 0
                """, (hp[0],))
                old_count = cursor.fetchone()[0]
                expected_old = hp[1] - 1  # 除了最新的，其他都应该是 0
                
                if old_count != expected_old:
                    log_test("历史记录 is_latest", False, 
                            f"product_id={hp[0]}: 期望 {expected_old} 条 is_latest=0，实际 {old_count}")
                    conn.close()
                    return False
            
            log_test("历史记录 is_latest", True, 
                    f"{len(historical_products)} 个商品的历史记录 is_latest 标记正确")
        else:
            log_test("历史记录 is_latest", True, "暂无历史记录商品（正常）")
        
        # 统计 is_latest 分布
        cursor.execute("SELECT is_latest, COUNT(*) FROM products GROUP BY is_latest")
        distribution = cursor.fetchall()
        log_test("is_latest 分布", True, 
                f"is_latest=1: {dict(distribution).get(1, 0)}条, is_latest=0: {dict(distribution).get(0, 0)}条")
        
        conn.close()
        return True
        
    except Exception as e:
        log_test("is_latest 验证", False, f"验证异常：{e}")
        return False


# ============================================================
# 测试 4: JSONL 备份验证
# ============================================================
def test_jsonl_backup():
    """测试 4: 验证 JSONL 备份文件"""
    print("\n" + "=" * 60)
    print("测试 4: JSONL 备份验证")
    print("=" * 60)
    
    if not DATA_DIR.exists():
        log_test("数据目录", False, "data 目录不存在")
        return False
    
    jsonl_files = list(DATA_DIR.glob("*.jsonl"))
    
    if not jsonl_files:
        log_test("JSONL 文件存在", False, "未找到 JSONL 备份文件")
        log_bug("BUG_US03_005", "缺少 JSONL 备份", "中",
               "检查 data 目录",
               "应有 products_*.jsonl 文件",
               "未找到任何 JSONL 文件",
               "影响数据备份和恢复")
        return False
    
    log_test("JSONL 文件存在", True, f"找到 {len(jsonl_files)} 个 JSONL 文件")
    
    try:
        # 验证第一个 JSONL 文件
        with open(jsonl_files[0], 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        if len(lines) == 0:
            log_test("JSONL 数据", False, "JSONL 文件为空")
            return False
        
        log_test("JSONL 记录数", True, f"{len(lines)} 条记录")
        
        # 验证每条记录包含 is_latest 字段
        missing_is_latest = 0
        for i, line in enumerate(lines):
            record = json.loads(line)
            if 'is_latest' not in record:
                missing_is_latest += 1
        
        if missing_is_latest > 0:
            log_test("JSONL is_latest 字段", False, f"{missing_is_latest} 条记录缺少 is_latest 字段")
            log_bug("BUG_US03_006", "JSONL 缺少 is_latest 字段", "中",
                   f"检查 {jsonl_files[0]}",
                   "所有 JSONL 记录应包含 is_latest 字段",
                   f"{missing_is_latest} 条记录缺失",
                   "影响 JSONL 数据查询")
            return False
        
        log_test("JSONL is_latest 字段", True, "所有记录包含 is_latest 字段")
        
        # 验证 JSONL 字段完整性
        required_fields = [
            'product_id', 'title', 'price_min', 'price_max', 'sales',
            'supplier_name', 'supplier_level', 'product_url', 'main_image_url',
            'thumbnail_urls', 'collected_at', 'is_latest'
        ]
        
        first_record = json.loads(lines[0])
        missing_fields = [f for f in required_fields if f not in first_record]
        
        if missing_fields:
            log_test("JSONL 字段完整性", False, f"缺少字段：{missing_fields}")
            return False
        
        log_test("JSONL 字段完整性", True, f"所有 {len(required_fields)} 个字段存在")
        
        return True
        
    except json.JSONDecodeError as e:
        log_test("JSONL 格式", False, f"JSON 解析失败：{e}")
        log_bug("BUG_US03_007", "JSONL 格式错误", "高",
               f"检查 {jsonl_files[0]}",
               "有效的 JSON 格式",
               f"解析失败：{e}",
               "影响数据读取")
        return False
    except Exception as e:
        log_test("JSONL 验证", False, f"验证异常：{e}")
        return False


# ============================================================
# 测试 5: 查询最新数据功能验证
# ============================================================
def test_query_latest_products():
    """测试 5: 验证查询最新数据功能"""
    print("\n" + "=" * 60)
    print("测试 5: 查询最新数据功能验证")
    print("=" * 60)
    
    db_path = DATA_DIR / "products.db"
    
    if not db_path.exists():
        log_test("数据库存在", False, "products.db 不存在")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 查询最新产品
        cursor.execute("SELECT * FROM products WHERE is_latest = 1")
        latest_products = cursor.fetchall()
        
        if len(latest_products) == 0:
            log_test("最新产品查询", False, "未找到 is_latest=1 的产品")
            conn.close()
            return False
        
        log_test("最新产品查询", True, f"查询到 {len(latest_products)} 个最新产品")
        
        # 验证查询结果包含关键字段
        cursor.execute("PRAGMA table_info(products)")
        columns = [row[1] for row in cursor.fetchall()]
        
        # 验证第一条记录
        if len(latest_products) > 0:
            first_product = latest_products[0]
            log_test("查询结果数据", True, 
                    f"示例：product_id={first_product[1]}, title={first_product[2][:20]}...")
        
        # 验证：查询最新产品的数量应该等于不同 product_id 的数量
        cursor.execute("SELECT COUNT(DISTINCT product_id) FROM products")
        distinct_products = cursor.fetchone()[0]
        
        # 注意：这里 latest_products 数量应该 <= distinct_products
        # 因为有些 product_id 可能只有历史记录（is_latest=0）
        if len(latest_products) > distinct_products:
            log_test("最新产品数量", False, 
                    f"最新产品数 {len(latest_products)} > 不同商品数 {distinct_products}")
            conn.close()
            return False
        
        log_test("最新产品数量", True, 
                f"{len(latest_products)} 个最新产品 / {distinct_products} 个总商品")
        
        conn.close()
        return True
        
    except Exception as e:
        log_test("查询功能验证", False, f"验证异常：{e}")
        return False


# ============================================================
# 测试 6: 数据合理性验证
# ============================================================
def test_data_validity():
    """测试 6: 验证数据合理性"""
    print("\n" + "=" * 60)
    print("测试 6: 数据合理性验证")
    print("=" * 60)
    
    db_path = DATA_DIR / "products.db"
    
    if not db_path.exists():
        log_test("数据库存在", False, "products.db 不存在")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查价格合理性
        cursor.execute("SELECT COUNT(*) FROM products WHERE price_min < 0 OR price_max < 0")
        negative_price = cursor.fetchone()[0]
        
        if negative_price > 0:
            log_test("价格合理性", False, f"{negative_price} 条记录价格为负数")
            log_bug("BUG_US03_008", "价格为负数", "中",
                   "检查 products 表",
                   "价格应为非负数",
                   f"{negative_price} 条记录价格为负",
                   "影响数据分析")
            conn.close()
            return False
        
        log_test("价格合理性", True, "所有价格非负")
        
        # 检查 price_min <= price_max
        cursor.execute("SELECT COUNT(*) FROM products WHERE price_min > price_max")
        price_inverted = cursor.fetchone()[0]
        
        if price_inverted > 0:
            log_test("价格区间合理性", False, f"{price_inverted} 条记录 price_min > price_max")
            log_bug("BUG_US03_009", "价格区间颠倒", "中",
                   "检查 products 表",
                   "price_min 应 <= price_max",
                   f"{price_inverted} 条记录价格区间颠倒",
                   "影响数据分析")
            conn.close()
            return False
        
        log_test("价格区间合理性", True, "所有价格区间正确")
        
        # 检查销量合理性
        cursor.execute("SELECT COUNT(*) FROM products WHERE sales < 0")
        negative_sales = cursor.fetchone()[0]
        
        if negative_sales > 0:
            log_test("销量合理性", False, f"{negative_sales} 条记录销量为负数")
            conn.close()
            return False
        
        log_test("销量合理性", True, "所有销量非负")
        
        # 检查 URL 格式
        cursor.execute("SELECT COUNT(*) FROM products WHERE product_url NOT LIKE 'http%'")
        invalid_url = cursor.fetchone()[0]
        
        if invalid_url > 0:
            log_test("URL 格式", False, f"{invalid_url} 条记录 URL 格式错误")
            conn.close()
            return False
        
        log_test("URL 格式", True, "所有 URL 格式正确")
        
        # 统计信息
        cursor.execute("SELECT MIN(price_min), MAX(price_max), AVG(sales) FROM products WHERE is_latest = 1")
        stats = cursor.fetchone()
        log_test("数据统计", True, 
                f"最新产品价格：{stats[0]}-{stats[1]} 元，平均销量：{stats[2]:.0f}")
        
        conn.close()
        return True
        
    except Exception as e:
        log_test("数据合理性验证", False, f"验证异常：{e}")
        return False


# ============================================================
# 主测试流程
# ============================================================
def main():
    """执行所有 QA 测试"""
    print("=" * 60)
    print("🧪 1688 商品爬虫 - US_03 QA 验收测试")
    print("=" * 60)
    print(f"测试人员：少锋 (QA)")
    print(f"测试时间：{datetime.now().isoformat()}")
    print(f"测试依据：US_03_DataStorage.json v1.0")
    print("=" * 60)
    
    tests = [
        ("数据库 Schema 验证", test_database_schema),
        ("单次任务内去重", test_deduplication_within_task),
        ("is_latest 标记验证", test_is_latest_flag),
        ("JSONL 备份验证", test_jsonl_backup),
        ("查询最新数据功能", test_query_latest_products),
        ("数据合理性验证", test_data_validity),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"\n❌ {name} 测试异常：{e}")
            results.append((name, False))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("📊 QA 测试结果汇总")
    print("=" * 60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{status} - {name}")
    
    print("-" * 60)
    print(f"总计：{passed}/{total} 测试通过")
    print(f"发现 Bug 数：{len(bug_list)}")
    
    # 生成测试结论
    if passed == total and len(bug_list) == 0:
        conclusion = "✅ 通过 - 所有测试用例通过，无 Bug"
        status_code = 0
    elif passed == total:
        conclusion = "⚠️ 通过 - 主要功能通过，存在轻微问题"
        status_code = 0
    else:
        conclusion = "❌ 不通过 - 需要修复后重新测试"
        status_code = 1
    
    print(f"\n测试结论：{conclusion}")
    
    # 输出 Bug 列表
    if bug_list:
        print("\n" + "=" * 60)
        print("🐛 Bug 列表")
        print("=" * 60)
        for bug in bug_list:
            print(f"\n【{bug['bug_id']}】{bug['title']}")
            print(f"  严重等级：{bug['severity']}")
            print(f"  复现步骤：{bug['steps']}")
            print(f"  期望结果：{bug['expected']}")
            print(f"  实际结果：{bug['actual']}")
            if bug.get('impact'):
                print(f"  影响范围：{bug['impact']}")
    
    return status_code


if __name__ == '__main__':
    sys.exit(main())
