from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import pandas as pd


@dataclass(frozen=True)
class BatteryOnlyParams:
    max_battery_capacity: float
    battery_rated_power_kwh: float
    buy_price: float
    sell_price: float


def _step_battery_only(
    row: pd.Series,
    battery_capacity: float,
    params: BatteryOnlyParams,
):
    load = row["load_site_kwh"]
    pv = row["pv_net_pos_kwh"]

    battery_space = params.max_battery_capacity - battery_capacity

    charge = 0.0
    discharge = 0.0
    buy_electricity = 0.0
    sell_electricity = 0.0

    if pv >= load:
        surplus = pv - load
        if surplus >= params.battery_rated_power_kwh:
            if battery_space >= params.battery_rated_power_kwh:
                charge = params.battery_rated_power_kwh
                sell_electricity = surplus - params.battery_rated_power_kwh
            else:
                charge = battery_space
                sell_electricity = surplus - battery_space
        else:
            if battery_space >= surplus:
                charge = surplus
            else:
                charge = battery_space
                sell_electricity = surplus - battery_space
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

    cost = buy_electricity * params.buy_price - sell_electricity * params.sell_price

    return (
        cost,
        battery_capacity,
        charge,
        discharge,
        buy_electricity,
        sell_electricity,
    )


def run_battery_only_simulation(
    df: pd.DataFrame,
    settings: Mapping[str, float],
) -> pd.DataFrame:
    params = BatteryOnlyParams(
        max_battery_capacity=settings["max_battery_capacity"],
        battery_rated_power_kwh=settings["battery_rated_power_kwh"],
        buy_price=settings["buy_price"],
        sell_price=settings["sell_price"],
    )

    df_result = df.copy()
    df_result["TIME"] = pd.to_datetime(df_result["TIME"])

    initial_capacity = float(
        df_result.iloc[0].get("batt_soc_kwh", params.max_battery_capacity)
    )

    cost_list = []
    battery_capacity_list = []
    charge_list = []
    discharge_list = []
    buy_electricity_list = []
    sell_electricity_list = []

    current_battery_capacity = initial_capacity

    for index, row in df_result.iterrows():
        if index == 0:
            cost_list.append(0.0)
            battery_capacity_list.append(current_battery_capacity)
            buy_electricity_list.append(0.0)
            sell_electricity_list.append(0.0)
            charge_list.append(0.0)
            discharge_list.append(0.0)
        else:
            (
                cost,
                current_battery_capacity,
                charge,
                discharge,
                buy_electricity,
                sell_electricity,
            ) = _step_battery_only(row, current_battery_capacity, params)

            cost_list.append(cost)
            battery_capacity_list.append(current_battery_capacity)
            buy_electricity_list.append(buy_electricity)
            sell_electricity_list.append(sell_electricity)
            charge_list.append(charge)
            discharge_list.append(discharge)

    df_result.loc[:, "cost"] = cost_list
    df_result.loc[:, "batt_soc_kwh"] = battery_capacity_list
    df_result.loc[:, "charge"] = charge_list
    df_result.loc[:, "discharge"] = discharge_list
    df_result.loc[:, "buy_electricity"] = buy_electricity_list
    df_result.loc[:, "sell_electricity"] = sell_electricity_list

    return df_result
