# 浏览器启动修复 - 技术设计

## Context

### 当前状态

项目使用 DrissionPage 4.1.1.2 库进行网页抓取，当前 `BossScraper` 类在 `scraper.py` 中初始化浏览器时：

1. **现有实现** (scraper.py:10-19):
   - 仅使用 `ChromiumOptions` 配置远程调试端口 (9222)
   - 假设用户已手动启动 Chrome 浏览器并带上 `--remote-debugging-port=9222` 参数
   - 如果浏览器未运行，`ChromiumPage(co)` 会直接失败
   - 没有回退机制或错误恢复

2. **配置管理** (config.py:19):
   - `CHROME_PORT = 9222` 硬编码在 Config 类中
   - 没有其他浏览器相关配置选项

3. **使用方式** (routers/scraper.py:46):
   - 在后台任务中直接实例化 `BossScraper()`
   - 如果浏览器未启动，整个爬虫任务失败

### 约束条件

1. **向后兼容性**: 必须保持现有 API 端点 `/scrape` 的功能不变
2. **依赖限制**: 只能使用 DrissionPage 库，不能引入新的浏览器自动化库
3. **环境差异**: 需要支持 Windows 开发环境和服务器环境
4. **用户体验**: 不应强制要求用户手动启动浏览器

### 利益相关者

- 开发者: 需要简化的开发流程，不需要每次手动启动浏览器
- 运维人员: 需要在服务器环境中以无头模式运行
- 最终用户: 爬虫应该自动启动，无需额外操作

## Goals / Non-Goals

**Goals:**
- 实现自动启动 Chrome 浏览器的功能，消除手动启动浏览器的前提条件
- 支持连接到已存在的浏览器实例（可选行为）
- 提供配置选项控制浏览器启动行为
- 支持无头模式以适应服务器环境
- 改善错误信息和日志记录
- 管理浏览器生命周期（自动启动的浏览器在完成时关闭）

**Non-Goals:**
- 不支持其他浏览器（Firefox, Edge 等），仅支持 Chrome/Chromium
- 不实现浏览器进程池或并发浏览器管理
- 不修改 DrissionPage 库本身
- 不改变爬虫的核心抓取逻辑

## Decisions

### 1. 浏览器初始化策略

**决策**: 采用"先连接，后启动"的渐进式策略

**理由**:
- **向后兼容**: 优先连接到现有浏览器，保持当前用户的工作流
- **用户体验**: 如果连接失败，自动启动浏览器，减少用户干预
- **灵活性**: 通过配置可以禁用自动启动，保留手动控制选项

**实现**:
```
1. 尝试连接到配置端口的浏览器
2. 如果连接成功 → 记录为"已连接"模式
3. 如果连接失败且 BROWSER_AUTO_LAUNCH=True → 启动新浏览器，记录为"已启动"模式
4. 如果连接失败且 BROWSER_AUTO_LAUNCH=False → 抛出异常
```

**替代方案考虑**:
- ❌ **仅启动新浏览器**: 会破坏现有用户的工作流（手动启动浏览器）
- ❌ **仅连接现有浏览器**: 无法解决核心问题（浏览器未启动）

### 2. 浏览器可用性检测

**决策**: 使用端口检测 + DrissionPage 异常捕获的双重确认

**理由**:
- **快速失败**: 端口检测可以快速判断浏览器是否运行
- **准确性**: DrissionPage 异常可以确认浏览器是否真正可用
- **兼容性**: 不依赖特定平台的进程检测工具

**实现**:
```python
import socket

def is_browser_available(port: int) -> bool:
    """检测指定端口是否有浏览器在监听"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex(('127.0.0.1', port))
            return result == 0
    except Exception:
        return False
```

**替代方案考虑**:
- ❌ **仅依赖 DrissionPage 异常**: 慢，且异常信息不够明确
- ❌ **进程名称检测**: 跨平台兼容性差（Windows vs Linux）

### 3. 浏览器启动方法

**决策**: 使用 DrissionPage 的 `ChromiumPage` 直接启动，不使用子进程

**理由**:
- **简单性**: DrissionPage 内置浏览器启动功能，无需额外代码
- **集成性**: 自动处理浏览器进程和调试端口配置
- **可控性**: 可以通过 ChromiumOptions 配置所有启动参数

**实现**:
```python
co = ChromiumOptions()
co.set_argument(f'--remote-debugging-port={Config.CHROME_PORT}')
if Config.BROWSER_HEADLESS:
    co.set_argument('--headless')
    co.set_argument('--disable-gpu')
    co.set_argument('--no-sandbox')
if Config.BROWSER_EXECUTABLE_PATH:
    co.set_browser_path(Config.BROWSER_EXECUTABLE_PATH)

# DrissionPage 会自动启动浏览器
self.page = ChromiumPage(co)
```

**替代方案考虑**:
- ❌ **使用 subprocess 启动 Chrome**: 需要手动管理进程、PID、清理等，复杂度高
- ❌ **使用 selenium webdriver**: 会引入新的依赖，增加项目复杂度

### 4. 生命周期管理

**决策**: 使用标志位跟踪浏览器来源，实现差异化清理

**理由**:
- **资源管理**: 自动启动的浏览器应该被清理，避免僵尸进程
- **用户期望**: 已存在的浏览器不应该被关闭
- **安全性**: 防止意外关闭用户正在使用的浏览器

**实现**:
```python
class BossScraper:
    def __init__(self):
        self._auto_launched = False  # 标志位
        # ... 初始化逻辑

    def __del__(self):
        if self._auto_launched and hasattr(self, 'page'):
            self.page.quit()
```

**替代方案考虑**:
- ❌ **总是关闭浏览器**: 会关闭用户手动启动的浏览器
- ❌ **从不关闭浏览器**: 会导致僵尸进程累积

### 5. 配置管理

**决策**: 添加新的配置项到 Config 类，使用环境变量覆盖

**理由**:
- **灵活性**: 不同环境可以有不同配置
- **安全性**: 敏感路径不硬编码
- **一致性**: 与现有配置模式一致（使用 dotenv）

**新增配置项**:
```python
# Config.py
BROWSER_AUTO_LAUNCH = True          # 默认自动启动
BROWSER_HEADLESS = False            # 默认有界面
BROWSER_EXECUTABLE_PATH = None      # 使用系统默认 Chrome
```

**环境变量映射**:
```env
BROWSER_AUTO_LAUNCH=true
BROWSER_HEADLESS=false
BROWSER_EXECUTABLE_PATH="C:\Program Files\Chrome\chrome.exe"
```

### 6. 错误处理和日志

**决策**: 分层错误处理 + 结构化日志

**理由**:
- **可调试性**: 详细日志帮助快速定位问题
- **用户友好**: 错误消息包含解决方案
- **可维护性**: 结构化日志便于日志分析工具处理

**日志级别**:
- INFO: 正常初始化（连接/启动成功）
- WARNING: 回退操作（连接失败，尝试启动）
- ERROR: 初始化完全失败

**错误消息格式**:
```python
raise BrowserInitializationError(
    f"Failed to initialize browser. "
    f"Attempted: connection to port {Config.CHROME_PORT}, launch: {Config.BROWSER_AUTO_LAUNCH}. "
    f"Reason: {error}. "
    f"Solution: {'Start Chrome with --remote-debugging-port=9222' if not Config.BROWSER_AUTO_LAUNCH else 'Check Chrome installation'}"
)
```

## Risks / Trade-offs

### Risk 1: 端口冲突
**描述**: 配置的调试端口可能被其他应用占用

**缓解措施**:
- 在浏览器启动前验证端口可用性
- 提供配置选项允许更改端口号
- 错误消息中明确提示端口冲突问题

### Risk 2: Chrome 未安装或路径异常
**描述**: 服务器环境可能没有安装 Chrome 或安装路径不标准

**缓解措施**:
- 支持通过 `BROWSER_EXECUTABLE_PATH` 指定路径
- 错误消息包含 Chrome 下载链接
- 文档中说明 Chrome 安装要求

### Risk 3: 无头模式兼容性问题
**描述**: 某些网站在无头模式下可能行为异常

**缓解措施**:
- 默认不启用无头模式
- 提供明确的配置选项
- 文档中说明无头模式的限制

### Risk 4: 资源泄漏
**描述**: 如果爬虫异常退出，浏览器进程可能未被清理

**缓解措施**:
- 使用 `try-finally` 和 `__del__` 确保清理
- 提供手动清理端点或工具
- 日志中记录浏览器进程 PID

### Trade-off 1: 启动时间 vs 可靠性
**选择**: 优先连接现有浏览器（更快），失败后才启动新浏览器

**权衡**: 可能增加 1-2 秒的连接尝试时间，但提供更好的用户体验

### Trade-off 2: 配置复杂度 vs 灵活性
**选择**: 提供多个配置选项（AUTO_LAUNCH, HEADLESS, EXECUTABLE_PATH）

**权衡**: 增加了配置复杂度，但提供了适应不同环境的能力

## Migration Plan

### 部署步骤

1. **Phase 1: 添加配置**
   - 更新 `config.py`，添加新的配置项
   - 更新 `.env.example` 文件，添加示例配置
   - 默认值保持向后兼容（AUTO_LAUNCH=True）

2. **Phase 2: 重构 BossScraper**
   - 创建辅助函数 `is_browser_available()`
   - 创建辅助函数 `launch_browser()`
   - 更新 `BossScraper.__init__()` 实现新逻辑
   - 添加 `__del__()` 方法处理清理

3. **Phase 3: 增强错误处理**
   - 定义自定义异常类 `BrowserInitializationError`
   - 更新日志格式
   - 添加更详细的错误消息

4. **Phase 4: 测试**
   - 本地测试：自动启动模式
   - 本地测试：连接现有浏览器模式
   - 服务器测试：无头模式
   - 错误场景测试：端口冲突、Chrome 未安装

5. **Phase 5: 文档更新**
   - 更新 README.md，说明新的配置选项
   - 添加故障排除部分
   - 更新部署指南

### 回滚策略

如果新实现出现问题：

1. **快速回滚**: 将 `BROWSER_AUTO_LAUNCH` 设置为 `False`，恢复为仅连接模式
2. **代码回滚**: 保留旧代码作为注释，可以快速恢复
3. **配置迁移**: 新配置项都有默认值，旧配置文件无需修改

### 兼容性保证

- ✅ 现有 API 端点 `/scrape` 完全兼容
- ✅ 现有环境变量不受影响
- ✅ 手动启动浏览器的用户不受影响（优先连接）
- ✅ 不会强制关闭用户已打开的浏览器

## Open Questions

1. **问题**: 是否需要在 API 端点中暴露浏览器状态？

   **状态**: 待决定
   **影响**: 如果暴露，可以添加 `/browser/status` 端点返回浏览器是否运行

2. **问题**: 是否支持配置多个调试端口尝试？

   **状态**: 不支持（当前设计）
   **理由**: 增加复杂度，使用场景不多

3. **问题**: 浏览器启动失败时是否应该重试？

   **状态**: 不重试（当前设计）
   **理由**: 启动失败通常是配置问题，重试无意义，快速失败更好

4. **问题**: 是否需要支持浏览器配置文件（user profile）？

   **状态**: 不支持（当前设计）
   **理由**: 爬虫不需要保持浏览器状态，使用临时配置文件即可
