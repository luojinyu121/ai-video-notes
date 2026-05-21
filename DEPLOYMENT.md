# 发布到 GitHub

## 前提条件

1. 已安装 Git
2. 已有 GitHub 账号

## 步骤

### 1. 在 GitHub 创建仓库

1. 访问 https://github.com/new
2. 填写仓库信息：
   - Repository name: `bili-note-generator`
   - Description: `B站视频AI笔记生成器 - Trae IDE Skill`
   - 选择 Public（公开）
   - 不勾选 "Add a README file"（我们已有）
3. 点击 "Create repository"

### 2. 初始化本地仓库

```powershell
cd bili-note-workflow

# 初始化 Git
git init

# 添加所有文件
git add .

# 提交
git commit -m "Initial commit: BiliNote Generator v1.0"

# 添加远程仓库（替换 YOUR_USERNAME 为你的 GitHub 用户名）
git remote add origin https://github.com/YOUR_USERNAME/bili-note-generator.git

# 推送
git push -u origin main
```

### 3. 发布版本

```powershell
# 创建标签
git tag -a v1.0 -m "First release"
git push origin v1.0
```

### 4. 配置 GitHub 页面（可选）

1. 在仓库 Settings → Pages
2. Source: Deploy from a branch
3. Branch: main / (root)
4. 保存

## 用户使用流程

```
1. GitHub 下载/克隆仓库
        ↓
2. 编辑 config/settings.json，填入自己的 B站 Cookie
        ↓
3. 把整个文件夹复制到 .trae/skills/bili-note-generator/
        ↓
4. 完成！开始使用
```

## 注意事项

### Cookie 安全
- 不要把真实的 `bilibili_cookie` 提交到 GitHub
- 已在 `.gitignore` 中排除 `settings.json`
- 用户需要自己填写 Cookie

### 目录结构
用户需要确保目录名称为 `bili-note-generator`：

```
.trae/skills/
    └── bili-note-generator/    ← 必须叫这个名字
        ├── SKILL.md
        ├── config/
        ├── scripts/
        └── ...
```

## 更新维护

```powershell
# 本地修改后
git add .
git commit -m "Update: xxx"
git push

# 创建新版本标签
git tag -a v1.1 -m "Version 1.1"
git push origin v1.1
```

## 建议

1. **保持 README 简洁清晰**
2. **定期更新 Cookie 配置说明**
3. **添加使用示例和截图**
4. **收集用户反馈持续优化**
