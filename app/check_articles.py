from database import get_db
from models import Article, Tag, article_tags
from sqlalchemy import func, text

def check_articles():
    db = next(get_db())
    try:
        # 計算總文章數
        total = db.query(Article).count()
        print(f"總共有 {total} 篇文章")
        
        # 計算總標籤數
        total_tags = db.query(Tag).count()
        print(f"總共有 {total_tags} 個標籤")
        
        # 依分類統計
        print("\n各分類文章數：")
        category_stats = db.query(
            Article.category, 
            func.count(Article.id)
        ).group_by(Article.category).all()
        for category, count in category_stats:
            print(f"- {category}: {count} 篇")
        
        # 顯示有內容的文章數量
        articles_with_content = db.query(Article).filter(
            Article.content.isnot(None),
            Article.content != ''
        ).count()
        print(f"\n有內容的文章數：{articles_with_content} 篇")
        
        # 顯示最新的5篇文章及其標籤
        print("\n最新的5篇文章：")
        latest = db.query(Article).order_by(Article.created_at.desc()).limit(5).all()
        for article in latest:
            print(f"- {article.title}")
            print(f"  分類：{article.category}")
            print(f"  標籤：{', '.join(tag.name for tag in article.tags)}")
            print(f"  內容長度：{len(article.content) if article.content else 0} 字")
            print(f"  更新時間：{article.updated_at}")
            print()
            
        # 標籤統計
        print("\n標籤統計：")
        tag_stats = db.query(
            Tag.name,
            func.count(article_tags.c.article_id).label('count')
        ).join(article_tags).group_by(Tag.name).order_by(text('count DESC')).limit(10).all()

        print("前10個最常用的標籤：")
        for tag_name, count in tag_stats:
            print(f"- {tag_name}: {count} 篇")
            
    finally:
        db.close()

if __name__ == "__main__":
    check_articles() 