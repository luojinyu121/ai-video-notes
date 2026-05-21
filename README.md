# AI Video Notes (Bilibili Video Note Generator)

这是一个专为 AI 编程核心环境设计的自动化 Agent Skill 工作流组合（以 Bilibili B站平台为基础）。它能够提取指定视频的完整字幕，然后通过自定义 AI 对内容进行分析与提炼，生成结构化的 Markdown 笔记及可以直接预览的 HTML 页面。

## 🌟 核心功能
* **全集字幕抓取**：基于 Python 自动化脚本，抓取输入视频的完全脱敏字幕。
* **自定义风格映射**：可生成学术、生活感悟、极简提纲、小红书风、会议纪要等不同流派的笔记。
* **排版引擎**：产出带时间戳链接、段落大纲、AI摘要的 .md 与 .html 同步报告。
* **原生无缝交互**：它通过向用户征求偏好然后再启动提取分析，全自动运作。

## 🔄 执行流程
本 Skill 受工作区/全局的 AI 调度控制，运行时主要遵循如下流程：
1. **触发唤醒**：在 AI 面板通过 /skill ai-video-notes + 视频 URL 唤起工具。
2. **偏好采集**：AI 首先主动用对话框（Checkbox 选择形式）收集您的排版需求与笔记风格。
3. **加载配置文件**：读取 config/settings.json 以明晰要求，明确排版。
4. **启动提取器**：通过 python scripts/01_extract_transcript.py {VideoID} 在 output 留下包含分段文本、时间轴的完整 JSON 副本。
5. **智能归纳提纯**：大模型依据 JSON 完整上下文语料（严禁部分截断读取），提取深层核心逻辑、重点纪要并根据前期下达的格式整理。
6. **产出交付**：将在 
ote_results/ 呈现 Markdown（供存档或发博）和 HTML 内容。

## 🛠️ 安装与部署指南

### 前置环境需求
- **Python 3.8+**
- 基本依赖：pip install -r requirements.txt （主要是 equests 和 markdown 库）
- 兼容最新智能 IDE。

### 使用步骤
1. 将本项目复制或克隆到您的 .github/skills/ai-video-notes 或 ~/.copilot/skills/ai-video-notes/ 目录。
2. 将 config/settings.json.template 重命名或复制为 config/settings.json，并填入您个人的 B 站 Cookie（仅供读取字幕使用，请勿随意上传）。
3. 重新加载 AI，在聊天输入 /skill ai-video-notes 你好，给我这期视频做个简短摘要 https://... 即可开始。
