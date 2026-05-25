# QUICK_START

## 1. 创建环境

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

## 2. 启动系统

```powershell
streamlit run app.py
```

## 3. 可选 OCR

```powershell
pip install -r requirements_ocr.txt
python scripts/ocr_dependency_check.py
```

## 4. 可选模型复现

```powershell
python scripts/prepare_data.py
python scripts/train_baseline.py
python scripts/evaluate_model.py
```

本仓库不包含完整训练集和大尺寸模型文件。模型复现需要联网访问公开数据集，或手动将公开数据文件放入 `data/raw/`。
