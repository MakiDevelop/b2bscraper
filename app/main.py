from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import logging
from scrapers.netadmin import scrape_netadmin

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Tech News Crawler",
    description="爬取科技新聞網站的 API",
    version="1.0.0"
)

# CORS 設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 健康檢查端點
@app.get("/")
async def root():
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat()
    }

# 手動觸發爬蟲
@app.post("/crawl/netadmin")
async def crawl_netadmin(background_tasks: BackgroundTasks):
    try:
        articles = await scrape_netadmin()
        return {
            "status": "success",
            "message": f"成功爬取 {len(articles)} 篇文章",
            "data": articles
        }
    except Exception as e:
        logger.error(f"爬蟲執行失敗: {str(e)}")
        return {
            "status": "error",
            "message": f"爬蟲執行失敗: {str(e)}"
        }

# 取得爬蟲狀態
@app.get("/status")
async def get_status():
    return {
        "status": "running",
        "last_update": datetime.now().isoformat(),
        "crawlers": {
            "netadmin": "active",
            "newcm": "pending",
            "mem": "pending"
        }
    } 