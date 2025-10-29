import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk

st.title("2024年高雄市觀光區人數 (向量 - 密度圖)")

# 0. 檢查 Mapbox 金鑰是否存在於 Secrets 中 (名稱應為 MAPBOX_API_KEY)
if "MAPBOX_API_KEY" not in st.secrets:
    st.error("Mapbox API Key (名稱需為 MAPBOX_API_KEY) 未設定！請在雲端 Secrets 中設定。")
    st.stop()

# --- 1. 上傳您那份「已包含經緯度」的 CSV 檔案 ---
uploaded_file = st.file_uploader(
    "請上傳您「已包含經緯度及遊客人數」的 CSV 檔案", 
    type=["csv"]
)

if uploaded_file is not None:
    st.write("---")
    st.subheader("步驟 1：讀取資料與欄位對應")
    
    try:
        data = pd.read_csv(uploaded_file)
        st.write("資料讀取成功，前 5 筆預覽：")
        st.dataframe(data.head())
    except Exception as e:
        st.error(f"讀取 CSV 時出錯: {e}")
        st.stop()

    # --- 2. (關鍵) 讓使用者手動對應欄位 ---
    # 這樣程式碼就有彈性，不怕您的欄位名稱不同
    
    st.write("---")
    st.subheader("步驟 2：請指定對應的欄位名稱")
    all_columns = data.columns.tolist()
    
    # 輔助函式：自動猜測可能的欄位名稱
    def guess_column(name_list, columns):
        for name in name_list: # 傳入可能的名稱
            for col in columns:
                if name.lower() in col.lower():
                    return col
        return columns[0] # 預設選第一個

    lat_col = st.selectbox(
        "請選擇『緯度』(Latitude) 欄位：", 
        all_columns, 
        index=all_columns.index(guess_column(['lat', '緯度'], all_columns))
    )
    lon_col = st.selectbox(
        "請選擇『經度』(Longitude) 欄位：", 
        all_columns, 
        index=all_columns.index(guess_column(['lon', 'lng', '經度'], all_columns))
    )
    weight_col = st.selectbox(
        "請選擇『權重 (遊客人數)』欄位：", 
        all_columns, 
        index=all_columns.index(guess_column(['人', '數', 'visit', 'tourist', '遊客'], all_columns))
    )

    # --- 3. (關鍵) 設定模擬比例 ---
    st.write("---")
    st.subheader("步驟 3：設定密度模擬")
    st.info("我們將依據「遊客人數」來生成模擬點，以呈現熱點。")
    
    # 讓使用者決定一個「比例尺」，例如 "每 1000 個遊客 = 1 個地圖上的點"
    scale_factor = st.slider(
        "請選擇比例尺：每 N 個遊客 = 1 個模擬點 (數字越小，地圖上的 3D 高塔越密、越高)", 
        min_value=1, 
        max_value=5000, 
        value=100  # 預設值設為 100
    )

    try:
        # --- 4. 生成模擬點 ---
        st.write(f"正在以 1:{scale_factor} 的比例生成模擬點...")
        points = []
        for _, row in data.iterrows():
            # 獲取座標和權重
            lat = pd.to_numeric(row[lat_col], errors='coerce')
            lon = pd.to_numeric(row[lon_col], errors='coerce')
            weight = pd.to_numeric(row[weight_col], errors='coerce') # 轉為數字，錯誤則忽略
            
            # 忽略缺資料的行
            if pd.isna(weight) or pd.isna(lat) or pd.isna(lon):
                continue 

            # 根據權重 (遊客人數) 和比例尺，計算要生成多少個點
            num_points = int(weight / scale_factor)
            
            # 在該景點的座標附近生成 num_points 個隨機點
            # (加上 np.random.randn() / 500 是為了讓點稍微散開，避免完全重疊)
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
        st.success(f"已成功從 {len(data)} 個景點，生成了 {len(data_for_map)} 個模擬點。")

        # --- 5. 設定 Pydeck (HexagonLayer) ---
        st.write("---")
        st.subheader("步驟 4：顯示 3D 觀光熱點地圖")
        layer_hexagon = pdk.Layer(
            'HexagonLayer',
            data=data_for_map, # <-- 使用我們新生成的 data_for_map
            get_position='[lon, lat]',
            radius=500, # 六邊形的半徑 (500 公尺)
            elevation_scale=10, # 高度拉高一點
            elevation_range=[0, 3000],
            pickable=True,
            extruded=True,
        )

        # 將地圖中心點設在所有景點的平均經緯度
        view_state_hexagon = pdk.ViewState(
            latitude=data[lat_col].mean(), 
            longitude=data[lon_col].mean(),
            zoom=10, # 縮放等級設為 10 (高雄市全覽)
            pitch=50, # 傾斜 50 度以顯示 3D
        )

        r_hexagon = pdk.Deck(
            layers=[layer_hexagon],
            initial_view_state=view_state_hexagon,
            tooltip={"text": "這個區域的熱度 (點)：{elevationValue}"}
        )
        
        # 顯示地圖！
        st.pydeck_chart(r_hexagon)
        
    except Exception as e:
        st.error(f"處理資料或繪圖時發生錯誤: {e}")

else:
    # 在使用者尚未上傳檔案時，顯示提示訊息
    st.info("請上傳您的 CSV 檔案以開始繪製「遊客熱點圖」。")

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