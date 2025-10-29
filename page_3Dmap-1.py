import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk

# --- (重要) 1. 請將這個設定區塊加到您 page_3Dmap-1.py 的最上方 ---

# **** 1-1. 您的 CSV 檔案名稱 ****
YOUR_CSV_FILE = "kaohsiung_tourist.csv" 

# **** 1-2. (請檢查) 您的「緯度」欄位名稱 ****
LAT_COLUMN = "lat"  # <--- 如果您的欄位名稱是 '緯度'，請改成 "緯度"

# **** 1-3. (請檢查) 您的「經度」欄位名稱 ****
LON_COLUMN = "lon"  # <--- 如果您的欄位名稱是 '經度'，請改成 "經度"

# **** 1-4. (請檢查) 您的「遊客人數」欄位名稱 ****
WEIGHT_COLUMN = "visitors" # <--- 請改成您遊客人數的實際欄位名稱

# --------------------------------------------

st.title("2024年高雄市觀光區人數 (向量 - 密度圖)")

# 0. 檢查 Mapbox 金鑰是否存在於 Secrets 中 (名稱應為 MAPBOX_API_KEY)
if "MAPBOX_API_KEY" not in st.secrets:
    st.error("Mapbox API Key (名稱需為 MAPBOX_API_KEY) 未設定！請在雲端 Secrets 中設定。")
    st.stop()

# --- 2. 直接讀取檔案 ---
try:
    data = pd.read_csv(YOUR_CSV_FILE)
except FileNotFoundError:
    st.error(f"錯誤：找不到檔案 '{YOUR_CSV_FILE}'。")
    st.error("請確保您的 CSV 檔案已上傳到 Streamlit (與 app.py 放在一起)，並且上面的檔案名稱拼寫正確。")
    st.stop()
except Exception as e:
    st.error(f"讀取 CSV '{YOUR_CSV_FILE}' 時出錯: {e}")
    st.stop()

# --- 3. 檢查欄位是否存在 ---
required_columns = {LAT_COLUMN, LON_COLUMN, WEIGHT_COLUMN}
if not required_columns.issubset(data.columns):
    st.error(f"錯誤：您在程式碼中設定的欄位名稱在 CSV 檔案中找不到。")
    st.error(f"您設定的欄位： {required_columns}")
    st.error(f"CSV 實際有的欄位： {data.columns.tolist()}")
    st.stop()


# --- 4. 設定模擬比例 (保留互動性) ---
st.info("我們將依據「遊客人數」來生成模擬點，以呈現熱點。")

scale_factor = st.slider(
    "請調整比例尺：每 N 個遊客 = 1 個模擬點 (數字越小，地圖 3D 高塔越密、越高)", 
    min_value=1, 
    max_value=5000, 
    value=100  # 預設值
)

# --- 5. 生成模擬點並繪製地圖 ---
try:
    points = []
    for _, row in data.iterrows():
        lat = pd.to_numeric(row[LAT_COLUMN], errors='coerce')
        lon = pd.to_numeric(row[LON_COLUMN], errors='coerce')
        weight = pd.to_numeric(row[WEIGHT_COLUMN], errors='coerce')
        
        if pd.isna(weight) or pd.isna(lat) or pd.isna(lon):
            continue 

        num_points = int(weight / scale_factor)
        
        for _ in range(num_points):
            points.append({
                "lat": lat + np.random.randn() / 500,
                "lon": lon + np.random.randn() / 500,
            })
    
    if not points:
        st.warning("生成的點數量為 0。")
        st.info("可能原因：您設定的「比例尺」數字太大，或「遊客人數」欄位數值太小。請試著將滑桿往左拉 (例如 50 或 10)。")
        st.stop()
        
    data_for_map = pd.DataFrame(points)

    # --- 6. 設定 Pydeck (HexagonLayer) ---
    st.subheader("3D 觀光熱點地圖")
    layer_hexagon = pdk.Layer(
        'HexagonLayer',
        data=data_for_map,
        get_position='[lon, lat]',
        radius=500, 
        elevation_scale=10, 
        elevation_range=[0, 3000],
        pickable=True,
        extruded=True,
    )

    # 將地圖中心點設在所有景點的平均經緯度
    view_state_hexagon = pdk.ViewState(
        latitude=data[LAT_COLUMN].mean(), 
        longitude=data[LON_COLUMN].mean(),
        zoom=10, 
        pitch=50, 
    )

    r_hexagon = pdk.Deck(
        layers=[layer_hexagon],
        initial_view_state=view_state_hexagon,
        tooltip={"text": "這個區域的熱度 (點)：{elevationValue}"}
    )
    
    # 顯示地圖！
    st.pydeck_chart(r_hexagon)
    
    # 顯示原始資料表 (可選)
    st.write("---")
    st.subheader("原始資料預覽")
    st.dataframe(data)
    
except Exception as e:
    st.error(f"處理資料或繪圖時發生錯誤: {e}")

# ===============================================
#          第二個地圖：模擬 DEM
# ===============================================

st.title("Pydeck 3D 地圖 (網格 - DEM 模擬)")

# --- 1. 模擬 DEM 網格資料 ---
x, y = np.meshgrid(np.linspace(-1, 1, 50), np.linspace(-1, 1, 50))
z = np.exp(-(x**2 + y**2) * 2) * 1000

data_dem_list = [] # 修正: 建立一個列表來收集字典
base_lat, base_lon = 25.0, 121.5
for i in range(50):
    for j in range(50):
        data_dem_list.append({ # 修正: 將字典附加到列表中
            "lon": base_lon + x[i, j] * 0.1,
            "lat": base_lat + y[i, j] * 0.1,
            "elevation": z[i, j]
        })
df_dem = pd.DataFrame(data_dem_list) # 從列表創建 DataFrame

# --- 2. 設定 Pydeck 圖層 (GridLayer) ---
layer_grid = pdk.Layer( # 稍微改個名字避免混淆
    'GridLayer',
    data=df_dem,
    get_position='[lon, lat]',
    get_elevation_weight='elevation', # 使用 'elevation' 欄位當作高度
    elevation_scale=1,
    cell_size=2000,
    extruded=True,
    pickable=True # 加上 pickable 才能顯示 tooltip
)

# --- 3. 設定視角 (View) ---
view_state_grid = pdk.ViewState( # 稍微改個名字避免混淆
    latitude=base_lat, longitude=base_lon, zoom=10, pitch=50
)

# --- 4. 組合並顯示 (第二個地圖) ---
r_grid = pdk.Deck( # 稍微改個名字避免混淆
    layers=[layer_grid],
    initial_view_state=view_state_grid,
    # mapbox_key=MAPBOX_KEY, # <--【修正點】移除這裡的 mapbox_key
    tooltip={"text": "海拔高度: {elevationValue} 公尺"} # GridLayer 用 elevationValue
)
st.pydeck_chart(r_grid)