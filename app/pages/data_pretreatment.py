import io
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# プロジェクトルート（app ディレクトリ）を import パスに追加
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# 前処理ロジックの import
from preprocess.data_process import merge_and_compress_hourly  # noqa: E402

ICON_PATH = ROOT / "images" / "greennavi.png"
if ICON_PATH.exists():
    st.set_page_config(page_title="GreenNavi", page_icon=str(ICON_PATH), layout="wide")
else:
    st.set_page_config(page_title="GreenNavi", page_icon=":seedling:", layout="wide")

st.title("データ前処理")

# コンテナ内の入出力ディレクトリ（Docker でマウントする）
DATA_ROOT = Path("/app/data")
OUTPUT_ROOT = Path("/app/output")

# /app/data の存在チェック
if not DATA_ROOT.exists():
    st.error(f"{DATA_ROOT} が存在しません。Docker の volume 設定を確認してください。")
    st.stop()

# 直下の CSV をざっと確認してユーザーに見せる（任意）
csv_files = sorted(list(DATA_ROOT.glob("*.csv")) + list(DATA_ROOT.glob("*.CSV")))
st.write(f"現在 `/app/data` 直下にある CSV ファイル数: **{len(csv_files)} 件**")
if csv_files:
    with st.expander("ファイル一覧を表示"):
        for f in csv_files:
            st.write(f"- {f.name}")
else:
    st.warning("`/app/data` 直下に CSV ファイルが見つかりません。")
    st.stop()

# 出力ファイル名を入力
output_filename = st.text_input("出力ファイル名", value="2025_merged_hour_all.csv")

# 前処理ボタン
if st.button("前処理を実行"):
    with st.spinner("前処理を実行中です…（数分かかる場合があります）"):
        try:
            # ここで単体スクリプトと同じロジックを呼び出す
            output_path = merge_and_compress_hourly(
                input_dir=DATA_ROOT,
                output_dir=OUTPUT_ROOT,
                output_filename=output_filename,
            )
        except Exception as e:  # noqa: BLE001
            st.error(f"前処理中にエラーが発生しました: {e}")
        else:
            st.success(f"前処理完了: {output_path}")

            # ダウンロード用に読み込み
            df = pd.read_csv(output_path)
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False)
            csv_bytes = csv_buffer.getvalue().encode("utf-8-sig")

            st.download_button(
                label="結合済み CSV をダウンロード",
                data=csv_bytes,
                file_name=output_filename,
                mime="text/csv",
            )
