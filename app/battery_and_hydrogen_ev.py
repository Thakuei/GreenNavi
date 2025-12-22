from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

import pandas as pd


@dataclass
class SimulationParams:
    max_battery_capacity: float
    buy_price: float
    sell_price: float
    battery_rated_power_kwh: float
    el_rated_power_kwh: float
    el_efficiency: float
    h2_storage_capacity_kwh: float
    fc_rated_power_kwh: float
    fc_efficiency: float
    production_month: Sequence[int]
    consumption_month: Sequence[int]
    ev_capacity_kwh: float
    ev_charge_power_kwh: float
    ev_eff_km_per_kwh: float
    ev_daily_distance_km: float
    ev_max_trips_per_day: int
    ev_trip_energy_kwh: float


def _cost_and_battery_capacity(
    row: pd.Series,
    battery_capacity: float,
    h2_storage_kwh: float,
    ev_soc_kwh: float,
    ev_trips_today: int,
    params: SimulationParams,
):
    load = row["load_site_kwh"]
    pv = row["pv_net_pos_kwh"]
    month = row["TIME"].month

    battery_space = params.max_battery_capacity - battery_capacity

    charge = 0.0
    discharge = 0.0
    buy_electricity = 0.0
    sell_electricity = 0.0
    remain_surplus = 0.0

    if pv >= load:
        surplus = pv - load
        if surplus >= params.battery_rated_power_kwh:
            if battery_space >= params.battery_rated_power_kwh:
                charge = params.battery_rated_power_kwh
                remain_surplus = surplus - params.battery_rated_power_kwh
            else:
                charge = battery_space
                remain_surplus = surplus - battery_space
        else:
            if battery_space >= surplus:
                charge = surplus
            else:
                charge = battery_space
                remain_surplus = surplus - battery_space
    else:
        shortage = load - pv
        if shortage >= params.battery_rated_power_kwh:
            if battery_capacity >= params.battery_rated_power_kwh:
                discharge = params.battery_rated_power_kwh
                buy_electricity = shortage - params.battery_rated_power_kwh
            else:
                discharge = battery_capacity
                buy_electricity = shortage - battery_capacity
        else:
            if battery_capacity >= shortage:
                discharge = shortage
            else:
                discharge = battery_capacity
                buy_electricity = shortage - battery_capacity

    battery_capacity = battery_capacity + charge - discharge
    if battery_capacity > params.max_battery_capacity:
        battery_capacity = params.max_battery_capacity
    if battery_capacity < 0:
        battery_capacity = 0.0

    h2_energy_kwh = 0.0
    el_input_used_kwh = 0.0
    fc_output_used_kwh = 0.0
    buy_before_h2 = buy_electricity

    ev_charge_used_kwh = 0.0
    ev_trip_count_this_hour = 0

    if month in params.production_month:
        surplus_after_h2 = 0.0
        if remain_surplus > 0:
            h2_storage_space_kwh = params.h2_storage_capacity_kwh - h2_storage_kwh
            h2_storage_space_kwh = max(h2_storage_space_kwh, 0.0)
            if h2_storage_space_kwh > 0:
                storage_limit_kwh = h2_storage_space_kwh / params.el_efficiency
                el_input_used_kwh = min(
                    remain_surplus, params.el_rated_power_kwh, storage_limit_kwh
                )

                h2_energy_kwh = el_input_used_kwh * params.el_efficiency
                h2_storage_kwh = min(
                    h2_storage_kwh + h2_energy_kwh, params.h2_storage_capacity_kwh
                )
                surplus_after_h2 = max(remain_surplus - el_input_used_kwh, 0.0)
            else:
                surplus_after_h2 = remain_surplus
        else:
            surplus_after_h2 = 0.0

        if surplus_after_h2 > 0:
            ev_space = max(params.ev_capacity_kwh - ev_soc_kwh, 0.0)
            if ev_space > 0:
                ev_charge_used_kwh = min(
                    surplus_after_h2, params.ev_charge_power_kwh, ev_space
                )
                ev_soc_kwh += ev_charge_used_kwh
                surplus_after_h2 -= ev_charge_used_kwh

        sell_electricity = max(surplus_after_h2, 0.0)

    elif month in params.consumption_month:
        if remain_surplus > 0:
            sell_electricity = remain_surplus

        if buy_electricity > 0 and h2_storage_kwh > 0:
            fc_possible_by_storage = h2_storage_kwh * params.fc_efficiency
            fc_possible = min(params.fc_rated_power_kwh, fc_possible_by_storage)

            fc_output_used_kwh = min(buy_electricity, fc_possible)
            if fc_output_used_kwh > 0:
                h2_consumed_kwh = fc_output_used_kwh / params.fc_efficiency
                h2_storage_kwh = max(h2_storage_kwh - h2_consumed_kwh, 0.0)
                buy_electricity -= fc_output_used_kwh

    if params.ev_max_trips_per_day > 0 and params.ev_trip_energy_kwh > 0:
        if (
            ev_trips_today < params.ev_max_trips_per_day
            and ev_soc_kwh >= params.ev_trip_energy_kwh
        ):
            ev_soc_kwh -= params.ev_trip_energy_kwh
            ev_trips_today += 1
            ev_trip_count_this_hour = 1

    cost = buy_electricity * params.buy_price - sell_electricity * params.sell_price

    return (
        cost,
        battery_capacity,
        charge,
        discharge,
        buy_electricity,
        sell_electricity,
        remain_surplus,
        h2_storage_kwh,
        h2_energy_kwh,
        el_input_used_kwh,
        fc_output_used_kwh,
        buy_before_h2,
        ev_soc_kwh,
        ev_charge_used_kwh,
        ev_trip_count_this_hour,
        ev_trips_today,
    )


def run_battery_and_hydrogen_ev_simulation(
    df: pd.DataFrame, settings: Mapping[str, object]
) -> pd.DataFrame:
    """
    Run the hourly simulation and return a DataFrame with additional metrics.
    """
    if df.empty:
        return df.copy()

    ev_trip_energy_kwh = (
        float(settings["ev_daily_distance_km"])
        / float(settings["ev_eff_km_per_kwh"])
        / int(settings["ev_max_trips_per_day"])
    )

    params = SimulationParams(
        max_battery_capacity=settings["max_battery_capacity"],
        buy_price=settings["buy_price"],
        sell_price=settings["sell_price"],
        battery_rated_power_kwh=settings["battery_rated_power_kwh"],
        el_rated_power_kwh=settings["el_rated_power_kwh"],
        el_efficiency=settings["el_efficiency"],
        h2_storage_capacity_kwh=settings["h2_storage_capacity_kwh"],
        fc_rated_power_kwh=settings["fc_rated_power_kwh"],
        fc_efficiency=settings["fc_efficiency"],
        production_month=settings["production_month"],
        consumption_month=settings["consumption_month"],
        ev_capacity_kwh=settings["ev_capacity_kwh"],
        ev_charge_power_kwh=settings["ev_charge_power_kwh"],
        ev_eff_km_per_kwh=settings["ev_eff_km_per_kwh"],
        ev_daily_distance_km=settings["ev_daily_distance_km"],
        ev_max_trips_per_day=settings["ev_max_trips_per_day"],
        ev_trip_energy_kwh=ev_trip_energy_kwh,
    )

    df_result = df.copy()
    df_result["TIME"] = pd.to_datetime(df_result["TIME"])

    battery_capacity_initial_value = float(
        df_result.iloc[0].get("batt_soc_kwh", params.max_battery_capacity)
    )
    h2_storage_kwh_initial_value = 0.0

    cost_list = []
    battery_capacity_list = []
    charge_list = []
    discharge_list = []
    buy_electricity_list = []
    sell_electricity_list = []
    remain_surplus_list = []
    h2_storage_kwh_list = []
    h2_energy_kwh_list = []
    el_input_used_kwh_list = []
    fc_output_used_kwh_list = []
    buy_before_h2_list = []
    ev_soc_kwh_list = []
    ev_charge_used_kwh_list = []
    ev_trip_count_list = []
    ev_trips_today_list = []

    current_battery_capacity = battery_capacity_initial_value
    current_h2_storage_kwh = h2_storage_kwh_initial_value
    ev_soc_kwh_initial_value = 0.0
    current_ev_soc_kwh = ev_soc_kwh_initial_value
    current_ev_trips_today = 0

    current_day = None

    for index, row in df_result.iterrows():
        # --- 日付が変わったら日次カウンタをリセット（追加ロジック） ---
        day = row["TIME"].date()
        if current_day is None:
            current_day = day
        elif day != current_day:
            current_day = day
            current_ev_trips_today = 0

        if index == 0:
            cost_list.append(0.0)
            battery_capacity_list.append(current_battery_capacity)
            buy_electricity_list.append(0.0)
            sell_electricity_list.append(0.0)
            charge_list.append(0.0)
            discharge_list.append(0.0)
            remain_surplus_list.append(0.0)
            h2_storage_kwh_list.append(current_h2_storage_kwh)
            h2_energy_kwh_list.append(0.0)
            el_input_used_kwh_list.append(0.0)
            fc_output_used_kwh_list.append(0.0)
            buy_before_h2_list.append(0.0)

            # EV初期行
            ev_soc_kwh_list.append(current_ev_soc_kwh)
            ev_charge_used_kwh_list.append(0.0)
            ev_trip_count_list.append(0)
            ev_trips_today_list.append(current_ev_trips_today)

            continue

        (
            cost_for_hour,
            end_of_hour_battery_capacity,
            charge,
            discharge,
            buy_electricity,
            sell_electricity,
            remain_surplus,
            next_h2_storage_kwh,
            h2_energy_kwh,
            el_input_used_kwh,
            fc_output_used_kwh,
            buy_before_h2,
            # EV
            next_ev_soc_kwh,
            ev_charge_used_kwh,
            ev_trip_count_this_hour,
            next_ev_trips_today,
        ) = _cost_and_battery_capacity(
            row,
            current_battery_capacity,
            current_h2_storage_kwh,
            current_ev_soc_kwh,
            current_ev_trips_today,
            params,
        )

        cost_list.append(cost_for_hour)
        battery_capacity_list.append(end_of_hour_battery_capacity)
        buy_electricity_list.append(buy_electricity)
        sell_electricity_list.append(sell_electricity)
        charge_list.append(charge)
        discharge_list.append(discharge)
        remain_surplus_list.append(remain_surplus)
        h2_storage_kwh_list.append(next_h2_storage_kwh)
        h2_energy_kwh_list.append(h2_energy_kwh)
        el_input_used_kwh_list.append(el_input_used_kwh)
        fc_output_used_kwh_list.append(fc_output_used_kwh)
        buy_before_h2_list.append(buy_before_h2)

        # EV
        ev_soc_kwh_list.append(next_ev_soc_kwh)
        ev_charge_used_kwh_list.append(ev_charge_used_kwh)
        ev_trip_count_list.append(ev_trip_count_this_hour)
        ev_trips_today_list.append(next_ev_trips_today)

        # 状態更新
        current_battery_capacity = end_of_hour_battery_capacity
        current_h2_storage_kwh = next_h2_storage_kwh
        current_ev_soc_kwh = next_ev_soc_kwh
        current_ev_trips_today = next_ev_trips_today

    # DataFrameへ反映
    df_result.loc[:, "cost"] = cost_list
    df_result.loc[:, "batt_soc_kwh"] = battery_capacity_list
    df_result.loc[:, "charge"] = charge_list
    df_result.loc[:, "discharge"] = discharge_list
    df_result.loc[:, "buy_electricity"] = buy_electricity_list
    df_result.loc[:, "sell_electricity"] = sell_electricity_list
    df_result.loc[:, "remain_surplus"] = remain_surplus_list
    df_result.loc[:, "h2_storage_kwh"] = h2_storage_kwh_list
    df_result.loc[:, "h2_energy_kwh"] = h2_energy_kwh_list
    df_result.loc[:, "el_input_used_kwh"] = el_input_used_kwh_list
    df_result.loc[:, "fc_output_used_kwh"] = fc_output_used_kwh_list
    df_result.loc[:, "buy_before_h2"] = buy_before_h2_list

    # EV列（追加）
    df_result.loc[:, "ev_soc_kwh"] = ev_soc_kwh_list
    df_result.loc[:, "ev_charge_used_kwh"] = ev_charge_used_kwh_list
    df_result.loc[:, "ev_trip_count"] = ev_trip_count_list
    df_result.loc[:, "ev_trips_today"] = ev_trips_today_list  # 検証・裏取り用

    # 設定確認用に1回あたり消費電力量も入れておく（列として一定値）
    df_result.loc[:, "ev_trip_energy_kwh"] = params.ev_trip_energy_kwh

    return df_result
