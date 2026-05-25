"""检查增强演示样例的 AIGC 风险指数。

该脚本只用于演示样例筛选，不改变模型、不参与训练。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.risk_model import predict_risk


INPUT_PATH = PROJECT_ROOT / "data" / "sample_seed" / "demo_texts_enhanced.csv"
REPORT_MD = PROJECT_ROOT / "reports" / "demo_examples_risk_check.md"
REPORT_CSV = PROJECT_ROOT / "reports" / "demo_examples_risk_check.csv"


def main() -> int:
    print("开始检查增强演示样例风险指数。")
    if not INPUT_PATH.exists():
        print(f"未找到演示样例文件：{INPUT_PATH}")
        return 1

    df = pd.read_csv(INPUT_PATH)
    rows = []
    warnings = []
    for _, row in df.iterrows():
        result = predict_risk(
            str(row.get("text", "")),
            assignment_type=str(row.get("assignment_type", "其他")),
            grade="高一",
            has_ai_statement=False,
        )
        probability = float(result["ai_probability"])
        risk_index = round(probability * 100, 2)
        intended = str(row.get("intended_level", "")).strip()
        if intended == "高风险" and probability < 0.75:
            warnings.append(f"{row.get('demo_id')} 预期为高风险，但当前 AIGC 风险指数为 {risk_index}%。")
        if intended == "高参考风险" and probability < 0.90:
            warnings.append(f"{row.get('demo_id')} 预期为高参考风险，但当前 AIGC 风险指数为 {risk_index}%。")
        rows.append(
            {
                "demo_id": row.get("demo_id", ""),
                "demo_name": row.get("demo_name", ""),
                "intended_level": intended,
                "assignment_type": row.get("assignment_type", ""),
                "aigc_risk_index": risk_index,
                "ai_probability": probability,
                "risk_level": result["risk_level"],
                "model_source": result["model_source"],
                "note": row.get("note", ""),
            }
        )

    out = pd.DataFrame(rows)
    REPORT_CSV.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(REPORT_CSV, index=False, encoding="utf-8-sig")

    lines = [
        "# 增强演示样例风险检查报告",
        "",
        "本报告基于当前正式模型对 `data/sample_seed/demo_texts_enhanced.csv` 逐条打分生成。演示样例仅用于展示系统功能，不代表真实学生文本。",
        "",
        "## 检查结果",
        "",
        "| demo_id | 样例名称 | 预期等级 | 实际风险等级 | AIGC 风险指数 |",
        "|---|---|---|---|---:|",
    ]
    for item in rows:
        lines.append(
            f"| {item['demo_id']} | {item['demo_name']} | {item['intended_level']} | "
            f"{item['risk_level']} | {item['aigc_risk_index']:.2f}% |"
        )
    lines.extend(["", "## 警告"])
    lines.extend([f"- {w}" for w in warnings] if warnings else ["- 无"])
    lines.extend(
        [
            "",
            "## 使用边界",
            "",
            "- AIGC 风险指数较低不等于文本一定未使用 AI。",
            "- AIGC 风险指数较高也不等于可直接认定违规。",
            "- 教师需结合草稿、访谈和使用声明综合判断。",
        ]
    )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"检查完成：{len(out)} 条。")
    print(f"CSV：{REPORT_CSV}")
    print(f"报告：{REPORT_MD}")
    if warnings:
        print("存在未达预期样例：")
        for warning in warnings:
            print(f"- {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
