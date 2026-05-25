"""本地 CSV 存储与班级分析看板统计。"""

from __future__ import annotations

import hashlib
import re
import uuid
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SUBMISSIONS_PATH = PROJECT_ROOT / "data" / "local" / "submissions.csv"

SUBMISSION_COLUMNS = [
    "record_id",
    "timestamp",
    "text_hash",
    "text_preview",
    "assignment_type",
    "grade",
    "has_ai_statement",
    "aigc_risk_index",
    "ai_probability",
    "risk_level",
    "process_transparency",
    "reasons",
    "suggestions",
    "source_type",
    "demo_flag",
    "source_note",
    "anonymous_student_id",
    "ocr_confidence",
    "ocr_status",
]

TRUE_VALUES = {"true", "1", "yes", "y", "是", "已填写", "已提交使用声明"}
FALSE_VALUES = {"false", "0", "no", "n", "否", "未填写", "未提交使用声明"}


def clean_value(value: object, default: str = "未记录") -> str:
    """把空值、nan、undefined 统一为页面可读文本。"""
    if value is None:
        return default
    if isinstance(value, float) and pd.isna(value):
        return default
    text = str(value).strip()
    if text == "" or text.lower() in {"nan", "none", "undefined", "null"}:
        return default
    return text


def normalize_whitespace(text: object) -> str:
    return re.sub(r"\s+", " ", clean_value(text, "")).strip()


def make_text_hash(text: str, assignment_type: str = "", grade: str = "") -> str:
    """按文本、作业类型和年级生成短哈希，用于重复保存防护。"""
    raw = f"{normalize_whitespace(text)}|{assignment_type}|{grade}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def make_preview(text: object, limit: int = 80) -> str:
    """只保留短摘要，不保存完整学生原文。"""
    preview = normalize_whitespace(text)
    return preview[:limit]


def normalize_statement(value: object) -> str:
    text = clean_value(value)
    lowered = text.lower()
    if lowered in TRUE_VALUES or text in TRUE_VALUES:
        return "已填写"
    if lowered in FALSE_VALUES or text in FALSE_VALUES:
        return "未填写"
    if "已" in text and "填写" in text:
        return "已填写"
    if "未" in text and "填写" in text:
        return "未填写"
    return "不确定"


def process_transparency_from_statement(value: object) -> str:
    normalized = normalize_statement(value)
    if normalized == "已填写":
        return "已提交使用声明"
    if normalized == "未填写":
        return "未提交使用声明"
    return "不确定"


def normalize_bool_text(value: object) -> str:
    text = clean_value(value, "false").lower()
    return "true" if text in TRUE_VALUES or text == "true" else "false"


def ensure_storage() -> None:
    """确保本地记录文件存在。"""
    SUBMISSIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not SUBMISSIONS_PATH.exists():
        pd.DataFrame(columns=SUBMISSION_COLUMNS).to_csv(SUBMISSIONS_PATH, index=False, encoding="utf-8-sig")


def _read_raw_submissions() -> pd.DataFrame:
    ensure_storage()
    try:
        return pd.read_csv(SUBMISSIONS_PATH, encoding="utf-8-sig")
    except pd.errors.EmptyDataError:
        return pd.DataFrame(columns=SUBMISSION_COLUMNS)


def migrate_submission_schema(df: pd.DataFrame) -> pd.DataFrame:
    """兼容旧版 submissions.csv，补齐新看板所需字段。"""
    if df.empty:
        return pd.DataFrame(columns=SUBMISSION_COLUMNS)

    migrated = df.copy()
    for column in SUBMISSION_COLUMNS:
        if column not in migrated.columns:
            migrated[column] = ""

    if "risk_score" in migrated.columns:
        missing = migrated["aigc_risk_index"].astype(str).str.strip().isin(["", "nan", "None"])
        migrated.loc[missing, "aigc_risk_index"] = migrated.loc[missing, "risk_score"]

    if "issues" in migrated.columns:
        missing = migrated["reasons"].astype(str).str.strip().isin(["", "nan", "None"])
        migrated.loc[missing, "reasons"] = migrated.loc[missing, "issues"]

    if "model_source" in migrated.columns:
        model_source = migrated["model_source"].astype(str)
        demo_mask = model_source.str.contains("匿名演示记录|演示", na=False)
        migrated.loc[demo_mask & migrated["source_type"].astype(str).str.strip().eq(""), "source_type"] = "demo_seed"
        migrated.loc[demo_mask, "demo_flag"] = "true"
        migrated.loc[demo_mask & migrated["source_note"].astype(str).str.strip().eq(""), "source_note"] = "匿名演示记录，仅用于系统展示"

    migrated["record_id"] = migrated["record_id"].apply(lambda x: clean_value(x, "") or str(uuid.uuid4()))
    migrated["timestamp"] = migrated["timestamp"].apply(lambda x: clean_value(x, datetime.now().isoformat(timespec="seconds")))
    migrated["assignment_type"] = migrated["assignment_type"].apply(clean_value)
    migrated["grade"] = migrated["grade"].apply(clean_value)
    migrated["risk_level"] = migrated["risk_level"].apply(clean_value)
    migrated["has_ai_statement"] = migrated["has_ai_statement"].apply(normalize_statement)
    migrated["process_transparency"] = migrated.apply(
        lambda row: clean_value(row.get("process_transparency"), process_transparency_from_statement(row.get("has_ai_statement"))),
        axis=1,
    )
    migrated["source_type"] = migrated["source_type"].apply(lambda x: clean_value(x, "manual_analysis"))
    migrated["demo_flag"] = migrated["demo_flag"].apply(normalize_bool_text)
    migrated["source_note"] = migrated.apply(
        lambda row: clean_value(
            row.get("source_note"),
            "匿名演示记录，仅用于系统展示" if row.get("demo_flag") == "true" else "用户手动输入",
        ),
        axis=1,
    )
    migrated["text_preview"] = migrated["text_preview"].apply(lambda x: make_preview(x, 80))

    if "text" in migrated.columns:
        empty_preview = migrated["text_preview"].astype(str).str.strip().isin(["", "未记录"])
        migrated.loc[empty_preview, "text_preview"] = migrated.loc[empty_preview, "text"].apply(lambda x: make_preview(x, 80))

    migrated["text_hash"] = migrated.apply(
        lambda row: clean_value(row.get("text_hash"), "")
        or make_text_hash(row.get("text_preview", ""), row.get("assignment_type", ""), row.get("grade", "")),
        axis=1,
    )

    for numeric_column in ["aigc_risk_index", "ai_probability"]:
        migrated[numeric_column] = pd.to_numeric(migrated[numeric_column], errors="coerce").fillna(0)

    migrated["reasons"] = migrated["reasons"].apply(lambda x: clean_value(x, ""))
    migrated["suggestions"] = migrated["suggestions"].apply(lambda x: clean_value(x, ""))
    return migrated[SUBMISSION_COLUMNS]


def load_submissions() -> pd.DataFrame:
    """读取本地分析记录，并自动迁移旧 schema。"""
    df = migrate_submission_schema(_read_raw_submissions())
    # 迁移后的列会写回，便于后续脚本和看板使用同一 schema。
    df.to_csv(SUBMISSIONS_PATH, index=False, encoding="utf-8-sig")
    return df


def recent_duplicate_exists(df: pd.DataFrame, text_hash: str, within_seconds: int = 180) -> bool:
    if df.empty or not text_hash:
        return False
    matched = df[df["text_hash"].astype(str) == str(text_hash)]
    if matched.empty:
        return False
    now = datetime.now()
    for value in matched["timestamp"].tail(5):
        try:
            ts = datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            try:
                ts = datetime.strptime(str(value), "%Y-%m-%d %H:%M:%S")
            except ValueError:
                return True
        if now - ts <= timedelta(seconds=within_seconds):
            return True
    return False


def build_submission_record(record: Dict[str, object]) -> Dict[str, object]:
    text = str(record.get("text", "") or "")
    assignment_type = clean_value(record.get("assignment_type"))
    grade = clean_value(record.get("grade"))
    text_hash = clean_value(record.get("text_hash"), "") or make_text_hash(text or record.get("text_preview", ""), assignment_type, grade)
    statement = normalize_statement(record.get("has_ai_statement"))
    demo_flag = normalize_bool_text(record.get("demo_flag"))

    return {
        "record_id": clean_value(record.get("record_id"), "") or str(uuid.uuid4()),
        "timestamp": clean_value(record.get("timestamp"), datetime.now().isoformat(timespec="seconds")),
        "text_hash": text_hash,
        "text_preview": make_preview(record.get("text_preview") or text, 80),
        "assignment_type": assignment_type,
        "grade": grade,
        "has_ai_statement": statement,
        "aigc_risk_index": round(float(record.get("aigc_risk_index") or record.get("risk_score") or 0), 2),
        "ai_probability": round(float(record.get("ai_probability") or 0), 6),
        "risk_level": clean_value(record.get("risk_level")),
        "process_transparency": clean_value(record.get("process_transparency"), process_transparency_from_statement(statement)),
        "reasons": clean_value(record.get("reasons") or record.get("issues"), ""),
        "suggestions": clean_value(record.get("suggestions"), ""),
        "source_type": clean_value(record.get("source_type"), "manual_analysis"),
        "demo_flag": demo_flag,
        "source_note": clean_value(
            record.get("source_note"),
            "匿名演示记录，仅用于系统展示" if demo_flag == "true" else "用户手动输入",
        ),
        "anonymous_student_id": clean_value(record.get("anonymous_student_id"), ""),
        "ocr_confidence": record.get("ocr_confidence") if record.get("ocr_confidence") is not None else "",
        "ocr_status": clean_value(record.get("ocr_status"), ""),
    }


def save_submission(record: Dict[str, object], dedupe: bool = True) -> Tuple[Path, bool]:
    """保存一次文本分析记录。返回（路径，是否新增）。"""
    df = load_submissions()
    row = build_submission_record(record)
    if dedupe and recent_duplicate_exists(df, str(row["text_hash"])):
        return SUBMISSIONS_PATH, False

    df = pd.concat([df, pd.DataFrame([row], columns=SUBMISSION_COLUMNS)], ignore_index=True)
    df.to_csv(SUBMISSIONS_PATH, index=False, encoding="utf-8-sig")
    return SUBMISSIONS_PATH, True


def save_submissions_dataframe(df: pd.DataFrame) -> None:
    """供演示填充脚本批量写入，保持统一 schema。"""
    out = migrate_submission_schema(df)
    SUBMISSIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(SUBMISSIONS_PATH, index=False, encoding="utf-8-sig")


def _split_issues(values: Iterable[object]) -> List[str]:
    issues: List[str] = []
    for value in values:
        text = clean_value(value, "")
        if not text:
            continue
        for item in re.split(r"[；;|]", text):
            item = item.strip()
            if item and item != "未记录":
                issues.append(item)
    return issues


def dashboard_stats(df: pd.DataFrame) -> Dict[str, object]:
    """生成班级分析看板统计摘要。"""
    df = migrate_submission_schema(df)
    if df.empty:
        return {
            "total": 0,
            "risk_distribution": {},
            "statement_ratio": 0.0,
            "type_distribution": {},
            "type_risk_distribution": [],
            "common_issues": [],
            "suggested_topics": ["如何透明说明 AI 辅助使用过程", "如何核实 AI 输出中的事实"],
            "demo_count": 0,
            "source_distribution": {},
            "image_ocr_count": 0,
            "batch_ocr_count": 0,
        }

    risk_distribution = df["risk_level"].apply(clean_value).value_counts().to_dict()
    type_distribution = df["assignment_type"].apply(clean_value).value_counts().to_dict()
    statement_values = df["has_ai_statement"].apply(normalize_statement)
    statement_ratio = round(float((statement_values == "已填写").mean()), 4)
    demo_count = int((df["demo_flag"].astype(str).str.lower() == "true").sum())
    source_distribution = df["source_type"].apply(clean_value).value_counts().to_dict()
    image_ocr_count = int((df["source_type"].astype(str) == "image_ocr_manual").sum())
    batch_ocr_count = int((df["source_type"].astype(str) == "batch_image_ocr").sum())

    pivot = (
        df.pivot_table(
            index="assignment_type",
            columns="risk_level",
            values="record_id",
            aggfunc="count",
            fill_value=0,
        )
        .reset_index()
        .to_dict(orient="records")
    )
    issue_counter = Counter(_split_issues(df.get("reasons", [])))
    common_issues = issue_counter.most_common(8)

    topics = ["我可以用 AI 写作业吗？", "AI 输出为什么需要核实？"]
    if any(risk_distribution.get(level, 0) for level in ["高风险", "高参考风险", "高置信高风险", "中风险"]):
        topics.append("怎样把 AI 辅助变成透明的学习过程？")
    if statement_ratio < 0.6:
        topics.append("如何填写学生 AI 使用声明？")

    return {
        "total": int(len(df)),
        "risk_distribution": risk_distribution,
        "statement_ratio": statement_ratio,
        "type_distribution": type_distribution,
        "type_risk_distribution": pivot,
        "common_issues": common_issues,
        "suggested_topics": topics,
        "demo_count": demo_count,
        "source_distribution": source_distribution,
        "image_ocr_count": image_ocr_count,
        "batch_ocr_count": batch_ocr_count,
    }
