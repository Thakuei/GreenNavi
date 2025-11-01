import japanize_matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st


def plot_buy_electricity(df: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(12, 6))
    monthly_avg_buy = df.groupby(df["TIME"].dt.to_period("M"))["buy_electricity"].mean()
    ax.bar(
        monthly_avg_buy.index.to_timestamp(),
        monthly_avg_buy,
        label="買電量 (kWh)",
        width=20,
    )
    ax.set_xlabel("時間")
    ax.set_ylabel("買電量 (kWh)")
    ax.set_title("買電量の時系列グラフ")
    ax.legend()
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    st.pyplot(fig)
