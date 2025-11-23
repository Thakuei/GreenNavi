import japanize_matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st


# MAXのときにグラフが200にならないのは月で計算しているため日数の関係で割ると200にはならない
def plot_h2_storage_kwh(df: pd.DataFrame):
    df_copy = df.copy()
    df_copy["month"] = df_copy["TIME"].dt.month
    monthly_h2_storage = df_copy.groupby("month")["h2_storage_kwh"].sum()

    # 年度順に並べ替え（4→12→1→3）
    order = [4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2, 3]
    monthly_h2_storage_ordered = monthly_h2_storage.loc[order]
    # ここがポイント：棒を描く位置は 0〜11 の連番にする
    x = range(len(order))

    plt.figure(figsize=(12, 5))
    plt.bar(x, monthly_h2_storage_ordered.values, color="lightgreen")

    # 値の表示
    for idx, value in enumerate(monthly_h2_storage_ordered.values):
        plt.text(
            x=idx,  # ← x 座標は idx
            y=value + 2,
            s=f"{value:.1f}",
            ha="center",
            va="bottom",
        )

    plt.xlabel("月")
    plt.ylabel("水素貯蔵量 (kWh)")
    plt.title("水素貯蔵量の推移（4月スタート）")
    plt.grid(True)

    plt.xticks(x, order)

    plt.tight_layout()
    st.pyplot(plt)
