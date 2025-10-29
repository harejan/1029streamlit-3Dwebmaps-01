import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd


st.title("Plotly 3D 地球儀：全球極端貧窮人口比例")

# --- 1. 定義我們要使用的「原始」檔案和欄位 ---
# (這必須是您在 GitHub 上傳的原始檔案名稱)
ORIGINAL_CSV_FILE = "share-of-population-in-extreme-poverty.zip/share-of-population-in-extreme-poverty.csv"
DATA_COLUMN = "Share of population in poverty ($3 a day, 2021 prices)"

# --- 2. 讀取「原始」 CSV 檔案 ---
try:
    df_raw = pd.read_csv(ORIGINAL_CSV_FILE)
except FileNotFoundError:
    st.error(f"錯誤：找不到您的原始檔案 '{ORIGINAL_CSV_FILE}'。")
    st.error("請確保您已將原始的 ZIP 檔案內容上傳到 GitHub (與 app.py 放在一起)。")
    st.stop()
except Exception as e:
    st.error(f"讀取原始檔案時出錯: {e}")
    st.stop()

# --- 3. (關鍵) 在 Streamlit 中即時清理資料 ---
st.write("正在讀取原始資料並即時清理...")
try:
    # 轉換 'Year' 欄位為數字
    df_clean = df_raw.copy()
    df_clean['Year'] = pd.to_numeric(df_clean['Year'], errors='coerce')
    df_clean = df_clean.dropna(subset=['Year'])
    df_clean['Year'] = df_clean['Year'].astype(int)

    # 篩選掉「地區」資料 (只保留有 3 位 ISO 代碼的「國家」)
    df_clean = df_clean.dropna(subset=['Code'])
    df_countries = df_clean[df_clean['Code'].str.len() == 3].copy()

    # 找出「最近的」、「擁有最多數據」的年份
    st.write("正在尋找資料最完整的年份...")
    # 找出每年有多少國家的數據
    year_counts = df_countries.dropna(subset=[DATA_COLUMN])['Year'].value_counts()
    # 篩選出數據量大於 100 個國家的年份
    comprehensive_years = year_counts[year_counts > 100].index
    
    if comprehensive_years.empty:
        # 如果找不到，就用數據最多的那一年
        best_year = year_counts.idxmax()
    else:
        # 如果找到了，就用這些年份中「最近」的那一年
        best_year = comprehensive_years.max()
        
    st.success(f"找到資料最完整的年份: {best_year}")

    # 最終篩選出該年份的資料
    df_final = df_countries[df_countries['Year'] == best_year]
    
    # 篩選掉該年份中沒有實際貧窮數據的國家
    df_plottable = df_final.dropna(subset=[DATA_COLUMN])

except Exception as e:
    st.error(f"清理資料時發生錯誤: {e}")
    st.stop()


# --- 4. 建立 3D 地理散點圖 (scatter_geo) ---
st.info(f"正在顯示 {best_year} 年，{len(df_plottable)} 個國家/地區的資料。")

fig = px.scatter_geo(
    df_plottable,
    
    locations="Code",        # 國家代碼 (例如 "TWN", "USA")
    color=DATA_COLUMN,       # 依據貧窮比例上色
    hover_name="Entity",     # 滑鼠懸停時顯示國家名稱
    size=DATA_COLUMN,        # 點的大小也代表貧窮比例
    
    # *** 關鍵：使用 "orthographic" 投影法來建立 3D 地球儀 ***
    projection="orthographic",
    
    # 美化
    color_continuous_scale=px.colors.sequential.YlOrRd_r, # 使用反向的黃-橘-紅 色階
    title=f"全球極端貧窮人口比例 ({best_year}年)"
)

fig.update_layout(
    geo=dict(
        bgcolor= 'rgba(0,0,0,0)', # 地球背景透明
        showland=True,
        landcolor="rgb(217, 217, 217)", # 陸地顏色
    )
)

# --- 5. 在 Streamlit 中顯示 ---
st.plotly_chart(fig, use_container_width=True)

st.write("---")
st.subheader(f"資料來源 ({best_year}年，已清理並篩選)")
st.dataframe(df_plottable)

# --- 1. 讀取範例 DEM 資料 ---
# Plotly 內建的 "volcano" (火山) DEM 數據 (儲存為 CSV)
# 這是一個 2D 陣列 (Grid)，每個格子的值就是海拔
z_data = pd.read_csv("https://raw.githubusercontent.com/plotly/datasets/master/api_docs/mt_bruno_elevation.csv")

# --- 2. 建立 3D Surface 圖 ---
# 建立一個 Plotly 的 Figure 物件，它是所有圖表元素的容器
fig = go.Figure(
    # data 參數接收一個包含所有 "trace" (圖形軌跡) 的列表。
    # 每個 trace 定義了一組數據以及如何繪製它。
    data=[
        # 建立一個 Surface (曲面) trace
        go.Surface(
            # *** 關鍵參數：z ***
            # z 參數需要一個 2D 陣列 (或列表的列表)，代表在 X-Y 平面上每個點的高度值。
            # z_data.values 會提取 pandas DataFrame 底層的 NumPy 2D 陣列。
            # Plotly 會根據這個 2D 陣列的結構來繪製 3D 曲面。
            z=z_data.values,

            # colorscale 參數指定用於根據 z 值 (高度) 對曲面進行著色的顏色映射方案。
            # "Viridis" 是 Plotly 提供的一個常用且視覺效果良好的顏色漸層。
            # 高度值較低和較高的點會有不同的顏色。
            colorscale="Viridis"
        )
    ] # data 列表結束
)

# --- 3. 調整 3D 視角和外觀 ---
# 使用 update_layout 方法來修改圖表的整體佈局和外觀設定
fig.update_layout(
    # 設定圖表的標題文字
    title="Mt. Bruno 火山 3D 地形圖 (可旋轉)",

    # 設定圖表的寬度和高度 (單位：像素)
    width=800,
    height=700,

    # scene 參數是一個字典，用於配置 3D 圖表的場景 (座標軸、攝影機視角等)
    scene=dict(
        # 設定 X, Y, Z 座標軸的標籤文字
        xaxis_title='經度 (X)',
        yaxis_title='緯度 (Y)',
        zaxis_title='海拔 (Z)'
        # 可以在 scene 字典中加入更多參數來控制攝影機初始位置、座標軸範圍等
    )
)

# 這段程式碼執行後，變數 `fig` 將包含一個設定好的 3D Surface Plotly 圖表物件。
# 你可以接著使用 fig.show() 或 st.plotly_chart(fig) 將其顯示出來。
# 這個圖表通常是互動式的，允許使用者用滑鼠旋轉、縮放和平移 3D 視角。

# --- 4. 在 Streamlit 中顯示 ---
st.plotly_chart(fig)