import aiohttp
from bs4 import BeautifulSoup
import traceback
from database import SessionLocal
from models import Article, Tag
import xml.etree.ElementTree as ET

async def get_article_links(session, url):
    """從 RSS 取得文章連結列表"""
    links = []
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-TW,zh;q=0.9,en;q=0.8'
        }
        
        rss_url = "https://www.2cm.com.tw/2cm/Rss.aspx"
        
        async with session.get(rss_url, headers=headers, timeout=10) as response:
            if response.status == 200:
                xml_content = await response.text()
                root = ET.fromstring(xml_content)
                
                # RSS 文章都在 item 標籤裡
                items = root.findall('.//item')
                print(f"[2CM] 從 RSS 找到 {len(items)} 篇文章")
                
                for item in items:
                    link = item.find('link')
                    if link is not None and link.text:
                        links.append(link.text)
                        print(f"[2CM] 找到文章連結: {link.text}")
                        
    except Exception as e:
        print(f"[2CM] 取得 RSS 文章列表時發生錯誤: {str(e)}")
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
                
                # 使用更精確的選擇器找標籤
                tag_box = soup.select_one('div.col-sm-9 div.pageTagBox')
                tag_list = []
                
                if tag_box:
                    tags = tag_box.find_all('span', {'class': 'pageTag', 'onclick': True})
                    if tags:
                        print(f"\n[2CM] 找到 {len(tags)} 個標籤")
                        for tag in tags:
                            tag_text = tag.get_text(strip=True)
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
    # RSS 只需要抓取一次
    links = await get_article_links(session, None)
    for link in links:
        yield link

async def scrape_2cm(batch_size=50):
    """爬取2CM文章"""
    print("開始爬取 2CM...")
    
    try:
        async with aiohttp.ClientSession() as session:
            db = SessionLocal()
            current_batch = []
            
            try:
                # 取得文章列表
                links = await get_article_links(session, "https://www.2cm.com.tw/2cm/zh-tw/tech")
                
                if not links:
                    print("[2CM] 沒有找到文章連結")
                    return
                
                print(f"[2CM] 找到 {len(links)} 篇文章")
                
                for url in links:
                    content = await get_article_content(session, url)
                    if content:
                        existing_article = db.query(Article).filter(Article.url == url).first()
                        
                        if existing_article:
                            print(f"\n[2CM] 更新文章: {content['title']}")
                            existing_article.title = content['title']
                            existing_article.content = content['content']
                            
                            # 清除現有標籤關聯
                            existing_article.tags = []
                            db.flush()
                            
                            # 處理標籤
                            for tag_name in content['tags']:
                                tag = db.query(Tag).filter(Tag.name == tag_name).first()
                                if not tag:
                                    tag = Tag(name=tag_name)
                                    db.add(tag)
                                    db.flush()
                                existing_article.tags.append(tag)
                                db.flush()
                            
                            current_batch.append(existing_article)
                        else:
                            print(f"\n[2CM] 新增文章: {content['title']}")
                            article = Article(
                                title=content['title'],
                                content=content['content'],
                                url=url,
                                source='2cm'
                            )
                            db.add(article)
                            db.flush()
                            
                            # 處理標籤
                            for tag_name in content['tags']:
                                tag = db.query(Tag).filter(Tag.name == tag_name).first()
                                if not tag:
                                    tag = Tag(name=tag_name)
                                    db.add(tag)
                                    db.flush()
                                article.tags.append(tag)
                                db.flush()
                            
                            current_batch.append(article)
                        
                        print(f"[2CM] 標籤: {', '.join(content['tags'])}")
                        
                        # 當達到批次大小時，提交到資料庫
                        if len(current_batch) >= batch_size:
                            print(f"\n[2CM] 寫入 {len(current_batch)} 篇文章到資料庫...")
                            db.commit()
                            current_batch = []
                            print("[2CM] 寫入完成！")
                
                # 處理最後一批
                if current_batch:
                    print(f"\n[2CM] 寫入最後 {len(current_batch)} 篇文章到資料庫...")
                    db.commit()
                    print("[2CM] 寫入完成！")
                    
            except Exception as e:
                print(f"[2CM] 處理文章時發生錯誤: {str(e)}")
                traceback.print_exc()
                db.rollback()
                
    except Exception as e:
        print(f"[2CM] 爬取過程發生錯誤: {str(e)}")
        traceback.print_exc()
    finally:
        db.close()