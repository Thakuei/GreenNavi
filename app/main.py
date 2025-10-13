import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st

from app.sidebar import render_sidebar
from app.simulation import run_simulation

ICON_PATH = Path(__file__).parent / "images" / "GreenNavi.png"
if ICON_PATH.exists():
    st.set_page_config(page_title="GreenNavi", page_icon=str(ICON_PATH))
else:
    st.set_page_config(page_title="GreenNavi", page_icon=":seedling:")

st.title("GreenNavi")

settings = render_sidebar()
uploaded_file = settings["uploaded_file"]
run_simulation_clicked = settings["run_simulation_clicked"]

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    st.success("CSVファイルを読み込みました")
    st.write("ファイル名:", uploaded_file.name)

    st.subheader("現在の設定値")
    st.table(
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

    if run_simulation_clicked:
        simulation_settings = {
            key: value
            for key, value in settings.items()
            if key not in {"uploaded_file", "run_simulation_clicked"}
        }

        try:
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
            st.table(
                {
                    "総コスト (円)": [result_df["cost"].sum() * -1],
                    "総買電量 (kWh)": [result_df["buy_electricity"].sum()],
                    "総売電量 (kWh)": [result_df["sell_electricity"].sum()],
                }
            )
    else:
        st.info(
            "設定を確認したらサイドバーの「シミュレーションを実行」を押してください"
        )
else:
    st.info("分析を始めるにはサイドバーからCSVファイルを選択してください")
