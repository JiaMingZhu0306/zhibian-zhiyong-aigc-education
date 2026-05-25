# 数据集与模型说明

## 一、数据来源

正式训练数据来自 `Hello-SimpleAI/HC3-Chinese` Human-ChatGPT 对比语料。系统将 human_answers 拆分为 human 样本，将 chatgpt_answers 拆分为 ai 样本，并统一为 `text`、`label`、`source_dataset`、`source`、`source_row_id`、`origin_field`、`group_id` 等字段。

清洗去重后总样本数为 33,925，其中 human=17,326，ai=16,599。train/val/test 为 23,665 / 5,144 / 5,116。划分方式为 group-wise split，同一 group_id 不跨训练集、验证集和测试集。

## 二、模型方法

模型使用 TF-IDF + Logistic Regression：

- `TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), max_features=50000, min_df=2)`
- `LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42)`

该方法训练快、CPU 可运行、便于复现，适合 5 天冲刺版智能信息系统原型。

## 三、测试指标

public_test 指标：

- Accuracy=0.976
- Precision(ai)=0.981
- Recall(ai)=0.9697
- F1(ai)=0.9753
- test_sample_count=5116

该指标只代表模型在公开 Human-ChatGPT 对比语料上的基线表现，不代表真实课堂中学生作文场景的绝对判断能力。

## 四、风险指数与阈值

AIGC 风险指数表示模型认为文本具有 AI 生成或 AI 润色特征的参考概率，不代表文本中 AI 生成内容占比，不作为学生违纪判定或处分依据。

- 0–35%：低风险
- 35–75%：中风险
- 75–90%：高风险
- 90% 以上：高参考风险

阈值用于教学展示和风险分层，不是纪律判定线。

## 五、学生作文外部验证

系统支持接入 7–12 年级中文学生作文数据作为 human-only 外部验证集。当前保留有效样本 92,701，用于观察模型对真实学生作文风格的误报风险。该外部验证集只有 human 标签，不能评估 AI 文本召回率，也不能作为学生违纪判定依据。

## 六、图片 OCR 与批量导入

图片作业识别与批量作业导入不参与模型训练，也不改变当前模型和阈值。教师可上传单张或多张作文、读后感、学习总结等图片，系统先进行 OCR 文字识别，教师确认或修正识别文本后，再进入 AIGC 风险提示流程。

OCR 识别可能存在漏字、错字或段落顺序错误，分析前请教师确认和必要修正识别文本。系统不默认保存原图。看板同步记录写入 `data/local/submissions.csv`，只保存 `text_preview`、`text_hash`、作业类型、年级、风险等级、来源说明等字段，不保存完整学生原文。

## 七、数据类型边界

- public dataset：HC3-Chinese，用于训练和测试基线模型。
- external validation：学生作文 human-only 外部验证，用于误报观察。
- demo examples：匿名演示样例和公开语料演示池，用于页面展示。
- local submissions：本地匿名试用记录，用于班级分析看板。
- OCR batch records：图片识别或批量导入后的本地匿名分析记录，不用于训练。
- teacher feedback：后续人工补充的真实教师试用反馈。

## 八、局限性

HC3-Chinese 与真实中学生作文存在场景差异；不同生成模型、提示词和文体会影响文本特征；OCR 质量会影响图片作业分析结果；外部验证只有 human 标签，不能衡量 AI 文本召回率。因此，系统只能作为教师教学辅助和风险提示工具，真实课堂应用需要结合草稿、访谈、学生 AI 使用声明和教师过程性观察综合判断。

本内容由 AI 辅助生成，仅供教师参考。
