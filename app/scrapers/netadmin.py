import aiohttp
from bs4 import BeautifulSoup
from datetime import datetime
import logging
import re
from models import Article, Tag
from database import get_db, SessionLocal
from sqlalchemy import func
import traceback
from typing import List
from sqlalchemy.orm import Session
import asyncio
from aiohttp import ClientTimeout

def clean_url(url):
    """清理 URL"""
    if '/netadmin/zh-tw/netadmin/zh-tw/' in url:
        return url.replace('/netadmin/zh-tw/netadmin/zh-tw/', '/netadmin/zh-tw/')
    return url

async def get_article_content(session, url):
	"""取得文章內容"""
	try:
		async with session.get(url, timeout=30) as response:
			if response.status == 200:
				html = await response.text()
				soup = BeautifulSoup(html, 'html.parser')
				
				# 修正選擇器以匹配實際網頁結構
				title = soup.select_one('.pageTitle h1')  # 文章標題
				content = soup.select_one('.pageContent')  # 文章內容
				tags = soup.select('.pageTagBox .pageTag')  # 修正為正確的標籤選擇器
				
				if title and content:
					tag_list = []
					if tags:
						# 直接取得 span 的文字內容
						tag_list = [tag.text.strip() for tag in tags if tag.text.strip()]
						print(f"[NetAdmin] 找到標籤: {tag_list}")
					else:
						print(f"[NetAdmin] 警告：沒有找到標籤")
						
						# 輸出頁面結構以供檢查
						print("[NetAdmin] 頁面結構預覽:")
						print(soup.prettify()[:1000])
					
					return {
						'title': title.text.strip(),
						'content': content.text.strip(),
						'tags': tag_list
					}
					
	except Exception as e:
		print(f"[NetAdmin] 取得文章內容時發生錯誤 {url}: {str(e)}")
		traceback.print_exc()
	return None

async def get_article_links(session, base_url, max_pages=100):
	"""取得文章連結列表"""
	all_links = []
	page = 1
	
	while page <= max_pages:  # 限制最多抓取10頁
		url = f"{base_url}?page={page}"
		try:
			print(f"\n[NetAdmin] 正在請求頁面 {page}/{max_pages}: {url}")
			async with session.get(url, timeout=30) as response:
				if response.status == 200:
					html = await response.text()
					soup = BeautifulSoup(html, 'html.parser')
					
					articles = soup.select('li.thumbnail.pageList')
					if not articles:  # 如果沒有找到文章，表示已經到最後一頁
						print(f"[NetAdmin] 頁面 {page} 沒有找到文章，結束抓取")
						break
						
					print(f"[NetAdmin] 在頁面 {page} 找到 {len(articles)} 篇文章")
					
					for article in articles:
						try:
							link_elem = article.select_one('a')
							title_elem = article.select_one('h4.pageListH4')
							date_elem = article.select_one('p.text-muted')
							
							if link_elem and title_elem:
								link = link_elem.get('href')
								if link:
									if not link.startswith('http'):
										link = f"https://www.netadmin.com.tw{link}"
										
									title = title_elem.text.strip()
									date = date_elem.text.strip() if date_elem else None
									
									print(f"[NetAdmin] 文章: {title}")
									print(f"[NetAdmin] 連結: {link}")
									
									all_links.append({
										'url': clean_url(link),
										'title': title,
										'date': date
									})
						except Exception as e:
							print(f"[NetAdmin] 處理文章連結時發生錯誤: {str(e)}")
							continue
							
					page += 1  # 繼續下一頁
				else:
					print(f"[NetAdmin] 頁面 {page} 請求失敗: {response.status}")
					break
					
		except Exception as e:
			print(f"[NetAdmin] 取得文章列表時發生錯誤: {str(e)}")
			traceback.print_exc()
			break
			
	print(f"[NetAdmin] 總共找到 {len(all_links)} 篇文章")
	return all_links

async def save_article(db: Session, url: str, title: str, content: str, tags: List[str]):
    """儲存文章到資料庫"""
    try:
        url = clean_url(url)
        
        # 檢查文章是否已存在
        existing = db.query(Article).filter(Article.url == url).first()
        if existing:
            print(f"[NetAdmin] 文章已存在: {title}")
            return
            
        # 建立新文章
        article = Article(
            url=url,
            title=title,
            content=content,
            source='netadmin',
            created_at=datetime.now()
        )
        
        # 處理標籤
        if tags:
            print(f"[NetAdmin] 正在處理 {len(tags)} 個標籤")
            for tag_name in tags:
                try:
                    # 檢查標籤是否已存在
                    tag = db.query(Tag).filter(func.lower(Tag.name) == func.lower(tag_name)).first()
                    if not tag:
                        print(f"[NetAdmin] 建立新標籤: {tag_name}")
                        tag = Tag(name=tag_name)
                        db.add(tag)
                    article.tags.append(tag)
                except Exception as e:
                    print(f"[NetAdmin] 處理標籤 {tag_name} 時發生錯誤: {str(e)}")
                    continue
        else:
            print(f"[NetAdmin] 警告：文章沒有標籤")
            
        db.add(article)
        db.commit()
        print(f"[NetAdmin] 已儲存文章: {title}")
        if article.tags:
            print(f"[NetAdmin] 已儲存標籤: {[tag.name for tag in article.tags]}")
        
    except Exception as e:
        db.rollback()
        print(f"[NetAdmin] 儲存文章時發生錯誤: {str(e)}")
        traceback.print_exc()

async def scrape_netadmin(batch_size: int = 50):
    """主要爬蟲函數"""
    print("[NetAdmin] 開始爬取...")
    
    categories = [
        "https://www.netadmin.com.tw/netadmin/zh-tw/feature/",
        "https://www.netadmin.com.tw/netadmin/zh-tw/news/",
        "https://www.netadmin.com.tw/netadmin/zh-tw/technology/"
    ]
    
    timeout = ClientTimeout(total=60)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        for category_url in categories:
            try:
                print(f"\n[NetAdmin] 處理分類: {category_url}")
                
                # 取得文章列表
                articles = await get_article_links(session, category_url)
                print(f"[NetAdmin] 找到 {len(articles)} 篇文章")
                
                # 批次處理文章
                for i in range(0, len(articles), batch_size):
                    batch = articles[i:i + batch_size]
                    tasks = []
                    
                    for article in batch:
                        task = asyncio.create_task(get_article_content(
                            session, article['url']
                        ))
                        tasks.append((article, task))
                    
                    # 等待批次完成
                    for article, task in tasks:
                        try:
                            content = await task
                            if content:
                                db = SessionLocal()
                                await save_article(
                                    db,
                                    article['url'],
                                    content['title'],
                                    content['content'],
                                    content['tags']
                                )
                                db.close()
                        except Exception as e:
                            print(f"[NetAdmin] 處理文章時發生錯誤: {str(e)}")
                            continue
                            
            except Exception as e:
                print(f"[NetAdmin] 處理分類時發生錯誤: {str(e)}")
                continue
                
    print("[NetAdmin] 爬取完成")

if __name__ == "__main__":
    asyncio.run(scrape_netadmin()) 