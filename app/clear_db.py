from database import Base, engine
from models import Article, Tag, article_tags

print("開始清除資料庫...")

try:
    # 刪除所有表格
    print("正在刪除表格...")
    Base.metadata.drop_all(bind=engine)
    print("表格已刪除")
    
    # 重新建立表格
    print("正在重新建立表格...")
    Base.metadata.create_all(bind=engine)
    print("表格已重新建立")
    
except Exception as e:
    print(f"發生錯誤: {str(e)}")
    raise

print("資料庫清除完成") 