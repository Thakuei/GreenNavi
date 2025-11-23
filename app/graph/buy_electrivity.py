import japanize_matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st


def plot_buy_electricity(df: pd.DataFrame):
    df_copy = df.copy()
    df_copy["month"] = df_copy["TIME"].dt.month
    monthly_buy = df_copy.groupby("month")["buy_electricity"].sum()

    # 年度順に並べ替え（4→12→1→3）
    order = [4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2, 3]
    monthly_buy_ordered = monthly_buy.loc[order]

    # ここがポイント：棒を描く位置は 0〜11 の連番にする
    x = range(len(order))

    plt.figure(figsize=(12, 5))
    plt.bar(x, monthly_buy_ordered.values, color="lightgreen")

    # 値の表示
    for idx, value in enumerate(monthly_buy_ordered.values):
        plt.text(
            x=idx,  # ← x 座標は idx
            y=value + 2,
            s=f"{value:.1f}",
            ha="center",
            va="bottom",
        )

    plt.xlabel("月")
    plt.ylabel("買電量 (kWh)")
    plt.title("買電量の推移（4月スタート）")
    plt.grid(True)

    plt.xticks(x, order)

    plt.tight_layout()
    st.pyplot(plt)
