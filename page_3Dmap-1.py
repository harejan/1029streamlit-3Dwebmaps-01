import streamlit as st
import pandas as pd
import pydeck as pdk
# 注意：這個版本不再需要 numpy

st.title("高雄市觀光熱點 3D 柱狀圖")

# --- (重要) 1. 請在這裡設定您的檔案和欄位名稱 ---

# 1-1. 您的 CSV 檔案名稱
# (請確保這個檔案已上傳到 GitHub，與 app.py 放在一起)
YOUR_CSV_FILE = "kaohsiung_tourist.csv" 

# 1-2. 您 CSV 中「緯度」的「橫列標題」
# (根據您的檔案，這個應該是 'lat')
LAT_ROW_NAME = "lat" 

# 1-3. 您 CSV 中「經度」的「橫列標題」
# (根據您的檔案，這個應該是 'lon')
LON_ROW_NAME = "lon"

# 1-4. (*** 請務必修改此行 ***) 
# 請將 "遊客人數" 改成您 CSV 中代表「遊客人數」的「橫列標題」
# 例如: "2023年遊客人數", "總計", 或 "visitors"
WEIGHT_ROW_NAME = "遊客人數" # <--- 請檢查並修改此行

# ----------------------------------------------------


# 0. 檢查 Mapbox 金鑰
if "MAPBOX_API_KEY" not in st.secrets:
    st.error("Mapbox API Key (名稱需為 MAPBOX_API_KEY) 未設定！")
    st.stop()

# --- 2. (關鍵) 讀取並「轉置」您的 CSV 檔案 ---
try:
    # 讀取 CSV，並將第一欄 (景點名稱, lat, lon...) 作為索引 (index)
    data_raw = pd.read_csv(YOUR_CSV_FILE, index_col=0)
    
    # 執行「轉置」(Transpose)，讓 (壽山動物園, 旗津...) 變成「列」
    data = data_raw.T 
    
    # 將索引 (景點名稱) 變回一個普通的欄位
    data = data.reset_index()
    data = data.rename(columns={'index': '景點名稱'})
    
    # 檢查您在上方設定的欄位是否存在
    required_cols = {LAT_ROW_NAME, LON_ROW_NAME, WEIGHT_ROW_NAME, '景點名稱'}
    if not required_cols.issubset(data.columns):
        st.error(f"錯誤：您在程式碼中設定的「橫列標題」在 CSV 檔案中找不到。")
        st.error(f"您設定的欄位: {required_cols}")
        st.error(f"CSV 轉置後的實際欄位: {data.columns.tolist()}")
        st.error(f"請檢查程式碼第 10-19 行的設定，特別是 `WEIGHT_ROW_NAME`。")
        st.stop()
        
    # 轉換資料型別，以防萬一
    data[LAT_ROW_NAME] = pd.to_numeric(data[LAT_ROW_NAME], errors='coerce')
    data[LON_ROW_NAME] = pd.to_numeric(data[LON_ROW_NAME], errors='coerce')
    data[WEIGHT_ROW_NAME] = pd.to_numeric(data[WEIGHT_ROW_NAME], errors='coerce')
    
    # 移除任何缺少座標或遊客人數的資料
    data = data.dropna(subset=[LAT_ROW_NAME, LON_ROW_NAME, WEIGHT_ROW_NAME])
    
except FileNotFoundError:
    st.error(f"錯誤：找不到檔案 '{YOUR_CSV_FILE}'。")
    st.error("請確保您的 CSV 檔案已上傳到 Streamlit (與 app.py 放在一起)。")
    st.stop()
except Exception as e:
    st.error(f"讀取或轉置 CSV 時出錯: {e}")
    st.stop()

# --- 3. 定義 Pydeck 圖層 ---

# 圖層 A: 3D 柱狀圖 (ColumnLayer)
column_layer = pdk.Layer(
    'ColumnLayer',
    data=data,
    get_position=[LON_ROW_NAME, LAT_ROW_NAME],  # [經度, 緯度]
    get_elevation=WEIGHT_ROW_NAME,             # 高度 = 遊客人數
    elevation_scale=0.01, # 將遊客人數縮小，避免柱子太高
    radius=500,                                # 每個柱子的半徑 (500 公尺)
    get_fill_color=[255, 165, 0, 180],         # 柱子顏色 (橘色)
    pickable=True,
    extruded=True,
)

# 圖層 B: 景點名稱 (TextLayer)
text_layer = pdk.Layer(
    'TextLayer',
    data=data,
    get_position=[LON_ROW_NAME, LAT_ROW_NAME],
    get_text='景點名稱',
    get_color=[0, 0, 0, 200], # 文字顏色 (黑色)
    get_size=14,              # 文字大小
    get_alignment_baseline="'bottom'", # 文字顯示在座標「上方」
    get_pixel_offset=[0, -10] # 向上偏移 10 像素
)

# --- 4. 設定地圖視角和 Tooltip ---
view_state = pdk.ViewState(
    latitude=data[LAT_ROW_NAME].mean(),   # 視角中心 (平均緯度)
    longitude=data[LON_ROW_NAME].mean(), # 視角中心 (平均經度)
    zoom=9.5,                             # 縮放等級
    pitch=50,                             # 傾斜 50 度
)

# Tooltip (滑鼠移上去時顯示的資訊) - 簡化版語法
tooltip = {
    "html": "<b>{景點名稱}</b><br/>" + WEIGHT_ROW_NAME + ": {" + WEIGHT_ROW_NAME + "}"
}

# --- 5. 組合圖層並顯示地圖 ---
r = pdk.Deck(
    layers=[column_layer, text_layer], # 同時顯示兩個圖層
    initial_view_state=view_state,
    tooltip=tooltip,
)

st.pydeck_chart(r)

# --- 6. (可選) 顯示處理過的資料表 ---
st.write("---")
st.subheader("地圖資料來源（已轉置）")
st.dataframe(data[['景點名稱', LAT_ROW_NAME, LON_ROW_NAME, WEIGHT_ROW_NAME]])

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