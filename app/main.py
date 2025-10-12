from pathlib import Path

import pandas as pd
import streamlit as st

ICON_PATH = Path(__file__).parent / "images" / "GreenNavi.png"
if ICON_PATH.exists():
    st.set_page_config(page_title="GreenNavi", page_icon=str(ICON_PATH))
else:
    st.set_page_config(page_title="GreenNavi", page_icon=":seedling:")

st.title("GreenNavi")

st.sidebar.header("1. データをアップロード")
uploaded_file = st.sidebar.file_uploader(
    "CSVファイルを選択してください", type="csv"
)

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    st.success("CSVファイルを読み込みました")
    st.dataframe(df)
else:
    st.info("分析を始めるにはサイドバーからCSVファイルを選択してください")

st.sidebar.header("2. シミュレーション設定")

max_battery_capacity = st.sidebar.number_input(
    "蓄電池容量 (kWh)", value=14.6, min_value=0.0, step=0.1, format="%.1f"
)
buy_price = st.sidebar.number_input(
    "買電単価 (円/kWh)", value=31.0, min_value=0.0, step=0.5
)
sell_price = st.sidebar.number_input(
    "売電単価 (円/kWh)", value=16.0, min_value=0.0, step=0.5
)
battery_rated_power_kwh = st.sidebar.number_input(
    "蓄電池 定格出力 (kW)", value=3.0, min_value=0.0, step=0.5
)
el_rated_power_kwh = st.sidebar.number_input(
    "電解装置 定格出力 (kW)", value=3.0, min_value=0.0, step=0.5
)
el_efficiency = st.sidebar.slider(
    "電解装置 効率", min_value=0.0, max_value=1.0, value=0.5, step=0.05
)
h2_storage_capacity_kwh = st.sidebar.number_input(
    "水素貯蔵容量 (kWh換算)", value=200.0, min_value=0.0, step=5.0
)
fc_rated_power_kwh = st.sidebar.number_input(
    "燃料電池 定格出力 (kW)", value=3.0, min_value=0.0, step=0.5
)
fc_efficiency = st.sidebar.slider(
    "燃料電池 効率", min_value=0.0, max_value=1.0, value=0.5, step=0.05
)

months = list(range(1, 13))
production_month = st.sidebar.multiselect(
    "発電月", options=months, default=[4, 5, 6, 7, 8, 9, 10, 11]
)
consumption_month = st.sidebar.multiselect(
    "消費月", options=months, default=[1, 2, 3, 12]
)

# st.subheader("現在の設定値")
# st.write(
#     {
#         "max_battery_capacity": max_battery_capacity,
#         "buy_price": buy_price,
#         "sell_price": sell_price,
#         "battery_rated_power_kwh": battery_rated_power_kwh,
#         "el_rated_power_kwh": el_rated_power_kwh,
#         "el_efficiency": el_efficiency,
#         "h2_storage_capacity_kwh": h2_storage_capacity_kwh,
#         "fc_rated_power_kwh": fc_rated_power_kwh,
#         "fc_efficiency": fc_efficiency,
#         "production_month": production_month,
#         "consumption_month": consumption_month,
#     }
# )
