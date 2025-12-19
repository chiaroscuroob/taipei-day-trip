import json
import mysql.connector

# 連線到 MySQL 資料庫
con = mysql.connector.connect(
    user="root", 
    password="520038", 
    host="localhost", 
    database="taipei_day_trip" 
)
cursor = con.cursor()

# 讀取 JSON 檔案
with open("data/taipei-attractions.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# 取得景點列表
attractions = data["result"]["results"]

# 跑迴圈，處理每個景點
for item in attractions:
    # 基本資料擷取
    name = item["name"]
    category = item["CAT"]
    description = item["description"]
    address = item["address"]
    transport = item["direction"]
    mrt = item["MRT"]
    # 把經緯度轉成數字 (float)
    lat = float(item["latitude"])
    lng = float(item["longitude"])
    # 開放時間
    memo_time = item["MEMO_TIME"]
    # 圖片網址處理
    pic = item["file"]
    
    # 以"https://" 切割(但會被切掉,後續要補上)用 split('https://') 來切割
    urls = pic.split("https://")
    
    # 準備空的清單來放需要的網址
    good_images = []
    
    for url in urls:
        # 過濾空字串
        if url == "": 
            continue
            
        # 補回被切掉的 https://，同為文字可直接 + (一對一)
        full_url = "https://" + url
        
        # 檢查結尾是否為 jpg 或 png
        # 保險機制 lower() 將字轉小寫確保一致，.JPG →.jpg
        if full_url.lower().endswith(".jpg") or full_url.lower().endswith(".png"):
            good_images.append(full_url)
            
    # 把篩選好的網址，用逗號接起來變成一個長字串，存進資料庫(join可串一對多資訊)
    images_str = ",".join(good_images)

    # 將整理好的資料Insert into(插入/新增)到資料庫taipei的attraction表格
    sql = """
        INSERT INTO attraction (
            name, category, description, address, 
            transport, mrt, lat, lng, images, memo_time
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    # 要塞進去的數值，順序要跟sql內寫的欄位一致
    val = (
        name, category, description, address, 
        transport, mrt, lat, lng, images_str, memo_time
    )
    
    # 將val的資料放進sql的%s內
    cursor.execute(sql, val)

# 提交變更並關閉連線
con.commit() # 將變更存入資料庫
print("所有景點資料已成功匯入") # 純通知功能，告知執行已完成
cursor.close() # 釋放記憶體及運算資源
con.close() # 切斷連線