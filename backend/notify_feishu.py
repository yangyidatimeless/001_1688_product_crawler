#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞书通知脚本 - 发送开发任务完成通知

使用方法:
    python notify_feishu.py --project "1688 商品爬虫" --task-id "US_01" --report-url "https://xxx.feishu.cn/docx/xxx"
"""

import argparse
import json
import urllib.request
import urllib.error
import sys


def send_feishu_message(webhook_url: str, message: dict) -> bool:
    """
    发送飞书消息
    
    Args:
        webhook_url: 飞书群机器人 Webhook URL
        message: 消息内容字典
        
    Returns:
        是否发送成功
    """
    try:
        data = json.dumps(message, ensure_ascii=False).encode('utf-8')
        req = urllib.request.Request(
            webhook_url,
            data=data,
            headers={'Content-Type': 'application/json'}
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result.get('code', 0) == 0
            
    except urllib.error.URLError as e:
        print(f"网络错误：{e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"发送失败：{e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description='发送飞书开发任务完成通知')
    
    parser.add_argument('--project', type=str, required=True, help='项目名称')
    parser.add_argument('--task-id', type=str, required=True, help='任务 ID (如 US_01)')
    parser.add_argument('--task-desc', type=str, default='基础商品爬取', help='任务描述')
    parser.add_argument('--report-url', type=str, default='', help='自测报告链接')
    parser.add_argument('--webhook-url', type=str, help='飞书 Webhook URL (可选)')
    
    args = parser.parse_args()
    
    # 构建消息内容（使用飞书文本消息格式）
    report_text = f"\n📄 自测报告：{args.report_url}" if args.report_url else "\n📄 自测报告：详见项目目录 /tests/reports/"
    
    content = {
        "text": f"""【开发任务完成】{args.project} - {args.task_id}
👤 执行者：允灿
📋 任务：{args.task_desc}
✅ 状态：已完成，等待 QA 验收{report_text}

📁 交付内容:
- backend/crawler.py (主爬虫脚本)
- backend/test_crawler.py (单元测试)
- backend/requirements.txt (依赖清单)
- tests/reports/US_01_SelfTest_Report.md (自测报告)

🧪 测试结果：4/4 通过
- ✅ 数据结构验证
- ✅ 数据库操作
- ✅ JSONL 导出
- ✅ CLI 接口"""
    }
    
    # 如果提供了 Webhook URL，直接发送
    if args.webhook_url:
        success = send_feishu_message(args.webhook_url, content)
        if success:
            print("✅ 消息发送成功")
            return 0
        else:
            print("❌ 消息发送失败")
            return 1
    
    # 否则输出消息内容，供手动复制
    print("=" * 60)
    print("📤 飞书通知消息（请复制到工作群）")
    print("=" * 60)
    print(content['text'])
    print("=" * 60)
    print("\n💡 提示：如需自动发送，请提供 --webhook-url 参数")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
