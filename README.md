# 智辨·智用：中学生 AIGC 作业规范使用与 AI 素养培养系统

> 项目署名：智辨·智用项目组

## 项目简介

本项目是一个面向中学生作文、读后感、学习总结、研究性学习报告等文本任务的 AIGC 作业规范使用与 AI 素养教育辅助系统。系统提供文本风险提示、图片作业 OCR 识别、批量作业导入、AI 使用声明管理、班级分析看板和 AI 素养教育资源生成等功能。

本系统是教学辅助工具，不是作弊判定工具；AIGC 风险指数表示模型认为文本具有 AI 生成或 AI 润色特征的参考概率，不代表文本中 AI 生成内容占比，不作为学生违纪判定或处分依据。教师应结合草稿、访谈、学生 AI 使用声明和课堂过程材料综合判断，并保留最终教育判断权。

## 功能模块

1. 首页总览：展示系统定位、流程和安全边界。
2. 作业文本分析：支持匿名文本输入并输出 AIGC 风险指数、风险等级、可解释原因和修改建议。
3. 文本输入：粘贴作文、读后感、学习总结、研究性学习报告等文本。
4. 单张图片 OCR：上传匿名作业图片，OCR 后由教师确认或修正文本再分析。
5. 批量图片导入：批量上传多张作业图片，支持 OCR 结果导出、人工修正 CSV 导入和批量分析。
6. 使用声明管理：生成学生 AI 使用声明模板和反思问题。
7. 班级分析看板：读取本地匿名摘要记录，展示风险分布、使用声明填写情况、作业类型分布和记录来源。
8. 素养教育资源：生成 AI 素养主题班会建议，内容标注“AI 辅助生成，仅供教师参考”。
9. 隐私与使用边界：说明匿名化、数据保存和教育使用边界。

## 快速启动

```powershell
cd zhibian-zhiyong-aigc-education
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

打开浏览器访问终端显示的本地地址，通常为：

```text
http://127.0.0.1:8501
```

## OCR 可选功能

基础文本分析不需要 OCR 依赖。若要使用图片作业识别和批量图片导入，可安装可选依赖：

```powershell
pip install -r requirements_ocr.txt
python scripts/ocr_dependency_check.py
```

如果 OCR 依赖未安装，系统仍可使用文本输入、演示样例、修正 CSV 导入和班级看板功能。

## 数据与模型

原型训练方案使用 `Hello-SimpleAI/HC3-Chinese` 公开 Human-ChatGPT 对比语料构建二分类基线模型，采用 TF-IDF + Logistic Regression。正式训练数据清洗后样本数为 33,925，其中 human=17,326，ai=16,599；train/val/test 为 23,665/5,144/5,116，并采用 group-wise split，避免同一问题样本跨训练集、验证集和测试集造成泄漏。

公开测试集指标用于模型原型验证：Accuracy=0.976，Precision(ai)=0.981，Recall(ai)=0.9697，F1(ai)=0.9753，test_sample_count=5116。HC3-Chinese 不完全等同于真实中学生作文，指标不能被解释为真实课堂场景下的绝对识别能力。

开源仓库默认不包含完整训练集、完整外部验证集或大尺寸模型文件。请参考 [MODEL_REPRODUCTION.md](MODEL_REPRODUCTION.md) 复现模型训练。

## 演示数据

仓库仅保留 `data/sample_seed/` 下的匿名演示样例和公开语料演示池。演示样例只用于展示系统流程，不代表真实学生数据。

## 大模型 API 配置

系统支持 OpenAI-compatible API，可接入兼容接口。请复制 `.env.example` 为 `.env` 并在本地填写：

```env
OPENAI_API_KEY=请在本地填写你的API密钥
OPENAI_BASE_URL=https://your-openai-compatible-endpoint/v1
OPENAI_MODEL=your-model-name
```

不要把 `.env`、真实 API Key 或任何密钥文件提交到 GitHub。

## 隐私与使用边界

- 不上传学生真实姓名、学校、班级、学号、联系方式等可识别信息。
- 不上传学生正脸照片；图片上传前应遮挡可识别信息。
- 班级分析看板只保存文本摘要、hash 和分析结果，不保存完整学生原文。
- 默认不保存原始图片；私有 OCR 全文文件不进入公开仓库。
- AI 生成内容必须标注，教师使用前应审核。
- 系统输出不是纪律、司法或人格评价结论。

## 复现流程

```powershell
python scripts/prepare_data.py
python scripts/train_baseline.py
python scripts/evaluate_model.py
python scripts/run_audit.py
streamlit run app.py
```

如无法访问公开数据集，脚本会进入演示模式或提示用户手动放置公开数据文件；请勿将少量 demo 数据作为正式模型效果结论。
