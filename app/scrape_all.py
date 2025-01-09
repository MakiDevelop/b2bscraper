import warnings
from bs4.builder import XMLParsedAsHTMLWarning

# 忽略 BeautifulSoup 的 XML/HTML 警告
warnings.filterwarnings('ignore', category=XMLParsedAsHTMLWarning)

import asyncio
import sys
import aiohttp
from scrapers.mem import scrape_mem
from scrapers.netadmin import scrape_netadmin
from scrapers.twocm import scrape_2cm

async def run_all_scrapers():
    """同時執行所有爬蟲"""
    try:
        # 建立所有爬蟲的任務
        tasks = [
            asyncio.create_task(scrape_mem(batch_size=50)),
            asyncio.create_task(scrape_netadmin(batch_size=50)),
            asyncio.create_task(scrape_2cm(batch_size=50))
        ]
        
        print("開始執行所有爬蟲...")
        # 等待所有爬蟲完成
        await asyncio.gather(*tasks)
        print("所有爬蟲執行完成！")
        
    except Exception as e:
        print(f"執行爬蟲時發生錯誤: {str(e)}")

if __name__ == "__main__":
    # 在 Windows 上需要使用 SelectEventLoop
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # 執行所有爬蟲
    asyncio.run(run_all_scrapers()) 