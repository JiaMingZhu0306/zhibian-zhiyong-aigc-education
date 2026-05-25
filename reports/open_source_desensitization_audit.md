# 开源前脱敏审计报告

- 生成时间：2026-05-25T11:23:37
- 源项目：本地开发项目（公开报告中不保留本机绝对路径）
- 开源目录：本地生成的干净开源目录
- 开源压缩包：project_aigc_open_source_release.zip
- 压缩包 SHA256：包内审计报告不写固定哈希；请以外部 `Get-FileHash` 结果为准。

## 复制概况
- 复制文件数：71
- 脱敏改写文件数：3
- 缺失可选文件数：0

## 模型文件处理
- 源模型大小：115,294,264 bytes
- 是否复制模型：否
- 处理说明：模型超过 90MB 时不进入普通 Git 仓库，改由 MODEL_REPRODUCTION.md 提供复现流程。

## 已跳过内容
- models/aigc_tfidf_lr.joblib：115,294,264 bytes，超过 90MB，未复制。

## 缺失或未找到的可选文件

## 脱敏改写文件
- GITHUB_UPLOAD_COMMANDS.md
- docs\05_installation_guide.md
- reports\student_essay_external_validation_report.md

## 警告项
- 开源包未包含模型文件，请按 MODEL_REPRODUCTION.md 复现训练。

## 失败项

## 结论
通过：未发现阻断开源发布的敏感内容。
