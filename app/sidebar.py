import streamlit as st


def render_sidebar():
    st.sidebar.header("1. データをアップロード")
    uploaded_file = st.sidebar.file_uploader(
        "CSVファイルを選択してください", type="csv"
    )

    st.sidebar.header("2. シミュレーション設定")
    
    mode = st.sidebar.segmented_control(
        "モード選択",
        options=["蓄電池", "蓄電池 + 水素"],
        default = "蓄電池 + 水素",
        width="stretch",
    )

    max_battery_capacity = st.sidebar.number_input(
        "蓄電池容量 (kWh)",
        value=14.6,
        min_value=0.0,
        max_value=14.6,
        step=0.1,
        format="%.1f",
    )
    buy_price = st.sidebar.number_input(
        "買電単価 (円/kWh)", value=31.0, min_value=0.0, step=0.5
    )
    sell_price = st.sidebar.number_input(
        "売電単価 (円/kWh)", value=16.0, min_value=0.0, step=0.5
    )
    battery_rated_power_kwh = st.sidebar.number_input(
        "蓄電池 定格出力 (kW)", value=3.0, min_value=0.0, step=0.5
    )
    el_rated_power_kwh = st.sidebar.number_input(
        "水電解装置 定格出力 (kW)", value=3.0, min_value=0.0, step=0.5
    )
    el_efficiency = st.sidebar.slider(
        "水電解装置 効率", min_value=0.0, max_value=1.0, value=0.5, step=0.05
    )
    h2_storage_capacity_kwh = st.sidebar.number_input(
        "水素貯蔵容量 (kWh換算)", value=200.0, min_value=0.0, step=5.0
    )
    fc_rated_power_kwh = st.sidebar.number_input(
        "燃料電池 定格出力 (kW)", value=3.0, min_value=0.0, step=0.5
    )
    fc_efficiency = st.sidebar.slider(
        "燃料電池 効率", min_value=0.0, max_value=1.0, value=0.5, step=0.05
    )

    months = list(range(1, 13))
    production_month = st.sidebar.multiselect(
        "発電月", options=months, default=[4, 5, 6, 7, 8, 9, 10, 11]
    )
    consumption_month = st.sidebar.multiselect(
        "消費月", options=months, default=[1, 2, 3, 12]
    )

    run_simulation_clicked = st.sidebar.button(
        "シミュレーションを実行", type="primary", width="stretch"
    )

    return {
        "uploaded_file": uploaded_file,
        "max_battery_capacity": max_battery_capacity,
        "buy_price": buy_price,
        "sell_price": sell_price,
        "battery_rated_power_kwh": battery_rated_power_kwh,
        "el_rated_power_kwh": el_rated_power_kwh,
        "el_efficiency": el_efficiency,
        "h2_storage_capacity_kwh": h2_storage_capacity_kwh,
        "fc_rated_power_kwh": fc_rated_power_kwh,
        "fc_efficiency": fc_efficiency,
        "production_month": production_month,
        "consumption_month": consumption_month,
        "run_simulation_clicked": run_simulation_clicked,
    }
