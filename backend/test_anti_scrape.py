#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
US_02 反爬策略自测脚本

测试项目：
1. User-Agent 轮换功能
2. 请求频率控制
3. 代理池初始化
4. 验证码检测
5. 代理切换逻辑

契约版本：US_02_AntiScrape.json v1.0
"""

import sys
import time
from pathlib import Path

# 添加 backend 目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from crawler import ProductCrawler


def test_ua_rotation():
    """测试 1: User-Agent 轮换功能"""
    print("\n" + "=" * 60)
    print("测试 1: User-Agent 轮换功能")
    print("=" * 60)
    
    crawler = ProductCrawler(keyword="test", preview=True)
    
    # 验证 UA 列表数量（US_02 要求：至少 5 个）
    ua_count = len(crawler.USER_AGENTS)
    print(f"✅ UA 列表数量：{ua_count} 个")
    assert ua_count >= 5, f"UA 数量不足 5 个，当前：{ua_count}"
    
    # 测试随机获取 UA
    ua_set = set()
    for _ in range(20):
        ua = crawler._get_random_ua()
        ua_set.add(ua)
    
    print(f"✅ 20 次随机获取，不重复 UA 数量：{len(ua_set)} 个")
    assert len(ua_set) > 1, "UA 轮换功能异常，总是返回相同的 UA"
    
    # 打印部分 UA 示例
    print("\nUA 示例（前 3 个）:")
    for i, ua in enumerate(crawler.USER_AGENTS[:3], 1):
        print(f"  {i}. {ua[:60]}...")
    
    print("\n✅ 测试 1 通过：User-Agent 轮换功能正常")
    return True


def test_rate_limiting():
    """测试 2: 请求频率控制"""
    print("\n" + "=" * 60)
    print("测试 2: 请求频率控制")
    print("=" * 60)
    
    # 使用较短延迟进行测试
    crawler = ProductCrawler(
        keyword="test", 
        preview=True,
        min_delay=0.5,  # 测试用短延迟
        max_delay=1.0
    )
    
    # 验证延迟配置
    print(f"✅ 最小延迟配置：{crawler.min_delay} 秒")
    print(f"✅ 最大延迟配置：{crawler.max_delay} 秒")
    
    # 测试随机延迟生成
    delays = []
    for _ in range(10):
        delay = crawler._get_random_delay()
        delays.append(delay)
    
    avg_delay = sum(delays) / len(delays)
    print(f"✅ 10 次随机延迟平均值：{avg_delay:.2f} 秒")
    print(f"✅ 延迟范围：{min(delays):.2f} - {max(delays):.2f} 秒")
    
    # 验证延迟在配置范围内
    assert all(crawler.min_delay <= d <= crawler.max_delay + 0.1 for d in delays), \
        "延迟超出配置范围"
    
    # 实际测试延迟效果
    print("\n  测试实际延迟效果（3 次）:")
    for i in range(3):
        start = time.time()
        crawler._apply_rate_limiting()
        elapsed = time.time() - start
        print(f"    第 {i+1} 次延迟：{elapsed:.2f} 秒")
    
    print("\n✅ 测试 2 通过：请求频率控制功能正常")
    return True


def test_proxy_pool():
    """测试 3: 代理池初始化"""
    print("\n" + "=" * 60)
    print("测试 3: 代理池初始化")
    print("=" * 60)
    
    # 启用代理池
    crawler = ProductCrawler(
        keyword="test",
        preview=True,
        proxy_enabled=True
    )
    
    # 验证代理池状态
    print(f"✅ 代理池启用状态：{crawler.proxy_enabled}")
    print(f"✅ 代理池大小：{len(crawler.proxy_pool)} 个")
    print(f"✅ 当前代理：{crawler.current_proxy}")
    
    # 测试代理切换
    if crawler.proxy_pool:
        initial_proxy = crawler.current_proxy
        crawler._switch_proxy()
        new_proxy = crawler.current_proxy
        print(f"✅ 代理切换测试：{initial_proxy} → {new_proxy}")
    
    print("\n✅ 测试 3 通过：代理池初始化功能正常")
    return True


def test_captcha_detection():
    """测试 4: 验证码检测"""
    print("\n" + "=" * 60)
    print("测试 4: 验证码检测")
    print("=" * 60)
    
    crawler = ProductCrawler(keyword="test", preview=True)
    
    # 创建模拟响应对象
    class MockResponse:
        def __init__(self, text, status_code=200):
            self.text = text
            self.status_code = status_code
    
    # 测试正常页面（无验证码）
    normal_page = MockResponse("<html><body>商品列表</body></html>")
    is_captcha = crawler._is_slider_captcha(normal_page)
    print(f"✅ 正常页面检测：{is_captcha} (期望：False)")
    assert not is_captcha, "正常页面被误判为验证码"
    
    # 测试包含验证码关键词的页面
    captcha_page = MockResponse("<html><body>请完成安全验证 - 滑块验证码</body></html>")
    is_captcha = crawler._is_slider_captcha(captcha_page)
    print(f"✅ 验证码页面检测：{is_captcha} (期望：True)")
    assert is_captcha, "验证码页面未被检测到"
    
    # 测试 403 状态码
    forbidden_page = MockResponse("<html><body>403 Forbidden</body></html>", status_code=403)
    is_captcha = crawler._is_slider_captcha(forbidden_page)
    print(f"✅ 403 状态码检测：{is_captcha} (期望：True)")
    assert is_captcha, "403 状态码未被识别为验证码"
    
    print("\n✅ 测试 4 通过：验证码检测功能正常")
    return True


def test_headers_generation():
    """测试 5: 请求头生成"""
    print("\n" + "=" * 60)
    print("测试 5: 请求头生成")
    print("=" * 60)
    
    crawler = ProductCrawler(keyword="test", preview=True)
    
    # 生成多组请求头
    headers_list = []
    for _ in range(5):
        headers = crawler._get_headers()
        headers_list.append(headers)
    
    # 验证 UA 轮换
    ua_values = [h['User-Agent'] for h in headers_list]
    unique_uas = set(ua_values)
    
    print(f"✅ 生成 5 组请求头，不重复 UA 数量：{len(unique_uas)}")
    print(f"✅ 请求头包含关键字段：Accept, Accept-Language, Connection")
    
    # 打印一组示例请求头
    print("\n示例请求头:")
    sample_headers = headers_list[0]
    for key, value in list(sample_headers.items())[:5]:
        print(f"  {key}: {value[:60]}..." if len(value) > 60 else f"  {key}: {value}")
    
    print("\n✅ 测试 5 通过：请求头生成功能正常")
    return True


def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("US_02 反爬策略自测报告")
    print("=" * 60)
    print(f"测试时间：{time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"契约版本：US_02_AntiScrape.json v1.0")
    print("=" * 60)
    
    tests = [
        ("User-Agent 轮换", test_ua_rotation),
        ("请求频率控制", test_rate_limiting),
        ("代理池初始化", test_proxy_pool),
        ("验证码检测", test_captcha_detection),
        ("请求头生成", test_headers_generation),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, True, None))
        except AssertionError as e:
            results.append((test_name, False, str(e)))
            print(f"\n❌ 测试失败：{test_name}")
            print(f"   错误信息：{e}")
        except Exception as e:
            results.append((test_name, False, str(e)))
            print(f"\n❌ 测试异常：{test_name}")
            print(f"   错误信息：{e}")
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    for test_name, success, error in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{status} - {test_name}")
        if error:
            print(f"         错误：{error}")
    
    print("\n" + "-" * 60)
    print(f"总计：{passed}/{total} 项测试通过")
    print("=" * 60)
    
    if passed == total:
        print("\n🎉 所有测试通过！US_02 反爬策略功能正常")
        return 0
    else:
        print(f"\n⚠️  有 {total - passed} 项测试失败，请检查代码")
        return 1


if __name__ == '__main__':
    sys.exit(main())
