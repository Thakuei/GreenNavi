from pathlib import Path
from sidebar import render_sidebar

import pandas as pd
import streamlit as st

ICON_PATH = Path(__file__).parent / "images" / "GreenNavi.png"
if ICON_PATH.exists():
    st.set_page_config(page_title="GreenNavi", page_icon=str(ICON_PATH))
else:
    st.set_page_config(page_title="GreenNavi", page_icon=":seedling:")

st.title("GreenNavi")

settings = render_sidebar()
uploaded_file = settings["uploaded_file"]

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    st.success("CSVファイルを読み込みました")
    st.write("ファイル名:", uploaded_file.name)
    st.dataframe(df)
else:
    st.info("分析を始めるにはサイドバーからCSVファイルを選択してください")

st.subheader("現在の設定値")
st.write(
    {
        "max_battery_capacity": settings["max_battery_capacity"],
        "buy_price": settings["buy_price"],
        "sell_price": settings["sell_price"],
        "battery_rated_power_kwh": settings["battery_rated_power_kwh"],
        "el_rated_power_kwh": settings["el_rated_power_kwh"],
        "el_efficiency": settings["el_efficiency"],
        "h2_storage_capacity_kwh": settings["h2_storage_capacity_kwh"],
        "fc_rated_power_kwh": settings["fc_rated_power_kwh"],
        "fc_efficiency": settings["fc_efficiency"],
        "production_month": settings["production_month"],
        "consumption_month": settings["consumption_month"],
    }
)
