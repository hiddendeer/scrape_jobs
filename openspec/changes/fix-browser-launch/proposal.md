# 修复浏览器启动问题

## Why

爬虫项目使用 DrissionPage 库连接到 Chrome 浏览器进行网页数据抓取。当前配置使用 `--remote-debugging-port=9222` 参数连接到已存在的浏览器实例，但启动时没有自动打开新的浏览器窗口，导致爬虫无法正常工作。这个问题阻止了整个爬虫系统的正常运行。

## What Changes

- **修改浏览器连接策略**: 添加自动启动新浏览器实例的功能，而不是仅依赖已存在的浏览器
- **增加配置选项**: 允许用户选择是连接到现有浏览器还是启动新浏览器
- **改进错误处理**: 当无法连接到现有浏览器时，自动回退到启动新浏览器
- **添加浏览器状态检测**: 在启动爬虫前检测浏览器是否已运行
- **增强日志记录**: 记录浏览器启动/连接的详细过程，便于问题排查

## Capabilities

### New Capabilities
- `browser-launcher`: 浏览器启动和连接管理功能，包括自动启动、连接检测、错误恢复等

### Modified Capabilities
- `scraper-core`: 修改 BossScraper 类的初始化逻辑，支持多种浏览器连接方式

## Impact

**受影响的代码**:
- `scraper.py`: BossScraper 类的 `__init__` 方法需要重构
- `config.py`: 添加新的配置项（如 BROWSER_AUTO_LAUNCH, BROWSER_HEADLESS 等）
- `routers/scraper.py`: 可能需要调整错误处理逻辑

**依赖项**:
- DrissionPage 4.1.1.2 (已安装，支持浏览器启动功能)

**API 兼容性**:
- `/scrape` 端点保持向后兼容
- 添加可选的配置参数，不影响现有调用方式
