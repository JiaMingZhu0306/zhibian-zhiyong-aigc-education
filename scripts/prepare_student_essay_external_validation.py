"""准备中文学生作文 human-only 外部验证集。

执行：
    python scripts/prepare_student_essay_external_validation.py

脚本优先从 GitHub 下载 pretrain_essays.tar.bz2；如果失败，会读取
data/raw/student_essays/ 下用户手动放置的 tar.bz2、json 或 jsonl 文件。

该数据只用于 external_validation_only，不参与 HC3 训练、阈值选择或 public_test 评估。
"""

from __future__ import annotations

import bz2
import io
import json
import os
import re
import sys
import tarfile
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import joblib
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "student_essays"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
REPORTS_DIR = PROJECT_ROOT / "reports"
MODEL_PATH = PROJECT_ROOT / "models" / "aigc_tfidf_lr.joblib"
OUTPUT_PATH = PROCESSED_DIR / "student_essay_external_validation.csv"
PREDICTIONS_PATH = REPORTS_DIR / "student_essay_external_validation_predictions.csv"
METRICS_PATH = REPORTS_DIR / "student_essay_external_validation_metrics.json"
REPORT_PATH = REPORTS_DIR / "student_essay_external_validation_report.md"

DATASET_NAME = "Chinese-Essay-Dataset-For-Pre-Training"
DOWNLOAD_URL = "https://github.com/cnunlp/Chinese-Essay-Dataset-For-Pre-Training/raw/main/pretrain_essays.tar.bz2"
TAR_NAME = "pretrain_essays.tar.bz2"


def chinese_count(text: str) -> int:
    return len(re.findall(r"[\u4e00-\u9fff]", str(text)))


def normalize_text(text: object) -> str:
    text = "" if text is None else str(text)
    text = text.replace("\ufeff", " ").replace("\u200b", " ")
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", text)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalize_for_duplicate(text: str) -> str:
    return re.sub(r"\s+", "", normalize_text(text))


def ensure_dirs() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def download_dataset_if_needed() -> Tuple[Optional[Path], str]:
    target = RAW_DIR / TAR_NAME
    if target.exists() and target.stat().st_size > 0:
        return target, f"发现本地压缩包：{target}"
    try:
        print(f"开始下载学生作文外部验证集：{DOWNLOAD_URL}")
        urllib.request.urlretrieve(DOWNLOAD_URL, target)
        return target, f"已从 GitHub 下载：{DOWNLOAD_URL}"
    except Exception as exc:
        if target.exists() and target.stat().st_size == 0:
            target.unlink()
        return None, f"在线下载失败：{exc}"


def iter_json_objects_from_bytes(data: bytes, name: str) -> Iterable[Dict[str, object]]:
    text = data.decode("utf-8", errors="ignore").strip()
    if not text:
        return []
    if name.lower().endswith(".jsonl"):
        items = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                loaded = json.loads(line)
                if isinstance(loaded, dict):
                    items.append(loaded)
            except json.JSONDecodeError:
                continue
        return items
    try:
        loaded = json.loads(text)
    except json.JSONDecodeError:
        items = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                loaded_line = json.loads(line)
                if isinstance(loaded_line, dict):
                    items.append(loaded_line)
            except json.JSONDecodeError:
                continue
        return items
    if isinstance(loaded, list):
        return [item for item in loaded if isinstance(item, dict)]
    if isinstance(loaded, dict):
        for key in ["data", "essays", "items", "records"]:
            if isinstance(loaded.get(key), list):
                return [item for item in loaded[key] if isinstance(item, dict)]
        return [loaded]
    return []


def read_tar_bz2(path: Path) -> Tuple[List[Dict[str, object]], List[str]]:
    rows: List[Dict[str, object]] = []
    messages: List[str] = []
    try:
        with tarfile.open(path, "r:bz2") as archive:
            members = [m for m in archive.getmembers() if m.isfile() and m.name.lower().endswith((".json", ".jsonl"))]
            for member in members:
                extracted = archive.extractfile(member)
                if extracted is None:
                    continue
                data = extracted.read()
                objects = list(iter_json_objects_from_bytes(data, member.name))
                messages.append(f"{member.name} 读取 {len(objects)} 条原始记录。")
                rows.extend(objects)
    except tarfile.ReadError:
        # 兼容少数用户把 bz2 单文件误命名为 tar.bz2 的情况。
        data = bz2.open(path, "rb").read()
        objects = list(iter_json_objects_from_bytes(data, path.name))
        messages.append(f"{path.name} 作为 bz2 单文件读取 {len(objects)} 条原始记录。")
        rows.extend(objects)
    return rows, messages


def read_manual_json_files() -> Tuple[List[Dict[str, object]], List[str]]:
    rows: List[Dict[str, object]] = []
    messages: List[str] = []
    for path in sorted(RAW_DIR.glob("**/*")):
        if not path.is_file() or path.suffix.lower() not in {".json", ".jsonl"}:
            continue
        data = path.read_bytes()
        objects = list(iter_json_objects_from_bytes(data, path.name))
        rows.extend(objects)
        messages.append(f"{path.name} 读取 {len(objects)} 条原始记录。")
    return rows, messages


def load_raw_essays() -> Tuple[List[Dict[str, object]], List[str]]:
    tar_path, download_message = download_dataset_if_needed()
    messages = [download_message]
    if tar_path is not None:
        rows, tar_messages = read_tar_bz2(tar_path)
        messages.extend(tar_messages)
        if rows:
            return rows, messages
    manual_rows, manual_messages = read_manual_json_files()
    messages.extend(manual_messages)
    return manual_rows, messages


def get_first(item: Dict[str, object], keys: List[str], default: str = "") -> str:
    for key in keys:
        value = item.get(key)
        if value is None:
            continue
        if isinstance(value, list):
            joined = "\n".join([str(part).strip() for part in value if str(part).strip()])
            if joined:
                return joined
        elif str(value).strip():
            return str(value).strip()
    return default


def normalize_essay(item: Dict[str, object], index: int) -> Optional[Dict[str, object]]:
    text = normalize_text(get_first(item, ["content", "text", "essay", "article", "body"]))
    if not text:
        return None
    if chinese_count(text) < 50 and len(text) < 80:
        return None
    return {
        "essay_id": get_first(item, ["id", "essay_id", "_id"], f"essay_{index}"),
        "text": text,
        "grade": get_first(item, ["grade", "grade_level", "年级"], "未记录"),
        "category": get_first(item, ["category", "type", "genre", "文体"], "未记录"),
        "rating": get_first(item, ["rating", "score", "level", "评分"], "未记录"),
        "source_dataset": DATASET_NAME,
        "label": "human",
        "split_usage": "external_validation_only",
    }


def build_external_df(raw_rows: List[Dict[str, object]]) -> pd.DataFrame:
    normalized: List[Dict[str, object]] = []
    seen = set()
    for index, item in enumerate(raw_rows):
        row = normalize_essay(item, index)
        if row is None:
            continue
        key = normalize_for_duplicate(row["text"])
        if key in seen:
            continue
        seen.add(key)
        normalized.append(row)
    columns = ["essay_id", "text", "grade", "category", "rating", "source_dataset", "label", "split_usage"]
    return pd.DataFrame(normalized, columns=columns)


def load_model():
    if not MODEL_PATH.exists():
        return None
    loaded = joblib.load(MODEL_PATH)
    if not isinstance(loaded, dict) or loaded.get("metadata", {}).get("training_mode") != "formal_public":
        return None
    return loaded["pipeline"]


def predict_risk_for_df(df: pd.DataFrame) -> pd.DataFrame:
    from src.risk_model import heuristic_ai_probability, risk_level

    result = df.copy()
    pipeline = load_model()
    if pipeline is None:
        probabilities = [heuristic_ai_probability(text) for text in result["text"]]
        source = "本地启发式规则"
    else:
        classes = list(pipeline.classes_)
        ai_index = classes.index("ai") if "ai" in classes else 1
        probabilities = pipeline.predict_proba(result["text"])[:, ai_index].tolist()
        source = "TF-IDF + Logistic Regression formal_public 模型"
    result["ai_probability"] = [round(float(p), 4) for p in probabilities]
    result["aigc_risk_index"] = [round(float(p) * 100, 1) for p in probabilities]
    result["risk_level"] = [risk_level(float(p)) for p in probabilities]
    result["model_source"] = source
    return result


def distribution(series: pd.Series) -> Dict[str, int]:
    return {str(key): int(value) for key, value in series.fillna("未记录").value_counts().to_dict().items()}


def write_outputs(raw_count: int, df: pd.DataFrame, predictions: pd.DataFrame, messages: List[str]) -> None:
    if df.empty:
        df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")
        predictions.to_csv(PREDICTIONS_PATH, index=False, encoding="utf-8-sig")
        metrics = {
            "data_loaded": False,
            "raw_sample_count": raw_count,
            "valid_sample_count": 0,
            "messages": messages,
            "instruction": "请将 pretrain_essays.tar.bz2 或解压后的 json/jsonl 文件放入 data/raw/student_essays/ 后重新运行脚本。",
        }
        METRICS_PATH.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
        REPORT_PATH.write_text(
            "# 中文学生作文外部验证报告\n\n"
            "当前未读取到有效学生作文数据。\n\n"
            "请将 `pretrain_essays.tar.bz2` 或解压后的 `json/jsonl` 文件放入 `data/raw/student_essays/` 后重新运行：\n\n"
            "```powershell\npython scripts/prepare_student_essay_external_validation.py\n```\n\n"
            "学生作文外部验证集只有 human 标签，只能观察模型对真实学生作文的误报风险，不能衡量 AI 文本召回率。\n",
            encoding="utf-8",
        )
        return

    df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")
    predictions.to_csv(PREDICTIONS_PATH, index=False, encoding="utf-8-sig")

    risk_dist = distribution(predictions["risk_level"])
    grade_dist = distribution(predictions["grade"])
    category_dist = distribution(predictions["category"])
    medium_or_above = int((predictions["risk_level"] != "低风险").sum())
    high_or_above = int(predictions["risk_level"].isin(["高风险", "高置信高风险"]).sum())
    very_high = int((predictions["risk_level"] == "高置信高风险").sum())
    valid_count = int(len(predictions))
    metrics = {
        "data_loaded": True,
        "raw_sample_count": int(raw_count),
        "valid_sample_count": valid_count,
        "grade_distribution": grade_dist,
        "category_distribution": category_dist,
        "risk_distribution": risk_dist,
        "false_positive_observation": {
            "medium_or_above_count": medium_or_above,
            "medium_or_above_rate": round(medium_or_above / max(valid_count, 1), 4),
            "high_or_above_count": high_or_above,
            "high_or_above_rate": round(high_or_above / max(valid_count, 1), 4),
            "very_high_count": very_high,
            "very_high_rate": round(very_high / max(valid_count, 1), 4),
        },
        "messages": messages,
        "limitation": "学生作文外部验证集只有 human 标签，只能观察模型对真实学生作文的误报风险，不能衡量 AI 文本召回率。",
    }
    METRICS_PATH.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")

    grade_lines = "\n".join([f"- {key}：{value}" for key, value in grade_dist.items()]) or "- 暂无"
    category_lines = "\n".join([f"- {key}：{value}" for key, value in category_dist.items()]) or "- 暂无"
    risk_lines = "\n".join([f"- {key}：{value}" for key, value in risk_dist.items()]) or "- 暂无"
    message_lines = "\n".join([f"- {message}" for message in messages]) or "- 无"
    REPORT_PATH.write_text(
        "# 中文学生作文外部验证报告\n\n"
        "## 一、数据读取\n"
        f"- 原始读取样本数：{raw_count}\n"
        f"- 有效样本数：{valid_count}\n"
        "- 标签：human\n"
        "- 用途：external_validation_only，不参与 HC3 训练、阈值选择或 public_test 评估。\n\n"
        "## 二、读取过程\n"
        f"{message_lines}\n\n"
        "## 三、年级分布\n"
        f"{grade_lines}\n\n"
        "## 四、文体分布\n"
        f"{category_lines}\n\n"
        "## 五、低/中/高风险分布\n"
        f"{risk_lines}\n\n"
        "## 六、human-only 外部验证误报观察\n"
        f"- 中风险及以上：{medium_or_above} 篇，占 {metrics['false_positive_observation']['medium_or_above_rate']:.2%}\n"
        f"- 高风险及以上：{high_or_above} 篇，占 {metrics['false_positive_observation']['high_or_above_rate']:.2%}\n"
        f"- 高置信高风险：{very_high} 篇，占 {metrics['false_positive_observation']['very_high_rate']:.2%}\n\n"
        "这些结果用于观察模型在真实学生作文风格文本上的误报风险，不用于训练当前 AIGC 分类器。\n\n"
        "## 七、局限性\n"
        "学生作文外部验证集只有 human 标签，只能观察模型对真实学生作文的误报风险，不能衡量 AI 文本召回率。\n"
        "该外部验证集不参与训练，不作为纪律判定依据。输出仅供教师参考。\n",
        encoding="utf-8",
    )


def main() -> int:
    print("开始准备中文学生作文 human-only 外部验证集。")
    ensure_dirs()
    raw_rows, messages = load_raw_essays()
    df = build_external_df(raw_rows)
    predictions = predict_risk_for_df(df) if not df.empty else df.copy()
    write_outputs(len(raw_rows), df, predictions, messages)
    print(f"原始读取样本数：{len(raw_rows)}")
    print(f"有效样本数：{len(df)}")
    print(f"标准文件：{OUTPUT_PATH}")
    print(f"外部验证报告：{REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
