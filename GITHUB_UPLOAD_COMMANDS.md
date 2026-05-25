# GITHUB_UPLOAD_COMMANDS

以下命令仅供参考。脚本不会自动登录 GitHub，也不会自动推送。

```powershell
cd zhibian-zhiyong-aigc-education_open_source
git init
git branch -M main
git add .
git commit -m "Initial open-source release"
git remote add origin https://github.com/<your-org-or-name>/zhibian-zhiyong-aigc-education.git
git push -u origin main
```

如果后续要上传超过 GitHub 普通限制的大模型文件，请使用 Git LFS 或单独发布到模型托管平台，不建议直接提交到普通 Git 仓库。
