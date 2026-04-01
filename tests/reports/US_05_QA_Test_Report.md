# US_05 日志与异常处理 - QA 测试报告

> 项目：1688 商品爬虫开发 - 选品分析工具  
> 任务 ID: T_US_05  
> 执行者：少锋 (QA)  
> 测试日期：2026-04-01  
> 契约版本：US_05_Logging.json v1.0

---

## 📋 测试概况

| 项目 | 内容 |
|------|------|
| 测试时间 | 2026-04-01 20:41 UTC |
| 测试人员 | 少锋 (QA) |
| 测试类型 | 集成测试 + 功能验证 |
| 测试依据 | US_05_Logging.json v1.0 |
| 测试脚本 | `/tests/qa_test_us05.py` |

---

## 📊 测试结果汇总

| 测试项 | 结果 | 说明 |
|--------|------|------|
| 独立日志文件（按日期命名） | ✅ 通过 | 日志文件命名格式：crawler_YYYYMMDD.log |
| 日志包含 INFO、WARNING、ERROR 级别 | ✅ 通过 | 4 个级别全部支持（DEBUG, INFO, WARNING, ERROR） |
| 网络异常时自动重试（最多 3 次） | ✅ 通过 | 指数退避 + 随机抖动策略 |
| 页面结构变化时记录详细错误信息 | ✅ 通过 | URL + 错误信息 + HTML 片段 |
| 日志输出到文件同时也在控制台显示 | ✅ 通过 | 双 Handler 配置 |
| 验证码检测日志 | ✅ 通过 | 包含 URL 和建议 |
| 日志格式验证 | ✅ 通过 | 格式：`%(asctime)s - %(name)s - %(levelname)s - %(message)s` |

**总计：7/7 测试通过**

---

## ✅ 验收标准验证

### 1. 独立日志文件（按日期命名）

**测试结果**: ✅ 通过

**验证**:
- 日志目录：`/backend/logs/`
- 文件命名：`crawler_YYYYMMDD.log`
- 文件编码：UTF-8
- 日志轮转：按天轮转

---

### 2. 日志包含 INFO、WARNING、ERROR 级别

**测试结果**: ✅ 通过

**验证**:
| 级别 | 说明 | 验证结果 |
|------|------|----------|
| DEBUG | 详细调试信息，用于开发 | ✅ |
| INFO | 正常流程信息，如开始抓取、已完成数量 | ✅ |
| WARNING | 可恢复异常，如代理失败、跳过商品 | ✅ |
| ERROR | 严重错误，如网络中断、解析失败 | ✅ |

---

### 3. 网络异常时自动重试（最多 3 次）

**测试结果**: ✅ 通过

**重试策略**:
- 最大重试次数：3 次
- 延迟策略：指数退避 + 随机抖动
- 延迟计算：`base_delay * (2 ** (attempt - 1)) + random.uniform(0, 2)`

**验证场景**:
- ✅ 重试成功：尝试 3 次后成功
- ✅ 重试失败：尝试 3 次后放弃并抛出异常

---

### 4. 页面结构变化时记录详细错误信息

**测试结果**: ✅ 通过

**记录信息**:
- ✅ URL
- ✅ 错误信息
- ✅ HTML 片段（前 200 字符）

**示例日志**:
```
2026-04-01 20:41:00 - 1688Crawler - ERROR - 页面解析失败:
2026-04-01 20:41:00 - 1688Crawler - ERROR -   URL: https://detail.1688.com/offer/123456.html
2026-04-01 20:41:00 - 1688Crawler - ERROR -   错误：Unable to find product price
2026-04-01 20:41:00 - 1688Crawler - ERROR -   HTML 片段：<html><body><div>测试页面</div></body></html>...
```

---

### 5. 日志输出到文件同时也在控制台显示

**测试结果**: ✅ 通过

**配置**:
- 文件 Handler：记录所有级别（DEBUG 及以上）
- 控制台 Handler：只记录 INFO 及以上

**验证**:
- ✅ 控制台输出：实时显示日志
- ✅ 文件输出：保存到 `logs/crawler_YYYYMMDD.log`

---

### 6. 验证码检测日志

**测试结果**: ✅ 通过

**记录信息**:
- ✅ 验证码检测警告
- ✅ URL
- ✅ 建议：使用代理或降低请求频率

**示例日志**:
```
2026-04-01 20:41:12 - 1688Crawler - WARNING - ⚠️ 检测到验证码!
2026-04-01 20:41:12 - 1688Crawler - WARNING -   URL: https://detail.1688.com/offer/789012.html
2026-04-01 20:41:12 - 1688Crawler - WARNING -   建议：使用代理或降低请求频率
```

---

### 7. 日志格式

**测试结果**: ✅ 通过

**格式**: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`

**示例**:
```
2026-04-01 20:41:12 - 1688Crawler - INFO - QA 测试 - 格式验证
```

---

## 📁 交付清单

- [x] `/backend/logger.py` - 日志管理模块
  - `CrawlerLogger` 类：日志管理器
  - `RetryHandler` 类：重试处理器
  - `log_parse_error()`: 解析错误日志
  - `log_captcha_detected()`: 验证码检测日志
- [x] `/backend/logs/` - 日志目录
- [x] `/backend/logs/crawler_YYYYMMDD.log` - 日志文件
- [x] `/tests/qa_test_us05.py` - QA 验收测试脚本
- [x] `/tests/reports/US_05_QA_Test_Report.md` - QA 测试报告（本文档）

---

## 🔧 使用方法

### 1. 创建日志管理器

```python
from logger import CrawlerLogger

# 创建日志管理器
logger = CrawlerLogger(log_dir='./logs', level='INFO')

# 记录日志
logger.info("开始抓取...")
logger.debug(f"请求 URL: {url}")
logger.warning("代理失败，切换备用代理")
logger.error("网络中断", exc_info=True)
```

### 2. 使用重试处理器

```python
from logger import RetryHandler

# 创建重试处理器
retry_handler = RetryHandler(max_retries=3, base_delay=5.0, logger=logger)

# 执行可能失败的函数
def fetch_url(url):
    response = requests.get(url)
    response.raise_for_status()
    return response.text

# 自动重试
try:
    html = retry_handler.execute_with_retry(fetch_url, url)
except Exception as e:
    logger.error(f"最终失败：{e}")
```

### 3. 记录解析错误

```python
from logger import log_parse_error

try:
    price = parse_price(html)
except Exception as e:
    log_parse_error(logger, url, html[:200], str(e))
```

### 4. 验证码检测

```python
from logger import log_captcha_detected

if is_captcha(html):
    log_captcha_detected(logger, url)
    # 暂停或切换代理
```

---

## 📝 测试结论

**US_05 日志与异常处理功能已完成**，所有验收标准通过：

- ✅ 独立日志文件（按日期命名）
- ✅ 多级别日志支持（DEBUG, INFO, WARNING, ERROR）
- ✅ 网络异常自动重试（最多 3 次，指数退避）
- ✅ 详细错误信息记录（URL + 错误 + HTML 片段）
- ✅ 双输出（文件 + 控制台）
- ✅ 验证码检测日志
- ✅ 标准日志格式

**测试统计**:
- 总测试用例：7
- 通过：7
- 失败：0
- 通过率：100%

**状态建议**: `[TODO]` → `[DONE]`

---

*报告生成时间：2026-04-01 20:41 UTC*  
*执行者：少锋（质量保障工程师）*  
*测试结论：✅ 通过 - 所有测试用例通过，无 Bug*
