"""生成轻量最终提交目录和可选 zip。"""
from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DELIVERABLE_ROOT = PROJECT_ROOT / "deliverables_final"
FINAL_ROOT = DELIVERABLE_ROOT / "zhibian_zhiyong_submission"
FINAL_ZIP = DELIVERABLE_ROOT / "zhibian_zhiyong_submission.zip"

STUDENT_PREDICTIONS = PROJECT_ROOT / "reports" / "student_essay_external_validation_predictions.csv"
STUDENT_SAMPLE = PROJECT_ROOT / "reports" / "student_essay_external_validation_sample.csv"

DOC_FILES = [
    "01_development_report_final.md",
    "02_case_info_form_final.md",
    "03_demo_video_script.md",
    "04_teacher_manual.md",
    "05_installation_guide.md",
    "06_dataset_model_description.md",
    "07_privacy_boundary.md",
    "08_teacher_feedback_form.md",
    "09_resource_list.md",
    "10_ppt_outline.md",
    "11_screenshot_checklist.md",
    "12_teacher_trial_record_template.md",
    "13_final_submission_checklist.md",
    "14_ui_style_notes.md",
]

REPORT_FILES = [
    "model_metrics.json",
    "model_card.md",
    "data_source_audit.md",
    "split_audit.json",
    "threshold_selection.json",
    "risk_threshold_explanation.md",
    "student_essay_external_validation_report.md",
    "student_essay_external_validation_metrics.json",
    "student_essay_external_validation_sample.csv",
    "audit_report.md",
    "confusion_matrix.csv",
    "dataset_label_distribution.csv",
    "evaluation_report.md",
    "demo_examples_risk_check.md",
    "demo_examples_risk_check.csv",
    "dashboard_demo_seed_report.md",
    "dashboard_demo_seed_records.csv",
    "ocr_dependency_check.md",
    "batch_upload_schema_check.md",
    "ui_readability_check.md",
]

DIR_IGNORE = shutil.ignore_patterns(
    "__pycache__",
    "*.pyc",
    ".pytest_cache",
    ".venv",
    "streamlit_server.log",
    "streamlit_server.err.log",
    "private_ocr_texts.csv",
    "uploaded_images",
    "ocr_cache",
    "ocr_test_images",
)


def copy_file(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def copy_dir(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=DIR_IGNORE)


def make_student_sample() -> None:
    """抽取外部验证小样本，只保留去文本字段，降低隐私风险。"""
    if not STUDENT_PREDICTIONS.exists():
        print("未找到学生作文外部验证预测明细，跳过小样本生成。")
        return

    df = pd.read_csv(STUDENT_PREDICTIONS)
    if df.empty:
        print("学生作文外部验证预测明细为空，跳过小样本生成。")
        return

    samples = []
    for level, limit in [("低风险", 10), ("中风险", 10), ("高风险", 8)]:
        samples.append(df[df["risk_level"] == level].head(limit))
    sample = pd.concat(samples, ignore_index=True) if samples else pd.DataFrame()

    keep_cols = ["essay_id", "grade", "category", "risk_level", "aigc_risk_index"]
    keep_cols = [col for col in keep_cols if col in sample.columns]
    sample = sample[keep_cols]
    STUDENT_SAMPLE.parent.mkdir(parents=True, exist_ok=True)
    sample.to_csv(STUDENT_SAMPLE, index=False, encoding="utf-8-sig")
    print(f"已生成学生作文外部验证小样本：{STUDENT_SAMPLE}，共 {len(sample)} 条。")


def copy_docs() -> None:
    for name in DOC_FILES:
        copy_file(PROJECT_ROOT / "docs" / name, FINAL_ROOT / "docs" / name)


def copy_reports() -> None:
    for name in REPORT_FILES:
        copy_file(PROJECT_ROOT / "reports" / name, FINAL_ROOT / "reports" / name)


def write_submission_readme() -> None:
    content = """# 智辨·智用最终提交包说明

本目录为轻量最终提交包，文件名统一使用英文或拼音，正文材料为中文。

## 快速运行

```powershell
cd system_code
pip install -r requirements.txt
streamlit run app.py
```

OCR 图片作业识别为可选功能，如需启用可运行：

```powershell
pip install -r requirements_ocr.txt
```

`system_code/models/aigc_tfidf_lr.joblib` 已包含正式基线模型，可用于离线演示。

## 数据说明

提交包不包含完整公开训练数据、原始学生作文数据或完整学生作文预测明细。`sample_data/demo_texts.csv` 与 `sample_data/demo_texts_enhanced.csv` 仅用于页面演示，`reports/student_essay_external_validation_sample.csv` 只保留少量去文本字段，用于说明外部验证样本的风险等级分布。

## 使用边界

AIGC 风险指数不是 AI 内容占比，不作为纪律处分依据。系统输出仅供教师参考，需结合草稿、访谈和 AI 使用声明综合判断。
"""
    (FINAL_ROOT / "README_submission.md").write_text(content, encoding="utf-8")


def zip_final_dir() -> None:
    if FINAL_ZIP.exists():
        FINAL_ZIP.unlink()
    with zipfile.ZipFile(FINAL_ZIP, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in FINAL_ROOT.rglob("*"):
            if path.is_file():
                archive.write(path, path.relative_to(FINAL_ROOT.parent))


def build_package() -> None:
    make_student_sample()
    if FINAL_ROOT.exists():
        shutil.rmtree(FINAL_ROOT)
    FINAL_ROOT.mkdir(parents=True, exist_ok=True)

    system_code = FINAL_ROOT / "system_code"
    for file_name in ["app.py", "requirements.txt", "requirements_ocr.txt", "README.md", ".env.example"]:
        copy_file(PROJECT_ROOT / file_name, system_code / file_name)
    copy_dir(PROJECT_ROOT / "src", system_code / "src")
    copy_dir(PROJECT_ROOT / "scripts", system_code / "scripts")
    copy_dir(PROJECT_ROOT / "config", system_code / "config")
    copy_dir(PROJECT_ROOT / "assets", system_code / "assets")
    copy_file(
        PROJECT_ROOT / "models" / "aigc_tfidf_lr.joblib",
        system_code / "models" / "aigc_tfidf_lr.joblib",
    )

    copy_docs()
    copy_reports()
    copy_file(
        PROJECT_ROOT / "data" / "sample_seed" / "demo_texts.csv",
        FINAL_ROOT / "sample_data" / "demo_texts.csv",
    )
    for sample_name in ["demo_texts.csv", "demo_texts_enhanced.csv", "hc3_high_risk_demo_pool.csv"]:
        copy_file(
            PROJECT_ROOT / "data" / "sample_seed" / sample_name,
            system_code / "data" / "sample_seed" / sample_name,
        )
        copy_file(
            PROJECT_ROOT / "data" / "sample_seed" / sample_name,
            FINAL_ROOT / "sample_data" / sample_name,
        )
    copy_dir(PROJECT_ROOT / "screenshots", FINAL_ROOT / "screenshots")
    write_submission_readme()
    zip_final_dir()


def main() -> int:
    print("开始生成轻量最终提交包。")
    build_package()
    print(f"最终提交目录：{FINAL_ROOT}")
    print(f"最终提交 zip：{FINAL_ZIP}")
    print("已排除 data/raw、完整 public 数据、完整学生作文验证数据和运行缓存。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
