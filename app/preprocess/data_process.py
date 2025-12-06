from __future__ import annotations

import glob
import os
from pathlib import Path
from typing import Optional

import pandas as pd


def merge_and_compress_hourly(
    input_dir: Path,
    output_dir: Path,
    output_filename: str = "2025_merged_hour_all.csv",
) -> Path:
    """
    指定フォルダ内の CSV をすべて読み込み、
    2秒データ → 1時間平均に圧縮して結合した CSV を出力する。

    Returns
    -------
    Path
        出力された CSV ファイルのパス
    """
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # *.csv / *.CSV を両方対象にする
    all_files = sorted(
        glob.glob(str(input_dir / "*.csv")) + glob.glob(str(input_dir / "*.CSV"))
    )

    if not all_files:
        raise FileNotFoundError(f"{input_dir} 内に CSV ファイルが見つかりません。")

    compressed_df_list: list[pd.DataFrame] = []

    for file in all_files:
        file_name = os.path.basename(file)
        try:
            df = pd.read_csv(file, encoding="shift_jis", skiprows=2, low_memory=False)

            # 不要列削除（あれば）
            drop_cols = [c for c in ["INDEX.1", "TIME.1"] if c in df.columns]
            if drop_cols:
                df = df.drop(columns=drop_cols)

            # 全 NaN 列を削除
            df = df.dropna(axis=1, how="all")

            if "TIME" not in df.columns:
                print(f"警告: {file_name} に TIME 列が無いためスキップ")
                continue

            df["TIME"] = pd.to_datetime(df["TIME"], errors="coerce")
            df = df.dropna(subset=["TIME"])

            if df.empty:
                print(f"警告: TIME 変換後に空になったためスキップ: {file_name}")
                continue

            # 1時間ごとにリサンプリング（平均）
            df = (
                df.set_index("TIME").resample("h").mean(numeric_only=True).reset_index()
            )

            if df.empty:
                print(f"警告: resample 後に空になったためスキップ: {file_name}")
                continue

            compressed_df_list.append(df)
            print(f"処理完了: {file_name}")

        except Exception as e:  # noqa: BLE001
            print(f"エラー: {file_name} - {e}")

    if not compressed_df_list:
        raise RuntimeError("有効なデータが 1 つも生成されませんでした。")

    merged_df = pd.concat(compressed_df_list, ignore_index=True)
    merged_df = merged_df.sort_values("TIME").reset_index(drop=True)

    # --- 変更点: デバッグログとエラーハンドリングを追加 ---
    print("transform_to_simulation_df を呼び出します...")
    try:
        merged_df = transform_to_simulation_df(merged_df, max_battery_capacity_kwh=7.4)
        print("transform_to_simulation_df の処理が完了しました。")
    except Exception as e:
        print(f"transform_to_simulation_df でエラーが発生しました: {e}")
        # エラー発生時に現在のカラム構成を確認できるようにする
        print(f"現在のカラム一覧: {merged_df.columns.tolist()}")
        raise e
    # ---------------------------------------------------

    output_path = output_dir / output_filename
    merged_df.to_csv(output_path, index=False)
    print(f"全ファイル結合: {output_path} に保存しました。👍")

    return output_path


# 後処理用の関数
def transform_to_simulation_df(
    df: pd.DataFrame,
    max_battery_capacity_kwh: float = 7.4,
) -> pd.DataFrame:
    """
    1時間平均済みデータに対して、
    ・必要カラムの抽出
    ・各種計算
    ・名前変更
    ・スケーリング
    を行い、シミュレーション用の形に整える。
    """

    # 元の列名のズレ（全角スペース付き）を補正
    df = df.rename(
        columns={
            "直流母線\u3000計測電圧（000.0V)": "直流母線計測電圧（000.0V)",
        }
    )

    # 必要なカラム
    desired_columns = [
        "TIME",
        "太陽光EZAグリッド電力(W)",
        "太陽光EZAバッテリ電力(W)",
        "バッテリEZAグリッド側電力(W)",
        "バッテリEZAバッテリ側電力(W)",
        "パワコンCT電流（00.00A）",
        "直流母線計測電圧（000.0V)",
        "制御電源電流(0.00A)",
        "バッテリSOC(%)",
    ]

    missing = [c for c in desired_columns if c not in df.columns]
    if missing:
        raise KeyError(f"必要なカラムが不足しています: {missing}")

    # 必要カラムだけ抜き出し
    df = df[desired_columns].copy()

    # --- 変数計算（元コードをほぼそのまま移植）---

    # 太陽光パネルの発電量 (1.7kW)
    df["太陽光パネル(1.7kw)の発電量"] = (
        df["太陽光EZAグリッド電力(W)"] + df["太陽光EZAバッテリ電力(W)"]
    )

    # コテージ102のAC負荷
    df["コテージ102のAC負荷"] = (df["パワコンCT電流（00.00A）"] * 0.01) * (
        df["直流母線計測電圧（000.0V)"] * 0.1
    )

    # コテージ102の制御装置負荷
    df["コテージ102の制御装置負荷"] = (df["制御電源電流(0.00A)"] * 0.01) * (
        df["直流母線計測電圧（000.0V)"] * 0.1
    )

    # コテージ102の総負荷
    df["コテージ102の負荷"] = (
        df["コテージ102のAC負荷"] + df["コテージ102の制御装置負荷"]
    )

    # 発電量の符号反転
    df["太陽光パネル(1.7kw)の発電量(反転)"] = -df["太陽光パネル(1.7kw)の発電量"]

    # 余剰電力（反転側 - 負荷）
    df["余剰電力"] = df["太陽光パネル(1.7kw)の発電量(反転)"] - df["コテージ102の負荷"]

    # ここからシミュレーション用に必要な列だけ残す
    df = df[
        [
            "TIME",
            "コテージ102の負荷",
            "余剰電力",
            "太陽光パネル(1.7kw)の発電量(反転)",
            "バッテリSOC(%)",
        ]
    ].copy()

    # SOC は最初の 1 行だけ使い、それ以降は NaN にする
    if "バッテリSOC(%)" in df.columns and len(df) > 1:
        df.loc[1:, "バッテリSOC(%)"] = float("nan")

    # 英語名に変換
    def change_name(df_: pd.DataFrame) -> pd.DataFrame:
        return df_.rename(
            columns={
                "コテージ102の負荷": "cottage_consumption",
                "太陽光パネル(1.7kw)の発電量(反転)": "pv_power_generation",
                "バッテリSOC(%)": "battery_capacity",
                "余剰電力": "surplus_electricity",
            }
        )

    df = change_name(df)

    # W → kW へのスケーリング
    df["cottage_consumption"] = df["cottage_consumption"] / 1000.0
    df["pv_power_generation"] = df["pv_power_generation"] / 1000.0
    df["surplus_electricity"] = df["surplus_electricity"] / 1000.0

    # % → kWh（バッテリ容量 7.4kWh 前提）
    df["battery_capacity"] = max_battery_capacity_kwh * (df["battery_capacity"] / 100.0)

    # 列名を最終形に
    df = df.rename(
        columns={
            "cottage_consumption": "load_site_kwh",
            "surplus_electricity": "pv_surplus_kwh",
            "battery_capacity": "batt_soc_kwh",
        }
    )

    # pv_power_generation を正負に分解
    pv = df["pv_power_generation"]
    df["pv_net_pos_kwh"] = pv.clip(lower=0)  # 正の部分
    df["pv_aux_kwh"] = (-pv).clip(lower=0)  # 負の部分

    # いったん元の surplus を捨てて再計算
    df.drop(columns=["pv_power_generation"], inplace=True)
    df.drop(columns=["pv_surplus_kwh"], inplace=True)

    df["pv_surplus_kwh"] = (df["pv_net_pos_kwh"] - df["load_site_kwh"]).clip(lower=0)
    df["load_deficit_kwh"] = (df["load_site_kwh"] - df["pv_net_pos_kwh"]).clip(lower=0)

    pv_scale = 6.7 / 1.7
    battery_scale = 14.6 / 7.4

    # PV のスケーリング
    df["pv_net_pos_kwh"] *= pv_scale
    df["pv_aux_kwh"] *= pv_scale

    # スケーリング後に余剰 / 不足を再計算
    gap = df["pv_net_pos_kwh"] - df["load_site_kwh"]
    df["pv_surplus_kwh"] = gap.clip(lower=0)
    df["load_deficit_kwh"] = (-gap).clip(lower=0)

    # 整合チェック（余剰と不足が同時に >0 になる行がないこと）
    assert (
        (df["pv_surplus_kwh"] > 0) & (df["load_deficit_kwh"] > 0)
    ).sum() == 0, "pv_surplus_kwh と load_deficit_kwh が同時に正の行があります"

    if not df.empty and pd.notna(df.loc[0, "batt_soc_kwh"]):
        df.loc[0, "batt_soc_kwh"] *= battery_scale

    # カラム並び替え
    df = df[
        [
            "TIME",
            "load_site_kwh",
            "pv_net_pos_kwh",
            "pv_aux_kwh",
            "pv_surplus_kwh",
            "load_deficit_kwh",
            "batt_soc_kwh",
        ]
    ].copy()

    # すべて NaN の行を削除
    df = df.dropna(
        subset=[
            "load_site_kwh",
            "pv_net_pos_kwh",
            "pv_aux_kwh",
            "pv_surplus_kwh",
            "load_deficit_kwh",
        ],
        how="all",
    )

    return df
