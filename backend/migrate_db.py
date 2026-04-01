#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本：添加 is_latest 字段

迁移内容：
- 为 products 表添加 is_latest 列（INTEGER，默认值 1）
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "products.db"


def migrate():
    """执行数据库迁移"""
    if not DB_PATH.exists():
        print(f"❌ 数据库文件不存在：{DB_PATH}")
        return False
    
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # 检查 is_latest 列是否已存在
    cursor.execute("PRAGMA table_info(products)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'is_latest' in columns:
        print("✅ is_latest 列已存在，无需迁移")
        conn.close()
        return True
    
    # 添加 is_latest 列
    try:
        cursor.execute('''
            ALTER TABLE products
            ADD COLUMN is_latest INTEGER DEFAULT 1
        ''')
        conn.commit()
        print("✅ 成功添加 is_latest 列")
        
        # 验证
        cursor.execute("PRAGMA table_info(products)")
        columns = [col[1] for col in cursor.fetchall()]
        print(f"📋 当前表结构：{columns}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 迁移失败：{e}")
        conn.close()
        return False


if __name__ == '__main__':
    success = migrate()
    exit(0 if success else 1)
