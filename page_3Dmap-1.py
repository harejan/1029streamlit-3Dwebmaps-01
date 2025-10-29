import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk

st.title("Pydeck 3D 地圖 (向量 - 密度圖)")

# 0. 檢查 Mapbox 金鑰是否存在於 Secrets 中 (名稱應為 MAPBOX_API_KEY)
if "MAPBOX_API_KEY" not in st.secrets:
    st.error("Mapbox API Key (名稱需為 MAPBOX_API_KEY) 未設定！請在雲端 Secrets 中設定。")
    st.stop()

# --- 1. 生成範例資料 (向量) ---
data = pd.DataFrame({
    'lat': 25.0478 + np.random.randn(1000) / 50,
    'lon': 121.5170 + np.random.randn(1000) / 50,
})

# --- 2. 設定 Pydeck 圖層 (Layer) ---
layer_hexagon = pdk.Layer( # 稍微改個名字避免混淆
    'HexagonLayer',
    data=data,
    get_position='[lon, lat]',
    radius=100,
    elevation_scale=4,
    elevation_range=[0, 1000],
    pickable=True,
    extruded=True,
)

# --- 3. 設定攝影機視角 (View State) ---
view_state_hexagon = pdk.ViewState( # 稍微改個名字避免混淆
    latitude=25.0478,
    longitude=121.5170,
    zoom=12,
    pitch=50,
)

# --- 4. 組合圖層和視角並顯示 (第一個地圖) ---
r_hexagon = pdk.Deck( # 稍微改個名字避免混淆
    layers=[layer_hexagon],
    initial_view_state=view_state_hexagon,
    # mapbox_key=MAPBOX_KEY, # <-- 移除
    tooltip={"text": "這個區域有 {elevationValue} 個熱點"}
)
st.pydeck_chart(r_hexagon)


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