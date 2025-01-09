from bs4 import BeautifulSoup
import traceback
import aiohttp
from database import SessionLocal
from models import Article, Tag

async def get_article_links(session, url):
    """取得文章連結列表"""
    links = []
    try:
        async with session.get(url, timeout=10) as response:
            if response.status == 200:
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # 先印出頁面結構以便除錯
                print("[TwoCM] 頁面內容:")
                print(soup.prettify()[:1000])
                
                # 尋找所有文章連結
                articles = soup.select('.indexArticle li a')
                print(f"[TwoCM] 找到 {len(articles)} 個文章連結")
                
                for article in articles:
                    link = article.get('href')
                    if link:
                        if not link.startswith('http'):
                            link = f"https://www.2cm.com.tw{link}"
                        links.append(link)
                        
    except Exception as e:
        print(f"[TwoCM] 取得文章列表時發生錯誤: {str(e)}")
        traceback.print_exc()
        
    return links

async def get_article_content(session, url):
    """取得文章內容"""
    try:
        async with session.get(url, timeout=10) as response:
            if response.status == 200:
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # 修正選擇器以匹配實際網頁結構
                title = soup.select_one('.pageTitle h1')
                content = soup.select_one('.pageContent')
                tags = soup.select('.pageTagBox .pageTag')
                
                if title and content:
                    return {
                        'title': title.text.strip(),
                        'content': content.text.strip(),
                        'tags': [tag.text.strip() for tag in tags] if tags else []
                    }
                    
    except Exception as e:
        print(f"[TwoCM] 取得文章內容時發生錯誤 {url}: {str(e)}")
        traceback.print_exc()
    return None

async def scrape_2cm(batch_size=50):
    """爬取 2cm 網站文章"""
    connector = aiohttp.TCPConnector(limit=10)
    async with aiohttp.ClientSession(connector=connector) as session:
        db = SessionLocal()
        try:
            print("[2CM] 開始爬取文章...")
            article_links = set()
            current_batch = []
            
            async for url in get_article_links_stream(session, max_depth=3):
                try:
                    # 檢查 URL 是否已存在
                    existing = db.query(Article).filter(Article.url == url).first()
                    if existing or url in article_links:
                        continue
                        
                    article_links.add(url)
                    content = await get_article_content(session, url)
                    
                    if content and content['title'] and content['content']:
                        # 建立文章物件
                        article = Article(
                            source='2cm',
                            title=content['title'],
                            content=content['content'],
                            url=url
                        )
                        
                        # 建立標籤
                        if content['tags']:
                            for tag_name in content['tags']:
                                tag = db.query(Tag).filter(Tag.name == tag_name).first()
                                if not tag:
                                    tag = Tag(name=tag_name)
                                    db.add(tag)
                                    db.commit()  # 先儲存標籤
                                article.tags.append(tag)
                        
                        current_batch.append(article)
                        print(f"\n[2CM] 已收集文章: {len(current_batch)}/{batch_size}")
                        print(f"[2CM] 標題: {content['title']}")
                        
                        if len(current_batch) >= batch_size:
                            print(f"\n[2CM] 開始寫入 {len(current_batch)} 篇文章到資料庫...")
                            db.add_all(current_batch)
                            db.commit()
                            print("[2CM] 寫入完成！")
                            return  # 完成一批次就結束
                    
                except Exception as e:
                    print(f"[2CM] 處理文章時發生錯誤 {url}: {str(e)}")
                    db.rollback()
                    continue
                    
        except Exception as e:
            print(f"[2CM] 爬取過程發生錯誤: {str(e)}")
            traceback.print_exc()
        finally:
            db.close()