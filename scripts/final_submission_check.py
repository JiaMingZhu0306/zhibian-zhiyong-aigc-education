"""最终提交包审计脚本。

检查轻量提交目录中的文件名、模型文件、大数据排除、必备文档、API Key
和不当表述，输出 reports/final_submission_check.md。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Callable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SUB_ROOT = PROJECT_ROOT / "deliverables_final" / "zhibian_zhiyong_submission"
REPORTS_DIR = PROJECT_ROOT / "reports"
OUT_PATH = REPORTS_DIR / "final_submission_check.md"

DANGEROUS_TERMS = [
    "AIGC" + "率",
    "AI" + "占比",
    "判定" + "作弊",
    "确定由" + "AI" + "生成",
    "100%" + "准确",
    "准确检测学生" + "作弊",
]

API_KEY_PATTERNS = [
    r"sk-[A-Za-z0-9]{20,}",
    r"AIza[A-Za-z0-9\-_]{20,}",
    r"AKIA[A-Z0-9]{16}",
    r"glpat-[A-Za-z0-9\-_]{20}",
]

CHINESE_CHAR_RE = re.compile(r"[\u4e00-\u9fff]")
HASH_U_RE = re.compile(r"#U[0-9a-fA-F]{4,}")

REQUIRED_DOCS = [
    "docs/01_development_report_final.md",
    "docs/02_case_info_form_final.md",
    "docs/03_demo_video_script.md",
    "docs/04_teacher_manual.md",
    "docs/05_installation_guide.md",
    "docs/06_dataset_model_description.md",
    "docs/07_privacy_boundary.md",
    "docs/08_teacher_feedback_form.md",
    "docs/09_resource_list.md",
    "docs/10_ppt_outline.md",
    "docs/11_screenshot_checklist.md",
    "docs/12_teacher_trial_record_template.md",
    "docs/13_final_submission_checklist.md",
    "docs/14_ui_style_notes.md",
]

REQUIRED_ASSETS = [
    "system_code/assets/hero_aigc_education.svg",
    "system_code/assets/workflow_education.svg",
    "system_code/assets/teacher_dashboard.svg",
    "system_code/assets/privacy_guard.svg",
    "system_code/assets/ai_statement.svg",
]

FORBIDDEN_PATHS = [
    "data/raw",
    "data/processed/public_all.csv",
    "data/processed/public_train.csv",
    "data/processed/public_val.csv",
    "data/processed/public_test.csv",
    "data/processed/student_essay_external_validation.csv",
    "reports/student_essay_external_validation_predictions.csv",
    "data/raw/student_essays/pretrain_essays.tar.bz2",
    "data/local/private_ocr_texts.csv",
    "data/local/uploaded_images",
    "data/local/ocr_cache",
    "data/local/ocr_test_images",
    "private_ocr_texts.csv",
    "uploaded_images",
    "ocr_cache",
    "ocr_test_images",
]

ALLOWED_CONTEXT_PREFIXES = [
    "禁止出现",
    "不得出现",
    "不允许出现",
    "需改写",
    "必须改写",
    "替换",
    "已替换",
    "本系统不是",
    "不作为",
    "不是",
]


def rel(path: Path) -> str:
    return str(path.relative_to(SUB_ROOT)).replace("\\", "/")


def collect_text_files(root: Path) -> list[Path]:
    suffixes = {".md", ".py", ".json", ".txt", ".env", ".csv", ".cfg", ".yaml", ".yml"}
    return [p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in suffixes]


def is_problematic_context(text: str, start: int) -> bool:
    left = max(0, start - 40)
    context = text[left:start]
    return not any(prefix in context for prefix in ALLOWED_CONTEXT_PREFIXES)


def check_submission_dir() -> tuple[list[str], list[str]]:
    if SUB_ROOT.exists():
        return [f"提交目录存在：{SUB_ROOT}"], []
    return [], [f"提交目录不存在：{SUB_ROOT}"]


def check_filename_encoding() -> tuple[list[str], list[str]]:
    passes: list[str] = []
    failures: list[str] = []
    if not SUB_ROOT.exists():
        return passes, failures

    hash_hits: list[str] = []
    chinese_hits: list[str] = []
    for item in SUB_ROOT.rglob("*"):
        if HASH_U_RE.search(item.name):
            hash_hits.append(rel(item))
        if CHINESE_CHAR_RE.search(item.name):
            chinese_hits.append(rel(item))

    if hash_hits:
        failures.append(f"文件名包含 #U 编码异常：{hash_hits[:8]}")
    else:
        passes.append("文件名无 #U 编码异常。")

    if chinese_hits:
        failures.append(f"文件名包含中文字符：{chinese_hits[:8]}")
    else:
        passes.append("文件名无中文字符。")

    return passes, failures


def check_model_file() -> tuple[list[str], list[str]]:
    target = SUB_ROOT / "system_code" / "models" / "aigc_tfidf_lr.joblib"
    if target.exists() and target.stat().st_size > 0:
        size_mb = target.stat().st_size / (1024 * 1024)
        return [f"模型文件存在：system_code/models/aigc_tfidf_lr.joblib（{size_mb:.1f} MB）"], []
    return [], ["缺少模型文件：system_code/models/aigc_tfidf_lr.joblib"]


def check_forbidden_paths() -> tuple[list[str], list[str]]:
    passes: list[str] = []
    failures: list[str] = []
    if not SUB_ROOT.exists():
        return passes, failures

    for forbidden in FORBIDDEN_PATHS:
        target = SUB_ROOT / forbidden
        if target.exists():
            failures.append(f"提交包误包含禁止内容：{forbidden}")
            continue
        basename = Path(forbidden).name
        matches = [p for p in SUB_ROOT.rglob(basename) if p.is_file() and p.stat().st_size > 1_000_000]
        if matches:
            failures.append(f"提交包含同名大文件 {basename}：{[rel(p) for p in matches[:3]]}")
        else:
            passes.append(f"未误包含：{forbidden}")
    return passes, failures


def check_required_docs() -> tuple[list[str], list[str]]:
    passes: list[str] = []
    failures: list[str] = []
    for doc in REQUIRED_DOCS:
        path = SUB_ROOT / doc
        if path.exists() and path.stat().st_size > 0:
            passes.append(f"必备文档存在：{doc}")
        else:
            failures.append(f"必备文档缺失或为空：{doc}")
    return passes, failures


def check_required_assets() -> tuple[list[str], list[str]]:
    passes: list[str] = []
    failures: list[str] = []
    for asset in REQUIRED_ASSETS:
        path = SUB_ROOT / asset
        if path.exists() and path.stat().st_size > 0:
            passes.append(f"本地 SVG 资产存在：{asset}")
        else:
            failures.append(f"本地 SVG 资产缺失或为空：{asset}")
    return passes, failures


def check_api_keys() -> tuple[list[str], list[str]]:
    passes: list[str] = []
    failures: list[str] = []
    if not SUB_ROOT.exists():
        return passes, failures

    hits: list[str] = []
    for path in collect_text_files(SUB_ROOT):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if any(re.search(pattern, text) for pattern in API_KEY_PATTERNS):
            hits.append(rel(path))

    if hits:
        failures.append(f"扫描到疑似真实 API Key：{hits[:8]}")
    else:
        passes.append("未扫描到真实 API Key。")
    return passes, failures


def check_dangerous_wording() -> tuple[list[str], list[str]]:
    passes: list[str] = []
    failures: list[str] = []
    if not SUB_ROOT.exists():
        return passes, failures

    hits: list[tuple[str, str]] = []
    for path in collect_text_files(SUB_ROOT):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for term in DANGEROUS_TERMS:
            for match in re.finditer(re.escape(term), text):
                if is_problematic_context(text, match.start()):
                    hits.append((rel(path), term))

    unique_hits = []
    seen = set()
    for hit in hits:
        if hit not in seen:
            unique_hits.append(hit)
            seen.add(hit)

    if unique_hits:
        failures.append(f"扫描到危险表述：{unique_hits[:12]}")
    else:
        passes.append("未扫描到危险表述。")
    return passes, failures


def check_audit_report() -> tuple[list[str], list[str]]:
    audit = PROJECT_ROOT / "reports" / "audit_report.md"
    if not audit.exists():
        return [], ["reports/audit_report.md 不存在。"]

    text = audit.read_text(encoding="utf-8", errors="ignore")
    match = re.search(r"## 失败项\s*\n(.*?)(?:\n##|\Z)", text, re.S)
    if not match:
        return [], ["reports/audit_report.md 缺少失败项段落。"]

    body = match.group(1).strip()
    if body in {"- 无", ""}:
        return ["audit_report.md 失败项为 0。"], []
    return [], [f"audit_report.md 仍有失败项：{body[:500]}"]


def run_checks() -> tuple[list[str], list[str]]:
    passes: list[str] = []
    failures: list[str] = []
    checks: list[Callable[[], tuple[list[str], list[str]]]] = [
        check_submission_dir,
        check_filename_encoding,
        check_model_file,
        check_forbidden_paths,
        check_required_docs,
        check_required_assets,
        check_api_keys,
        check_dangerous_wording,
        check_audit_report,
    ]
    for check in checks:
        current_passes, current_failures = check()
        passes.extend(current_passes)
        failures.extend(current_failures)
    return passes, failures


def write_report(passes: list[str], failures: list[str]) -> None:
    lines = [
        "# 最终提交包审计报告",
        "",
        f"通过项：{len(passes)}",
        f"失败项：{len(failures)}",
        "",
        "## 通过项",
    ]
    lines.extend([f"- {item}" for item in passes] if passes else ["- 无"])
    lines.extend(["", "## 失败项"])
    lines.extend([f"- {item}" for item in failures] if failures else ["- 无"])
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    print("=== 最终提交包审计 ===")
    passes, failures = run_checks()
    write_report(passes, failures)
    print(f"通过项：{len(passes)}，失败项：{len(failures)}")
    print(f"报告已写入：{OUT_PATH}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
