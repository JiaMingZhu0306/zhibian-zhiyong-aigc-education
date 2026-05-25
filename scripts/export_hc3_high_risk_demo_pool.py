"""从 public_test 中导出公开语料高风险演示池。

该脚本不训练模型，只使用当前模型对 HC3 public_test 中 label=ai 的样本打分。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.risk_model import predict_risk


INPUT_PATH = PROJECT_ROOT / "data" / "processed" / "public_test.csv"
OUTPUT_PATH = PROJECT_ROOT / "data" / "sample_seed" / "hc3_high_risk_demo_pool.csv"


def main() -> int:
    print("开始导出 HC3 公开语料高风险演示池。")
    if not INPUT_PATH.exists():
        print(f"未找到 {INPUT_PATH}，请先运行 python scripts/prepare_data.py。")
        return 0

    df = pd.read_csv(INPUT_PATH)
    if "label" not in df.columns or "text" not in df.columns:
        print("public_test.csv 缺少 label 或 text 字段，无法导出。")
        return 0

    ai_df = df[df["label"].astype(str).str.lower() == "ai"].copy()
    if ai_df.empty:
        print("public_test.csv 中未找到 label=ai 的样本。")
        return 0

    rows = []
    for idx, row in ai_df.iterrows():
        text = str(row.get("text", ""))
        result = predict_risk(text, assignment_type="其他", grade="高一", has_ai_statement=False)
        rows.append(
            {
                "demo_id": f"hc3_ai_{idx}",
                "text": text,
                "aigc_risk_index": round(float(result["ai_probability"]) * 100, 2),
                "ai_probability": float(result["ai_probability"]),
                "risk_level": result["risk_level"],
                "source_dataset": row.get("source_dataset", row.get("source", "HC3-Chinese")),
                "note": "公开语料演示样例，来自 Human-ChatGPT 对比语料，不是真实学生作文。",
            }
        )

    out = pd.DataFrame(rows).sort_values("ai_probability", ascending=False).head(30)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")
    print(f"已导出：{OUTPUT_PATH}，共 {len(out)} 条。")
    print("注意：这些样例来自公开 Human-ChatGPT 对比语料，不能称为真实学生作文。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
