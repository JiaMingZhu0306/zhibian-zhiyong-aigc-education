"""生成匿名演示记录，便于班级分析看板录屏展示。

该脚本默认不自动运行。生成的数据只标注为“匿名演示记录”，不能作为真实试用反馈。
"""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SUBMISSIONS_PATH = PROJECT_ROOT / "data" / "local" / "submissions.csv"

COLUMNS = [
    "timestamp",
    "grade",
    "assignment_type",
    "has_ai_statement",
    "risk_level",
    "risk_score",
    "ai_probability",
    "model_source",
    "text_length",
    "issues",
]


def main() -> int:
    SUBMISSIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now()
    records = [
        ("初一", "作文", True, "低风险", 22.4, "细节较具体；表达较自然"),
        ("初二", "读后感", False, "中风险", 51.8, "观点展开比较机械；缺少个人阅读细节"),
        ("初三", "学习总结", True, "低风险", 30.2, "有学习过程描述"),
        ("高一", "研究性学习报告", False, "高风险", 82.6, "段落结构高度规整；资料来源说明不足"),
        ("高二", "作文", True, "中风险", 63.5, "句式较整齐；个人经历不足"),
        ("高三", "读后感", True, "低风险", 18.9, "有具体情节和个人感受"),
        ("高一", "学习总结", False, "高置信高风险", 91.3, "语言模板化；观点展开比较机械"),
        ("初二", "作文", True, "低风险", 27.7, "保留了较多生活细节"),
    ]
    rows = []
    for idx, (grade, assignment_type, statement, level, score, issues) in enumerate(records):
        rows.append(
            {
                "timestamp": (now - timedelta(minutes=idx * 8)).strftime("%Y-%m-%d %H:%M:%S"),
                "grade": grade,
                "assignment_type": assignment_type,
                "has_ai_statement": statement,
                "risk_level": level,
                "risk_score": score,
                "ai_probability": round(score / 100, 4),
                "model_source": "匿名演示记录",
                "text_length": 420 + idx * 37,
                "issues": issues,
            }
        )

    df = pd.DataFrame(rows, columns=COLUMNS)
    df.to_csv(SUBMISSIONS_PATH, index=False, encoding="utf-8-sig")
    print(f"已生成匿名演示记录：{SUBMISSIONS_PATH}，共 {len(df)} 条。")
    print("注意：该文件仅用于页面演示，不能作为真实教师试用反馈。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
