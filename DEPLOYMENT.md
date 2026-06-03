# 部署指南

## 前提条件

1. Git 已安装
2. GitHub 账号

## 发布到 GitHub

```powershell
cd ai-video-notes

# 初始化 Git（如果还没有）
git init
git add -A
git commit -m "Initial commit"

# 添加远程仓库
git remote add origin https://github.com/YOUR_USERNAME/ai-video-notes.git
git push -u origin main
```

## 用户使用流程

```
1. git clone https://github.com/xxx/ai-video-notes
        ↓
2. 编辑 config/settings.json，填入自己的 B站 Cookie
   （bilibili_cookie 字段，占位符 "YOUR_BILIBILI_COOKIE_HERE"）
        ↓
3. pip install -r requirements.txt
        ↓
4. 安装 yt-dlp（音频降级方案需要）
        ↓
5. 放在 .github/skills/ai-video-notes/ 目录下
        ↓
6. 完成！输入 /skill ai-video-notes + 视频 URL
```

## Cookie 安全

- `config/settings.json` 仓库中的 Cookie 字段为占位符
- 用户克隆后需填入自己的 B站 Cookie
- ⚠️ **不要在推送的代码中包含你的真实 Cookie**
- 如不小心泄露，立即去 B站更换 Cookie
