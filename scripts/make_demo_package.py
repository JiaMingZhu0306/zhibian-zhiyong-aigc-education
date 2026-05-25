"""整理参赛演示交付目录，不默认压缩。"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DELIVERABLE_ROOT = PROJECT_ROOT / "deliverables" / "智辨智用_创AI案例配套资源"


def copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.exists():
        shutil.copy2(src, dst)


def copy_dir(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    if src.exists():
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache"))


def ensure_demo_report() -> None:
    sys.path.insert(0, str(PROJECT_ROOT))
    try:
        from src.report_generator import write_demo_class_report
        from src.storage import dashboard_stats, load_submissions

        df = load_submissions()
        stats = dashboard_stats(df)
        write_demo_class_report(stats, df)
    except Exception as exc:
        report_path = PROJECT_ROOT / "reports" / "demo_class_report.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            "# 班级 AIGC 作业规范使用分析报告\n\n"
            f"当前未能读取本地记录，已生成占位报告。原因：{exc}\n\n"
            "本报告仅供教师参考，不作为纪律处分依据，示例数据应保持匿名化。\n\n"
            "AI 辅助生成，仅供教师参考。",
            encoding="utf-8",
        )


def run_audit() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/run_audit.py"],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        raise RuntimeError("审计存在失败项，已停止整理交付目录。请先查看 reports/audit_report.md。")


def main() -> None:
    print("第8步：开始整理 deliverables 目录。")
    ensure_demo_report()
    run_audit()

    if DELIVERABLE_ROOT.exists():
        shutil.rmtree(DELIVERABLE_ROOT)
    DELIVERABLE_ROOT.mkdir(parents=True, exist_ok=True)

    system_code = DELIVERABLE_ROOT / "system_code"
    for file in ["app.py", "requirements.txt", "README.md", ".env.example"]:
        copy_file(PROJECT_ROOT / file, system_code / file)
    copy_dir(PROJECT_ROOT / "src", system_code / "src")
    copy_dir(PROJECT_ROOT / "scripts", system_code / "scripts")
    copy_dir(PROJECT_ROOT / "config", system_code / "config")
    copy_dir(PROJECT_ROOT / "assets", system_code / "assets")

    copy_dir(PROJECT_ROOT / "docs", DELIVERABLE_ROOT / "docs")
    copy_dir(PROJECT_ROOT / "screenshots", DELIVERABLE_ROOT / "screenshots")
    (DELIVERABLE_ROOT / "reports").mkdir(parents=True, exist_ok=True)
    for file in [
        "model_metrics.json",
        "confusion_matrix.csv",
        "model_card.md",
        "audit_report.md",
        "demo_class_report.md",
        "data_source_audit.md",
        "split_audit.json",
        "dataset_label_distribution.csv",
        "duplicate_audit.csv",
        "threshold_selection.json",
        "evaluation_report.md",
        "risk_threshold_explanation.md",
        "student_essay_external_validation_report.md",
        "student_essay_external_validation_metrics.json",
        "student_essay_external_validation_predictions.csv",
    ]:
        copy_file(PROJECT_ROOT / "reports" / file, DELIVERABLE_ROOT / "reports" / file)

    copy_file(PROJECT_ROOT / "data" / "sample_seed" / "demo_texts.csv", DELIVERABLE_ROOT / "sample_data" / "demo_texts.csv")

    print(f"交付目录已生成：{DELIVERABLE_ROOT}")
    print("未默认生成 zip。需要提交时，可手动压缩该目录。")


if __name__ == "__main__":
    main()
