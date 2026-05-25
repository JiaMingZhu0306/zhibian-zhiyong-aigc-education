# 模型卡：AIGC 文本风险提示基线模型

## 模型用途
本模型用于中学生作文、读后感、学习总结等文本的教学风险提示，帮助教师发现疑似 AI 生成或 AI 润色特征，并开展 AI 素养教育。输出仅供教师参考，不作为纪律处分依据。

## 数据来源
- 数据源：Hello-SimpleAI/HC3-Chinese
- 清洗去重后总样本数：33925
- 标签分布：{'human': 17326, 'ai': 16599}
- train/val/test：23665 / 5144 / 5116
- public dataset：用于训练和评估模型。
- demo_texts.csv：仅用于页面演示，不参与正式模型评估。
- local submissions.csv：仅用于教师本地试用记录。
- teacher feedback：后续人工补充。

## 划分方式
数据采用 group-wise split，按同一 question 或原始行构造 group_id，避免同问题下的人类回答和 ChatGPT 回答跨训练集、验证集和测试集造成泄漏。验证集用于选择风险阈值，public_test 仅用于最终评估。

## 模型方法
- 特征：TF-IDF 字符 n-gram
- 参数：analyzer='char_wb'，ngram_range=(2, 5)，max_features=50000，min_df=2
- 分类器：LogisticRegression(max_iter=1000, class_weight='balanced', random_state=42)

## 阈值选择
- 低/中风险分界：0.5
- 高风险分界：0.75
- 选择说明：在 public_val.csv 上选择 ai 类 F1 最高的阈值；若并列，选择最接近原教学展示阈值 0.45 的值。test 集未参与阈值选择。

## 页面风险等级阈值
- 低风险：`0 <= ai_probability < 0.35`
- 中风险：`0.35 <= ai_probability < 0.75`
- 高风险：`0.75 <= ai_probability < 0.90`
- 高置信高风险：`ai_probability >= 0.90`

AIGC 风险指数不是 AI 内容占比，而是模型参考概率。以上页面阈值用于教学解释和分层引导，不是纪律判定线。

## 中文学生作文外部验证
除 HC3-Chinese 公开 Human-ChatGPT 对比语料外，系统还支持接入 7–12 年级中文学生作文数据作为 human-only 外部验证集，用于观察模型在真实学生作文风格上的误报风险。该外部验证集不参与训练，不作为纪律判定依据。

## public_test 指标
- test_sample_count：5116
- Accuracy：0.976
- Precision(ai)：0.981
- Recall(ai)：0.9697
- F1(ai)：0.9753
- per_class_support：{'human': 2608, 'ai': 2508}
- confusion_matrix：{'labels': ['human', 'ai'], 'matrix': [[2561, 47], [76, 2432]]}

## 局限性
- HC3 是人类回答 vs ChatGPT 回答，不完全等同于中学生作文。
- 模型只能做风险提示，不能作为纪律处分依据。
- 真实课堂应用需要结合学生草稿、访谈和 AI 使用声明。
- 系统使用公开 Human-ChatGPT 对比语料构建 AIGC 文本风险提示基线模型，并通过 group-wise split 避免同问题样本跨训练集和测试集造成泄漏。由于公开语料不完全等同于真实中学生作文，本模型仅作为教师教学辅助和风险提示工具，不作为学生违纪判定或处分依据。
