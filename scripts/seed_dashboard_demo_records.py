"""填充班级分析看板匿名演示记录。

默认从已处理公开语料中抽取样本，经当前模型预测后写入 data/local/submissions.csv。
所有记录均标注为公开语料演示记录，仅用于系统展示，不代表真实学生数据。
"""

from __future__ import annotations

import argparse
import random
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.explanation import build_feedback
from src.risk_model import predict_risk
from src.storage import (
    SUBMISSION_COLUMNS,
    load_submissions,
    make_preview,
    make_text_hash,
    save_submissions_dataframe,
)


SOURCE_CANDIDATES = [
    PROJECT_ROOT / "data" / "processed" / "public_test.csv",
    PROJECT_ROOT / "data" / "processed" / "public_val.csv",
    PROJECT_ROOT / "data" / "processed" / "public_train.csv",
    PROJECT_ROOT / "data" / "sample_seed" / "demo_texts_enhanced.csv",
]

ASSIGNMENT_TYPES = ["作文", "读后感", "学习总结", "研究性学习报告", "其他"]
GRADES = ["初一", "初二", "初三", "高一", "高二", "高三"]
STATEMENT_VALUES = ["已填写"] * 6 + ["未填写"] * 3 + ["不确定"]


def read_source() -> tuple[pd.DataFrame, Path | None]:
    for path in SOURCE_CANDIDATES:
        if not path.exists():
            continue
        df = pd.read_csv(path)
        if df.empty:
            continue
        if "text" not in df.columns and "generated_text" in df.columns:
            df = df.rename(columns={"generated_text": "text"})
        if "text" not in df.columns:
            continue
        df = df[df["text"].astype(str).str.strip().ne("")].copy()
        if not df.empty:
            return df, path
    return pd.DataFrame(), None


def sample_rows(df: pd.DataFrame, n: int) -> pd.DataFrame:
    rng = random.Random(42)
    if "label" in df.columns:
        parts = []
        half = n // 2
        for label, target in [("human", half), ("ai", n - half)]:
            label_df = df[df["label"].astype(str).str.lower() == label]
            if not label_df.empty:
                parts.append(label_df.sample(n=min(target, len(label_df)), random_state=42))
        sample = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
        if len(sample) < n:
            rest = df.drop(sample.index, errors="ignore")
            if rest.empty:
                rest = df
            add = rest.sample(n=n - len(sample), replace=len(rest) < n - len(sample), random_state=43)
            sample = pd.concat([sample, add], ignore_index=True)
        return sample.sample(frac=1, random_state=44).head(n).reset_index(drop=True)

    picked = df.sample(n=n, replace=len(df) < n, random_state=42).reset_index(drop=True)
    # fallback 演示数据行数很少时，打乱作业类型和年级以便看板更像完整演示。
    picked["_seed_assignment_type"] = [rng.choice(ASSIGNMENT_TYPES) for _ in range(len(picked))]
    return picked


def statement_to_process(value: str) -> str:
    if value == "已填写":
        return "已提交使用声明"
    if value == "未填写":
        return "未提交使用声明"
    return "不确定"


def build_records(sample: pd.DataFrame, source_path: Path, n: int) -> list[dict[str, object]]:
    rng = random.Random(2026)
    base_time = datetime.now() - timedelta(minutes=n)
    records: list[dict[str, object]] = []

    for idx, row in sample.iterrows():
        text = str(row.get("text", "")).strip()
        assignment_type = str(row.get("_seed_assignment_type") or rng.choice(ASSIGNMENT_TYPES))
        if assignment_type not in ASSIGNMENT_TYPES:
            assignment_type = rng.choice(ASSIGNMENT_TYPES)
        grade = rng.choice(GRADES)
        statement = rng.choice(STATEMENT_VALUES)

        result = predict_risk(text, assignment_type=assignment_type, grade=grade, has_ai_statement=(statement == "已填写"))
        feedback = build_feedback(text, result)
        text_hash = make_text_hash(text, assignment_type, grade)
        timestamp = (base_time + timedelta(minutes=int(idx))).isoformat(timespec="seconds")

        records.append(
            {
                "record_id": str(uuid.uuid4()),
                "timestamp": timestamp,
                "text_hash": text_hash,
                "text_preview": make_preview(text, 80),
                "assignment_type": assignment_type,
                "grade": grade,
                "has_ai_statement": statement,
                "aigc_risk_index": result["risk_index"],
                "ai_probability": result["ai_probability"],
                "risk_level": result["risk_level"],
                "process_transparency": statement_to_process(statement),
                "reasons": "；".join(feedback["reasons"][:5]),
                "suggestions": "；".join(feedback["suggestions"][:5]),
                "source_type": "public_dataset_demo" if "public_" in source_path.name else "demo_seed",
                "demo_flag": "true",
                "source_note": "公开语料演示记录，仅用于系统展示，不代表真实学生数据"
                if "public_" in source_path.name
                else "匿名演示样例，仅用于系统展示，不代表真实学生数据",
            }
        )
    return records


def write_report(records: list[dict[str, object]], source_path: Path, kept_manual: int) -> None:
    reports_dir = PROJECT_ROOT / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(records, columns=SUBMISSION_COLUMNS)
    df.to_csv(reports_dir / "dashboard_demo_seed_records.csv", index=False, encoding="utf-8-sig")

    risk_dist = df["risk_level"].value_counts().to_dict()
    type_dist = df["assignment_type"].value_counts().to_dict()
    grade_dist = df["grade"].value_counts().to_dict()
    statement_dist = df["has_ai_statement"].value_counts().to_dict()
    lines = [
        "# 班级分析看板演示记录填充报告",
        "",
        f"- 数据来源：{source_path.relative_to(PROJECT_ROOT)}",
        f"- 生成数量：{len(df)}",
        f"- 保留手动记录：{kept_manual} 条",
        "- 保存内容：仅保存文本摘要、风险结果和统计字段，不保存完整原文。",
        "- 记录性质：公开语料演示记录或匿名演示记录，仅用于系统展示，不代表真实学生数据。",
        "",
        "## 风险等级分布",
    ]
    lines.extend([f"- {k}：{v}" for k, v in risk_dist.items()] or ["- 暂无"])
    lines.extend(["", "## 作业类型分布"])
    lines.extend([f"- {k}：{v}" for k, v in type_dist.items()] or ["- 暂无"])
    lines.extend(["", "## 年级分布"])
    lines.extend([f"- {k}：{v}" for k, v in grade_dist.items()] or ["- 暂无"])
    lines.extend(["", "## 使用声明填写情况"])
    lines.extend([f"- {k}：{v}" for k, v in statement_dist.items()] or ["- 暂无"])
    (reports_dir / "dashboard_demo_seed_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="生成班级分析看板匿名演示记录")
    parser.add_argument("--n", type=int, default=100, help="生成演示记录数量")
    parser.add_argument("--replace-demo", action="store_true", help="删除已有 demo_flag=true 的演示记录，保留手动记录")
    parser.add_argument("--clear-all", action="store_true", help="清空全部记录后重新生成")
    args = parser.parse_args()

    source_df, source_path = read_source()
    if source_df.empty or source_path is None:
        print("未找到可用公开语料或增强演示样例，请先运行 prepare_data.py 或检查 data/sample_seed/demo_texts_enhanced.csv。")
        return 0

    existing = load_submissions()
    if args.clear_all:
        kept = existing.iloc[0:0].copy()
    elif args.replace_demo and "demo_flag" in existing.columns:
        kept = existing[existing["demo_flag"].astype(str).str.lower() != "true"].copy()
    else:
        kept = existing.copy()

    sample = sample_rows(source_df, max(args.n, 1))
    records = build_records(sample, source_path, len(sample))
    combined = pd.concat([kept, pd.DataFrame(records, columns=SUBMISSION_COLUMNS)], ignore_index=True)
    save_submissions_dataframe(combined)
    write_report(records, source_path, kept_manual=len(kept))

    df = pd.DataFrame(records)
    print(f"已生成 {len(df)} 条班级分析看板演示记录。")
    print(f"数据来源：{source_path}")
    print(f"风险分布：{df['risk_level'].value_counts().to_dict()}")
    print(f"作业类型分布：{df['assignment_type'].value_counts().to_dict()}")
    print("所有演示记录已标注 demo_flag=true，且只保存文本摘要。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
