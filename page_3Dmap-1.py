import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk

st.title("高雄市觀光熱點 3D 密度圖")
st.subheader("（依遊客人數加權）")

# --- 1. 設定您的檔案名稱 ---
# (請確保這個檔案已上傳到 GitHub，與 app.py 放在一起)
YOUR_CSV_FILE = "kaohsiung_tourist.csv" 

# ------------------------------

# 0. 檢查 Mapbox 金鑰
if "MAPBOX_API_KEY" not in st.secrets:
    st.error("Mapbox API Key (名稱需為 MAPBOX_API_KEY) 未設定！")
    st.stop()

# --- 2. (關鍵) 讀取並「轉置」您的 CSV 檔案 ---
try:
    # 讀取 CSV，並將第一欄 (景點名稱) 作為索引 (index)
    data_raw = pd.read_csv(YOUR_CSV_FILE, index_col=0)
    
    # 執行「轉置」(Transpose)，讓 (壽山動物園, 旗津...) 變成「列」
    data = data_raw.T 
    
    # 將索引 (景點名稱) 變回一個普通的欄位
    data = data.reset_index()
    
    # 重新命名這個新欄位，方便辨識
    data = data.rename(columns={'index': '景點名稱'})
    
    st.success(f"成功讀取並轉置檔案 '{YOUR_CSV_FILE}'！")
    
except FileNotFoundError:
    st.error(f"錯誤：找不到檔案 '{YOUR_CSV_FILE}'。")
    st.error("請確保您的 CSV 檔案已上傳到 Streamlit (與 app.py 放在一起)。")
    st.stop()
except Exception as e:
    st.error(f"讀取或轉置 CSV 時出錯: {e}")
    st.stop()

# --- 3. (關鍵) 讓使用者手動對應欄位 ---
# 現在 data 已經是「長資料」，我們可以用下拉選單來選欄位
st.write("---")
st.subheader("步驟 1：請指定對應的欄位名稱")
st.info("程式已自動將您的寬資料轉置。請檢查以下欄位是否正確。")

all_columns = data.columns.tolist()

# 輔助函式：自動猜測可能的欄位名稱
def guess_column(name_list, columns):
    for name in name_list: # 傳入可能的名稱
        for col in columns:
            if name.lower() in col.lower():
                return col
    return columns[0] # 預設選第一個

# 讓使用者選擇 緯度
lat_col = st.selectbox(
    "請選擇『緯度』(Latitude) 欄位：", 
    all_columns, 
    index=all_columns.index(guess_column(['lat', '緯度'], all_columns))
)
# 讓使用者選擇 經度
lon_col = st.selectbox(
    "請選擇『經度』(Longitude) 欄位：", 
    all_columns, 
    index=all_columns.index(guess_column(['lon', 'lng', '經度'], all_columns))
)
# 讓使用者選擇 遊客人數 (權重)
# 這裡會列出所有 'lat', 'lon', '景點名稱' 以外的欄位
weight_options = [col for col in all_columns if col not in [lat_col, lon_col, '景點名稱']]
if not weight_options:
    st.error("錯誤：找不到任何可作為「遊客人數」的欄位。")
    st.stop()

weight_col = st.selectbox(
    "請選擇『權重 (遊客人數)』欄位：", 
    weight_options, 
    index=weight_options.index(guess_column(['人', '數', 'visit', 'tourist', '遊客'], weight_options))
)

st.success(f"您選擇以「{weight_col}」作為密度權重。")

# --- 4. 設定模擬比例 ---
st.write("---")
st.subheader("步驟 2：設定密度模擬")
scale_factor = st.slider(
    "請調整比例尺：每 N 個遊客 = 1 個模擬點 (數字越小，地圖 3D 高塔越密、越高)", 
    min_value=10, 
    max_value=20000, 
    value=5000, # 預設值
    step=10
)

# --- 5. 生成模擬點並繪製地圖 ---
try:
    points = []
    for _, row in data.iterrows():
        lat = pd.to_numeric(row[lat_col], errors='coerce')
        lon = pd.to_numeric(row[lon_col], errors='coerce')
        weight = pd.to_numeric(row[weight_col], errors='coerce')
        
        if pd.isna(weight) or pd.isna(lat) or pd.isna(lon) or weight <= 0:
            continue 

        num_points = int(weight / scale_factor)
        
        for _ in range(num_points):
            points.append({
                "lat": lat + np.random.randn() / 500,
                "lon": lon + np.random.randn() / 500,
            })
    
    if not points:
        st.warning("生成的點數量為 0。")
        st.info("可能原因：您設定的「比例尺」數字太大。請試著將滑桿往左拉。")
        st.stop()
        
    data_for_map = pd.DataFrame(points)

    # --- 6. 設定 Pydeck (HexagonLayer) ---
    st.write("---")
    st.subheader(f"步驟 3：{weight_col} 觀光熱點地圖")
    layer_hexagon = pdk.Layer(
        'HexagonLayer',
        data=data_for_map,
        get_position='[lon, lat]',
        radius=1000, 
        elevation_scale=20, 
        elevation_range=[0, 3000],
        pickable=True,
        extruded=True,
    )

    view_state_hexagon = pdk.ViewState(
        latitude=data[lat_col].astype(float).mean(), 
        longitude=data[lon_col].astype(float).mean(),
        zoom=9.5, 
        pitch=50, 
    )

    r_hexagon = pdk.Deck(
        layers=[layer_hexagon],
        initial_view_state=view_state_hexagon,
        tooltip={"text": "這個區域的熱度 (點)：{elevationValue}"}
    )
    
    st.pydeck_chart(r_hexagon)
    
    # 顯示原始資料表 (可選)
    st.write("---")
    st.subheader("轉置後的原始資料預覽")
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