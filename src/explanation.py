"""生成可解释教学反馈。"""

from __future__ import annotations

import re
from typing import Dict, List

from .risk_model import TEMPLATE_WORDS, count_chinese_chars, normalize_text


def analyze_text_features(text: str) -> Dict[str, float]:
    """提取用于解释的轻量特征。"""
    clean = normalize_text(text)
    chinese_count = count_chinese_chars(clean)
    sentences = [s.strip() for s in re.split(r"[。！？!?；;]", clean) if s.strip()]
    paragraphs = [p.strip() for p in clean.splitlines() if p.strip()]
    sentence_lengths = [count_chinese_chars(s) for s in sentences] or [0]
    template_hits = [word for word in TEMPLATE_WORDS if word in clean]
    personal_detail_hits = re.findall(
        r"(我|我们|第一次|记得|那天|妈妈|爸爸|同学|老师|家里|校园|操场|实验|观察|采访|失败|困惑|修改)",
        clean,
    )

    avg_len = sum(sentence_lengths) / max(len(sentence_lengths), 1)
    variance = sum((x - avg_len) ** 2 for x in sentence_lengths) / max(len(sentence_lengths), 1)
    return {
        "chinese_count": chinese_count,
        "sentence_count": len(sentences),
        "paragraph_count": len(paragraphs),
        "avg_sentence_len": round(avg_len, 2),
        "sentence_length_variance": round(variance, 2),
        "template_hit_count": len(template_hits),
        "personal_detail_count": len(personal_detail_hits),
    }


def build_explanations(text: str, risk_result: Dict[str, object]) -> List[str]:
    """根据模型分数和规则特征生成教师可理解原因。"""
    features = analyze_text_features(text)
    reasons: List[str] = []
    score = float(risk_result.get("ai_probability", 0))

    if score >= 0.35:
        reasons.append("AIGC 风险指数提示文本可能存在疑似 AI 生成或 AI 润色特征。")
    if features["template_hit_count"] >= 2:
        reasons.append("语言中出现较多模板化表达，整体表达较为概括。")
    if features["personal_detail_count"] <= 2 and features["chinese_count"] >= 180:
        reasons.append("文本中个人经历、具体场景和过程细节相对不足。")
    if 20 <= features["avg_sentence_len"] <= 45 and features["sentence_length_variance"] < 70:
        reasons.append("部分句式长度较为接近，阅读上呈现较整齐的节奏。")
    if features["paragraph_count"] >= 4:
        reasons.append("段落结构较规整，可进一步核对是否保留了真实写作过程。")
    if score >= 0.75:
        reasons.append("观点展开比较平稳但个性化表达不足，建议重点查看草稿和修改痕迹。")

    if not reasons:
        reasons.append("当前文本未呈现明显模板化特征，但仍建议保留写作过程材料。")
    reasons.append("以上解释是教学反馈，不作为纪律处分依据。")
    return reasons


def build_suggestions(text: str, risk_result: Dict[str, object]) -> List[str]:
    """生成学生可执行的修改建议。"""
    features = analyze_text_features(text)
    suggestions = [
        "补充真实经历、观察过程或课堂学习细节。",
        "写明主要资料来源，区分查阅材料和个人观点。",
        "保留提纲、草稿、修改记录，便于说明自己的学习过程。",
        "如使用生成式 AI，请标注 AI 辅助使用情况。",
        "用自己的语言重写关键段落，尤其是结论和观点展开部分。",
    ]
    if features["personal_detail_count"] <= 2:
        suggestions.insert(0, "增加一个具体场景，例如一次讨论、实验、阅读或修改经历。")
    return suggestions[:6]


def build_feedback(text: str, risk_result: Dict[str, object]) -> Dict[str, object]:
    """统一输出解释、建议和特征摘要。"""
    return {
        "features": analyze_text_features(text),
        "reasons": build_explanations(text, risk_result),
        "suggestions": build_suggestions(text, risk_result),
        "notice": "解释内容仅供教师参考，需结合草稿、访谈、学生 AI 使用声明综合判断。",
    }
