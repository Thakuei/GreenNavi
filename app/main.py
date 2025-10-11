import pandas as pd
from pathlib import Path
import streamlit as st

ICON_PATH = Path(__file__).parent / "images" / "GreenNavi.png"
if ICON_PATH.exists():
    st.set_page_config(page_title="GreenNavi", page_icon=str(ICON_PATH))
else:
    st.set_page_config(page_title="GreenNavi", page_icon=":seedling:")

st.title("GreenNavi")

st.sidebar.header("データをアップロード")
uploaded_file = st.sidebar.file_uploader(
    "CSVファイルを選択してください", type="csv"
)

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    st.success("CSVファイルを読み込みました")
    st.dataframe(df)
else:
    st.info("分析を始めるにはサイドバーからCSVファイルを選択してください")