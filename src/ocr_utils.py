"""可选 OCR 工具。

OCR 依赖不作为基础运行依赖；未安装时返回清晰状态，避免影响文本分析主流程。
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any, Dict


IMAGE_SUFFIX = ".png"


def get_available_ocr_provider() -> str:
    """返回当前可用 OCR provider。"""
    try:
        import rapidocr_onnxruntime  # noqa: F401

        return "rapidocr"
    except Exception:
        pass
    try:
        import paddleocr  # noqa: F401

        return "paddleocr"
    except Exception:
        pass
    try:
        import pytesseract  # noqa: F401
        from PIL import Image  # noqa: F401

        return "pytesseract"
    except Exception:
        pass
    return "none"


def _bytes_to_temp_path(image_bytes: bytes, suffix: str = IMAGE_SUFFIX) -> Path:
    handle = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    handle.write(image_bytes)
    handle.close()
    return Path(handle.name)


def _normalize_result(success: bool, text: str = "", confidence: float | None = None, provider: str = "none", error: str = "") -> Dict[str, Any]:
    return {
        "success": success,
        "text": text.strip(),
        "mean_confidence": confidence,
        "provider": provider,
        "error": error,
    }


def _ocr_with_rapidocr(image_bytes: bytes, suffix: str) -> Dict[str, Any]:
    from rapidocr_onnxruntime import RapidOCR

    path = _bytes_to_temp_path(image_bytes, suffix)
    try:
        ocr = RapidOCR()
        result, _ = ocr(str(path))
        lines: list[str] = []
        scores: list[float] = []
        for item in result or []:
            if len(item) >= 3:
                lines.append(str(item[1]))
                try:
                    scores.append(float(item[2]))
                except Exception:
                    pass
        confidence = sum(scores) / len(scores) if scores else None
        return _normalize_result(True, "\n".join(lines), confidence, "rapidocr")
    finally:
        path.unlink(missing_ok=True)


def _ocr_with_paddleocr(image_bytes: bytes, suffix: str) -> Dict[str, Any]:
    from paddleocr import PaddleOCR

    path = _bytes_to_temp_path(image_bytes, suffix)
    try:
        ocr = PaddleOCR(use_angle_cls=True, lang="ch", show_log=False)
        result = ocr.ocr(str(path), cls=True)
        lines: list[str] = []
        scores: list[float] = []
        for page in result or []:
            for item in page or []:
                if len(item) >= 2 and len(item[1]) >= 2:
                    lines.append(str(item[1][0]))
                    try:
                        scores.append(float(item[1][1]))
                    except Exception:
                        pass
        confidence = sum(scores) / len(scores) if scores else None
        return _normalize_result(True, "\n".join(lines), confidence, "paddleocr")
    finally:
        path.unlink(missing_ok=True)


def _ocr_with_pytesseract(image_bytes: bytes) -> Dict[str, Any]:
    import io

    import pytesseract
    from PIL import Image

    image = Image.open(io.BytesIO(image_bytes))
    text = pytesseract.image_to_string(image, lang="chi_sim+eng")
    confidence = None
    try:
        data = pytesseract.image_to_data(image, lang="chi_sim+eng", output_type=pytesseract.Output.DICT)
        scores = [float(x) / 100 for x in data.get("conf", []) if str(x).strip() not in {"", "-1"}]
        confidence = sum(scores) / len(scores) if scores else None
    except Exception:
        pass
    return _normalize_result(True, text, confidence, "pytesseract")


def ocr_image(image_path_or_bytes: str | Path | bytes, file_suffix: str = IMAGE_SUFFIX) -> Dict[str, Any]:
    """识别图片文字。失败时不抛异常，返回 success=false。"""
    try:
        if isinstance(image_path_or_bytes, (str, Path)):
            path = Path(image_path_or_bytes)
            image_bytes = path.read_bytes()
            suffix = path.suffix or file_suffix
        else:
            image_bytes = image_path_or_bytes
            suffix = file_suffix

        provider = get_available_ocr_provider()
        if provider == "rapidocr":
            return _ocr_with_rapidocr(image_bytes, suffix)
        if provider == "paddleocr":
            return _ocr_with_paddleocr(image_bytes, suffix)
        if provider == "pytesseract":
            return _ocr_with_pytesseract(image_bytes)
        return _normalize_result(
            False,
            provider="none",
            error="当前未安装 OCR 可选依赖。可运行 pip install -r requirements_ocr.txt 后重试。",
        )
    except Exception as exc:
        return _normalize_result(False, provider=get_available_ocr_provider(), error=str(exc))
