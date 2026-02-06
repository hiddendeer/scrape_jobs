# 爬取某聘数据

基于 FastAPI 的后端项目，使用 DrissionPage 从 Boss Zhipin 爬取职位数据并存储到 MySQL 数据库中

## 浏览器配置

项目支持自动启动 Chrome 浏览器，无需手动启动。可以通过 `.env` 文件配置浏览器行为：

```env
# 浏览器配置
# 自动启动浏览器（默认：true）
BROWSER_AUTO_LAUNCH=true

# 无头模式，适合服务器环境（默认：false）
BROWSER_HEADLESS=false

# 自定义 Chrome 路径（可选）
# BROWSER_EXECUTABLE_PATH="C:\Program Files\Google\Chrome\Application\chrome.exe"
```

### 使用模式

1. **自动启动模式（默认）**：
   - 系统自动启动 Chrome 浏览器
   - 爬虫结束后自动关闭浏览器
   - 推荐用于开发和生产环境

2. **手动连接模式**：
   - 设置 `BROWSER_AUTO_LAUNCH=false`
   - 手动启动 Chrome：`chrome.exe --remote-debugging-port=9222`
   - 浏览器不会被自动关闭
   - 适合调试场景

3. **无头模式**：
   - 设置 `BROWSER_HEADLESS=true`
   - 无需图形界面，适合服务器环境
   - 推荐用于生产部署

### Chrome 安装要求

- Windows: 安装 Google Chrome 到标准位置
- Linux: `sudo apt-get install google-chrome-stable`
- macOS: 从 https://www.google.com/chrome/ 下载安装

**Trigger a Scrape Task**:
    Send a POST request to `/scrape`:
    ```json
    POST http://localhost:8001/scrape
    {
        "keyword": "Python",
        "pages": 3
    }
    ```

## 故障排除

### 浏览器启动失败

**问题**: `Failed to initialize browser`

**解决方案**:
1. 检查 Chrome 是否已安装
2. 如果使用自定义路径，设置 `BROWSER_EXECUTABLE_PATH`
3. 检查端口 9222 是否被占用
4. 查看详细错误信息获取具体原因

### 连接现有浏览器失败

**问题**: `No browser detected on port 9222`

**解决方案**:
1. 设置 `BROWSER_AUTO_LAUNCH=true` 使用自动启动
2. 或手动启动 Chrome: `chrome.exe --remote-debugging-port=9222`

### 无头模式问题

**问题**: 无头模式下某些功能异常

**解决方案**:
- 部分网站可能在无头模式下行为不同
- 如有问题，设置 `BROWSER_HEADLESS=false`
