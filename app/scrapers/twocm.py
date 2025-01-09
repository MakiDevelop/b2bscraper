import aiohttp
from bs4 import BeautifulSoup
import traceback
from database import SessionLocal
from models import Article, Tag

async def get_article_links(session, url):
    """取得文章連結列表"""
    links = []
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-TW,zh;q=0.9,en;q=0.8'
        }
        
        async with session.get(url, headers=headers, timeout=10) as response:
            if response.status == 200:
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                articles = soup.select('.indexArticle li a')
                print(f"[2CM] 找到 {len(articles)} 個文章連結")
                
                for article in articles:
                    link = article.get('href')
                    if link:
                        if not link.startswith('http'):
                            link = f"https://www.2cm.com.tw{link}"
                        links.append(link)
                        
    except Exception as e:
        print(f"[2CM] 取得文章列表時發生錯誤: {str(e)}")
        traceback.print_exc()
        
    return links

async def get_article_content(session, url):
    """取得文章內容"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-TW,zh;q=0.9,en;q=0.8'
        }
        
        async with session.get(url, headers=headers, timeout=10) as response:
            if response.status == 200:
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                title = soup.select_one('.pageTitle h1')
                content = soup.select_one('.pageContent')
                
                tags = soup.find_all('span', class_='pageTag')
                tag_list = []
                
                if tags:
                    print(f"\n[2CM] 找到 {len(tags)} 個標籤")
                    for tag in tags:
                        tag_text = tag.text.strip()
                        if tag_text:
                            tag_list.append(tag_text)
                            print(f"[2CM] 標籤: {tag_text}")
                
                if title and content:
                    result = {
                        'title': title.text.strip(),
                        'content': content.text.strip(),
                        'tags': tag_list
                    }
                    return result
                    
    except Exception as e:
        print(f"[2CM] 取得文章內容時發生錯誤 {url}: {str(e)}")
        traceback.print_exc()
    return None

async def get_article_links_stream(session, max_depth=10):
    """串流方式取得文章連結"""
    base_url = "https://www.2cm.com.tw/2cm/news"
    
    for page in range(1, max_depth + 1):
        url = f"{base_url}/page/{page}" if page > 1 else base_url
        print(f"[2CM] 正在爬取第 {page} 頁: {url}")
        
        links = await get_article_links(session, url)
        for link in links:
            yield link

async def scrape_2cm(batch_size=50):
    """爬取 2cm 網站文章"""
    connector = aiohttp.TCPConnector(limit=10)
    async with aiohttp.ClientSession(connector=connector) as session:
        db = SessionLocal()
        try:
            print("[2CM] 開始爬取文章...")
            article_links = set()
            current_batch = []
            
            async for url in get_article_links_stream(session, max_depth=10):
                try:
                    existing = db.query(Article).filter(Article.url == url).first()
                    if existing or url in article_links:
                        continue
                        
                    article_links.add(url)
                    content = await get_article_content(session, url)
                    
                    if content and content['title'] and content['content']:
                        article = Article(
                            source='2cm',
                            title=content['title'],
                            content=content['content'],
                            url=url
                        )
                        
                        db.add(article)
                        db.flush()
                        
                        # 處理標籤
                        if content['tags']:
                            for tag_name in content['tags']:
                                tag = db.query(Tag).filter(Tag.name == tag_name).first()
                                if not tag:
                                    tag = Tag(name=tag_name)
                                    db.add(tag)
                                    db.flush()
                                article.tags.append(tag)
                        
                        current_batch.append(article)
                        print(f"\n[2CM] 已收集文章: {len(current_batch)}/{batch_size}")
                        print(f"[2CM] 標題: {content['title']}")
                        
                        if len(current_batch) >= batch_size:
                            print(f"\n[2CM] 開始寫入 {len(current_batch)} 篇文章到資料庫...")
                            db.commit()
                            print("[2CM] 寫入完成！")
                            return
                    
                except Exception as e:
                    print(f"[2CM] 處理文章時發生錯誤 {url}: {str(e)}")
                    db.rollback()
                    continue
                    
            # 處理最後一批
            if current_batch:
                print(f"\n[2CM] 開始寫入最後 {len(current_batch)} 篇文章到資料庫...")
                db.commit()
                print("[2CM] 寫入完成！")
                    
        except Exception as e:
            print(f"[2CM] 爬取過程發生錯誤: {str(e)}")
            traceback.print_exc()
        finally:
            db.close()