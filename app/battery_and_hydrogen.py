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


def _cost_and_battery_capacity(
    row: pd.Series,
    battery_capacity: float,
    h2_storage_kwh: float,
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

    if month in params.production_month:
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
                sell_electricity = max(remain_surplus - el_input_used_kwh, 0.0)
            else:
                sell_electricity = remain_surplus

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
    )


def run_battery_and_hydrogen_simulation(
    df: pd.DataFrame, settings: Mapping[str, object]
) -> pd.DataFrame:
    """
    Run the hourly simulation and return a DataFrame with additional metrics.
    """
    if df.empty:
        return df.copy()

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

    current_battery_capacity = battery_capacity_initial_value
    current_h2_storage_kwh = h2_storage_kwh_initial_value

    for index, row in df_result.iterrows():
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
        else:
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
            ) = _cost_and_battery_capacity(
                row, current_battery_capacity, current_h2_storage_kwh, params
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

            current_battery_capacity = end_of_hour_battery_capacity
            current_h2_storage_kwh = next_h2_storage_kwh

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

    return df_result
