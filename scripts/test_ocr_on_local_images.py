"""对 data/local/ocr_test_images 中的本地匿名图片执行 OCR 测试。

报告只保留 text_preview，不写入 OCR 全文，也不保存或复制原图。
"""

from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ocr_utils import get_available_ocr_provider, ocr_image  # noqa: E402


IMAGE_DIR = PROJECT_ROOT / "data" / "local" / "ocr_test_images"
REPORT_PATH = PROJECT_ROOT / "reports" / "ocr_local_image_test_report.md"
CSV_PATH = PROJECT_ROOT / "reports" / "ocr_local_image_test_results.csv"
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def preview_text(text: str, max_len: int = 120) -> str:
    normalized = " ".join(str(text or "").split())
    if len(normalized) <= max_len:
        return normalized
    return normalized[:max_len] + "..."


def image_files() -> list[Path]:
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    return sorted(
        path for path in IMAGE_DIR.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )


def main() -> int:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    provider = get_available_ocr_provider()
    files = image_files()
    rows: list[dict[str, object]] = []

    for path in files:
        result = ocr_image(path)
        text = result.get("text", "") or ""
        confidence = result.get("mean_confidence")
        text_length = len(text.strip())
        rows.append(
            {
                "file_name": path.name,
                "ocr_provider": result.get("provider", provider),
                "success": bool(result.get("success")),
                "mean_confidence": confidence,
                "text_length": text_length,
                "text_preview": preview_text(text),
                "need_manual_review": (not result.get("success")) or text_length < 80 or (
                    confidence is not None and float(confidence) < 0.60
                ),
                "error": result.get("error", ""),
            }
        )

    df = pd.DataFrame(
        rows,
        columns=[
            "file_name",
            "ocr_provider",
            "success",
            "mean_confidence",
            "text_length",
            "text_preview",
            "need_manual_review",
            "error",
        ],
    )
    df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")

    success_count = int(df["success"].sum()) if not df.empty else 0
    failure_count = int(len(df) - success_count)
    review_count = int(df["need_manual_review"].sum()) if not df.empty else 0

    lines = [
        "# 本地匿名图片 OCR 测试报告",
        "",
        f"- 图片目录：`{IMAGE_DIR}`",
        f"- 当前 OCR provider：{provider}",
        f"- 扫描图片数量：{len(files)}",
        f"- OCR 成功数量：{success_count}",
        f"- OCR 失败数量：{failure_count}",
        f"- 需人工复核数量：{review_count}",
        "",
        "## 隐私说明",
        "",
        "- 本脚本不保存原图，不复制原图，不把 OCR 全文写入报告。",
        "- 报告和 CSV 只保留文件名、识别状态、置信度、文本长度、text_preview 和错误信息。",
        "- 请确保测试图片已遮挡学生姓名、学校、班级、学号等可识别信息。",
        "- OCR 识别可能存在漏字、错字或段落顺序错误，进入 AIGC 风险分析前必须由教师确认或修正。",
        "",
    ]

    if not files:
        lines.extend(
            [
                "## 测试结果",
                "",
                "当前目录为空，尚未执行图片 OCR。请把 2–5 张匿名作文、读后感或学习总结图片放入 `data/local/ocr_test_images/` 后重新运行：",
                "",
                "```powershell",
                "python scripts/test_ocr_on_local_images.py",
                "```",
                "",
            ]
        )
    else:
        lines.extend(["## 测试结果", ""])
        for row in rows:
            confidence = row["mean_confidence"]
            confidence_text = "未提供" if confidence is None or pd.isna(confidence) else f"{float(confidence):.3f}"
            lines.extend(
                [
                    f"### {row['file_name']}",
                    "",
                    f"- OCR provider：{row['ocr_provider']}",
                    f"- success：{row['success']}",
                    f"- mean_confidence：{confidence_text}",
                    f"- text_length：{row['text_length']}",
                    f"- need_manual_review：{row['need_manual_review']}",
                    f"- text_preview：{row['text_preview'] or '无'}",
                    f"- error：{row['error'] or '无'}",
                    "",
                ]
            )

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"OCR 本地图片测试完成：图片 {len(files)}，成功 {success_count}，失败 {failure_count}")
    print(f"报告：{REPORT_PATH}")
    print(f"CSV：{CSV_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
