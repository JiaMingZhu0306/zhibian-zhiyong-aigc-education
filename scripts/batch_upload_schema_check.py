"""检查图片 OCR 与批量导入相关 schema 和提交包排除规则。"""

from __future__ import annotations

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.storage import load_submissions  # noqa: E402


REPORT_PATH = PROJECT_ROOT / "reports" / "batch_upload_schema_check.md"

REQUIRED_SUBMISSION_COLUMNS = {
    "record_id",
    "timestamp",
    "text_hash",
    "text_preview",
    "assignment_type",
    "grade",
    "has_ai_statement",
    "aigc_risk_index",
    "risk_level",
    "source_type",
    "source_note",
    "anonymous_student_id",
    "ocr_confidence",
    "ocr_status",
}


def main() -> int:
    passes: list[str] = []
    warnings: list[str] = []
    failures: list[str] = []

    submissions_path = PROJECT_ROOT / "data" / "local" / "submissions.csv"
    if submissions_path.exists():
        df = load_submissions()
        missing = sorted(REQUIRED_SUBMISSION_COLUMNS - set(df.columns))
        if missing:
            failures.append(f"submissions.csv 缺少字段：{missing}")
        else:
            passes.append("submissions.csv 支持 OCR/批量导入扩展字段。")
        if "text" in df.columns:
            failures.append("submissions.csv 不应包含完整 text 字段。")
        else:
            passes.append("submissions.csv 未保存完整原文字段。")
    else:
        warnings.append("data/local/submissions.csv 不存在，系统会在首次保存时创建。")

    private_path = PROJECT_ROOT / "data" / "local" / "private_ocr_texts.csv"
    if private_path.exists():
        warnings.append("private_ocr_texts.csv 存在：该文件为本地私有 OCR 全文文件，不得进入最终提交包。")
    else:
        passes.append("当前未发现 private_ocr_texts.csv。")

    package_script_path = PROJECT_ROOT / "scripts" / "make_final_submission_package.py"
    package_script = package_script_path.read_text(encoding="utf-8", errors="ignore")
    for keyword in ["private_ocr_texts.csv", "uploaded_images", "ocr_cache"]:
        if keyword in package_script:
            passes.append(f"最终提交包脚本包含排除规则：{keyword}")
        else:
            failures.append(f"最终提交包脚本缺少排除规则：{keyword}")

    app_text = (PROJECT_ROOT / "app.py").read_text(encoding="utf-8", errors="ignore")
    for keyword in ["batch_analysis_results.csv", "anonymous_student_id", "saved_to_dashboard"]:
        if keyword in app_text:
            passes.append(f"批量分析结果包含字段或下载逻辑：{keyword}")
        else:
            failures.append(f"批量分析结果缺少字段或下载逻辑：{keyword}")

    lines = [
        "# 批量图片导入 Schema 检查报告",
        "",
        f"- 通过项：{len(passes)}",
        f"- 警告项：{len(warnings)}",
        f"- 失败项：{len(failures)}",
        "",
        "## 通过项",
    ]
    lines.extend([f"- {item}" for item in passes] or ["- 无"])
    lines.extend(["", "## 警告项"])
    lines.extend([f"- {item}" for item in warnings] or ["- 无"])
    lines.extend(["", "## 失败项"])
    lines.extend([f"- {item}" for item in failures] or ["- 无"])

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"批量导入 schema 检查完成：通过 {len(passes)}，警告 {len(warnings)}，失败 {len(failures)}")
    print(f"报告：{REPORT_PATH}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
