# 安装部署说明

## 一、基础环境

建议使用 Python 3.10 或 3.11。当前项目在 Windows 环境下开发，项目目录为：

```powershell
zhibian-zhiyong-aigc-education
```

## 二、使用 conda 启动

```powershell
cd zhibian-zhiyong-aigc-education
conda activate aigc_edu
pip install -r requirements.txt
python scripts/seed_dashboard_demo_records.py --n 100 --replace-demo
python scripts/run_audit.py
python scripts/final_submission_check.py
python scripts/ui_readability_check.py
streamlit run app.py
```

启动后访问：`http://127.0.0.1:8501`

如果端口 8501 被占用，可使用：

```powershell
streamlit run app.py --server.port 8502
```

## 三、使用 venv 启动

```powershell
cd zhibian-zhiyong-aigc-education
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## 四、可选 OCR 功能安装

基础功能不依赖 OCR 包。如果需要启用图片作业识别和批量图片导入，请额外安装：

```powershell
pip install -r requirements_ocr.txt
python scripts/ocr_dependency_check.py
```

`requirements_ocr.txt` 默认包含 rapidocr_onnxruntime、opencv-python-headless 和 pillow。若 OCR 依赖安装失败，系统仍可使用文本输入、演示样例、批量 CSV 修正分析和班级分析看板功能。

OCR 识别可能存在漏字、错字或段落顺序错误，分析前请教师确认和必要修正识别文本。请在上传前遮挡学生姓名、班级、学号等可识别信息。

当前本地演示环境已成功安装 OCR 可选依赖，依赖检查可识别到 rapidocr provider。若在其他电脑部署，仍需单独运行 `pip install -r requirements_ocr.txt`。

## 五、可选大模型配置

系统支持 OpenAI-compatible 国产大模型接口。请在本地 `.env` 中配置：

```env
OPENAI_API_KEY=请在本地填写你的API密钥
OPENAI_BASE_URL=https://your-openai-compatible-endpoint/v1
OPENAI_MODEL=your-model-name
```

不要把真实 API Key 写入代码、文档、报告或提交包。未配置 API 时，系统会使用本地模板生成演示反馈。

## 六、常用命令

```powershell
python scripts/prepare_data.py
python scripts/train_baseline.py
python scripts/evaluate_model.py
python scripts/seed_dashboard_demo_records.py --n 100 --replace-demo
python scripts/ocr_dependency_check.py
python scripts/batch_upload_schema_check.py
python scripts/run_audit.py
python scripts/make_final_submission_package.py
python scripts/final_submission_check.py
python scripts/ui_readability_check.py
streamlit run app.py
```

本内容由 AI 辅助生成，仅供教师参考。
