import json
from database import get_db
from models.article import Article
from datetime import datetime

def export_to_ndjson():
    db = next(get_db())
    try:
        # 取得所有文章
        articles = db.query(Article).all()
        
        # 建立輸出檔案名稱，包含時間戳記
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'netadmin_articles_{timestamp}.ndjson'
        
        # 寫入 NDJSON 檔案
        with open(filename, 'w', encoding='utf-8') as f:
            for article in articles:
                # 將每篇文章轉換成 dict
                article_dict = {
                    'title': article.title,
                    'url': article.url,
                    'category': article.category,
                    'summary': article.summary,
                    'content': article.content,
                    'source': article.source,
                    'created_at': article.created_at.isoformat() if article.created_at else None,
                    'updated_at': article.updated_at.isoformat() if article.updated_at else None
                }
                # 寫入一行 JSON
                f.write(json.dumps(article_dict, ensure_ascii=False) + '\n')
        
        print(f"已匯出 {len(articles)} 篇文章到 {filename}")
        
    finally:
        db.close()

if __name__ == "__main__":
    export_to_ndjson() 