import pandas as pd
import streamlit as st

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
