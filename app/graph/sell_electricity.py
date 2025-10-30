import matplotlib.pyplot as plt
import japanize_matplotlib
import streamlit as st
import pandas as pd

def plot_sell_electricity(df: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(12, 6))
    monthly_avg_sell = df.groupby(df["TIME"].dt.to_period("M"))["sell_electricity"].mean()
    ax.bar(monthly_avg_sell.index.to_timestamp(), monthly_avg_sell, label="売電量 (kWh)", width=20)
    ax.set_xlabel("時間")
    ax.set_ylabel("売電量 (kWh)")
    ax.set_title("売電量の時系列グラフ")
    ax.legend()
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    st.pyplot(fig)
