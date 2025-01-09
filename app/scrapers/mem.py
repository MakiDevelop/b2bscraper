from database import get_db, SessionLocal
from models import Article, Tag
import aiohttp
import asyncio
import traceback
from bs4 import BeautifulSoup

async def get_article_links(session, max_depth=2, current_depth=1, max_concurrent=5):
    """遞迴爬取文章列表頁面的連結"""
    try:
        if current_depth > max_depth:
            return set()
            
        base_url = "https://www.mem.com.tw/"
        all_links = set()
        to_visit = {base_url}
        visited = set()
        
        while to_visit:
            # 取出最多 max_concurrent 個 URL 一起處理
            current_batch = set()
            while len(current_batch) < max_concurrent and to_visit:
                current_batch.add(to_visit.pop())
            
            if not current_batch:
                break
                
            # 建立非同步任務
            tasks = []
            for url in current_batch:
                if url not in visited:
                    visited.add(url)
                    tasks.append(process_page(session, url, current_depth, max_depth))
            
            # 等待所有任務完成
            if tasks:
                results = await asyncio.gather(*tasks)
                for article_links, new_pages in results:
                    all_links.update(article_links)
                    to_visit.update(new_pages - visited)
                    
            print(f"目前第 {current_depth} 層，已找到 {len(all_links)} 篇文章")
            
        return all_links
            
    except Exception as e:
        print(f"爬取文章列表時發生錯誤: {str(e)}")
        traceback.print_exc()
        return set()

async def process_page(session, url, current_depth, max_depth):
    """處理單一頁面"""
    article_links = set()
    new_pages = set()
    
    try:
        print(f"正在爬取: {url}")
        async with session.get(url) as response:
            if response.status == 200:
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # 找出所有的連結
                for a in soup.find_all('a', href=True):
                    link = a['href']
                    # 確保是完整的 URL
                    if not link.startswith('http'):
                        if link.startswith('/'):
                            link = "https://www.mem.com.tw" + link
                        else:
                            link = "https://www.mem.com.tw/" + link
                            
                    # 檢查是否為 mem.com.tw 的網址
                    if not link.startswith('https://www.mem.com.tw/'):
                        continue
                        
                    # 檢查是否為文章頁面
                    if await is_article_page(session, link):
                        article_links.add(link)
                    # 如果是列表頁面且未達到最大深度，加入待訪問列表
                    elif current_depth < max_depth and is_list_page(link):
                        new_pages.add(link)
                        
    except Exception as e:
        print(f"處理頁面時發生錯誤 {url}: {str(e)}")
        
    return article_links, new_pages

def is_list_page(url):
    """檢查是否為列表頁面"""
    list_patterns = [
        '/category/',
        '/tag/',
        '/page/',
        '?s=',
        '/vendor/',
        '/books/',
        '/magazine/',
        '/whitepaper/'
    ]
    return any(pattern in url for pattern in list_patterns)

async def is_article_page(session, url):
    """檢查頁面是否為文章內容頁"""
    try:
        async with session.get(url) as response:
            if response.status == 200:
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # 檢查是否有文章標題和內容的特定 class
                article_title = soup.find('h1', class_='mem-post-single-title')
                article_content = soup.find('div', class_='mem-post-single-content')
                
                return bool(article_title and article_content)
    except:
        return False
    return False

async def get_article_content(session, url):
    """取得文章內容"""
    try:
        async with session.get(url) as response:
            if response.status == 200:
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # 取得標題
                title = soup.select_one('.mem-post-single-title')
                if not title:
                    return None
                
                # 取得內文
                content = soup.select_one('.mem-post-single-content')
                if not content:
                    return None
                    
                # 取得標籤
                tags = []
                tag_elements = soup.select('.mem-post-single-tags ul li a')
                for tag in tag_elements:
                    tags.append(tag.text.strip())
                
                return {
                    'title': title.text.strip(),
                    'content': content.text.strip(),
                    'tags': tags
                }
                
    except Exception as e:
        print(f"[MEM] 取得文章內容時發生錯誤 {url}: {str(e)}")
        return None

async def scrape_mem(batch_size=50):
    """爬取 mem 網站文章"""
    print("[MEM] 開始爬取...")
    
    timeout = aiohttp.ClientTimeout(total=30, connect=10, sock_connect=10, sock_read=10)
    connector = aiohttp.TCPConnector(limit=10, force_close=True)
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        db = SessionLocal()
        try:
            base_urls = [
                "https://www.mem.com.tw/category/news/",
                "https://www.mem.com.tw/category/tech/",
                "https://www.mem.com.tw/category/ee/",
                "https://www.mem.com.tw/category/car/"
            ]
            
            article_links = set()
            for base_url in base_urls:
                print(f"\n[MEM] 正在處理分類: {base_url}")
                try:
                    async with session.get(base_url) as response:
                        if response.status == 200:
                            html = await response.text()
                            soup = BeautifulSoup(html, 'html.parser')
                            
                            # 印出頁面結構以便除錯
                            print("[MEM] 頁面結構:")
                            print(soup.select('.post_layout_5_grid'))
                            
                            # 嘗試不同的選擇器
                            selectors = [
                                '.post_layout_5_grid_item a',
                                '.post_layout_5_grid .post_layout_5_grid_item a',
                                '.elementor-widget-container .post_layout_5_grid_item a',
                                'div[class*="post_layout_5"] a'
                            ]
                            
                            for selector in selectors:
                                articles = soup.select(selector)
                                print(f"[MEM] 使用選擇器 '{selector}' 找到 {len(articles)} 篇文章")
                                
                                if articles:
                                    for article in articles:
                                        url = article.get('href')
                                        if url and 'mem.com.tw' in url:
                                            article_links.add(url)
                                            print(f"[MEM] 找到文章連結: {url}")
                            
                            print(f"[MEM] 在 {base_url} 找到 {len(article_links)} 篇文章")
                            
                except Exception as e:
                    print(f"[MEM] 處理分類頁面時發生錯誤 {base_url}: {str(e)}")
                    traceback.print_exc()
                    continue
            
            # 處理找到的文章
            current_batch = []
            for url in article_links:
                try:
                    # 檢查 URL 是否已存在
                    existing = db.query(Article).filter(Article.url == url).first()
                    if existing:
                        print(f"[MEM] 文章已存在: {url}")
                        continue
                    
                    content = await get_article_content(session, url)
                    if content and content['title'] and content['content']:
                        article = Article(
                            source='mem',
                            title=content['title'],
                            content=content['content'],
                            url=url
                        )
                        
                        # 處理標籤
                        if content['tags']:
                            for tag_name in content['tags']:
                                tag = db.query(Tag).filter(Tag.name == tag_name).first()
                                if not tag:
                                    tag = Tag(name=tag_name)
                                    db.add(tag)
                                article.tags.append(tag)
                        
                        current_batch.append(article)
                        print(f"[MEM] 已收集文章: {len(current_batch)}/{batch_size}")
                        print(f"[MEM] 標題: {content['title']}")
                        
                        if len(current_batch) >= batch_size:
                            print(f"[MEM] 開始寫入 {len(current_batch)} 篇文章到資料庫...")
                            db.add_all(current_batch)
                            db.commit()
                            print("[MEM] 寫入完成！")
                            return
                            
                except Exception as e:
                    print(f"[MEM] 處理文章時發生錯誤 {url}: {str(e)}")
                    continue
                    
        except Exception as e:
            print(f"[MEM] 爬取過程發生錯誤: {str(e)}")
            traceback.print_exc()
        finally:
            if current_batch:
                try:
                    db.add_all(current_batch)
                    db.commit()
                except:
                    db.rollback()
            db.close()

async def get_article_links_stream(session, max_depth=2):
    """串流方式產生文章連結"""
    base_url = "https://www.mem.com.tw/"
    to_visit = {base_url}
    visited = set()
    current_depth = 1
    
    while to_visit and current_depth <= max_depth:
        url = to_visit.pop()
        if url in visited:
            continue
            
        visited.add(url)
        print(f"正在爬取第 {current_depth} 層: {url}")
        
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    for a in soup.find_all('a', href=True):
                        link = a['href']
                        if not link.startswith('http'):
                            if link.startswith('/'):
                                link = "https://www.mem.com.tw" + link
                            else:
                                link = "https://www.mem.com.tw/" + link
                                
                        if not link.startswith('https://www.mem.com.tw/'):
                            continue
                            
                        if await is_article_page(session, link):
                            yield link
                        elif current_depth < max_depth and is_list_page(link):
                            to_visit.add(link)
                            
        except Exception as e:
            print(f"處理頁面時發生錯誤 {url}: {str(e)}")
            continue
            
        if not to_visit:
            current_depth += 1 