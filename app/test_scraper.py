import asyncio
import sys
from scrapers.mem import scrape_mem
from scrapers.netadmin import scrape_netadmin
from scrapers.twocm import scrape_2cm

async def main(source):
    if source == 'mem':
        print("開始爬取 MEM...")
        await scrape_mem(batch_size=50)
    elif source == 'netadmin':
        print("開始爬取 NetAdmin...")
        await scrape_netadmin(batch_size=50)
    elif source == '2cm':
        print("開始爬取 2CM...")
        await scrape_2cm(batch_size=50)
    else:
        print(f"未知的來源: {source}")
        print("可用的來源: mem, netadmin, 2cm")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("使用方式: python test_scraper.py [來源]")
        print("可用的來源: mem, netadmin, 2cm")
        sys.exit(1)
        
    source = sys.argv[1]
    
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main(source)) 