"""在 public_test.csv 上评估正式基线模型。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

import joblib
import pandas as pd
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = PROJECT_ROOT / "models" / "aigc_tfidf_lr.joblib"
TEST_PATH = PROJECT_ROOT / "data" / "processed" / "public_test.csv"
SUMMARY_PATH = PROJECT_ROOT / "data" / "processed" / "dataset_summary.json"
REPORTS_DIR = PROJECT_ROOT / "reports"
METRICS_PATH = REPORTS_DIR / "model_metrics.json"
CONFUSION_PATH = REPORTS_DIR / "confusion_matrix.csv"
MODEL_CARD_PATH = REPORTS_DIR / "model_card.md"
EVAL_REPORT_PATH = REPORTS_DIR / "evaluation_report.md"
THRESHOLD_PATH = REPORTS_DIR / "threshold_selection.json"

LABELS = ["human", "ai"]


def read_json(path: Path) -> Dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


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


def length_bucket(length: int) -> str:
    if length < 120:
        return "短文本"
    if length < 300:
        return "中文本"
    return "长文本"


def write_final_model_card(summary: Dict[str, object], threshold_info: Dict[str, object], metrics: Dict[str, object]) -> None:
    cm = metrics.get("confusion_matrix", {})
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
        "验证集用于选择风险阈值，public_test 仅用于最终评估。\n\n"
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
        "## public_test 指标\n"
        f"- test_sample_count：{metrics.get('test_sample_count')}\n"
        f"- Accuracy：{metrics.get('accuracy')}\n"
        f"- Precision(ai)：{metrics.get('precision')}\n"
        f"- Recall(ai)：{metrics.get('recall')}\n"
        f"- F1(ai)：{metrics.get('f1')}\n"
        f"- per_class_support：{metrics.get('per_class_support')}\n"
        f"- confusion_matrix：{cm}\n\n"
        "## 局限性\n"
        "- HC3 是人类回答 vs ChatGPT 回答，不完全等同于中学生作文。\n"
        "- 模型只能做风险提示，不能作为纪律处分依据。\n"
        "- 真实课堂应用需要结合学生草稿、访谈和 AI 使用声明。\n"
        "- 系统使用公开 Human-ChatGPT 对比语料构建 AIGC 文本风险提示基线模型，并通过 group-wise split 避免同问题样本跨训练集和测试集造成泄漏。由于公开语料不完全等同于真实中学生作文，本模型仅作为教师教学辅助和风险提示工具，不作为学生违纪判定或处分依据。\n"
    )
    MODEL_CARD_PATH.write_text(content, encoding="utf-8")


def main() -> int:
    print("第3步补充：开始在 public_test 上评估模型。")
    if not MODEL_PATH.exists():
        raise FileNotFoundError("模型文件不存在，请先执行 python scripts/train_baseline.py")
    if not TEST_PATH.exists():
        raise FileNotFoundError("public_test.csv 不存在，请先执行 python scripts/prepare_data.py")

    loaded = joblib.load(MODEL_PATH)
    if not isinstance(loaded, dict) or loaded.get("metadata", {}).get("training_mode") != "formal_public":
        raise RuntimeError("当前模型不是 formal_public 训练结果，不能报告正式 public_test 指标。")

    pipeline = loaded["pipeline"]
    metadata = loaded.get("metadata", {})
    threshold_info = read_json(THRESHOLD_PATH) or metadata.get("thresholds", {})
    threshold = float(threshold_info.get("selected_threshold", threshold_info.get("low_threshold", 0.45)))
    test_df = pd.read_csv(TEST_PATH)
    if test_df.empty:
        raise RuntimeError("public_test.csv 为空，不能评估正式模型。")

    classes = list(pipeline.classes_)
    ai_index = classes.index("ai") if "ai" in classes else 1
    probabilities = pipeline.predict_proba(test_df["text"])[:, ai_index]
    y_pred = predict_from_probability(probabilities, threshold)

    metrics = compute_metrics(test_df["label"], y_pred)
    cm = confusion_matrix(test_df["label"], y_pred, labels=LABELS)
    confusion_payload = {
        "labels": LABELS,
        "matrix": cm.astype(int).tolist(),
    }
    metrics.update(
        {
            "evaluated_on": "public_test",
            "final_evaluation_split": "public_test",
            "threshold": threshold,
            "test_sample_count": int(len(test_df)),
            "confusion_matrix": confusion_payload,
            "boundary_note": "该模型用于教学风险提示，不作为纪律处分依据。",
        }
    )

    pd.DataFrame(cm, index=[f"true_{x}" for x in LABELS], columns=[f"pred_{x}" for x in LABELS]).to_csv(
        CONFUSION_PATH,
        encoding="utf-8-sig",
    )

    test_df = test_df.copy()
    test_df["pred"] = y_pred
    test_df["length_bucket"] = test_df["chinese_chars"].apply(length_bucket)
    bucket_rows = []
    for bucket, group in test_df.groupby("length_bucket"):
        row = {"bucket": bucket, "count": int(len(group))}
        row.update(compute_metrics(group["label"], group["pred"]))
        bucket_rows.append(row)
    metrics["length_bucket_performance"] = bucket_rows

    previous = read_json(METRICS_PATH)
    previous.update(
        {
            "training_mode": "formal_public",
            "formal_model_trained": True,
            "training_data_file": "data/processed/public_train.csv",
            "threshold_selection_split": "public_val",
            "final_evaluation_split": "public_test",
            "test_metrics": metrics,
        }
    )
    METRICS_PATH.write_text(json.dumps(previous, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = read_json(SUMMARY_PATH)
    write_final_model_card(summary, threshold_info, metrics)

    bucket_lines = "\n".join(
        [f"- {row['bucket']}：数量 {row['count']}，Accuracy {row['accuracy']}，F1(ai) {row['f1']}" for row in bucket_rows]
    )
    report = (
        "# 模型评估报告\n\n"
        "该模型用于教学风险提示，不作为纪律处分依据。public_val 用于阈值选择，public_test 用于最终评估。\n\n"
        "## public_test 指标\n"
        f"- test_sample_count：{metrics['test_sample_count']}\n"
        f"- Accuracy：{metrics['accuracy']}\n"
        f"- Precision(ai)：{metrics['precision']}\n"
        f"- Recall(ai)：{metrics['recall']}\n"
        f"- F1(ai)：{metrics['f1']}\n"
        f"- per_class_support：{metrics['per_class_support']}\n\n"
        "## 不同长度文本表现\n"
        f"{bucket_lines or '- 暂无分桶结果。'}\n\n"
        "## 使用说明\n"
        "系统使用公开 Human-ChatGPT 对比语料构建 AIGC 文本风险提示基线模型，并通过 group-wise split 避免同问题样本跨训练集和测试集造成泄漏。由于公开语料不完全等同于真实中学生作文，本模型仅作为教师教学辅助和风险提示工具，不作为学生违纪判定或处分依据。\n"
    )
    EVAL_REPORT_PATH.write_text(report, encoding="utf-8")

    print("public_test 评估完成。")
    print(f"测试集指标：{metrics}")
    print(f"评估报告：{EVAL_REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
