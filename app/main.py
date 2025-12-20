import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st

ICON_PATH = ROOT / "images" / "greennavi.png"
if ICON_PATH.exists():
    st.set_page_config(page_title="GreenNavi", page_icon=str(ICON_PATH), layout="wide")
else:
    st.set_page_config(page_title="GreenNavi", page_icon=":seedling:", layout="wide")

from app.battery_and_hydrogen import run_battery_and_hydrogen_simulation
from app.battery_and_hydrogen_ev import run_battery_and_hydrogen_ev_simulation
from app.battery_only import run_battery_only_simulation
from app.graph.buy_electrivity import plot_buy_electricity
from app.graph.h2_storage_kwh import plot_h2_storage_kwh
from app.graph.repair_the_cottage import plot_repair_the_cottage
from app.graph.sell_electricity import plot_sell_electricity
from app.sidebar import render_sidebar

st.header("GreenNavi", divider=True)

settings = render_sidebar()
uploaded_file = settings["uploaded_file"]
run_simulation_clicked = settings["run_simulation_clicked"]
compare_both = settings["compare_both"]

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)

    if "TIME" in df.columns:
        df["TIME"] = pd.to_datetime(df["TIME"], errors="coerce")
        df = df.dropna(subset=["TIME"]).reset_index(drop=True)

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
                "EVバッテリー容量": settings["ev_capacity_kwh"],
                "EV充電出力": settings["ev_charge_power_kwh"],
                "EV電費": settings["ev_eff_km_per_kwh"],
                "EV走行予定総距離(km/日)": settings["ev_daily_distance_km"],
                "EV運行回数(回/日)": settings["ev_max_trips_per_day"],
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

        def summarize(
            df_: pd.DataFrame, battery_only_simulation: float = None
        ) -> pd.DataFrame:
            household_consumption = sum(df_["pv_net_pos_kwh"]) - sum(
                df_["sell_electricity"]
            )
            total_cost = df_["cost"].sum() * -1
            total_buy_electricity = df_["buy_electricity"].sum()
            total_sell_electricity = df_["sell_electricity"].sum()
            carbon_dioxide_emissions = total_buy_electricity * 0.431  # kg-CO2/kWh
            result = {
                "エネルギーコスト (円)": [total_cost],
                "総買電量 (kWh)": [total_buy_electricity],
                "総売電量 (kWh)": [total_sell_electricity],
                "自家消費率 (%)": [
                    household_consumption / sum(df_["pv_net_pos_kwh"]) * 100
                ],
                "二酸化炭素排出量(kg-CO2)": [carbon_dioxide_emissions],  # kg-CO2
            }

            if battery_only_simulation is not None:
                reduction_rate = (total_buy_electricity / battery_only_simulation) * 100
                result["削減率 (%) (削減率=水素導入時の買電量/蓄電池単体の買電量)"] = [
                    reduction_rate
                ]
            else:
                result["削減率 (%) (削減率=水素導入時の買電量/蓄電池単体の買電量)"] = [
                    "--"
                ]

            return pd.DataFrame.from_dict(
                result,
                orient="index",
                columns=["値"],
            )

        try:
            if compare_both and settings["mode"] in (
                "蓄電池 + 水素",
                "蓄電池 + 水素 + EV",
            ):
                if settings["mode"] == "蓄電池 + 水素":
                    col_l, col_r = st.columns(2)

                    with col_l:
                        st.subheader("蓄電池", divider=True)
                        with st.expander("蓄電池"):
                            result_df_battery = run_battery_only_simulation(
                                df, simulation_settings
                            )
                            st.dataframe(result_df_battery)
                        battery_only_simulation = result_df_battery[
                            "buy_electricity"
                        ].sum()
                        st.subheader("主要指標(蓄電池)", divider="green")
                        st.table(summarize(result_df_battery))
                        st.subheader("時系列グラフ", divider="rainbow")
                        plot_sell_electricity(result_df_battery)
                        plot_buy_electricity(result_df_battery)

                    with col_r:
                        st.subheader("蓄電池 + 水素", divider=True)
                        with st.expander("蓄電池 + 水素"):
                            result_df_hydrogen = run_battery_and_hydrogen_simulation(
                                df, simulation_settings
                            )
                            st.dataframe(result_df_hydrogen)
                        st.subheader("主要指標(蓄電池 + 水素)", divider="green")
                        st.table(summarize(result_df_hydrogen, battery_only_simulation))
                        st.subheader("時系列グラフ", divider="rainbow")
                        plot_sell_electricity(result_df_hydrogen)
                        plot_buy_electricity(result_df_hydrogen)
                        plot_h2_storage_kwh(result_df_hydrogen)
                        plot_repair_the_cottage(result_df_hydrogen)

                    result_df = None
                else:
                    col_batt, col_h2, col_ev = st.columns(3)

                    with col_batt:
                        st.subheader("蓄電池", divider=True)
                        with st.expander("蓄電池"):
                            result_df_battery = run_battery_only_simulation(
                                df, simulation_settings
                            )
                            st.dataframe(result_df_battery)
                        battery_only_simulation = result_df_battery[
                            "buy_electricity"
                        ].sum()
                        st.subheader("主要指標(蓄電池)", divider="green")
                        st.table(summarize(result_df_battery))
                        st.subheader("時系列グラフ", divider="rainbow")
                        plot_sell_electricity(result_df_battery)
                        plot_buy_electricity(result_df_battery)

                    with col_h2:
                        st.subheader("蓄電池 + 水素", divider=True)
                        with st.expander("蓄電池 + 水素"):
                            result_df_hydrogen = run_battery_and_hydrogen_simulation(
                                df, simulation_settings
                            )
                            st.dataframe(result_df_hydrogen)
                        st.subheader("主要指標(蓄電池 + 水素)", divider="green")
                        st.table(summarize(result_df_hydrogen, battery_only_simulation))
                        st.subheader("時系列グラフ", divider="rainbow")
                        plot_sell_electricity(result_df_hydrogen)
                        plot_buy_electricity(result_df_hydrogen)
                        plot_h2_storage_kwh(result_df_hydrogen)
                        plot_repair_the_cottage(result_df_hydrogen)

                    with col_ev:
                        st.subheader("蓄電池 + 水素 + EV", divider=True)
                        with st.expander("蓄電池 + 水素 + EV"):
                            result_df_ev = run_battery_and_hydrogen_ev_simulation(
                                df, simulation_settings
                            )
                            st.dataframe(result_df_ev)
                        st.subheader("主要指標(蓄電池 + 水素 + EV)", divider="green")
                        st.table(summarize(result_df_ev, battery_only_simulation))
                        st.subheader("時系列グラフ", divider="rainbow")
                        plot_sell_electricity(result_df_ev)
                        plot_buy_electricity(result_df_ev)
                        plot_h2_storage_kwh(result_df_ev)

                    result_df = None

            else:
                if settings["mode"] == "蓄電池":
                    st.subheader("蓄電池", divider=True)
                    result_df = run_battery_only_simulation(df, simulation_settings)
                elif settings["mode"] == "蓄電池 + 水素":
                    st.subheader("蓄電池 + 水素", divider=True)
                    result_df = run_battery_and_hydrogen_simulation(
                        df, simulation_settings
                    )
                else:
                    st.subheader("蓄電池 + 水素 + EV", divider=True)
                    result_df = run_battery_and_hydrogen_ev_simulation(
                        df, simulation_settings
                    )

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
            plot_repair_the_cottage(result_df)
            if settings["mode"] in ("蓄電池 + 水素", "蓄電池 + 水素 + EV"):
                plot_h2_storage_kwh(result_df)

    else:
        st.info(
            "設定を確認したらサイドバーの「シミュレーションを実行」を押してください"
        )
else:
    st.info("分析を始めるにはサイドバーからCSVファイルを選択してください")
