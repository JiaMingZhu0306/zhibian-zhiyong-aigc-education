# MODEL_REPRODUCTION

## 模型文件说明

本开源包未包含 `models/aigc_tfidf_lr.joblib`。源模型文件大小约 115,294,264 字节，超过开源普通仓库建议阈值，建议按下方流程复现训练或使用 Git LFS 单独管理。

## 数据准备

优先使用公开数据集：

```python
load_dataset("Hello-SimpleAI/HC3-Chinese")
```

如果该数据集不可用，脚本会尝试 `Hello-SimpleAI/HC3`；如仍不可用，可手动将公开 CSV/JSON/JSONL/Parquet 放入 `data/raw/`。

## 训练流程

```powershell
python scripts/prepare_data.py
python scripts/train_baseline.py
python scripts/evaluate_model.py
```

训练脚本使用 TF-IDF + Logistic Regression，固定 random_state=42。数据划分采用 group-wise split，避免同一问题的人类回答和 ChatGPT 回答跨训练集、验证集和测试集造成泄漏。

## 指标边界

公开测试集指标只用于模型原型验证。HC3-Chinese 是 Human-ChatGPT 对比语料，不完全等同于真实中学生作文；模型只能用于教学风险提示，不能作为纪律处分依据。
