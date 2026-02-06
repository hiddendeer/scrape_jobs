# 浏览器启动修复 - 回滚指南

## 快速回滚步骤

如果新实现出现问题，可以按以下步骤快速回滚：

### 选项 1: 配置回滚（推荐）

1. 在 `.env` 文件中设置：
   ```
   BROWSER_AUTO_LAUNCH=false
   ```

2. 重启应用

3. 手动启动 Chrome 浏览器：
   ```bash
   # Windows
   "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222

   # Linux
   google-chrome --remote-debugging-port=9222

   # macOS
   /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222
   ```

### 选项 2: 代码回滚

如果需要完全恢复到旧实现：

```bash
# 恢复备份文件
cp scraper.py.backup scraper.py
cp config.py.backup config.py

# 重启应用
```

## 回滚检查清单

- [ ] 停止当前运行的应用
- [ ] 执行回滚操作（配置回滚或代码回滚）
- [ ] 验证配置文件已正确修改/恢复
- [ ] 启动 Chrome 浏览器（如果使用配置回滚）
- [ ] 重启应用
- [ ] 测试爬虫功能是否正常
- [ ] 检查日志确认没有错误

## 已备份文件

- `scraper.py.backup` - 原始 scraper.py 文件
- `config.py.backup` - 原始 config.py 文件

## 回滚后验证

1. 检查应用日志，确认浏览器连接成功
2. 触发一次测试爬取
3. 验证数据正确保存到数据库
4. 确认没有浏览器相关的错误信息

## 联系支持

如果回滚后仍有问题，请检查：
1. Chrome 浏览器版本是否兼容
2. 端口 9222 是否被其他程序占用
3. DrissionPage 库版本是否正确
