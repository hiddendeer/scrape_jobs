# 浏览器启动修复 - 实施任务清单

## 1. 配置管理

- [x] 1.1 在 `config.py` 中添加 `BROWSER_AUTO_LAUNCH` 配置项（默认值: True）
- [x] 1.2 在 `config.py` 中添加 `BROWSER_HEADLESS` 配置项（默认值: False）
- [x] 1.3 在 `config.py` 中添加 `BROWSER_EXECUTABLE_PATH` 配置项（默认值: None）
- [x] 1.4 创建或更新 `.env.example` 文件，添加新的浏览器配置示例
- [x] 1.5 验证所有配置项可以从环境变量正确读取

## 2. 辅助函数和异常类

- [x] 2.1 创建自定义异常类 `BrowserInitializationError`，继承自 Exception
- [x] 2.2 实现 `is_browser_available(port: int) -> bool` 函数，使用 socket 检测端口
- [x] 2.3 在 `is_browser_available` 中添加超时处理（1秒超时）
- [x] 2.4 添加异常捕获，确保函数在出错时返回 False
- [ ] 2.5 为辅助函数添加单元测试

## 3. BossScraper 类重构

- [x] 3.1 在 `BossScraper.__init__()` 中添加 `self._auto_launched = False` 标志位
- [x] 3.2 实现浏览器可用性检测逻辑：调用 `is_browser_available()`
- [x] 3.3 实现连接逻辑：如果浏览器可用，尝试连接到现有浏览器
- [x] 3.4 实现自动启动逻辑：如果浏览器不可用且 `BROWSER_AUTO_LAUNCH=True`，启动新浏览器
- [x] 3.5 实现配置逻辑：根据 `BROWSER_HEADLESS` 和 `BROWSER_EXECUTABLE_PATH` 配置 ChromiumOptions
- [x] 3.6 在成功启动浏览器后设置 `self._auto_launched = True`
- [x] 3.7 添加详细的日志记录（INFO 级别：连接/启动成功）
- [x] 3.8 添加 WARNING 级别日志：连接失败，尝试启动

## 4. ChromiumOptions 配置增强

- [x] 4.1 保留现有的 `--remote-debugging-port` 配置
- [x] 4.2 添加条件逻辑：当 `BROWSER_HEADLESS=True` 时，设置 `--headless` 参数
- [x] 4.3 添加条件逻辑：当 `BROWSER_HEADLESS=True` 时，设置 `--disable-gpu` 参数
- [x] 4.4 添加条件逻辑：当 `BROWSER_HEADLESS=True` 时，设置 `--no-sandbox` 参数
- [x] 4.5 添加条件逻辑：当 `BROWSER_EXECUTABLE_PATH` 有值时，调用 `set_browser_path()`
- [x] 4.6 验证自定义可执行路径是否存在（如果配置了）

## 5. 错误处理和日志

- [x] 5.1 更新 `BossScraper.__init__()` 中的异常处理逻辑
- [x] 5.2 当连接失败且 `BROWSER_AUTO_LAUNCH=False` 时，抛出 `BrowserInitializationError`
- [x] 5.3 当启动失败时，捕获异常并抛出 `BrowserInitializationError`，附带详细错误信息
- [x] 5.4 在错误消息中包含：调试端口号、是否尝试启动、失败原因、解决方案
- [x] 5.5 添加 ERROR 级别日志记录初始化完全失败的情况
- [x] 5.6 确保所有异常消息都是用户友好的，包含可操作的解决步骤

## 6. 生命周期管理

- [x] 6.1 在 `BossScraper` 类中实现 `__del__()` 方法
- [x] 6.2 在 `__del__()` 中检查 `self._auto_launched` 标志位
- [x] 6.3 如果 `self._auto_launched=True` 且 `self.page` 存在，调用 `self.page.quit()`
- [x] 6.4 添加日志记录浏览器清理操作
- [x] 6.5 使用 `try-except` 包裹清理逻辑，避免在 `__del__` 中抛出异常
- [x] 6.6 考虑添加显式的 `close()` 方法供用户主动调用

## 7. 测试 - 本地开发环境

- [ ] 7.1 测试场景：手动启动浏览器后运行爬虫（连接模式）
- [ ] 7.2 测试场景：不启动浏览器，直接运行爬虫（自动启动模式）
- [ ] 7.3 验证自动启动的浏览器在爬虫结束后被正确关闭
- [ ] 7.4 验证手动启动的浏览器在爬虫结束后保持运行
- [ ] 7.5 检查日志输出，确认包含所有必要的初始化信息
- [ ] 7.6 测试 `BROWSER_AUTO_LAUNCH=False` 配置，验证浏览器未启动时抛出异常

## 8. 测试 - 无头模式

- [ ] 8.1 设置 `BROWSER_HEADLESS=True` 配置
- [ ] 8.2 运行爬虫，验证浏览器以无头模式启动
- [ ] 8.3 验证所有抓取功能在无头模式下正常工作
- [ ] 8.4 检查系统任务管理器，确认没有可见的 Chrome 窗口
- [ ] 8.5 验证无头浏览器在完成后被正确清理

## 9. 测试 - 错误场景

- [ ] 9.1 测试场景：配置的端口被其他程序占用
- [ ] 9.2 测试场景：Chrome 未安装（设置错误的 `BROWSER_EXECUTABLE_PATH`）
- [ ] 9.3 测试场景：`BROWSER_EXECUTABLE_PATH` 指向不存在的文件
- [ ] 9.4 验证所有错误场景都抛出 `BrowserInitializationError`
- [ ] 9.5 验证错误消息包含有用的调试信息和解决方案
- [ ] 9.6 测试异常恢复：配置修复后可以正常运行

## 10. 代码质量和重构

- [x] 10.1 检查 `scraper.py` 代码，确保符合项目编码规范
- [x] 10.2 为新增的辅助函数添加类型注解
- [x] 10.3 为新增的辅助函数添加文档字符串
- [x] 10.4 为 `BossScraper.__init__()` 和 `__del__()` 添加详细注释
- [x] 10.5 确保没有硬编码值（端口、路径等都从配置读取）
- [ ] 10.6 运行代码格式化工具（black 或类似工具）
- [ ] 10.7 运行代码检查工具（pylint 或类似工具）

## 11. 文档更新

- [x] 11.1 更新 README.md，添加新的配置选项说明
- [x] 11.2 在 README.md 中添加"浏览器配置"部分
- [x] 11.3 添加故障排除（Troubleshooting）部分
- [x] 11.4 说明无头模式的使用场景和限制
- [x] 11.5 添加 Chrome 安装要求说明
- [x] 11.6 更新部署指南，包含服务器环境配置示例
- [x] 11.7 提供 `.env` 配置示例

## 12. 集成验证

- [ ] 12.1 运行完整的爬虫流程，验证从 API 调用到数据存储的全过程
- [ ] 12.2 测试 `/scrape` 端点，验证向后兼容性
- [ ] 12.3 测试多城市爬取功能，验证浏览器重用是否正常
- [ ] 12.4 验证后台任务的错误处理逻辑
- [ ] 12.5 进行端到端测试：启动服务 → 触发爬虫 → 验证数据
- [ ] 12.6 检查日志文件，确认日志格式和级别正确

## 13. 回滚和应急准备

- [x] 13.1 备份当前的 `scraper.py` 文件
- [x] 13.2 备份当前的 `config.py` 文件
- [x] 13.3 准备快速回滚脚本或命令
- [x] 13.4 记录回滚步骤（设置 `BROWSER_AUTO_LAUNCH=False`）
- [ ] 13.5 测试回滚流程，确保可以快速恢复到旧实现
- [x] 13.6 创建回滚检查清单

## 14. 性能验证

- [ ] 14.1 测量浏览器启动时间（自动启动模式）
- [ ] 14.2 测量浏览器连接时间（连接现有浏览器模式）
- [ ] 14.3 验证内存使用情况，确保无内存泄漏
- [ ] 14.4 运行长时间爬取任务，验证稳定性
- [ ] 14.5 对比新旧实现的性能差异
- [ ] 14.6 记录性能指标作为基线
