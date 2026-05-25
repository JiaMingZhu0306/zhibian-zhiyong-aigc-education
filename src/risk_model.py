"""文本风险提示模型封装。

本模块输出的是教学风险提示，不是学生评价或纪律处理结论。
教师需要结合草稿、访谈、学生 AI 使用声明等材料综合判断。
"""

from __future__ import annotations

import re
import json
from pathlib import Path
from typing import Any, Dict, Optional

import joblib


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = PROJECT_ROOT / "models" / "aigc_tfidf_lr.joblib"
THRESHOLD_PATH = PROJECT_ROOT / "reports" / "threshold_selection.json"
RISK_CONFIG_PATH = PROJECT_ROOT / "config" / "risk_thresholds.json"

DEFAULT_RISK_CONFIG = {
    "low_risk_max": 0.35,
    "medium_risk_max": 0.75,
    "high_risk_max": 0.90,
    "label_names": {
        "low": "低风险",
        "medium": "中风险",
        "high": "高风险",
        "very_high": "高置信高风险",
    },
    "warning_text": "AIGC 风险指数仅供教师参考，不代表文本中 AI 生成内容占比，不作为纪律处分依据。",
}


_MODEL_CACHE: Optional[Dict[str, Any]] = None
_THRESHOLD_CACHE: Optional[Dict[str, Any]] = None


TEMPLATE_WORDS = [
    "综上所述",
    "总而言之",
    "不可否认",
    "值得注意的是",
    "在当今社会",
    "随着时代的发展",
    "具有重要意义",
    "我们应该",
    "从多个角度来看",
    "不仅如此",
]


def count_chinese_chars(text: str) -> int:
    """统计中文字符数量。"""
    return len(re.findall(r"[\u4e00-\u9fff]", text or ""))


def normalize_text(text: str) -> str:
    """进行轻量清洗，保留中文标点和换行。"""
    text = (text or "").strip()
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def load_thresholds() -> Dict[str, Any]:
    """读取页面风险等级阈值配置。"""
    global _THRESHOLD_CACHE
    if _THRESHOLD_CACHE is not None:
        return _THRESHOLD_CACHE
    thresholds = DEFAULT_RISK_CONFIG.copy()
    thresholds["label_names"] = DEFAULT_RISK_CONFIG["label_names"].copy()
    if RISK_CONFIG_PATH.exists():
        try:
            data = json.loads(RISK_CONFIG_PATH.read_text(encoding="utf-8"))
            thresholds.update(
                {
                    "low_risk_max": float(data.get("low_risk_max", DEFAULT_RISK_CONFIG["low_risk_max"])),
                    "medium_risk_max": float(data.get("medium_risk_max", DEFAULT_RISK_CONFIG["medium_risk_max"])),
                    "high_risk_max": float(data.get("high_risk_max", DEFAULT_RISK_CONFIG["high_risk_max"])),
                    "warning_text": data.get("warning_text", DEFAULT_RISK_CONFIG["warning_text"]),
                }
            )
            if isinstance(data.get("label_names"), dict):
                thresholds["label_names"].update(data["label_names"])
        except Exception:
            thresholds = DEFAULT_RISK_CONFIG.copy()
            thresholds["label_names"] = DEFAULT_RISK_CONFIG["label_names"].copy()
    _THRESHOLD_CACHE = thresholds
    return thresholds


def risk_level(ai_probability: float) -> str:
    """把 AI 风险概率转换为页面展示等级。"""
    thresholds = load_thresholds()
    labels = thresholds["label_names"]
    if ai_probability < thresholds["low_risk_max"]:
        return labels["low"]
    if ai_probability < thresholds["medium_risk_max"]:
        return labels["medium"]
    if ai_probability < thresholds["high_risk_max"]:
        return labels["high"]
    return labels["very_high"]


def load_model() -> Optional[Dict[str, Any]]:
    """加载本地基线模型；如果尚未训练则返回 None。"""
    global _MODEL_CACHE
    if _MODEL_CACHE is not None:
        return _MODEL_CACHE
    if not MODEL_PATH.exists():
        return None
    try:
        loaded = joblib.load(MODEL_PATH)
    except Exception:
        return None
    if isinstance(loaded, dict) and "pipeline" in loaded:
        metadata = loaded.get("metadata", {})
        if metadata.get("training_mode") != "formal_public":
            return None
        _MODEL_CACHE = loaded
    else:
        return None
    return _MODEL_CACHE


def heuristic_ai_probability(text: str, has_ai_statement: bool = False) -> float:
    """在模型不可用时使用可解释启发式生成演示风险分数。"""
    clean = normalize_text(text)
    chinese_count = count_chinese_chars(clean)
    if chinese_count == 0:
        return 0.35

    paragraphs = [p.strip() for p in clean.splitlines() if p.strip()]
    sentences = [s for s in re.split(r"[。！？!?；;]", clean) if s.strip()]
    avg_sentence_len = chinese_count / max(len(sentences), 1)
    paragraph_count = max(len(paragraphs), 1)
    template_hits = sum(1 for word in TEMPLATE_WORDS if word in clean)
    detail_hits = len(re.findall(r"(我|我们|第一次|记得|那天|妈妈|爸爸|同学|老师|家里|校园|操场|实验|观察|采访)", clean))
    digit_hits = len(re.findall(r"\d", clean))

    score = 0.42
    score += min(template_hits * 0.055, 0.22)
    if 22 <= avg_sentence_len <= 45:
        score += 0.08
    if paragraph_count >= 4 and len(set(len(p) // 20 for p in paragraphs)) <= 2:
        score += 0.08
    if detail_hits <= 2:
        score += 0.12
    if digit_hits == 0 and chinese_count > 350:
        score += 0.04
    if chinese_count < 120:
        score -= 0.08
    return max(0.05, min(0.95, score))


def predict_risk(
    text: str,
    assignment_type: str = "作文",
    grade: str = "初一",
    has_ai_statement: bool = False,
) -> Dict[str, Any]:
    """预测文本的疑似 AI 生成或 AI 润色风险。"""
    clean = normalize_text(text)
    model = load_model()
    source = "本地启发式规则"
    probability = heuristic_ai_probability(clean, has_ai_statement=False)

    if model is not None and clean:
        pipeline = model["pipeline"]
        try:
            classes = list(pipeline.classes_)
            probabilities = pipeline.predict_proba([clean])[0]
            ai_index = classes.index("ai") if "ai" in classes else 1
            probability = float(probabilities[ai_index])
            source = "TF-IDF + Logistic Regression 基线模型"
        except Exception:
            source = "模型读取异常，已切换为本地启发式规则"

    level = risk_level(probability)
    return {
        "text": clean,
        "assignment_type": assignment_type,
        "grade": grade,
        "has_ai_statement": bool(has_ai_statement),
        "process_transparency": "已填写 AI 使用声明" if has_ai_statement else "未填写 AI 使用声明",
        "ai_probability": round(probability, 4),
        "risk_score": round(probability * 100, 1),
        "risk_index": round(probability * 100, 1),
        "risk_level": level,
        "model_source": source,
        "thresholds": load_thresholds(),
        "advisory": load_thresholds()["warning_text"],
    }
