"""公开数据准备脚本。

执行：
    python scripts/prepare_data.py

本脚本优先尝试 Hello-SimpleAI/HC3-Chinese，其次尝试 Hello-SimpleAI/HC3。
如果 datasets 方式不可用，会尝试 Hugging Face Hub 中的 all.jsonl。
如果在线方式仍失败，则扫描 data/raw/ 下的 csv/json/jsonl/parquet 文件。

重要边界：
data/sample_seed/demo_texts.csv 只作为页面演示样例，不参与正式模型训练和评估。
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
SAMPLE_FILE = PROJECT_ROOT / "data" / "sample_seed" / "demo_texts.csv"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
REPORTS_DIR = PROJECT_ROOT / "reports"

PUBLIC_ALL_PATH = PROCESSED_DIR / "public_all.csv"
PUBLIC_TRAIN_PATH = PROCESSED_DIR / "public_train.csv"
PUBLIC_VAL_PATH = PROCESSED_DIR / "public_val.csv"
PUBLIC_TEST_PATH = PROCESSED_DIR / "public_test.csv"
SUMMARY_PATH = PROCESSED_DIR / "dataset_summary.json"

SPLIT_AUDIT_PATH = REPORTS_DIR / "split_audit.json"
DATA_SOURCE_AUDIT_PATH = REPORTS_DIR / "data_source_audit.md"
LABEL_DISTRIBUTION_PATH = REPORTS_DIR / "dataset_label_distribution.csv"
DUPLICATE_AUDIT_PATH = REPORTS_DIR / "duplicate_audit.csv"

RANDOM_STATE = 42
MIN_TOTAL_ROWS = 1000
MIN_CLASS_ROWS = 500
MIN_CHINESE_CHARS = 50
MIN_TOTAL_CHARS = 80
STANDARD_COLUMNS = [
    "text",
    "label",
    "source_dataset",
    "source",
    "source_row_id",
    "origin_field",
    "group_id",
    "chinese_chars",
    "total_chars",
    "normalized_text_hash",
]


def chinese_count(text: str) -> int:
    return len(re.findall(r"[\u4e00-\u9fff]", str(text)))


def normalize_text(text: object) -> str:
    text = "" if text is None else str(text)
    text = text.replace("\ufeff", " ").replace("\u200b", " ")
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", text)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalized_for_duplicate(text: str) -> str:
    text = normalize_text(text).lower()
    text = re.sub(r"\s+", "", text)
    return text


def text_hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def is_garbled(text: str) -> bool:
    if not text:
        return True
    total = len(text)
    replacement_count = text.count("�")
    visible_count = len(re.findall(r"[\u4e00-\u9fffA-Za-z0-9，。！？；：、“”‘’（）《》,.!?;:'\"()\\-]", text))
    if replacement_count >= 3:
        return True
    if total >= 80 and visible_count / max(total, 1) < 0.55:
        return True
    return False


def as_list(value: object) -> List[str]:
    if value is None:
        return []
    if isinstance(value, float) and math.isnan(value):
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, tuple):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []
        if stripped.startswith("[") and stripped.endswith("]"):
            try:
                loaded = json.loads(stripped)
                if isinstance(loaded, list):
                    return [str(item) for item in loaded if str(item).strip()]
            except Exception:
                pass
        return [stripped]
    return [str(value)]


def make_group_id(source_dataset: str, source: str, source_row_id: object, question: object = None) -> str:
    if question:
        digest = text_hash(normalize_text(question))[:16]
        return f"{source_dataset}::{source}::{source_row_id}::{digest}"
    return f"{source_dataset}::{source}::{source_row_id}"


def make_record(
    text: str,
    label: str,
    source_dataset: str,
    source: str,
    source_row_id: object,
    origin_field: str,
    group_id: str,
) -> Dict[str, object]:
    clean = normalize_text(text)
    return {
        "text": clean,
        "label": label,
        "source_dataset": source_dataset,
        "source": source or "unknown",
        "source_row_id": str(source_row_id),
        "origin_field": origin_field,
        "group_id": group_id,
    }


def expand_hc3_item(item: Dict[str, object], source_dataset: str, source_row_id: object) -> List[Dict[str, object]]:
    source = str(item.get("source") or item.get("category") or "unknown")
    question = item.get("question") or item.get("prompt") or ""
    group_id = str(item.get("group_id") or make_group_id(source_dataset, source, source_row_id, question))

    rows: List[Dict[str, object]] = []
    for field in ["human_answers", "human_answer", "answers"]:
        if field in item:
            for text in as_list(item.get(field)):
                rows.append(make_record(text, "human", source_dataset, source, source_row_id, field, group_id))
            break
    for field in ["chatgpt_answers", "chatgpt_answer", "ai_answers", "model_answers"]:
        if field in item:
            for text in as_list(item.get(field)):
                rows.append(make_record(text, "ai", source_dataset, source, source_row_id, field, group_id))
            break
    return rows


def expand_labeled_item(item: Dict[str, object], source_dataset: str, source_row_id: object) -> List[Dict[str, object]]:
    label = str(item.get("label", "")).strip().lower()
    if label not in {"human", "ai"}:
        return []
    text = item.get("text") or item.get("content") or item.get("answer") or item.get("response")
    if text is None:
        return []
    source = str(item.get("source") or "manual_raw")
    group_id = str(item.get("group_id") or make_group_id(source_dataset, source, source_row_id, item.get("question")))
    return [make_record(text, label, source_dataset, source, source_row_id, "text", group_id)]


def expand_item(item: Dict[str, object], source_dataset: str, source_row_id: object) -> List[Dict[str, object]]:
    rows = expand_hc3_item(item, source_dataset, source_row_id)
    if rows:
        return rows
    return expand_labeled_item(item, source_dataset, source_row_id)


def iter_dataset_items(dataset_obj) -> Iterable[Tuple[object, Dict[str, object]]]:
    if hasattr(dataset_obj, "items") and not isinstance(dataset_obj, list):
        for split_name, split_data in dataset_obj.items():
            for index, item in enumerate(split_data):
                yield f"{split_name}:{index}", dict(item)
    else:
        for index, item in enumerate(dataset_obj):
            yield index, dict(item)


def load_with_datasets(name: str) -> Tuple[List[Dict[str, object]], str]:
    try:
        from datasets import load_dataset
    except Exception as exc:
        return [], f"datasets 库不可用：{exc}"
    try:
        dataset_obj = load_dataset(name)
    except Exception as exc:
        return [], f"{name} 通过 datasets 加载失败：{exc}"

    rows: List[Dict[str, object]] = []
    for source_row_id, item in iter_dataset_items(dataset_obj):
        rows.extend(expand_item(item, name, source_row_id))
    return rows, f"{name} 通过 datasets 成功读取，展开 {len(rows)} 条样本。"


def load_with_hf_hub(name: str) -> Tuple[List[Dict[str, object]], str]:
    try:
        from huggingface_hub import hf_hub_download
    except Exception as exc:
        return [], f"huggingface_hub 不可用：{exc}"
    try:
        path = hf_hub_download(repo_id=name, repo_type="dataset", filename="all.jsonl")
    except Exception as exc:
        return [], f"{name} 的 all.jsonl 下载失败：{exc}"

    rows: List[Dict[str, object]] = []
    with open(path, "r", encoding="utf-8") as handle:
        for index, line in enumerate(handle):
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            rows.extend(expand_item(item, name, index))
    return rows, f"{name} 通过 Hugging Face Hub all.jsonl 成功读取，展开 {len(rows)} 条样本。"


def load_public_dataset() -> Tuple[List[Dict[str, object]], List[str], str]:
    messages: List[str] = []
    attempts = ["Hello-SimpleAI/HC3-Chinese", "Hello-SimpleAI/HC3"]
    for name in attempts:
        rows, message = load_with_datasets(name)
        messages.append(message)
        if rows:
            return rows, messages, name
        rows, message = load_with_hf_hub(name)
        messages.append(message)
        if rows:
            return rows, messages, name
    return [], messages, ""


def read_raw_file(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix == ".json":
        return pd.read_json(path)
    if suffix == ".jsonl":
        return pd.read_json(path, lines=True)
    if suffix == ".parquet":
        return pd.read_parquet(path)
    raise ValueError(f"不支持的文件类型：{path.name}")


def load_raw_files() -> Tuple[List[Dict[str, object]], List[str]]:
    rows: List[Dict[str, object]] = []
    messages: List[str] = []
    if not RAW_DIR.exists():
        return rows, ["data/raw/ 目录不存在。"]

    files = [
        path
        for path in sorted(RAW_DIR.iterdir())
        if path.is_file() and path.suffix.lower() in {".csv", ".json", ".jsonl", ".parquet"}
    ]
    if not files:
        return rows, ["data/raw/ 下未发现 csv/json/jsonl/parquet 文件。"]

    for file_path in files:
        try:
            df = read_raw_file(file_path)
        except Exception as exc:
            messages.append(f"{file_path.name} 读取失败：{exc}")
            continue
        file_rows: List[Dict[str, object]] = []
        for index, row in df.iterrows():
            item = row.dropna().to_dict()
            file_rows.extend(expand_item(item, f"manual_raw::{file_path.name}", index))
        rows.extend(file_rows)
        messages.append(f"{file_path.name} 读取 {len(df)} 行，展开 {len(file_rows)} 条样本。")
    return rows, messages


def clean_and_filter(rows: Sequence[Dict[str, object]]) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, int]]:
    if not rows:
        empty = pd.DataFrame(columns=STANDARD_COLUMNS)
        duplicate_empty = pd.DataFrame(columns=["normalized_text_hash", "duplicate_count", "labels", "example_text"])
        return empty, duplicate_empty, {
            "raw_rows": 0,
            "empty_removed": 0,
            "short_removed": 0,
            "garbled_removed": 0,
            "duplicate_removed": 0,
        }

    df = pd.DataFrame(rows)
    for column in ["text", "label", "source_dataset", "source", "source_row_id", "origin_field", "group_id"]:
        if column not in df.columns:
            df[column] = ""
        df[column] = df[column].astype(str).map(normalize_text)

    raw_rows = len(df)
    df = df[df["label"].isin(["human", "ai"])].copy()
    before_empty = len(df)
    df = df[df["text"].astype(bool)].copy()
    empty_removed = before_empty - len(df)

    df["chinese_chars"] = df["text"].map(chinese_count)
    df["total_chars"] = df["text"].map(len)
    before_short = len(df)
    df = df[(df["chinese_chars"] >= MIN_CHINESE_CHARS) | (df["total_chars"] >= MIN_TOTAL_CHARS)].copy()
    short_removed = before_short - len(df)

    before_garbled = len(df)
    df = df[~df["text"].map(is_garbled)].copy()
    garbled_removed = before_garbled - len(df)

    df["normalized_text"] = df["text"].map(normalized_for_duplicate)
    df["normalized_text_hash"] = df["normalized_text"].map(text_hash)
    duplicate_groups = (
        df.groupby("normalized_text_hash")
        .agg(
            duplicate_count=("text", "size"),
            labels=("label", lambda values: ",".join(sorted(set(values)))),
            example_text=("text", "first"),
        )
        .reset_index()
    )
    duplicate_audit = duplicate_groups[duplicate_groups["duplicate_count"] > 1].copy()
    before_dedup = len(df)
    df = df.drop_duplicates(subset=["normalized_text"]).drop(columns=["normalized_text"]).reset_index(drop=True)
    duplicate_removed = before_dedup - len(df)

    stats = {
        "raw_rows": int(raw_rows),
        "empty_removed": int(empty_removed),
        "short_removed": int(short_removed),
        "garbled_removed": int(garbled_removed),
        "duplicate_removed": int(duplicate_removed),
    }
    return df[STANDARD_COLUMNS], duplicate_audit, stats


def split_groupwise(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    groups = sorted(df["group_id"].dropna().unique().tolist())
    if not groups:
        return df.iloc[0:0].copy(), df.iloc[0:0].copy(), df.iloc[0:0].copy()

    def make_split(seed: int) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        group_series = pd.Series(groups).sample(frac=1, random_state=seed).tolist()
        train_end = int(len(group_series) * 0.70)
        val_end = train_end + int(len(group_series) * 0.15)
        train_groups = set(group_series[:train_end])
        val_groups = set(group_series[train_end:val_end])
        test_groups = set(group_series[val_end:])
        return (
            df[df["group_id"].isin(train_groups)].copy(),
            df[df["group_id"].isin(val_groups)].copy(),
            df[df["group_id"].isin(test_groups)].copy(),
        )

    train_df, val_df, test_df = make_split(RANDOM_STATE)
    for offset in range(100):
        candidate = make_split(RANDOM_STATE + offset)
        if all(set(part["label"]) == {"human", "ai"} for part in candidate if not part.empty):
            train_df, val_df, test_df = candidate
            break
    return train_df.reset_index(drop=True), val_df.reset_index(drop=True), test_df.reset_index(drop=True)


def label_distribution_by_split(train_df: pd.DataFrame, val_df: pd.DataFrame, test_df: pd.DataFrame) -> Dict[str, Dict[str, int]]:
    result: Dict[str, Dict[str, int]] = {}
    for split_name, split_df in [("train", train_df), ("val", val_df), ("test", test_df)]:
        result[split_name] = {label: int(count) for label, count in split_df["label"].value_counts().to_dict().items()}
    return result


def build_split_audit(train_df: pd.DataFrame, val_df: pd.DataFrame, test_df: pd.DataFrame) -> Dict[str, object]:
    train_groups = set(train_df["group_id"].unique())
    val_groups = set(val_df["group_id"].unique())
    test_groups = set(test_df["group_id"].unique())
    return {
        "train_rows": int(len(train_df)),
        "val_rows": int(len(val_df)),
        "test_rows": int(len(test_df)),
        "train_groups": int(len(train_groups)),
        "val_groups": int(len(val_groups)),
        "test_groups": int(len(test_groups)),
        "overlap_train_val_groups": sorted(train_groups & val_groups),
        "overlap_train_test_groups": sorted(train_groups & test_groups),
        "overlap_val_test_groups": sorted(val_groups & test_groups),
        "label_distribution_by_split": label_distribution_by_split(train_df, val_df, test_df),
    }


def has_split_overlap(split_audit: Dict[str, object]) -> bool:
    return any(
        split_audit.get(key)
        for key in [
            "overlap_train_val_groups",
            "overlap_train_test_groups",
            "overlap_val_test_groups",
        ]
    )


def split_has_both_labels(split_df: pd.DataFrame) -> bool:
    return set(split_df["label"].unique()) == {"human", "ai"}


def formal_thresholds_met(df: pd.DataFrame, train_df: pd.DataFrame, val_df: pd.DataFrame, test_df: pd.DataFrame, split_audit: Dict[str, object]) -> Tuple[bool, List[str]]:
    reasons: List[str] = []
    label_counts = df["label"].value_counts().to_dict()
    if len(df) < MIN_TOTAL_ROWS:
        reasons.append(f"清洗去重后总样本数 {len(df)} < {MIN_TOTAL_ROWS}")
    if label_counts.get("human", 0) < MIN_CLASS_ROWS:
        reasons.append(f"human 样本数 {label_counts.get('human', 0)} < {MIN_CLASS_ROWS}")
    if label_counts.get("ai", 0) < MIN_CLASS_ROWS:
        reasons.append(f"ai 样本数 {label_counts.get('ai', 0)} < {MIN_CLASS_ROWS}")
    for name, split_df in [("train", train_df), ("val", val_df), ("test", test_df)]:
        if split_df.empty:
            reasons.append(f"{name} split 为空")
        elif not split_has_both_labels(split_df):
            reasons.append(f"{name} split 未同时包含 human 和 ai")
    if has_split_overlap(split_audit):
        reasons.append("group_id 存在跨 split 交叉")
    return not reasons, reasons


def write_label_distribution(df: pd.DataFrame, train_df: pd.DataFrame, val_df: pd.DataFrame, test_df: pd.DataFrame) -> None:
    rows: List[Dict[str, object]] = []
    for split_name, split_df in [("all", df), ("train", train_df), ("val", val_df), ("test", test_df)]:
        counts = split_df["label"].value_counts().to_dict() if not split_df.empty else {}
        for label in ["human", "ai"]:
            rows.append({"split": split_name, "label": label, "count": int(counts.get(label, 0))})
    pd.DataFrame(rows).to_csv(LABEL_DISTRIBUTION_PATH, index=False, encoding="utf-8-sig")


def write_data_source_audit(summary: Dict[str, object], messages: List[str], threshold_reasons: List[str]) -> None:
    status = "正式公开数据训练模式" if summary.get("training_mode") == "formal_public" else "demo_mode"
    message_lines = "\n".join([f"- {message}" for message in messages]) or "- 无"
    reason_lines = "\n".join([f"- {reason}" for reason in threshold_reasons]) or "- 已满足正式训练门槛"
    content = (
        "# 数据来源审计报告\n\n"
        f"## 当前状态\n\n{status}\n\n"
        "## 数据加载过程\n"
        f"{message_lines}\n\n"
        "## 样本统计\n"
        f"- 清洗去重后总样本数：{summary.get('total_after_cleaning', 0)}\n"
        f"- human 样本数：{summary.get('label_distribution', {}).get('human', 0)}\n"
        f"- ai 样本数：{summary.get('label_distribution', {}).get('ai', 0)}\n"
        f"- train/val/test：{summary.get('train_size', 0)} / {summary.get('val_size', 0)} / {summary.get('test_size', 0)}\n"
        f"- group-wise split：{summary.get('group_wise_split', False)}\n\n"
        "## 门槛检查\n"
        f"{reason_lines}\n\n"
        "## 使用边界\n"
        "系统使用公开 Human-ChatGPT 对比语料构建 AIGC 文本风险提示基线模型，并通过 group-wise split 避免同问题样本跨训练集和测试集造成泄漏。"
        "由于公开语料不完全等同于真实中学生作文，本模型仅作为教师教学辅助和风险提示工具，不作为学生违纪判定或处分依据。\n\n"
    )
    if summary.get("training_mode") != "formal_public":
        content += "当前公开数据不足，系统进入 demo_mode，不能报告正式模型性能。当前版本完成了系统流程和演示数据验证，但公开训练数据尚未成功接入，模型指标不能作为正式效果结论。\n"
    DATA_SOURCE_AUDIT_PATH.write_text(content, encoding="utf-8")


def write_empty_outputs(messages: List[str], threshold_reasons: List[str]) -> None:
    empty = pd.DataFrame(columns=STANDARD_COLUMNS)
    for path in [PUBLIC_ALL_PATH, PUBLIC_TRAIN_PATH, PUBLIC_VAL_PATH, PUBLIC_TEST_PATH]:
        empty.to_csv(path, index=False, encoding="utf-8-sig")
    split_audit = {
        "train_rows": 0,
        "val_rows": 0,
        "test_rows": 0,
        "train_groups": 0,
        "val_groups": 0,
        "test_groups": 0,
        "overlap_train_val_groups": [],
        "overlap_train_test_groups": [],
        "overlap_val_test_groups": [],
        "label_distribution_by_split": {"train": {}, "val": {}, "test": {}},
    }
    SPLIT_AUDIT_PATH.write_text(json.dumps(split_audit, ensure_ascii=False, indent=2), encoding="utf-8")
    pd.DataFrame(columns=["split", "label", "count"]).to_csv(LABEL_DISTRIBUTION_PATH, index=False, encoding="utf-8-sig")
    pd.DataFrame(columns=["normalized_text_hash", "duplicate_count", "labels", "example_text"]).to_csv(
        DUPLICATE_AUDIT_PATH,
        index=False,
        encoding="utf-8-sig",
    )
    summary = {
        "dataset_mode": "demo_mode",
        "training_mode": "demo_mode",
        "selected_data_source": "",
        "total_after_cleaning": 0,
        "label_distribution": {},
        "source_distribution": {},
        "train_size": 0,
        "val_size": 0,
        "test_size": 0,
        "group_wise_split": True,
        "can_train_formal_model": False,
        "formal_training_blockers": threshold_reasons,
        "messages": messages,
        "note": "当前公开数据不足，系统进入 demo_mode，不能报告正式模型性能。",
    }
    SUMMARY_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    write_data_source_audit(summary, messages, threshold_reasons)


def main() -> int:
    print("第2步：开始准备公开训练数据。")
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    messages: List[str] = []
    rows, public_messages, selected_source = load_public_dataset()
    messages.extend(public_messages)

    if not rows:
        raw_rows, raw_messages = load_raw_files()
        messages.extend(raw_messages)
        rows = raw_rows
        selected_source = "data/raw" if raw_rows else ""

    df, duplicate_audit, cleaning_stats = clean_and_filter(rows)
    duplicate_audit.to_csv(DUPLICATE_AUDIT_PATH, index=False, encoding="utf-8-sig")

    if df.empty:
        reasons = ["未获得可用于正式训练的公开或手动原始数据。"]
        write_empty_outputs(messages, reasons)
        print("未获得公开训练数据，已进入 demo_mode。")
        print(f"数据来源审计报告：{DATA_SOURCE_AUDIT_PATH}")
        return 0

    train_df, val_df, test_df = split_groupwise(df)
    split_audit = build_split_audit(train_df, val_df, test_df)
    if has_split_overlap(split_audit):
        SPLIT_AUDIT_PATH.write_text(json.dumps(split_audit, ensure_ascii=False, indent=2), encoding="utf-8")
        raise RuntimeError("group_id 存在跨 split 交叉，已停止数据准备。")

    can_train, threshold_reasons = formal_thresholds_met(df, train_df, val_df, test_df, split_audit)
    training_mode = "formal_public" if can_train else "demo_mode"

    df.to_csv(PUBLIC_ALL_PATH, index=False, encoding="utf-8-sig")
    train_df.to_csv(PUBLIC_TRAIN_PATH, index=False, encoding="utf-8-sig")
    val_df.to_csv(PUBLIC_VAL_PATH, index=False, encoding="utf-8-sig")
    test_df.to_csv(PUBLIC_TEST_PATH, index=False, encoding="utf-8-sig")
    train_df.to_csv(PROCESSED_DIR / "train.csv", index=False, encoding="utf-8-sig")
    val_df.to_csv(PROCESSED_DIR / "val.csv", index=False, encoding="utf-8-sig")
    test_df.to_csv(PROCESSED_DIR / "test.csv", index=False, encoding="utf-8-sig")
    SPLIT_AUDIT_PATH.write_text(json.dumps(split_audit, ensure_ascii=False, indent=2), encoding="utf-8")
    write_label_distribution(df, train_df, val_df, test_df)

    summary = {
        "dataset_mode": training_mode,
        "training_mode": training_mode,
        "selected_data_source": selected_source,
        "total_after_cleaning": int(len(df)),
        "label_distribution": {label: int(count) for label, count in df["label"].value_counts().to_dict().items()},
        "source_distribution": {source: int(count) for source, count in df["source"].value_counts().to_dict().items()},
        "source_dataset_distribution": {
            source: int(count) for source, count in df["source_dataset"].value_counts().to_dict().items()
        },
        "train_size": int(len(train_df)),
        "val_size": int(len(val_df)),
        "test_size": int(len(test_df)),
        "train_groups": int(split_audit["train_groups"]),
        "val_groups": int(split_audit["val_groups"]),
        "test_groups": int(split_audit["test_groups"]),
        "group_wise_split": True,
        "can_train_formal_model": can_train,
        "formal_training_blockers": threshold_reasons,
        "min_total_rows": MIN_TOTAL_ROWS,
        "min_class_rows": MIN_CLASS_ROWS,
        "cleaning_stats": cleaning_stats,
        "messages": messages,
        "demo_texts_role": "仅用于页面演示，不参与正式模型训练或评估。",
        "note": (
            "公开数据已满足正式训练门槛。"
            if can_train
            else "当前公开数据不足，系统进入 demo_mode，不能报告正式模型性能。"
        ),
    }
    SUMMARY_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    write_data_source_audit(summary, messages, threshold_reasons)

    print("公开数据准备完成。")
    print(f"数据源：{selected_source or '未获得公开数据'}")
    print(f"清洗去重后总样本数：{len(df)}")
    print(f"标签分布：{summary['label_distribution']}")
    print(f"train/val/test：{len(train_df)} / {len(val_df)} / {len(test_df)}")
    print(f"训练模式：{training_mode}")
    print(f"数据来源审计报告：{DATA_SOURCE_AUDIT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

