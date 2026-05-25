"""图片作业批量导入与分析工具。"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Dict, Iterable, List, Tuple

import pandas as pd

from src.explanation import build_feedback
from src.ocr_utils import ocr_image
from src.risk_model import predict_risk
from src.storage import make_preview, make_text_hash, save_submission


def build_anonymous_id(index: int) -> str:
    return f"S{index:03d}"


def process_single_image_upload(uploaded_file, ocr_provider: str | None = None) -> Dict[str, object]:
    """对 Streamlit 上传文件执行 OCR。ocr_provider 参数保留用于扩展。"""
    image_bytes = uploaded_file.getvalue()
    suffix = "." + uploaded_file.name.split(".")[-1].lower() if "." in uploaded_file.name else ".png"
    result = ocr_image(image_bytes, file_suffix=suffix)
    text = str(result.get("text", ""))
    confidence = result.get("mean_confidence")
    need_review = len(text.strip()) < 80 or (confidence is not None and float(confidence) < 0.60) or not result.get("success")
    return {
        "file_name": uploaded_file.name,
        "file_size": len(image_bytes),
        "ocr_status": "success" if result.get("success") else "failed",
        "ocr_provider": result.get("provider", "none"),
        "ocr_confidence": confidence,
        "ocr_text": text,
        "ocr_text_preview": make_preview(text, 80),
        "need_manual_review": bool(need_review),
        "error": result.get("error", ""),
    }


def analyze_text_record(
    text: str,
    assignment_type: str,
    grade: str,
    has_ai_statement: bool | str,
    source_type: str,
    source_note: str,
    anonymous_student_id: str = "",
    ocr_confidence: float | None = None,
    ocr_status: str = "",
    save_to_dashboard: bool = True,
) -> Dict[str, object]:
    statement_bool = has_ai_statement in {True, "true", "1", "是", "已填写"}
    result = predict_risk(text, assignment_type=assignment_type, grade=grade, has_ai_statement=statement_bool)
    feedback = build_feedback(text, result)
    text_hash = make_text_hash(text, assignment_type, grade)
    saved = False
    record_id = str(uuid.uuid4())
    if save_to_dashboard:
        _, saved = save_submission(
            {
                "record_id": record_id,
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "text": text,
                "text_hash": text_hash,
                "assignment_type": assignment_type,
                "grade": grade,
                "has_ai_statement": "已填写" if statement_bool else "未填写",
                "aigc_risk_index": result["risk_index"],
                "ai_probability": result["ai_probability"],
                "risk_level": result["risk_level"],
                "process_transparency": result["process_transparency"],
                "reasons": "；".join(feedback["reasons"][:5]),
                "suggestions": "；".join(feedback["suggestions"][:5]),
                "source_type": source_type,
                "demo_flag": False,
                "source_note": source_note,
                "anonymous_student_id": anonymous_student_id,
                "ocr_confidence": ocr_confidence,
                "ocr_status": ocr_status,
            },
            dedupe=True,
        )
    return {
        "record_id": record_id,
        "anonymous_student_id": anonymous_student_id,
        "assignment_type": assignment_type,
        "grade": grade,
        "aigc_risk_index": result["risk_index"],
        "ai_probability": result["ai_probability"],
        "risk_level": result["risk_level"],
        "process_transparency": result["process_transparency"],
        "reasons_summary": "；".join(feedback["reasons"][:3]),
        "suggestions_summary": "；".join(feedback["suggestions"][:3]),
        "saved_to_dashboard": saved,
        "text_hash": text_hash,
        "text_preview": make_preview(text, 80),
    }


def batch_analyze_records(records: Iterable[Dict[str, object]], save_to_dashboard: bool = True, force_review_records: bool = False) -> List[Dict[str, object]]:
    outputs: List[Dict[str, object]] = []
    for item in records:
        text = str(item.get("corrected_text") or item.get("ocr_text") or "").strip()
        if not text:
            outputs.append({**item, "saved_to_dashboard": False, "skip_reason": "文本为空或 OCR 失败"})
            continue
        if len(text) < 80:
            outputs.append({**item, "saved_to_dashboard": False, "skip_reason": "文本过短，建议人工复核"})
            continue
        if item.get("need_manual_review") and not force_review_records:
            outputs.append({**item, "saved_to_dashboard": False, "skip_reason": "需要人工复核，未强制分析"})
            continue
        outputs.append(
            analyze_text_record(
                text=text,
                assignment_type=str(item.get("assignment_type", "其他")),
                grade=str(item.get("grade", "未记录")),
                has_ai_statement=item.get("has_ai_statement", "未填写"),
                source_type="batch_image_ocr",
                source_note="批量图片 OCR 识别后分析",
                anonymous_student_id=str(item.get("anonymous_student_id", "")),
                ocr_confidence=item.get("ocr_confidence"),
                ocr_status=str(item.get("ocr_status", "")),
                save_to_dashboard=save_to_dashboard,
            )
        )
    return outputs


def validate_batch_csv(df: pd.DataFrame) -> Tuple[bool, List[str]]:
    required = {"anonymous_student_id", "corrected_text", "assignment_type", "grade", "has_ai_statement"}
    missing = sorted(required - set(df.columns))
    errors: List[str] = []
    if missing:
        errors.append(f"缺少字段：{missing}")
    if "corrected_text" in df.columns and df["corrected_text"].fillna("").astype(str).str.strip().eq("").all():
        errors.append("corrected_text 全为空。")
    return not errors, errors
