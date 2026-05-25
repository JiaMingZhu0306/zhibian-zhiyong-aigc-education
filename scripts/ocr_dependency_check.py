"""检查 OCR 可选依赖状态。"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ocr_utils import get_available_ocr_provider


REPORT_PATH = PROJECT_ROOT / "reports" / "ocr_dependency_check.md"


def has_module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def main() -> int:
    checks = {
        "rapidocr_onnxruntime": has_module("rapidocr_onnxruntime"),
        "paddleocr": has_module("paddleocr"),
        "pytesseract": has_module("pytesseract"),
        "PIL": has_module("PIL"),
    }
    provider = get_available_ocr_provider()
    lines = [
        "# OCR 可选依赖检查报告",
        "",
        f"- 当前可用 OCR provider：{provider}",
        "",
        "## 依赖状态",
    ]
    lines.extend([f"- {name}：{'可用' if ok else '未安装'}" for name, ok in checks.items()])
    lines.extend(
        [
            "",
            "## 安装建议",
            "",
            "基础系统不依赖 OCR 包。若需要图片作业识别功能，可运行：",
            "",
            "```powershell",
            "pip install -r requirements_ocr.txt",
            "```",
            "",
            "如果 OCR 依赖安装失败，系统仍可使用文本输入和批量 CSV 修正分析功能。",
        ]
    )
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"OCR 依赖检查完成：provider={provider}")
    print(f"报告：{REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
