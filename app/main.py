import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st

ICON_PATH = ROOT / "images" / "greennavi.png"
if ICON_PATH.exists():
    st.set_page_config(page_title="GreenNavi", page_icon=str(ICON_PATH))
else:
    st.set_page_config(page_title="GreenNavi", page_icon=":seedling:")

from app.battery_only import run_battery_only_simulation
from app.graph.buy_electrivity import plot_buy_electricity
from app.graph.sell_electricity import plot_sell_electricity
from app.sidebar import render_sidebar
from app.simulation import run_simulation

st.header("GreenNavi", divider=True)

settings = render_sidebar()
uploaded_file = settings["uploaded_file"]
run_simulation_clicked = settings["run_simulation_clicked"]
compare_both = settings["compare_both"]

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    st.success("CSVファイルを読み込みました。ファイル名: {}".format(uploaded_file.name))

    st.subheader("現在の設定値")
    st.table(
        pd.DataFrame.from_dict(
            {
                "蓄電池最大容量": settings["max_battery_capacity"],
                "買電価格": settings["buy_price"],
                "売電価格": settings["sell_price"],
                "蓄電池定格出力": settings["battery_rated_power_kwh"],
                "水電解装置定格出力": settings["el_rated_power_kwh"],
                "水電解装置効率": settings["el_efficiency"],
                "水素貯蔵容量": settings["h2_storage_capacity_kwh"],
                "燃料電池定格出力": settings["fc_rated_power_kwh"],
                "燃料電池効率": settings["fc_efficiency"],
                "発電月": settings["production_month"],
                "消費月": settings["consumption_month"],
            },
            orient="index",
            columns=["値"],
        )
    )

    if run_simulation_clicked:
        simulation_settings = {
            key: value
            for key, value in settings.items()
            if key not in {"uploaded_file", "run_simulation_clicked"}
        }

        def summarize(df_: pd.DataFrame) -> pd.DataFrame:
            household_consumption = sum(df_["pv_net_pos_kwh"]) - sum(
                df_["sell_electricity"]
            )
            total_cost = df_["cost"].sum() * -1
            total_buy_electricity = df_["buy_electricity"].sum()
            total_sell_electricity = df_["sell_electricity"].sum()

            return pd.DataFrame.from_dict(
                {
                    "総コスト (円)": [total_cost],
                    "総買電量 (kWh)": [total_buy_electricity],
                    "総売電量 (kWh)": [total_sell_electricity],
                    "自家消費率 (%)": [
                        household_consumption / sum(df_["pv_net_pos_kwh"]) * 100
                    ],
                    "自給率 (%)": [
                        household_consumption
                        / (household_consumption + total_buy_electricity)
                        * 100
                    ],
                },
                orient="index",
                columns=["値"],
            )

        try:
            if compare_both:
                col_l, col_r = st.columns(2)

                with col_l:
                    st.subheader("蓄電池", divider=True)
                    with st.expander("蓄電池"):
                        result_df = run_battery_only_simulation(df, simulation_settings)
                        st.dataframe(result_df)
                    st.subheader("主要指標(蓄電池)", divider="green")
                    st.table(summarize(result_df))
                    st.subheader("時系列グラフ", divider="rainbow")
                    plot_sell_electricity(result_df)
                    plot_buy_electricity(result_df)

                with col_r:
                    st.subheader("蓄電池 + 水素", divider=True)
                    with st.expander("蓄電池 + 水素"):
                        result_df = run_simulation(df, simulation_settings)
                        st.dataframe(result_df)
                    st.subheader("主要指標(蓄電池 + 水素)", divider="green")
                    st.table(summarize(result_df))
                    st.subheader("時系列グラフ", divider="rainbow")
                    plot_sell_electricity(result_df)
                    plot_buy_electricity(result_df)

                result_df = None

            else:
                if settings["mode"] == "蓄電池":
                    st.subheader("蓄電池", divider=True)
                    result_df = run_battery_only_simulation(df, simulation_settings)
                else:
                    st.subheader("蓄電池 + 水素", divider=True)
                    result_df = run_simulation(df, simulation_settings)

        except KeyError as error:
            st.error(f"CSV内に必要な列が見つかりません: {error}")
            result_df = None
        except Exception as error:  # noqa: BLE001
            st.error(f"シミュレーションの実行中にエラーが発生しました: {error}")
            result_df = None

        if result_df is not None:
            st.subheader("シミュレーション結果")
            st.dataframe(result_df)
            st.subheader("主要指標")
            st.table(summarize(result_df))
            st.subheader("時系列グラフ", divider="rainbow")
            plot_sell_electricity(result_df)
            plot_buy_electricity(result_df)

    else:
        st.info(
            "設定を確認したらサイドバーの「シミュレーションを実行」を押してください"
        )
else:
    st.info("分析を始めるにはサイドバーからCSVファイルを選択してください")
