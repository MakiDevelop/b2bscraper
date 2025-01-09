from database import get_db
from models.article import Article

def test_db_connection():
    try:
        # 取得資料庫連線
        db = next(get_db())
        
        # 測試查詢
        result = db.query(Article).first()
        print("資料庫連線成功！")
        
        # 如果有資料，印出第一筆
        if result:
            print(f"找到文章：{result.title}")
        else:
            print("資料表是空的")
            
    except Exception as e:
        print(f"連線錯誤：{str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    test_db_connection() 