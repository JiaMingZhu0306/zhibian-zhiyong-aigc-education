# 最终提交前检查清单

AI 辅助生成，仅供教师参考。请在正式提交前逐项核对，不要把本清单视为自动合规保证。

## 一、系统代码

- [ ] `app.py`、`requirements.txt`、`requirements_ocr.txt`、`README.md`、`.env.example` 完整。
- [ ] `src/`、`scripts/`、`config/`、`assets/` 完整。
- [ ] `models/aigc_tfidf_lr.joblib` 存在且可加载。
- [ ] `config/risk_thresholds.json` 存在。
- [ ] 不含真实 API Key，`.env` 不进入最终提交包。
- [ ] 文件名无 `#U` 编码异常。
- [ ] 最终提交目录中的主要文件名使用英文或拼音。

## 二、功能检查

- [ ] 首页总览可打开，Hero 按钮可跳转到“作业文本分析”和“班级分析看板”。
- [ ] 顶部文字导航清晰可见，当前页面高亮正常。
- [ ] 作业类型、年级等下拉框文字清晰可见。
- [ ] 文本输入分析可输出 AIGC 风险指数、风险等级、可解释原因和修改建议。
- [ ] 分析完成后自动同步到班级分析看板。
- [ ] 单张图片识别入口可上传图片并预览。
- [ ] OCR 识别结果可由教师确认或修正后再分析。
- [ ] 批量作业导入可上传多张图片、导出 OCR 结果 CSV、上传修正 CSV。
- [ ] 批量分析结果可同步到班级分析看板。
- [ ] 使用声明管理页面可生成声明模板和反思问题。
- [ ] 素养教育资源页面可生成班会资源，内容标注“AI 辅助生成，仅供教师参考”。
- [ ] 隐私与使用边界页面完整展示红线清单。

## 三、数据与模型报告

- [ ] `reports/model_metrics.json` 来自 formal_public 测试集。
- [ ] `reports/model_card.md` 说明 HC3-Chinese 数据来源、group-wise split、指标和局限性。
- [ ] `reports/data_source_audit.md` 存在。
- [ ] `reports/split_audit.json` 显示 group_id 无跨 split。
- [ ] `reports/risk_threshold_explanation.md` 说明 AIGC 风险指数不是 AI 内容占比。
- [ ] `reports/student_essay_external_validation_report.md` 说明 human-only 外部验证用途。
- [ ] `reports/ocr_dependency_check.md` 已生成。
- [ ] `reports/batch_upload_schema_check.md` 已生成。
- [ ] `reports/audit_report.md` 失败项为 0。
- [ ] `reports/final_submission_check.md` 失败项为 0。

## 四、文档材料

- [ ] `docs/01_development_report_final.md` 已更新到最终版。
- [ ] `docs/02_case_info_form_final.md` 可复制到比赛案例信息表。
- [ ] `docs/03_demo_video_script.md` 包含图片作业识别和批量作业导入演示片段。
- [ ] `docs/04_teacher_manual.md` 包含 OCR、批量导入和看板同步说明。
- [ ] `docs/05_installation_guide.md` 包含基础依赖和可选 OCR 依赖安装方式。
- [ ] `docs/06_dataset_model_description.md` 清晰区分 public dataset、external validation、demo examples、local submissions 和 teacher feedback。
- [ ] `docs/07_privacy_boundary.md` 包含上传前匿名化、不默认保存原图、看板不保存完整原文。
- [ ] `docs/08_teacher_feedback_form.md` 为真实教师试用反馈空表，不伪造反馈。
- [ ] `docs/09_resource_list.md` 列出最终提交包资源。
- [ ] `docs/10_ppt_outline.md` 包含 8–10 页 PPT 大纲。
- [ ] `docs/11_screenshot_checklist.md` 包含 OCR、批量导入和看板同步截图项。
- [ ] `docs/12_teacher_trial_record_template.md` 为真实试用记录空白模板。
- [ ] `docs/14_ui_style_notes.md` 说明当前 UI 风格和录屏注意事项。

## 五、隐私与包体检查

- [ ] 最终提交包不包含 `data/raw/`。
- [ ] 最终提交包不包含完整 `public_train.csv`、`public_val.csv`、`public_test.csv`。
- [ ] 最终提交包不包含完整学生作文外部验证 CSV 或预测 CSV。
- [ ] 最终提交包不包含 `pretrain_essays.tar.bz2`。
- [ ] 最终提交包不包含 `data/local/private_ocr_texts.csv`。
- [ ] 最终提交包不包含 `data/local/uploaded_images/`。
- [ ] 最终提交包不包含 `data/local/ocr_cache/`。
- [ ] 最终提交包不包含任何原始学生图片。
- [ ] 最终提交包不包含完整学生原文文件。
- [ ] 最终提交包只保留匿名演示 CSV、模型指标、模型卡、审计报告和说明文档。

## 六、人工提交材料

- [ ] 案例信息表 Word/PDF 已填写。
- [ ] 开发与应用报告 Word 已排版。
- [ ] 演示视频 MP4 已录制。
- [ ] 配套资源 ZIP 已生成。
- [ ] 首页、文本分析、OCR、批量导入、看板、声明管理、班会资源、隐私边界截图已补齐。
- [ ] 教师真实试用反馈已收集，不使用虚构反馈。
- [ ] Word/PDF 格式转换已检查。
- [ ] 单位盖章、联系人信息和上传材料已确认。
