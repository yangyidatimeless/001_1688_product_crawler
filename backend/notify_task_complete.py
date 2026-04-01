#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
发送开发任务完成通知到飞书群聊

使用方式:
python notify_task_complete.py "项目名称" "任务 ID" "任务描述" "自测报告链接"
"""

import json
import sys
import requests

# 飞书 Webhook URL（需要替换为实际的 webhook 地址）
# 注意：这里使用群聊 ID 方式发送，需要飞书机器人权限
WEBHOOK_URL = "https://open.feishu.cn/open-apis/bot/v2/hook/YOUR_WEBHOOK_TOKEN"

# 群聊 ID（从 DEV_TASK_RULE.md 中获取）
CHAT_ID = "oc_8b44573aa0c9854f370d68cfdc78af67"


def send_feishu_message(title: str, content: str):
    """
    发送飞书消息
    
    Args:
        title: 消息标题
        content: 消息内容（Markdown 格式）
    """
    # 构建消息体（使用交互式卡片）
    message = {
        "msg_type": "interactive",
        "card": {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "template": "green",
                "title": {
                    "content": title,
                    "tag": "plain_text"
                }
            },
            "elements": [
                {
                    "tag": "markdown",
                    "content": content
                }
            ]
        }
    }
    
    try:
        response = requests.post(WEBHOOK_URL, json=message)
        result = response.json()
        
        if result.get('code') == 0:
            print("✅ 飞书通知发送成功")
            return True
        else:
            print(f"❌ 飞书通知发送失败：{result}")
            return False
            
    except Exception as e:
        print(f"❌ 发送异常：{e}")
        return False


def main():
    if len(sys.argv) < 5:
        print("用法：python notify_task_complete.py <项目名称> <任务 ID> <任务描述> <自测报告链接>")
        sys.exit(1)
    
    project_name = sys.argv[1]
    task_id = sys.argv[2]
    task_description = sys.argv[3]
    self_test_report = sys.argv[4]
    
    # 构建通知内容
    title = f"【开发任务完成】{project_name} - T_{task_id}"
    
    content = f"""👤 **执行者**：允灿
📋 **任务**：{task_description}
✅ **状态**：已完成，等待 QA 验收
📄 **自测报告**：{self_test_report}

---
🚀 US_02 反爬策略实现完成：
- ✅ User-Agent 轮换（7 个 UA）
- ✅ 请求频率限制（2-5 秒）
- ✅ 代理池集成
- ✅ 验证码检测与处理
- ✅ 代理失败自动切换"""
    
    # 发送通知
    success = send_feishu_message(title, content)
    
    if success:
        print("\n" + "=" * 50)
        print("📢 工作通知已发送")
        print("=" * 50)
        print(f"项目名称：{project_name}")
        print(f"任务 ID: T_{task_id}")
        print(f"任务描述：{task_description}")
        print(f"自测报告：{self_test_report}")
        print("=" * 50)
    else:
        print("\n⚠️  通知发送失败，请检查 Webhook 配置")
        sys.exit(1)


if __name__ == "__main__":
    main()
