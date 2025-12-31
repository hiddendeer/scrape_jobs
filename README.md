# 爬取某聘数据

基于 FastAPI 的后端项目，使用 DrissionPage 从 Boss Zhipin 爬取职位数据并存储到 MySQL 数据库中

**Trigger a Scrape Task**:
    Send a POST request to `/scrape`:
    ```json
    POST http://localhost:8001/scrape
    {
        "keyword": "Python",
        "pages": 3
    }
    ```
