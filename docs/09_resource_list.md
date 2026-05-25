# 配套资源清单

## 一、最终提交材料

- 案例信息表 Word/PDF。
- 开发与应用报告 Word。
- 演示视频 MP4。
- 配套资源 ZIP。
- 系统源码。
- 模型文件 `aigc_tfidf_lr.joblib`。
- 教师使用手册。
- 安装部署说明。
- 数据与模型说明。
- 隐私合规与使用边界说明。
- 系统截图。
- 教师真实试用反馈表或空白模板。
- 审计报告和最终提交检查报告。

## 二、系统代码资源

最终提交包中的 `system_code/` 建议包含：

- `app.py`
- `requirements.txt`
- `requirements_ocr.txt`
- `README.md`
- `.env.example`
- `src/`
- `scripts/`
- `config/`
- `assets/`
- `models/aigc_tfidf_lr.joblib`

## 三、报告资源

建议包含：

- `reports/model_metrics.json`
- `reports/model_card.md`
- `reports/data_source_audit.md`
- `reports/split_audit.json`
- `reports/threshold_selection.json`
- `reports/risk_threshold_explanation.md`
- `reports/student_essay_external_validation_report.md`
- `reports/student_essay_external_validation_metrics.json`
- `reports/student_essay_external_validation_sample.csv`
- `reports/ocr_dependency_check.md`
- `reports/batch_upload_schema_check.md`
- `reports/audit_report.md`
- `reports/final_submission_check.md`

## 四、演示数据资源

- `data/sample_seed/demo_texts.csv`
- `data/sample_seed/demo_texts_enhanced.csv`
- `data/sample_seed/hc3_high_risk_demo_pool.csv`（如存在）
- `reports/dashboard_demo_seed_report.md`
- `reports/dashboard_demo_seed_records.csv`

演示记录仅用于系统展示，不代表真实学生数据。

## 五、OCR 与批量导入资源

系统新增图片作业识别与批量作业导入功能。教师可上传单张或多张作文图片，系统先进行 OCR 识别，教师确认或修正识别文本后，再进行 AIGC 风险提示，并将结果同步到班级分析看板。

OCR 功能代码和安装说明可以进入提交包，但以下内容不得进入提交包：

- `data/local/private_ocr_texts.csv`
- `data/local/uploaded_images/`
- `data/local/ocr_cache/`
- 任何原始学生图片
- 任何完整学生原文文件

## 六、不应包含的内容

- 真实 API Key。
- `data/raw/`。
- 完整 public_train/public_val/public_test。
- 完整学生作文外部验证 CSV 或预测 CSV。
- `pretrain_essays.tar.bz2`。
- `.venv/`。
- `__pycache__/`。
- Streamlit 日志。

本内容由 AI 辅助生成，仅供教师参考。
