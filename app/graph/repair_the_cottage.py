import japanize_matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

def plot_repair_the_cottage(df: pd.DataFrame):
    df_copy = df.copy()
    df_copy["month"] = df_copy["TIME"].dt.month

    # PVで賄えなかった不足（PVの後ろの不足）
    df_copy["shortage_after_pv"] = (df_copy["load_site_kwh"] - df_copy["pv_net_pos_kwh"]).clip(lower=0)

    # 月別集計（kWh）
    monthly = df_copy.groupby("month").agg(
        shortage_after_pv=("shortage_after_pv", "sum"),
        battery_discharge=("discharge", "sum"),
        fc_output=("fc_output_used_kwh", "sum"),
        grid_buy=("buy_electricity", "sum"),
    )

    # ★ 4月スタート順に並べ替え
    order = [4,5,6,7,8,9,10,11,12,1,2,3]
    monthly = monthly.loc[order]
    x = list(range(len(order)))

    # NumPy配列にして stacked bar の bottom に使う
    months = monthly.index.values
    batt = monthly["battery_discharge"].values
    fc   = monthly["fc_output"].values
    grid = monthly["grid_buy"].values

    plt.figure(figsize=(10, 8))

    # バッテリー
    plt.bar(x, batt, label="バッテリー放電量", color="lightskyblue")

    # 燃料電池（バッテリーの上に積む）
    plt.bar(x, fc, bottom=batt, label="燃料電池出力", color="lightgreen")

    # 買電（バッテリー＋FCの上に積む）
    plt.bar(x, grid, bottom=batt + fc, label="買電量", color="gold")

    plt.xlabel("月")
    plt.ylabel("電力量 (kWh)")
    plt.title("コテージ不足電力を何で補ったか（月別・4月スタート）")

    # ★ x軸も年度順に修正
    plt.xticks(x, months)

    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    st.pyplot(plt)
