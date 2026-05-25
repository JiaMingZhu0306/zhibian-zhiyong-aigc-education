# OCR 可选依赖检查报告

- 当前可用 OCR provider：rapidocr

## 依赖状态
- rapidocr_onnxruntime：可用
- paddleocr：未安装
- pytesseract：可用
- PIL：可用

## 安装建议

基础系统不依赖 OCR 包。若需要图片作业识别功能，可运行：

```powershell
pip install -r requirements_ocr.txt
```

如果 OCR 依赖安装失败，系统仍可使用文本输入和批量 CSV 修正分析功能。
