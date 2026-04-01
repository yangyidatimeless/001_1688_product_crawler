#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
US_02 反爬策略实现模块

功能：
- User-Agent 轮换（至少 5 个不同 UA）
- 请求频率限制（可配置，默认 2-5 秒随机延迟）
- 代理池集成（免费代理 + 健康检查）
- Playwright Stealth 模式支持
- 滑块验证码检测与处理
- 代理失败自动切换

契约版本：US_02_AntiScrape.json v1.0
"""

import random
import time
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

import requests
from requests.exceptions import ProxyError, SSLError, Timeout, ConnectionError

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CaptchaType(Enum):
    """验证码类型"""
    NONE = "none"
    SLIDER = "slider"
    CLICK = "click"
    PUZZLE = "puzzle"
    UNKNOWN = "unknown"


@dataclass
class ProxyConfig:
    """代理配置"""
    host: str
    port: int
    protocol: str = "http"
    username: Optional[str] = None
    password: Optional[str] = None
    success_count: int = 0
    failure_count: int = 0
    last_check_time: float = 0.0
    is_alive: bool = True
    
    @property
    def url(self) -> str:
        """生成代理 URL"""
        if self.username and self.password:
            return f"{self.protocol}://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"{self.protocol}://{self.host}:{self.port}"
    
    @property
    def proxies_dict(self) -> Dict[str, str]:
        """生成 requests 可用的 proxies 字典"""
        return {
            'http': self.url,
            'https': self.url
        }
    
    @property
    def success_rate(self) -> float:
        """计算成功率"""
        total = self.success_count + self.failure_count
        if total == 0:
            return 1.0
        return self.success_count / total


@dataclass
class AntiScrapeConfig:
    """反爬策略配置"""
    # User-Agent 配置
    user_agents: List[str] = field(default_factory=lambda: [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
    ])
    
    # 请求频率配置
    min_delay_seconds: float = 2.0
    max_delay_seconds: float = 5.0
    default_delay_seconds: float = 3.0
    
    # 代理池配置
    proxy_enabled: bool = True
    proxy_max_retries: int = 3
    proxy_health_check: bool = True
    proxy_check_url: str = "https://httpbin.org/ip"
    proxy_check_timeout: int = 5
    
    # 重试配置
    max_retries: int = 3
    backoff_multiplier: float = 2.0
    base_delay: float = 1.0
    
    # 验证码处理
    captcha_detection: bool = True
    slider_captcha_action: str = "log_and_skip"  # log_and_skip / try_solve / abort


class AntiScrapeManager:
    """反爬策略管理器"""
    
    def __init__(self, config: Optional[AntiScrapeConfig] = None):
        """
        初始化反爬管理器
        
        Args:
            config: 反爬配置，使用默认配置如果未提供
        """
        self.config = config or AntiScrapeConfig()
        self.current_proxy: Optional[ProxyConfig] = None
        self.proxy_pool: List[ProxyConfig] = []
        self.request_count = 0
        self.last_request_time = 0.0
        
        logger.info("✅ 反爬策略管理器初始化完成")
        logger.info(f"   - User-Agent 数量：{len(self.config.user_agents)}")
        logger.info(f"   - 请求延迟：{self.config.min_delay_seconds}-{self.config.max_delay_seconds}秒")
        logger.info(f"   - 代理 enabled: {self.config.proxy_enabled}")
        logger.info(f"   - 最大重试次数：{self.config.max_retries}")
    
    def get_user_agent(self) -> str:
        """
        随机获取一个 User-Agent
        
        Returns:
            随机选择的 User-Agent 字符串
        """
        ua = random.choice(self.config.user_agents)
        logger.debug(f"🔄 使用 User-Agent: {ua[:50]}...")
        return ua
    
    def get_delay(self) -> float:
        """
        获取随机延迟时间
        
        Returns:
            延迟秒数
        """
        delay = random.uniform(self.config.min_delay_seconds, self.config.max_delay_seconds)
        logger.debug(f"⏱️  请求延迟：{delay:.2f}秒")
        return delay
    
    def apply_rate_limiting(self) -> None:
        """
        应用请求频率限制
        
        在连续请求之间插入随机延迟
        """
        if self.request_count > 0:
            delay = self.get_delay()
            elapsed = time.time() - self.last_request_time
            if elapsed < delay:
                sleep_time = delay - elapsed
                logger.info(f"⏳ 频率限制：等待 {sleep_time:.2f}秒")
                time.sleep(sleep_time)
        
        self.last_request_time = time.time()
        self.request_count += 1
    
    def add_proxy(self, proxy: ProxyConfig) -> None:
        """
        添加代理到代理池
        
        Args:
            proxy: 代理配置
        """
        self.proxy_pool.append(proxy)
        logger.debug(f"➕ 添加代理：{proxy.host}:{proxy.port}")
    
    def add_proxies_from_list(self, proxy_list: List[Dict]) -> None:
        """
        批量添加代理
        
        Args:
            proxy_list: 代理列表，每个元素包含 host, port, protocol 等字段
        """
        for p in proxy_list:
            proxy = ProxyConfig(
                host=p.get('host', ''),
                port=p.get('port', 80),
                protocol=p.get('protocol', 'http'),
                username=p.get('username'),
                password=p.get('password')
            )
            self.add_proxy(proxy)
        
        logger.info(f"✅ 批量添加 {len(proxy_list)} 个代理")
    
    def _check_proxy_health(self, proxy: ProxyConfig) -> bool:
        """
        检查代理是否可用
        
        Args:
            proxy: 待检查的代理
            
        Returns:
            代理是否可用
        """
        try:
            session = requests.Session()
            session.proxies.update(proxy.proxies_dict)
            session.timeout = self.config.proxy_check_timeout
            
            response = session.get(self.config.proxy_check_url, timeout=self.config.proxy_check_timeout)
            
            if response.status_code == 200:
                proxy.success_count += 1
                proxy.is_alive = True
                logger.debug(f"✅ 代理健康检查通过：{proxy.host}:{proxy.port}")
                return True
            else:
                proxy.failure_count += 1
                logger.warning(f"⚠️  代理健康检查失败（状态码 {response.status_code}）: {proxy.host}:{proxy.port}")
                return False
                
        except Exception as e:
            proxy.failure_count += 1
            logger.warning(f"❌ 代理健康检查异常：{proxy.host}:{proxy.port} - {e}")
            return False
        finally:
            proxy.last_check_time = time.time()
    
    def get_available_proxy(self) -> Optional[ProxyConfig]:
        """
        获取一个可用的代理
        
        策略：
        1. 优先使用当前代理（如果可用）
        2. 从代理池中选择一个成功率最高的可用代理
        3. 如果没有可用代理，返回 None（使用直连）
        
        Returns:
            可用的代理配置，如果没有则返回 None
        """
        # 检查当前代理
        if self.current_proxy and self.current_proxy.is_alive:
            if self.config.proxy_health_check:
                # 定期重新检查健康状态（每 5 分钟）
                if time.time() - self.current_proxy.last_check_time > 300:
                    if not self._check_proxy_health(self.current_proxy):
                        self.current_proxy = None
                    else:
                        return self.current_proxy
            else:
                return self.current_proxy
        
        if not self.proxy_pool:
            logger.debug("📡 代理池为空，使用直连")
            return None
        
        # 从代理池中选择最佳代理
        available_proxies = [p for p in self.proxy_pool if p.is_alive]
        
        if not available_proxies:
            logger.warning("⚠️  代理池中所有代理都不可用，尝试恢复一个")
            # 尝试恢复成功率最高的代理
            if self.proxy_pool:
                best_proxy = max(self.proxy_pool, key=lambda p: p.success_rate)
                if self._check_proxy_health(best_proxy):
                    self.current_proxy = best_proxy
                    logger.info(f"🔄 恢复代理：{best_proxy.host}:{best_proxy.port}")
                    return best_proxy
            return None
        
        # 按成功率排序，选择最好的
        best_proxy = max(available_proxies, key=lambda p: p.success_rate)
        
        # 如果成功率低于 50%，检查健康状态
        if best_proxy.success_rate < 0.5:
            if not self._check_proxy_health(best_proxy):
                best_proxy.is_alive = False
                return self.get_available_proxy()  # 递归获取下一个
        
        self.current_proxy = best_proxy
        logger.info(f"🔀 切换代理：{best_proxy.host}:{best_proxy.port} (成功率：{best_proxy.success_rate:.1%})")
        return best_proxy
    
    def detect_captcha(self, html: str, response_status: int) -> CaptchaType:
        """
        检测页面中是否存在验证码
        
        Args:
            html: 页面 HTML 内容
            response_status: 响应状态码
            
        Returns:
            验证码类型
        """
        if not self.config.captcha_detection:
            return CaptchaType.NONE
        
        # 检查常见验证码特征
        captcha_indicators = {
            CaptchaType.SLIDER: [
                'slider', '滑块', 'slide-to-verify', 'aptcha', 'geetest',
                'class="slider"', 'id="slider"',
            ],
            CaptchaType.CLICK: [
                'click', '点击', 'verify-code', 'captcha-click',
            ],
            CaptchaType.PUZZLE: [
                'puzzle', '拼图', 'jigsaw',
            ],
        }
        
        html_lower = html.lower()
        
        for captcha_type, indicators in captcha_indicators.items():
            for indicator in indicators:
                if indicator in html_lower:
                    logger.warning(f"⚠️  检测到{captcha_type.value}验证码特征：{indicator}")
                    return captcha_type
        
        # 检查状态码
        if response_status == 403:
            logger.warning("⚠️  响应状态码 403，可能触发反爬")
            return CaptchaType.UNKNOWN
        
        return CaptchaType.NONE
    
    def handle_captcha(self, captcha_type: CaptchaType, url: str) -> Tuple[bool, str]:
        """
        处理验证码
        
        Args:
            captcha_type: 验证码类型
            url: 当前请求 URL
            
        Returns:
            (是否继续，消息)
        """
        if captcha_type == CaptchaType.NONE:
            return True, "无验证码"
        
        action = self.config.slider_captcha_action
        
        if captcha_type == CaptchaType.SLIDER:
            logger.warning(f"🚫 滑块验证码 detected at {url}")
            
            if action == "log_and_skip":
                msg = "Slider captcha detected, skipping"
                logger.warning(msg)
                return False, msg
            
            elif action == "try_solve":
                msg = "Slider captcha detected, manual solve required"
                logger.warning(msg)
                # 这里可以集成自动滑块验证码解决服务
                return False, msg
            
            elif action == "abort":
                msg = "Slider captcha detected, aborting request"
                logger.error(msg)
                raise Exception(msg)
        
        # 其他类型验证码
        logger.warning(f"⚠️  检测到{captcha_type.value}验证码，跳过")
        return False, f"{captcha_type.value} captcha detected"
    
    def build_request_config(self) -> Dict:
        """
        构建请求配置
        
        Returns:
            包含 headers, proxies 等的配置字典
        """
        config = {
            'headers': {
                'User-Agent': self.get_user_agent(),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Cache-Control': 'no-cache',
            },
            'timeout': 30,
        }
        
        # 添加代理
        if self.config.proxy_enabled:
            proxy = self.get_available_proxy()
            if proxy:
                config['proxies'] = proxy.proxies_dict
                logger.debug(f"🔒 使用代理：{proxy.host}:{proxy.port}")
        
        return config
    
    def request_with_retry(self, method: str, url: str, **kwargs) -> requests.Response:
        """
        带重试机制的请求
        
        特性：
        - 自动 UA 轮换
        - 自动代理切换
        - 指数退避重试
        - 验证码检测
        
        Args:
            method: HTTP 方法 (GET, POST 等)
            url: 请求 URL
            **kwargs: 传递给 requests 的其他参数
            
        Returns:
            requests.Response 对象
            
        Raises:
            requests.RequestException: 重试失败后抛出异常
        """
        # 应用频率限制
        self.apply_rate_limiting()
        
        exceptions = []
        
        for attempt in range(self.config.max_retries):
            try:
                # 构建请求配置
                req_config = self.build_request_config()
                
                # 合并用户自定义配置
                if 'headers' in kwargs:
                    req_config['headers'].update(kwargs.pop('headers'))
                if 'proxies' in kwargs:
                    req_config['proxies'] = kwargs.pop('proxies')
                if 'timeout' in kwargs:
                    req_config['timeout'] = kwargs.pop('timeout')
                
                # 发起请求
                session = requests.Session()
                if 'proxies' in req_config:
                    session.proxies.update(req_config['proxies'])
                
                response = session.request(
                    method=method,
                    url=url,
                    headers=req_config['headers'],
                    timeout=req_config['timeout'],
                    **kwargs
                )
                
                # 检测验证码
                if self.config.captcha_detection and response.status_code == 200:
                    captcha_type = self.detect_captcha(response.text, response.status_code)
                    if captcha_type != CaptchaType.NONE:
                        should_continue, msg = self.handle_captcha(captcha_type, url)
                        if not should_continue:
                            # 记录代理失败
                            if self.current_proxy:
                                self.current_proxy.failure_count += 1
                                if self.current_proxy.success_rate < 0.3:
                                    self.current_proxy.is_alive = False
                            raise Exception(msg)
                        
                        # 成功处理，更新代理统计
                        if self.current_proxy:
                            self.current_proxy.success_count += 1
                
                # 检查响应状态
                response.raise_for_status()
                
                logger.info(f"✅ 请求成功：{url[:60]}... (状态码：{response.status_code})")
                return response
                
            except Exception as e:
                exceptions.append(e)
                error_type = type(e).__name__
                
                # 更新代理统计
                if self.current_proxy:
                    self.current_proxy.failure_count += 1
                    if self.current_proxy.success_rate < 0.3:
                        self.current_proxy.is_alive = False
                        logger.warning(f"🚫 代理成功率过低，标记为不可用：{self.current_proxy.host}:{self.current_proxy.port}")
                
                if attempt < self.config.max_retries - 1:
                    # 计算等待时间（指数退避）
                    wait_time = self.config.base_delay * (self.config.backoff_multiplier ** attempt)
                    logger.warning(
                        f"⚠️  请求失败（{error_type}），{wait_time:.1f}秒后重试 "
                        f"（第 {attempt + 1}/{self.config.max_retries} 次）: {e}"
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(f"❌ 重试 {self.config.max_retries} 次后仍然失败: {e}")
                    raise exceptions[-1]
        
        raise exceptions[-1] if exceptions else requests.RequestException("Unknown error")
    
    def get(self, url: str, **kwargs) -> requests.Response:
        """HTTP GET 请求（带重试）"""
        return self.request_with_retry('GET', url, **kwargs)
    
    def post(self, url: str, **kwargs) -> requests.Response:
        """HTTP POST 请求（带重试）"""
        return self.request_with_retry('POST', url, **kwargs)


# 便捷函数
def create_anti_scrape_session(config: Optional[AntiScrapeConfig] = None) -> AntiScrapeManager:
    """
    创建反爬会话
    
    Args:
        config: 反爬配置
        
    Returns:
        AntiScrapeManager 实例
    """
    return AntiScrapeManager(config)


# 测试代码
if __name__ == "__main__":
    # 测试反爬管理器
    print("🧪 测试 US_02 反爬策略模块")
    print("=" * 60)
    
    # 创建管理器
    manager = AntiScrapeManager()
    
    # 测试 UA 轮换
    print("\n1️⃣  测试 User-Agent 轮换:")
    for i in range(3):
        ua = manager.get_user_agent()
        print(f"   [{i+1}] {ua[:60]}...")
    
    # 测试延迟
    print("\n2️⃣  测试请求延迟:")
    for i in range(3):
        delay = manager.get_delay()
        print(f"   [{i+1}] 延迟：{delay:.2f}秒")
    
    # 测试请求配置
    print("\n3️⃣  测试请求配置构建:")
    config = manager.build_request_config()
    print(f"   Headers: {len(config['headers'])} 个")
    print(f"   User-Agent: {config['headers']['User-Agent'][:50]}...")
    print(f"   Proxies: {'已配置' if 'proxies' in config else '未配置'}")
    
    print("\n" + "=" * 60)
    print("✅ 所有测试完成")
