# Boss Zhipin Scraper Backend

This project is a FastAPI-based backend that uses DrissionPage to scrape job data from Boss Zhipin and stores it in a MySQL database.

## Prerequisites

1.  **Python 3.8+**
2.  **MySQL Database**: Ensure you have a database (default: `boss_zhipin_db`) created.
3.  **Chrome Browser**: Must be installed.
4.  **Google Chrome launched with remote debugging**:
    ```bash
    chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\selenum\AutomationProfile"
    ```
    *Note: Adjust path to chrome.exe and user-data-dir as needed.*

## Setup

1.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

2.  Configure database in `config.py` or use `.env` file:
    ```env
    DB_HOST=localhost
    DB_PORT=3306
    DB_USER=root
    DB_PASSWORD=root
    DB_NAME=boss_zhipin_db
    ```

## Usage

1.  **Start the API server**:
    ```bash
    python main.py
    ```
    Or using uvicorn directly:
    ```bash
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
    ```

2.  **Trigger a Scrape Task**:
    Send a POST request to `/scrape`:
    ```json
    POST http://localhost:8000/scrape
    {
        "keyword": "Python",
        "pages": 3
    }
    ```

## Project Structure

- `main.py`: FastAPI application entry point.
- `scraper.py`: `BossScraper` class using DrissionPage (Listener mode).
- `cleaner.py`: Data cleaning utilities (Salary, Experience).
- `database.py`: MySQL connection and operations.
- `config.py`: Configuration settings.
