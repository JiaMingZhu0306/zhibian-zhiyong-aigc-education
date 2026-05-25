# 数据来源审计报告

## 当前状态

正式公开数据训练模式

## 数据加载过程
- Hello-SimpleAI/HC3-Chinese 通过 datasets 加载失败：Dataset scripts are no longer supported, but found HC3-Chinese.py
- Hello-SimpleAI/HC3-Chinese 通过 Hugging Face Hub all.jsonl 成功读取，展开 39641 条样本。

## 样本统计
- 清洗去重后总样本数：33925
- human 样本数：17326
- ai 样本数：16599
- train/val/test：23665 / 5144 / 5116
- group-wise split：True

## 门槛检查
- 已满足正式训练门槛

## 使用边界
系统使用公开 Human-ChatGPT 对比语料构建 AIGC 文本风险提示基线模型，并通过 group-wise split 避免同问题样本跨训练集和测试集造成泄漏。由于公开语料不完全等同于真实中学生作文，本模型仅作为教师教学辅助和风险提示工具，不作为学生违纪判定或处分依据。

