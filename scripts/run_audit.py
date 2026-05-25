"""项目自检脚本。"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List, Tuple

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = PROJECT_ROOT / "reports"
AUDIT_PATH = REPORTS_DIR / "audit_report.md"


REQUIRED_FILES = [
    "app.py",
    "requirements.txt",
    "requirements_ocr.txt",
    "README.md",
    "docs/01_开发与应用报告_草稿.md",
    "docs/02_案例信息表_填报草稿.md",
    "docs/03_演示视频脚本_8分钟.md",
    "docs/04_教师使用手册.md",
    "docs/05_安装部署说明.md",
    "docs/06_数据集与模型说明.md",
    "docs/07_隐私合规与使用边界说明.md",
    "docs/08_教师试用反馈表.md",
    "docs/09_配套资源清单.md",
    "docs/11_系统截图清单.md",
    "config/risk_thresholds.json",
    "scripts/prepare_data.py",
    "scripts/prepare_student_essay_external_validation.py",
    "scripts/generate_ai_essay_counterpart_optional.py",
    "scripts/train_baseline.py",
    "scripts/evaluate_model.py",
    "scripts/run_audit.py",
    "scripts/make_demo_package.py",
    "scripts/seed_dashboard_demo_records.py",
    "scripts/ocr_dependency_check.py",
    "scripts/batch_upload_schema_check.py",
    "scripts/test_ocr_on_local_images.py",
    "src/risk_model.py",
    "src/explanation.py",
    "src/llm_client.py",
    "src/storage.py",
    "src/ocr_utils.py",
    "src/batch_processor.py",
    "src/report_generator.py",
    "reports/data_source_audit.md",
    "reports/split_audit.json",
    "reports/dataset_label_distribution.csv",
    "reports/duplicate_audit.csv",
    "reports/risk_threshold_explanation.md",
    "data/processed/public_train.csv",
    "data/processed/public_val.csv",
    "data/processed/public_test.csv",
]

MODEL_OUTPUTS = [
    "models/aigc_tfidf_lr.joblib",
    "reports/model_metrics.json",
    "reports/model_card.md",
]

PUBLIC_DATA_FILES = [
    "data/processed/public_train.csv",
    "data/processed/public_val.csv",
    "data/processed/public_test.csv",
]

RISK_TERMS = [
    "AIGC" + "率",
    "AI" + "占比",
    "判定" + "作弊",
    "确定" + "AI" + "生成",
    "确定由" + "AI" + "生成",
    "抓" + "作弊",
    "绝对" + "准确",
    "100%" + "准确",
]

REQUIRED_PHRASES = [
    "仅供教师参考",
    "不作为纪律" + "处分" + "依据",
    "AI 辅助生成",
    "匿名化",
]


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8-sig")


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def check_required_files() -> Tuple[List[str], List[str]]:
    passes, failures = [], []
    for file in REQUIRED_FILES:
        path = PROJECT_ROOT / file
        if path.exists() and path.stat().st_size > 0:
            passes.append(f"文件存在且非空：{file}")
        else:
            failures.append(f"缺少或为空：{file}")
    return passes, failures


def check_model_outputs() -> Tuple[List[str], List[str]]:
    passes, warnings = [], []
    for file in MODEL_OUTPUTS:
        path = PROJECT_ROOT / file
        if path.exists() and path.stat().st_size > 0:
            passes.append(f"模型结果存在：{file}")
        else:
            warnings.append(f"模型结果尚未生成：{file}。如训练失败，应在报告中如实说明。")
    return passes, warnings


def iter_scan_files() -> List[Path]:
    ignored = {".git", ".venv", "venv", "__pycache__", "deliverables"}
    files = []
    for path in PROJECT_ROOT.rglob("*"):
        if any(part in ignored for part in path.parts):
            continue
        if path == AUDIT_PATH:
            continue
        if path.suffix.lower() in {".md", ".py"}:
            files.append(path)
    return files


def is_allowed_context(text: str, term: str, start: int) -> bool:
    if term != "处分" + "依据":
        return False
    left = max(0, start - 16)
    right = min(len(text), start + len(term) + 8)
    context = text[left:right]
    return (
        "不作为纪律" + "处分" + "依据" in context
        or "不能作为纪律" + "处分" + "依据" in context
        or "不作为学生违纪判定或" + "处分" + "依据" in context
    )


def check_wording_risk() -> Tuple[List[str], List[str]]:
    warnings, failures = [], []
    for path in iter_scan_files():
        text = read_text(path)
        rel = path.relative_to(PROJECT_ROOT)
        for term in RISK_TERMS:
            for match in re.finditer(re.escape(term), text):
                if is_allowed_context(text, term, match.start()):
                    warnings.append(f"{rel} 出现合规必要短语中的“{term}”，上下文为否定边界提示。")
                else:
                    failures.append(f"{rel} 出现需修改表述：“{term}”。")
    return warnings, failures


def check_compliance_phrases() -> Tuple[List[str], List[str]]:
    passes, failures = [], []
    app_text = read_text(PROJECT_ROOT / "app.py") if (PROJECT_ROOT / "app.py").exists() else ""
    docs_text = ""
    for path in (PROJECT_ROOT / "docs").glob("*.md"):
        docs_text += "\n" + read_text(path)
    combined = app_text + "\n" + docs_text
    for phrase in REQUIRED_PHRASES:
        if phrase in combined:
            passes.append(f"已出现合规提示：{phrase}")
        else:
            failures.append(f"缺少合规提示：{phrase}")
    return passes, failures


def check_report_length() -> Tuple[List[str], List[str]]:
    path = PROJECT_ROOT / "docs" / "01_开发与应用报告_草稿.md"
    if not path.exists():
        return [], ["开发与应用报告缺失，无法统计字数。"]
    text = read_text(path)
    chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
    message = f"开发与应用报告中文字数统计：{chinese_chars} 个中文字符。"
    if chinese_chars <= 3300:
        return [message], []
    return [], [message + " 建议压缩到 3000 字左右。"]


def check_public_data_files() -> Tuple[List[str], List[str], List[str]]:
    passes, warnings, failures = [], [], []
    for file in PUBLIC_DATA_FILES:
        path = PROJECT_ROOT / file
        if not path.exists():
            failures.append(f"公开数据文件缺失：{file}")
            continue
        try:
            df = pd.read_csv(path)
        except Exception as exc:
            failures.append(f"公开数据文件无法读取：{file}，原因：{exc}")
            continue
        if df.empty:
            warnings.append(f"严重警告：公开数据文件为空：{file}")
        else:
            passes.append(f"公开数据文件存在且非空：{file}，{len(df)} 行")

    summary_path = PROJECT_ROOT / "data" / "processed" / "dataset_summary.json"
    if summary_path.exists():
        passes.append("dataset_summary.json 存在。")
    else:
        failures.append("dataset_summary.json 缺失。")
    return passes, warnings, failures


def check_dataset_scale_and_split() -> Tuple[List[str], List[str], List[str]]:
    passes, warnings, failures = [], [], []
    summary = read_json(PROJECT_ROOT / "data" / "processed" / "dataset_summary.json")
    split_audit = read_json(PROJECT_ROOT / "reports" / "split_audit.json")
    if not summary:
        failures.append("无法读取 dataset_summary.json。")
        return passes, warnings, failures

    total = int(summary.get("total_after_cleaning", 0) or 0)
    label_distribution = summary.get("label_distribution", {}) or {}
    human_count = int(label_distribution.get("human", 0) or 0)
    ai_count = int(label_distribution.get("ai", 0) or 0)

    if total >= 1000:
        passes.append(f"公开数据总样本数达标：{total}")
    else:
        warnings.append(f"严重警告：公开数据总样本数 {total} < 1000，不能报告正式模型性能。")
    if human_count >= 500:
        passes.append(f"human 样本数达标：{human_count}")
    else:
        warnings.append(f"严重警告：human 样本数 {human_count} < 500。")
    if ai_count >= 500:
        passes.append(f"ai 样本数达标：{ai_count}")
    else:
        warnings.append(f"严重警告：ai 样本数 {ai_count} < 500。")

    if summary.get("training_mode") == "formal_public":
        passes.append("dataset_summary.json 标记为 formal_public。")
    elif summary.get("training_mode") == "demo_mode":
        warnings.append("严重警告：当前仍处于 demo_mode，不能写作数据支撑完成。")
    else:
        warnings.append(f"严重警告：未知训练模式：{summary.get('training_mode')}")

    for key in ["overlap_train_val_groups", "overlap_train_test_groups", "overlap_val_test_groups"]:
        overlap = split_audit.get(key, [])
        if overlap:
            failures.append(f"group_id 跨 split：{key} 包含 {len(overlap)} 个交叉 group。")
        else:
            passes.append(f"group_id 无交叉：{key}")

    label_by_split = split_audit.get("label_distribution_by_split", {}) or {}
    for split_name in ["train", "val", "test"]:
        labels = label_by_split.get(split_name, {}) or {}
        if labels.get("human", 0) > 0 and labels.get("ai", 0) > 0:
            passes.append(f"{split_name} split 同时包含 human 和 ai。")
        else:
            warnings.append(f"严重警告：{split_name} split 未同时包含 human 和 ai。")
    return passes, warnings, failures


def check_metrics_source() -> Tuple[List[str], List[str], List[str]]:
    passes, warnings, failures = [], [], []
    metrics = read_json(PROJECT_ROOT / "reports" / "model_metrics.json")
    if not metrics:
        warnings.append("严重警告：model_metrics.json 不存在或不可读。")
        return passes, warnings, failures

    if metrics.get("training_data_file") == "data/processed/public_train.csv":
        passes.append("model_metrics.json 标记训练来源为 public_train.csv。")
    else:
        warnings.append("严重警告：model_metrics.json 未标记训练来源为 public_train.csv，需确认是否仍基于 demo_texts。")

    if metrics.get("final_evaluation_split") == "public_test":
        passes.append("model_metrics.json 标记最终评估集为 public_test。")
    else:
        warnings.append("严重警告：model_metrics.json 未标记 public_test 为最终评估集。")

    test_metrics = metrics.get("test_metrics", {}) or {}
    if test_metrics.get("evaluated_on") == "public_test" and int(test_metrics.get("test_sample_count", 0) or 0) >= 1:
        passes.append(f"public_test 指标存在，测试样本数：{test_metrics.get('test_sample_count')}")
    else:
        warnings.append("严重警告：缺少来自 public_test 的正式测试指标。")

    text = json.dumps(metrics, ensure_ascii=False)
    if "sample_seed" in text or "demo_texts" in text:
        warnings.append("严重警告：model_metrics.json 中出现 sample_seed/demo_texts，需确认没有把演示数据作为正式指标。")
    return passes, warnings, failures


def check_model_card_keywords() -> Tuple[List[str], List[str]]:
    passes, failures = [], []
    path = PROJECT_ROOT / "reports" / "model_card.md"
    if not path.exists():
        return passes, ["model_card.md 缺失。"]
    text = read_text(path)
    for keyword in ["仅供教师参考", "不作为纪律处分依据", "group-wise split", "HC3", "局限性"]:
        if keyword in text:
            passes.append(f"model_card.md 包含关键词：{keyword}")
        else:
            failures.append(f"model_card.md 缺少关键词：{keyword}")
    return passes, failures


def check_risk_threshold_config() -> Tuple[List[str], List[str]]:
    passes, failures = [], []
    path = PROJECT_ROOT / "config" / "risk_thresholds.json"
    data = read_json(path)
    if not data:
        return passes, ["config/risk_thresholds.json 缺失或不可读。"]
    expected = {
        "low_risk_max": 0.35,
        "medium_risk_max": 0.75,
        "high_risk_max": 0.90,
    }
    for key, value in expected.items():
        if abs(float(data.get(key, -1)) - value) < 1e-9:
            passes.append(f"风险阈值配置正确：{key}={value}")
        else:
            failures.append(f"风险阈值配置异常：{key} 应为 {value}，实际为 {data.get(key)}")
    return passes, failures


def check_risk_index_explanation() -> Tuple[List[str], List[str]]:
    passes, failures = [], []
    app_text = read_text(PROJECT_ROOT / "app.py") if (PROJECT_ROOT / "app.py").exists() else ""
    readme_text = read_text(PROJECT_ROOT / "README.md") if (PROJECT_ROOT / "README.md").exists() else ""
    combined = app_text + "\n" + readme_text
    if "AIGC 风险指数不是 AI 内容占比" in combined or "不代表文本中有多少比例由 AI 生成" in combined:
        passes.append("页面或 README 已说明 AIGC 风险指数不是 AI 内容占比。")
    else:
        failures.append("页面或 README 缺少 AIGC 风险指数不是 AI 内容占比的说明。")
    return passes, failures


def check_student_external_validation() -> Tuple[List[str], List[str], List[str]]:
    passes, warnings, failures = [], [], []
    path = PROJECT_ROOT / "data" / "processed" / "student_essay_external_validation.csv"
    if not path.exists():
        warnings.append("学生作文外部验证文件尚未生成。")
        return passes, warnings, failures
    try:
        df = pd.read_csv(path)
    except Exception as exc:
        failures.append(f"学生作文外部验证文件无法读取：{exc}")
        return passes, warnings, failures
    if df.empty:
        warnings.append("学生作文外部验证文件为空，请确认是否已下载或放置数据。")
        return passes, warnings, failures
    if set(df.get("label", [])) == {"human"}:
        passes.append("学生作文外部验证集 label 全为 human。")
    else:
        failures.append("学生作文外部验证集 label 不全为 human。")
    if set(df.get("split_usage", [])) == {"external_validation_only"}:
        passes.append("学生作文外部验证集 split_usage 全为 external_validation_only。")
    else:
        failures.append("学生作文外部验证集 split_usage 不全为 external_validation_only。")

    external_source = "Chinese-Essay-Dataset-For-Pre-Training"
    for split_name in ["public_train.csv", "public_val.csv", "public_test.csv"]:
        split_path = PROJECT_ROOT / "data" / "processed" / split_name
        if not split_path.exists():
            continue
        split_df = pd.read_csv(split_path, usecols=lambda c: c in {"source_dataset", "text"})
        if "source_dataset" in split_df.columns and external_source in set(split_df["source_dataset"].dropna().astype(str)):
            failures.append(f"{split_name} 中出现学生作文外部验证数据来源。")
        else:
            passes.append(f"{split_name} 未混入学生作文外部验证数据来源。")
    return passes, warnings, failures


def check_local_submission_schema() -> Tuple[List[str], List[str], List[str]]:
    passes, warnings, failures = [], [], []
    path = PROJECT_ROOT / "data" / "local" / "submissions.csv"
    if not path.exists():
        warnings.append("data/local/submissions.csv 尚不存在，班级看板将显示空状态。")
        return passes, warnings, failures
    try:
        df = pd.read_csv(path)
    except Exception as exc:
        failures.append(f"data/local/submissions.csv 无法读取：{exc}")
        return passes, warnings, failures

    required = {
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
    }
    missing = sorted(required - set(df.columns))
    if missing:
        failures.append(f"submissions.csv schema 缺少字段：{missing}")
    else:
        passes.append("submissions.csv schema 已包含班级看板所需字段。")

    if "text" in df.columns:
        warnings.append("submissions.csv 存在完整原文字段 text，看板记录不应保存完整学生原文。")
    else:
        passes.append("submissions.csv 未保存完整原文字段 text。")

    if {"demo_flag", "source_note"}.issubset(df.columns):
        demo_rows = df[df["demo_flag"].astype(str).str.lower().isin(["true", "1", "yes"])]
        if not demo_rows.empty and demo_rows["source_note"].fillna("").astype(str).str.strip().eq("").any():
            failures.append("demo_flag=true 的记录存在 source_note 为空。")
        else:
            passes.append("演示记录均包含 source_note 来源说明。")
    return passes, warnings, failures


def check_ocr_and_batch_support() -> Tuple[List[str], List[str], List[str]]:
    passes, warnings, failures = [], [], []
    private_path = PROJECT_ROOT / "data" / "local" / "private_ocr_texts.csv"
    if private_path.exists():
        warnings.append("data/local/private_ocr_texts.csv 存在，该文件为本地私有 OCR 全文文件，不得进入提交包。")
    else:
        passes.append("未发现 private_ocr_texts.csv。")

    package_text = read_text(PROJECT_ROOT / "scripts" / "make_final_submission_package.py")
    for keyword in ["private_ocr_texts.csv", "uploaded_images", "ocr_cache", "ocr_test_images"]:
        if keyword in package_text:
            passes.append(f"最终提交包脚本包含 OCR 隐私排除规则：{keyword}")
        else:
            failures.append(f"最终提交包脚本缺少 OCR 隐私排除规则：{keyword}")

    app_text = read_text(PROJECT_ROOT / "app.py") if (PROJECT_ROOT / "app.py").exists() else ""
    docs_text = ""
    for path in (PROJECT_ROOT / "docs").glob("*.md"):
        docs_text += "\n" + read_text(path)
    combined = app_text + "\n" + docs_text

    required_phrases = [
        "OCR 识别可能存在漏字、错字或段落顺序错误",
        "请在上传前遮挡学生姓名",
        "不默认保存原图",
        "图片作业识别",
        "批量作业导入",
    ]
    for phrase in required_phrases:
        if phrase in combined:
            passes.append(f"OCR/批量导入说明已包含：{phrase}")
        else:
            failures.append(f"OCR/批量导入说明缺少：{phrase}")
    return passes, warnings, failures


def build_report(passes: List[str], warnings: List[str], failures: List[str]) -> str:
    def block(items: List[str]) -> str:
        return "\n".join([f"- {item}" for item in items]) if items else "- 无"

    return (
        "# 项目审计报告\n\n"
        "## 通过项\n"
        f"{block(passes)}\n\n"
        "## 警告项\n"
        f"{block(warnings)}\n\n"
        "## 失败项\n"
        f"{block(failures)}\n\n"
        "## 下一步建议\n"
        "- 若使用公开数据失败，应明确标注 demo_mode，不能报告正式模型性能。\n"
        "- 演示前建议补充 2-3 张系统截图和一份真实教师试用反馈。\n"
        "- 不上传学生真实姓名、班级、学校和其他可识别信息，文本样例保持匿名化。\n"
    )


def main() -> int:
    print("第7步：开始执行项目审计。")
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    passes: List[str] = []
    warnings: List[str] = []
    failures: List[str] = []

    file_passes, file_failures = check_required_files()
    passes.extend(file_passes)
    failures.extend(file_failures)

    model_passes, model_warnings = check_model_outputs()
    passes.extend(model_passes)
    warnings.extend(model_warnings)

    wording_warnings, wording_failures = check_wording_risk()
    warnings.extend(wording_warnings)
    failures.extend(wording_failures)

    compliance_passes, compliance_failures = check_compliance_phrases()
    passes.extend(compliance_passes)
    failures.extend(compliance_failures)

    length_passes, length_failures = check_report_length()
    passes.extend(length_passes)
    failures.extend(length_failures)

    data_passes, data_warnings, data_failures = check_public_data_files()
    passes.extend(data_passes)
    warnings.extend(data_warnings)
    failures.extend(data_failures)

    scale_passes, scale_warnings, scale_failures = check_dataset_scale_and_split()
    passes.extend(scale_passes)
    warnings.extend(scale_warnings)
    failures.extend(scale_failures)

    metrics_passes, metrics_warnings, metrics_failures = check_metrics_source()
    passes.extend(metrics_passes)
    warnings.extend(metrics_warnings)
    failures.extend(metrics_failures)

    card_passes, card_failures = check_model_card_keywords()
    passes.extend(card_passes)
    failures.extend(card_failures)

    threshold_passes, threshold_failures = check_risk_threshold_config()
    passes.extend(threshold_passes)
    failures.extend(threshold_failures)

    index_passes, index_failures = check_risk_index_explanation()
    passes.extend(index_passes)
    failures.extend(index_failures)

    external_passes, external_warnings, external_failures = check_student_external_validation()
    passes.extend(external_passes)
    warnings.extend(external_warnings)
    failures.extend(external_failures)

    submission_passes, submission_warnings, submission_failures = check_local_submission_schema()
    passes.extend(submission_passes)
    warnings.extend(submission_warnings)
    failures.extend(submission_failures)

    ocr_passes, ocr_warnings, ocr_failures = check_ocr_and_batch_support()
    passes.extend(ocr_passes)
    warnings.extend(ocr_warnings)
    failures.extend(ocr_failures)

    report = build_report(passes, warnings, failures)
    AUDIT_PATH.write_text(report, encoding="utf-8")

    print(f"审计完成：通过 {len(passes)} 项，警告 {len(warnings)} 项，失败 {len(failures)} 项。")
    print(f"审计报告：{AUDIT_PATH}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
