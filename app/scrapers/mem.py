from datetime import datetime
from models.article import Article, Tag
from database import SessionLocal
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import unquote
import traceback

async def scrape_mem(batch_size=50):
    """爬取 mem 網站文章"""
    print("[MEM] 開始爬取...")
    
    timeout = aiohttp.ClientTimeout(total=60)
    connector = aiohttp.TCPConnector(limit=10, force_close=True)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout, headers=headers) as session:
        db = SessionLocal()
        try:
            article_links = set()
            
            # 爬取首頁
            async with session.get("https://www.mem.com.tw/") as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # 找出所有文章連結
                    for link in soup.find_all('a', href=True):
                        href = link['href']
                        if (href.startswith('https://www.mem.com.tw/') and 
                            not any(x in href for x in ['category', 'magazine', 'seminar', 'vendor', 'video', 'whitepaper'])):
                            article_links.add(href)
                    
                    print(f"\n[MEM] 首頁找到 {len(article_links)} 篇文章")
            
            # 爬取每篇文章內容
            for url in article_links:
                try:
                    print(f"\n[MEM] 正在爬取文章: {unquote(url)}")
                    
                    # 檢查文章是否已存在
                    existing_article = db.query(Article).filter(Article.url == url).first()
                    if existing_article:
                        print(f"[MEM] 文章已存在: {url}")
                        continue
                    
                    async with session.get(url) as article_response:
                        if article_response.status != 200:
                            continue
                            
                        article_html = await article_response.text()
                        article_soup = BeautifulSoup(article_html, 'html.parser')
                        
                        # 取得文章資訊
                        title = article_soup.select_one('.mem-post-single-title')
                        title = title.text.strip() if title else ""
                        
                        content = article_soup.select_one('.mem-post-single-content')
                        content = content.text.strip() if content else ""
                        
                        # 取得摘要 (使用內容的前200字)
                        summary = content[:200] if content else ""
                        
                        # 只處理有標題和內容的文章
                        if title and content:
                            # 建立文章
                            article = Article(
                                title=title,
                                url=url,
                                summary=summary,
                                content=content,
                                source="MEM",
                                category="news"
                            )
                            db.add(article)
                            
                            # 處理標籤
                            tags = article_soup.select('.mem-post-single-tags ul li a')
                            if tags:
                                for tag_elem in tags:
                                    tag_name = tag_elem.text.strip()
                                    # 檢查標籤是否已存在
                                    tag = db.query(Tag).filter(Tag.name == tag_name).first()
                                    if not tag:
                                        tag = Tag(name=tag_name)
                                        db.add(tag)
                                        db.flush()
                                    article.tags.append(tag)
                            
                            db.commit()
                            print(f"[MEM] 成功儲存文章: {title}")
                            
                except Exception as e:
                    print(f"[MEM] 處理文章時發生錯誤 {url}: {str(e)}")
                    db.rollback()
                    continue
                    
        except Exception as e:
            print(f"[MEM] 發生錯誤: {str(e)}")
            db.rollback()
        finally:
            db.close() 