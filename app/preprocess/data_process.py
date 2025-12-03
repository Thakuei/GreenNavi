# app/preprocess/merge_hourly.py
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
            df = df.set_index("TIME").resample("1H").mean(numeric_only=True).reset_index()

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

    output_path = output_dir / output_filename
    merged_df.to_csv(output_path, index=False)
    print(f"全ファイル結合: {output_path} に保存しました。👍")

    return output_path
