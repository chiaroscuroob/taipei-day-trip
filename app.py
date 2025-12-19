from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse,FileResponse

import mysql.connector
app=FastAPI()

# Static Pages (Never Modify Code in this Block)
@app.get("/", include_in_schema=False)
async def index(request: Request):
	return FileResponse("./static/index.html", media_type="text/html")
@app.get("/attraction/{id}", include_in_schema=False)
async def attraction(request: Request, id: int):
	return FileResponse("./static/attraction.html", media_type="text/html")
@app.get("/booking", include_in_schema=False)
async def booking(request: Request):
	return FileResponse("./static/booking.html", media_type="text/html")
@app.get("/thankyou", include_in_schema=False)
async def thankyou(request: Request):
	return FileResponse("./static/thankyou.html", media_type="text/html")

# 資料庫連線設定
db_config = {
    "user": "root",
    "password": "520038", 
    "host": "localhost",
    "database": "taipei_day_trip"
}

# 建立資料庫連線函式
def get_db_connection():
    return mysql.connector.connect(**db_config) # **解包字典並傳入連線參數

# 取得景點資料列表
@app.get("/api/attractions")
# 定義函式參數，接收 page(分頁/預設為int數字、0頁)
# category(景點分類/預設none=沒有要搜尋),keyword(捷運站、景點名稱模糊比對/預設none=沒有要搜尋) 
def get_attractions(page: int = 0, category: str = None, keyword: str = None):
    try:
        con = get_db_connection()
        cursor = con.cursor()
        
        # 動態組合 SQL 指令，根據有無 category 與 keyword 來決定要加哪些條件
        # WHERE 1=1 為了方便後續加 AND 條件
        sql = """
            SELECT id, name, category, description, address, 
                transport, mrt, lat, lng, images 
            FROM attraction 
            WHERE 1=1
        """
        val = []  # 用來存放 SQL 參數的列表

        # 處理 category (精確搜尋) 假設不是空值→true
        if category:
            # += 用來串接字串，變SELECT ... WHERE 1=1 AND category = %s
            # %s 為佔位符，後面會用val列表來填入實際的值
            sql += " AND category = %s"
            val.append(category) # 把 category 的值加入 val 列表

        # 處理 keyword (模糊搜尋 Name 或 精確搜尋 MRT)
        if keyword:
            sql += " AND (name LIKE %s OR mrt = %s)" # ( ) 符合其中一個條件即可，LIKE 為模糊搜尋，=為精確搜尋
            val.append(f"%{keyword}%") # 放入第一個%s，name LIKE %keyword% (前後加 % 為模糊比對)
            val.append(keyword) # 放入第二個%s，mrt = %s (精確比對)

        # 依照規格每頁8筆資料，會跳過前面page*8 筆
        rows_per_page = 8
        offset = page * rows_per_page

        # 套用分頁設定：排序與分頁
        sql += " LIMIT %s, %s" # "LIMIT 跳過幾筆,取幾筆"
        val.append(offset) # 跳過前 offset 筆
        val.append(rows_per_page + 1) # 多取一筆來判斷是否有下一頁

        # 執行 SQL 查詢(帶入參數)
        cursor.execute(sql, tuple(val)) # sql為訂單資料，val為參數列表(轉成tuple格式，不可修改)
        results = cursor.fetchall() # 抓取所有查詢結果

        # 整理資料
        data = []
        for row in results: # 一筆一筆處理查詢結果
            images_list = row[9].split(",") if row[9] else [] # 將圖片字串以逗號分隔成列表，若無圖片則為空列表
            attraction = {
                "id": row[0],
                "name": row[1],
                "category": row[2],
                "description": row[3],
                "address": row[4],
                "transport": row[5],
                "mrt": row[6],
                "lat": row[7],
                "lng": row[8],
                "images": images_list
            }
            data.append(attraction) # 把整理好的景點資料加入 data 列表

        # 處理「下一頁」邏輯
        next_page = None # 預設沒有下一頁，如果資料庫抓回來的資料沒有超過 8 筆，程式就不會進入 if 判斷式
        if len(data) > 8: # 如果抓到超過 8 筆
            next_page = page + 1 # 設定下一頁頁碼
            data.pop() # data.pop() 移除最後一筆多取的資料
        
        # 回傳結果
        return JSONResponse(content={
            "nextPage": next_page, 
            "data": data
        })
    
    except Exception as e: # 先將此錯誤狀況命名為e
        # 在伺服器控制台印出詳細錯誤，方便除錯
        print(f"Error: {e}")
        # 回傳500錯誤訊息
        return JSONResponse(status_code=500, content={
            "error": True,
            "message": "伺服器內部錯誤"
        })

    finally:
        # 檢查游標是否存在，存在才關閉
        if 'cursor' in locals() and cursor:
            cursor.close()
        # 檢查連線變數名稱 con 是否存在且成功連線
        if 'con' in locals() and con:
            con.close()

# 根據景點編號取得景點資料
@app.get("/api/attraction/{attractionId}")
def get_attraction_by_id(attractionId: int):
    try:
        # 建立資料庫連線
        con = get_db_connection()
        cursor = con.cursor()

        # 準備 SQL 指令
        # """ 多行字串方便閱讀資料，可以換行
        # WHERE id = %s 為佔位符，確保資料被當作純數值，防止SQL注入攻擊、提升安全性
        sql = """
            SELECT id, name, category, description, address, 
                   transport, mrt, lat, lng, images 
            FROM attraction 
            WHERE id = %s
        """
        
        # 執行 SQL 查詢，帶入景點編號參數
        cursor.execute(sql, (attractionId, ))
        
        # 取得結果
        # ID 只有一筆，只需要 fetchone() 抓一筆，不需使用 fetchall()
        row = cursor.fetchone()

        # 判斷有沒有抓到資料，若有則整理並回傳
        if row:
            images_list = row[9].split(",") if row[9] else [] # 將圖片字串以逗號分隔成列表，若無圖片則為空列表
            response_data = {
                "id": row[0],
                "name": row[1],
                "category": row[2],
                "description": row[3],
                "address": row[4],
                "transport": row[5],
                "mrt": row[6],
                "lat": row[7],
                "lng": row[8],
                "images": images_list
            }
            
            # 回傳成功的 JSON (包在 "data" 裡面)
            return JSONResponse(content={
                "data": response_data
            })
        
        else:
            # 如果row是None，代表找不到這個 ID
            # 景點編號不正確，回傳400錯誤
            return JSONResponse(status_code=400, content={
                "error": True,
                "message": "景點編號不正確"
            })
        
    except Exception as e: # 先將此錯誤狀況命名為e
        # 在伺服器控制台印出詳細錯誤，方便除錯
        print(f"Error: {e}")
        # 回傳500錯誤訊息
        return JSONResponse(status_code=500, content={
            "error": True,
            "message": "伺服器內部錯誤"
        })
    
    finally:
        # 檢查游標是否存在，存在才關閉
        if 'cursor' in locals() and cursor:
            cursor.close()
        # 檢查連線變數名稱con是否存在且成功連線
        if 'con' in locals() and con:
            con.close()

# 取得景點分類名稱列表
@app.get("/api/categories")
def get_categories():
    try:
        con = get_db_connection()
        cursor = con.cursor()
        
        # DISTINCT:去除category分類重複的部分
        sql = """
            SELECT DISTINCT category FROM attraction
        """
        cursor.execute(sql)
        # fetchall() 列出所有查詢結果
        results = cursor.fetchall()
        
        # 利用列表生成式 List Comprehension 來整理資料(適合單一欄位資料)
        categories = [row[0] for row in results]

        # 回傳分類列表
        return JSONResponse(content={
            "data": categories
        }) 

    except Exception as e: # 先將此錯誤狀況命名為e
        # 在伺服器控制台印出詳細錯誤，方便除錯
        print(f"Error: {e}")
        # 回傳500錯誤訊息
        return JSONResponse(status_code=500, content={
            "error": True, 
            "message": "伺服器內部錯誤"
        })

    finally:
        # 檢查游標是否存在，存在才關閉
        if 'cursor' in locals() and cursor:
            cursor.close()
        # 檢查連線變數名稱 con 是否存在且成功連線
        if 'con' in locals() and con:
            con.close()

# 取得捷運站名稱列表
@app.get("/api/mrts")
def get_mrts():
    try:
        con = get_db_connection()
        cursor = con.cursor()

        # SQL 指令
        # WHERE: 排除掉沒有捷運站資料的景點 (NULL 或 空字串)
        # GROUP BY: 把相同捷運站名稱的資料「疊在一起」
        # ORDER BY COUNT(*): 按照週邊景點的數量由大到小排序 (DESC)
        sql = """
            SELECT mrt 
            FROM attraction 
            WHERE mrt IS NOT NULL AND mrt != ''
            GROUP BY mrt 
            ORDER BY COUNT(*) DESC
        """
        
        cursor.execute(sql)
        results = cursor.fetchall()
        
        # 利用列表生成式 List Comprehension 來整理資料(適合單一欄位資料)
        mrt_list = [row[0] for row in results]
        
        return JSONResponse(content={
            "data": mrt_list
        })

    except Exception as e: # 先將此錯誤狀況命名為e
        # 在伺服器控制台印出詳細錯誤，方便除錯
        print(f"Error: {e}")
        # 回傳500錯誤訊息
        return JSONResponse(status_code=500, content={
            "error": True,
            "message": "伺服器內部錯誤"
        })
    
    finally:
        # 檢查游標是否存在，存在才關閉
        if 'cursor' in locals() and cursor:
            cursor.close()
        # 檢查連線變數名稱 con 是否存在且成功連線
        if 'con' in locals() and con:
            con.close()