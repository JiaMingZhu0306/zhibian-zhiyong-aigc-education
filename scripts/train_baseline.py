"""训练 TF-IDF + Logistic Regression 基线模型。

正式训练只读取 data/processed/public_train.csv 和 public_val.csv。
如果公开数据未达到门槛，脚本不会训练正式模型，会写入 demo_mode 报告。
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score
from sklearn.pipeline import Pipeline


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
MODELS_DIR = PROJECT_ROOT / "models"
REPORTS_DIR = PROJECT_ROOT / "reports"
MODEL_PATH = MODELS_DIR / "aigc_tfidf_lr.joblib"
METRICS_PATH = REPORTS_DIR / "model_metrics.json"
CONFUSION_PATH = REPORTS_DIR / "confusion_matrix.csv"
MODEL_CARD_PATH = REPORTS_DIR / "model_card.md"
THRESHOLD_PATH = REPORTS_DIR / "threshold_selection.json"
SUMMARY_PATH = PROCESSED_DIR / "dataset_summary.json"
SPLIT_AUDIT_PATH = REPORTS_DIR / "split_audit.json"

PUBLIC_TRAIN_PATH = PROCESSED_DIR / "public_train.csv"
PUBLIC_VAL_PATH = PROCESSED_DIR / "public_val.csv"

LABELS = ["human", "ai"]
DEFAULT_HIGH_THRESHOLD = 0.75


def read_json(path: Path) -> Dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_public_split(path: Path, name: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"缺少 {path}，请先执行 python scripts/prepare_data.py")
    df = pd.read_csv(path)
    if df.empty:
        raise RuntimeError(f"{name} 为空，不能训练正式模型。")
    required = {"text", "label", "group_id"}
    missing = required - set(df.columns)
    if missing:
        raise RuntimeError(f"{name} 缺少字段：{sorted(missing)}")
    return df


def validate_formal_training(summary: Dict[str, object], split_audit: Dict[str, object]) -> Tuple[bool, List[str]]:
    reasons: List[str] = []
    if summary.get("training_mode") != "formal_public":
        reasons.append("dataset_summary.json 未标记为 formal_public。")
    if not summary.get("can_train_formal_model"):
        reasons.append("数据准备阶段未通过正式训练门槛。")
    for key in ["overlap_train_val_groups", "overlap_train_test_groups", "overlap_val_test_groups"]:
        if split_audit.get(key):
            reasons.append(f"{key} 非空，存在 group_id 跨 split。")
    return not reasons, reasons


def compute_metrics(y_true, y_pred) -> Dict[str, object]:
    return {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "precision": round(float(precision_score(y_true, y_pred, pos_label="ai", zero_division=0)), 4),
        "recall": round(float(recall_score(y_true, y_pred, pos_label="ai", zero_division=0)), 4),
        "f1": round(float(f1_score(y_true, y_pred, pos_label="ai", zero_division=0)), 4),
        "per_class_support": {label: int((pd.Series(y_true) == label).sum()) for label in LABELS},
    }


def predict_from_probability(probabilities, threshold: float) -> List[str]:
    return ["ai" if probability >= threshold else "human" for probability in probabilities]


def select_threshold(pipeline: Pipeline, val_df: pd.DataFrame) -> Dict[str, object]:
    classes = list(pipeline.classes_)
    ai_index = classes.index("ai") if "ai" in classes else 1
    probabilities = pipeline.predict_proba(val_df["text"])[:, ai_index]
    candidate_thresholds = [round(x / 100, 2) for x in range(30, 86, 5)]
    rows: List[Dict[str, object]] = []
    for threshold in candidate_thresholds:
        y_pred = predict_from_probability(probabilities, threshold)
        rows.append(
            {
                "threshold": threshold,
                "f1": round(float(f1_score(val_df["label"], y_pred, pos_label="ai", zero_division=0)), 4),
                "precision": round(float(precision_score(val_df["label"], y_pred, pos_label="ai", zero_division=0)), 4),
                "recall": round(float(recall_score(val_df["label"], y_pred, pos_label="ai", zero_division=0)), 4),
            }
        )
    best_f1 = max(row["f1"] for row in rows)
    best_candidates = [row for row in rows if row["f1"] == best_f1]
    selected = min(best_candidates, key=lambda row: abs(row["threshold"] - 0.45))["threshold"]
    high_threshold = max(DEFAULT_HIGH_THRESHOLD, round(min(0.95, selected + 0.25), 2))
    return {
        "candidate_thresholds": candidate_thresholds,
        "val_f1_by_threshold": rows,
        "selected_threshold": selected,
        "low_threshold": selected,
        "high_threshold": high_threshold,
        "selection_reason": "在 public_val.csv 上选择 ai 类 F1 最高的阈值；若并列，选择最接近原教学展示阈值 0.45 的值。test 集未参与阈值选择。",
    }


def write_demo_mode_model_card(summary: Dict[str, object], reasons: List[str]) -> None:
    reason_lines = "\n".join([f"- {reason}" for reason in reasons]) or "- 公开数据未满足正式训练门槛。"
    content = (
        "# 模型卡：AIGC 文本风险提示基线模型\n\n"
        "## 当前状态\n"
        "当前公开数据不足，系统进入 demo_mode，不能报告正式模型性能。"
        "当前版本完成了系统流程和演示数据验证，但公开训练数据尚未成功接入，模型指标不能作为正式效果结论。\n\n"
        "## 阻断原因\n"
        f"{reason_lines}\n\n"
        "## 使用边界\n"
        "输出仅供教师参考，不作为纪律处分依据。demo_texts.csv 只能用于页面演示，不能作为正式模型评估依据。\n"
    )
    MODEL_CARD_PATH.write_text(content, encoding="utf-8")
    metrics = {
        "training_mode": "demo_mode",
        "formal_model_trained": False,
        "blockers": reasons,
        "dataset_summary": summary,
        "note": "当前仅为演示数据，不作为正式模型结果。",
    }
    METRICS_PATH.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    pd.DataFrame(columns=["pred_human", "pred_ai"], index=["true_human", "true_ai"]).to_csv(
        CONFUSION_PATH,
        encoding="utf-8-sig",
    )
    if MODEL_PATH.exists():
        MODEL_PATH.unlink()


def write_training_model_card(
    summary: Dict[str, object],
    threshold_info: Dict[str, object],
    val_metrics: Dict[str, object],
) -> None:
    content = (
        "# 模型卡：AIGC 文本风险提示基线模型\n\n"
        "## 模型用途\n"
        "本模型用于中学生作文、读后感、学习总结等文本的教学风险提示，帮助教师发现疑似 AI 生成或 AI 润色特征，并开展 AI 素养教育。"
        "输出仅供教师参考，不作为纪律处分依据。\n\n"
        "## 数据来源\n"
        f"- 数据源：{summary.get('selected_data_source', '未记录')}\n"
        f"- 清洗去重后总样本数：{summary.get('total_after_cleaning', '未记录')}\n"
        f"- 标签分布：{summary.get('label_distribution', {})}\n"
        f"- train/val/test：{summary.get('train_size')} / {summary.get('val_size')} / {summary.get('test_size')}\n"
        "- public dataset：用于训练和评估模型。\n"
        "- demo_texts.csv：仅用于页面演示，不参与正式模型评估。\n"
        "- local submissions.csv：仅用于教师本地试用记录。\n"
        "- teacher feedback：后续人工补充。\n\n"
        "## 划分方式\n"
        "数据采用 group-wise split，按同一 question 或原始行构造 group_id，避免同问题下的人类回答和 ChatGPT 回答跨训练集、验证集和测试集造成泄漏。"
        "验证集用于选择风险阈值，测试集仅用于最终评估。\n\n"
        "## 模型方法\n"
        "- 特征：TF-IDF 字符 n-gram\n"
        "- 参数：analyzer='char_wb'，ngram_range=(2, 5)，max_features=50000，min_df=2\n"
        "- 分类器：LogisticRegression(max_iter=1000, class_weight='balanced', random_state=42)\n\n"
        "## 阈值选择\n"
        f"- 低/中风险分界：{threshold_info.get('low_threshold')}\n"
        f"- 高风险分界：{threshold_info.get('high_threshold')}\n"
        f"- 选择说明：{threshold_info.get('selection_reason')}\n\n"
        "## 页面风险等级阈值\n"
        "- 低风险：`0 <= ai_probability < 0.35`\n"
        "- 中风险：`0.35 <= ai_probability < 0.75`\n"
        "- 高风险：`0.75 <= ai_probability < 0.90`\n"
        "- 高置信高风险：`ai_probability >= 0.90`\n\n"
        "AIGC 风险指数不是 AI 内容占比，而是模型参考概率。以上页面阈值用于教学解释和分层引导，不是纪律判定线。\n\n"
        "## 中文学生作文外部验证\n"
        "除 HC3-Chinese 公开 Human-ChatGPT 对比语料外，系统还支持接入 7–12 年级中文学生作文数据作为 human-only 外部验证集，用于观察模型在真实学生作文风格上的误报风险。该外部验证集不参与训练，不作为纪律判定依据。\n\n"
        "## 验证集指标\n"
        f"- Accuracy：{val_metrics.get('accuracy')}\n"
        f"- Precision(ai)：{val_metrics.get('precision')}\n"
        f"- Recall(ai)：{val_metrics.get('recall')}\n"
        f"- F1(ai)：{val_metrics.get('f1')}\n\n"
        "## 局限性\n"
        "- HC3 是人类回答 vs ChatGPT 回答，不完全等同于中学生作文。\n"
        "- 模型只能做风险提示，不能作为纪律处分依据。\n"
        "- 真实课堂应用需要结合学生草稿、访谈和 AI 使用声明。\n"
        "- 系统使用公开 Human-ChatGPT 对比语料构建 AIGC 文本风险提示基线模型，并通过 group-wise split 避免同问题样本跨训练集和测试集造成泄漏。由于公开语料不完全等同于真实中学生作文，本模型仅作为教师教学辅助和风险提示工具，不作为学生违纪判定或处分依据。\n"
    )
    MODEL_CARD_PATH.write_text(content, encoding="utf-8")


def main() -> int:
    print("第3步：开始训练公开数据基线模型。")
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    summary = read_json(SUMMARY_PATH)
    split_audit = read_json(SPLIT_AUDIT_PATH)
    ok, reasons = validate_formal_training(summary, split_audit)
    if not ok:
        write_demo_mode_model_card(summary, reasons)
        print("公开数据未满足正式训练条件，已写入 demo_mode 模型卡。")
        for reason in reasons:
            print(f"阻断原因：{reason}")
        return 0

    train_df = load_public_split(PUBLIC_TRAIN_PATH, "public_train.csv")
    val_df = load_public_split(PUBLIC_VAL_PATH, "public_val.csv")

    pipeline = Pipeline(
        steps=[
            (
                "tfidf",
                TfidfVectorizer(
                    analyzer="char_wb",
                    ngram_range=(2, 5),
                    max_features=50000,
                    min_df=2,
                ),
            ),
            (
                "clf",
                LogisticRegression(
                    max_iter=1000,
                    class_weight="balanced",
                    random_state=42,
                ),
            ),
        ]
    )
    pipeline.fit(train_df["text"], train_df["label"])
    threshold_info = select_threshold(pipeline, val_df)
    THRESHOLD_PATH.write_text(json.dumps(threshold_info, ensure_ascii=False, indent=2), encoding="utf-8")

    classes = list(pipeline.classes_)
    ai_index = classes.index("ai") if "ai" in classes else 1
    val_probabilities = pipeline.predict_proba(val_df["text"])[:, ai_index]
    val_pred = predict_from_probability(val_probabilities, float(threshold_info["selected_threshold"]))
    val_metrics = compute_metrics(val_df["label"], val_pred)
    val_metrics.update(
        {
            "evaluated_on": "public_val",
            "sample_count": int(len(val_df)),
            "threshold": threshold_info["selected_threshold"],
        }
    )

    labels = LABELS
    cm = confusion_matrix(val_df["label"], val_pred, labels=labels)
    pd.DataFrame(cm, index=[f"true_{x}" for x in labels], columns=[f"pred_{x}" for x in labels]).to_csv(
        CONFUSION_PATH,
        encoding="utf-8-sig",
    )

    metadata = {
        "training_mode": "formal_public",
        "trained_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "dataset_summary": summary,
        "thresholds": threshold_info,
        "validation_metrics": val_metrics,
        "training_data_file": "data/processed/public_train.csv",
        "threshold_selection_file": "reports/threshold_selection.json",
    }
    joblib.dump({"pipeline": pipeline, "metadata": metadata}, MODEL_PATH)

    metrics = {
        "training_mode": "formal_public",
        "formal_model_trained": True,
        "trained_at": metadata["trained_at"],
        "training_data_file": "data/processed/public_train.csv",
        "threshold_selection_split": "public_val",
        "risk_thresholds": {
            "low_threshold": threshold_info["low_threshold"],
            "high_threshold": threshold_info["high_threshold"],
        },
        "validation_metrics": val_metrics,
        "note": "验证集用于阈值选择，最终效果以 public_test 评估为准。",
    }
    METRICS_PATH.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    write_training_model_card(summary, threshold_info, val_metrics)

    print("公开数据模型训练完成。")
    print(f"模型文件：{MODEL_PATH}")
    print(f"阈值文件：{THRESHOLD_PATH}")
    print(f"验证集指标：{val_metrics}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
