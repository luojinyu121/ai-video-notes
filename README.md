# AI Video Notes

这是一个专为 AI 编程核心环境设计的自动化 Agent Skill 工作流组合。它能够提取指定视频的完整字幕，然后通过自定义 AI 对内容进行分析与提炼，生成结构化的 Markdown 笔记及可以直接预览的 HTML 页面。

## 🌟 核心功能
* **全集字幕抓取**：基于 Python 自动化脚本，抓取输入视频的完全脱敏字幕。
* **🔊 音频降级方案（v1.0.2 新增）**：无字幕视频自动下载音频 → faster-whisper 语音转文字 → 继续正常笔记生成流程。
* **📺 分集视频支持（v1.0.2 新增）**：完整支持 `?p=N` 参数，精确定位多集视频（合集/videopod）的指定集数。
* **自定义风格映射**：可生成学术、生活感悟、极简提纲、小红书风、会议纪要等不同流派的笔记。
* **排版引擎**：产出带时间戳链接、段落大纲、AI摘要的 .md 与 .html 同步报告。
* **原生无缝交互**：它通过向用户征求偏好然后再启动提取分析，全自动运作。

## 🔄 执行流程
本 Skill 受工作区/全局的 AI 调度控制，运行时主要遵循如下流程：
1. **触发唤醒**：在 AI 面板通过 /skill ai-video-notes + 视频 URL 唤起工具。
2. **偏好采集**：AI 首先主动用对话框（Checkbox 选择形式）收集您的排版需求与笔记风格。
3. **加载配置文件**：读取 config/settings.json 以明晰要求，明确排版。
4. **启动提取器**：通过 `python scripts/01_extract_transcript.py "{完整视频URL}"` 获取字幕。
   - ✅ 有字幕 → 直接提取
   - ❌ 无字幕 → 自动下载音频 → faster-whisper 转录 → 生成标准 JSON
5. **智能归纳提纯**：大模型依据 JSON 完整上下文语料（严禁部分截断读取），提取深层核心逻辑、重点纪要并根据前期下达的格式整理。
6. **产出交付**：在 note_results/ 呈现 HTML / Markdown 内容。

## 🛠️ 安装与部署指南

### 前置环境需求
- **Python 3.10+**
- 基本依赖：`pip install -r requirements.txt`
- 音频降级方案额外依赖：
  - `faster-whisper`（语音转文字，首次运行自动下载 small 模型 ~500MB）
  - `ffmpeg`（可选，av 库自带解码器，Windows 上通常不需要）
  - `yt-dlp`（音频下载，独立安装）

### 使用步骤
1. 将本项目复制或克隆到您的 `.github/skills/ai-video-notes/` 目录。
2. 将 `config/settings.json.template` 复制为 `config/settings.json`，并填入您个人的 B 站 Cookie。
3. 重新加载 AI，在聊天输入 `/skill ai-video-notes` + 视频 URL 即可开始。

> ⚠️ **安全提示**：`config/settings.json`（含 B站 Cookie）已在 `.gitignore` 中排除，不会被推送到 GitHub。请勿在公开场合分享此文件。

## 📋 版本历史

### v1.0.2 (2026-06-03)
- 🔊 **音频降级方案**：`scripts/01b_audio_fallback.py` — 无字幕视频自动用 yt-dlp 下载音频 → faster-whisper 语音转文字 → 输出标准 `_transcript_full.json`
- 📺 **分集视频支持**：完整支持 `?p=N` 参数，精确定位多集视频的指定集数
- 🐛 **异常处理修复**：`downloaders/bilibili_downloader.py` 所有裸 `except` 改为打印具体异常信息
- 📝 **SKILL.md 更新**：完整 URL 流程 + 音频降级文档
- 🔒 **安全增强**：`.gitignore` 排除 `config/settings.json`、`output/`、`note_results/`、cookie 临时文件

### v1.0.1 (2026-05-22)
- 🎬 B站字幕 API 提取
- 🎨 8 种笔记风格 + 4 种输出格式
- 📄 Markdown + HTML 双输出
- 🎯 自定义风格映射系统

## 🔒 隐私与安全
- `config/settings.json`（含 B站 Cookie）**不会被推送到 GitHub**（已在 `.gitignore` 中）
- Cookie 临时文件（`.cookies_*.txt`）**不会被跟踪**
- 音频缓存（`output/*.m4a`）**不会被提交**
- 生成的笔记（`note_results/`）仅在本地保存
