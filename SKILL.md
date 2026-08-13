---
name: "ai-video-notes"
description: "Generates AI video notes from Bilibili URLs. Invoke when user provides a Bilibili video URL and asks for notes, summary, or tutorial. CRITICAL: Always read FULL transcript - never partial."
---

# Bilibili Video Note Generator

Generates structured, styled video notes from Bilibili video URLs with AI-powered analysis.

## ⚠️ CRITICAL RULES (MUST FOLLOW)

1. **ALWAYS read FULL transcript** - NEVER stop at 50%, 80% or any partial amount
2. **ALWAYS verify duration** - Check the LAST subtitle segment's end time to confirm full coverage
3. **NEVER skip asking preferences** - Always ask style + format + output format BEFORE generating
4. **ALWAYS ask output format** - Ask user: HTML (.html) / Markdown (.md) / Both. HTML is recommended for best presentation.
5. **ONLY generate selected format(s)** - If user picks HTML only, SKIP Markdown entirely. If MD only, SKIP HTML.
6. **ALWAYS read style definition first** - Read `./config/settings.json` to get exact style requirements
7. **⚠️ CRITICAL: Use YOUR OWN AI ability to generate notes** - Do NOT rely on scripts that just copy-paste subtitles. You MUST analyze the content and generate structured notes with AI-powered insights.
8. **HTML output MUST follow the HTML模板规范** - See Step 8 for exact CSS, structure, and timestamp linking requirements
9. **⛔ 批量/并行子 Agent 必须使用 Haiku 模型** - 任何用来读字幕/生成笔记的子 Agent 必须指定 `model: haiku`。主 Agent 不得用自身模型启动子 Agent。违反此规则将导致 token 大量浪费。

## 📁 File Paths

```
Skill Directory = ai-video-notes/     （克隆后为仓库根目录）
├── SKILL.md                 # This file（技能定义）
├── config/
│   └── settings.json        # 风格定义与配置（填入你的 B站 Cookie）
├── scripts/
│   ├── 01_extract_transcript.py   # 字幕提取（Cookie 校验 + auth_key 刷新 + 覆盖度校验）
│   ├── 01b_audio_fallback.py      # 音频降级：下载音频 + Whisper 转录
│   ├── 02_capture_frames.py       # 图文笔记截图嵌入（解析 {{SHOT:秒数}} → base64 内嵌 HTML）
│   ├── batch_audio_extract.py     # 批量音频降级转录（修复分集文件名冲突）
│   └── setup_cookie.py
├── downloaders/
│   └── bilibili_downloader.py     # B站 API 字幕下载器（curl + wbi 签名）
├── output/                  # 字幕输出（gitignored）
└── note_results/            # 笔记输出（gitignored）

⚠️ 运行脚本前请先 `cd` 到 skill 目录；`output/`、`note_results/` 等相对路径均指 Skill Directory 下的子目录。
```

## Workflow

## 模式检测

收到 B站 URL 后，先判断模式：

| 用户意图 | 模式 | 说明 |
|----------|------|------|
| 单个视频（URL 无 `?p=` 或只指定单集） | **单集模式** → `## Workflow` | 主 Agent 全程处理 |
| 合集/多集（用户说"批量""第1,3,5集"或提供 videopod URL） | **批量模式** → `## Batch Mode Workflow` | 子 Agent 并行 |

### Step 1: Extract Video URL
Parse video ID and page number from URL.
- e.g., `https://www.bilibili.com/video/BV1xxx/?p=8` → video_id = `BV1xxx`, page = `8`
- e.g., `https://www.bilibili.com/video/BV1xxx/`（无 `?p=`）→ video_id = `BV1xxx`, page = `""`（空字符串，单集模式）
- **⚠️ CRITICAL**: Keep the FULL URL with query parameters (especially `?p=`). Do NOT strip to just the BV ID.
- For multi-episode videos (videopod, 合集), the `?p=N` parameter specifies which episode to process.
- **`page` 变量必须在后续所有时间戳链接中使用**：合集用 `?p={page}&t={秒数}`，单集用 `?t={秒数}`

### Step 2: Ask User Preferences (MANDATORY - NEVER SKIP)

Use AskUserQuestion tool with multiSelect: true. Split style options across max 3 questions (each ≤4 options).
**Default recommendation: HTML output with 完整格式 (toc+link+summary).**

**Style Selection (Multi-select)**:
| Option | Style | Description |
|--------|-------|-------------|
| A | detailed | Comprehensive, covers everything |
| B | tutorial | Step-by-step, beginner-friendly |
| C | academic | Formal, citation-ready structure |
| D | minimal | Concise, quick reference |
| E | xiaohongshu | 小红书爆款风格 |
| F | life_journal | 生活感悟风格 |
| G | task_oriented | 任务导向风格 |
| H | business | 商业报告风格 |
| I | meeting_minutes | 会议纪要风格 |

**Format Selection (Multi-select)**:
| Option | Format | Description |
|--------|--------|-------------|
| 1 | toc+link+summary | Full format (recommended) |
| 2 | toc | Table of contents |
| 3 | link | Clickable timestamps |
| 4 | summary | AI summary |

**Output Format (Multi-select)**:
| Option | Output | Description |
|--------|--------|-------------|
| HTML | HTML (.html) | Beautiful styled webpage (recommended) |
| MD | Markdown (.md) | Clean markdown file |
| Both | Both | Generate both formats |

**Note Type（笔记类型，Multi-select）**:
| Option | Type | Description |
|--------|------|-------------|
| 图文笔记 | Rich (recommended) | HTML 中每个章节插入视频关键画面截图（base64 内嵌，不额外存储图片） |
| 文字笔记 | Text | 纯文本笔记（现状），不含截图 |

**⚠️ IMPORTANT**:
- ONLY generate the format(s) user selected. If user picks HTML only, DO NOT generate MD. If user picks MD only, DO NOT generate HTML.
- **图文笔记**：仅对 HTML 生效，MD 不含截图。生成 HTML 时必须在每个章节时间戳后插入 `{{SHOT:秒数}}` 占位符，并运行 Step 8.5 嵌入脚本。
- **文字笔记**：保持现有纯文本流程，不插入占位符、不运行嵌入脚本。

### Step 3: Read Style Definition Document (MANDATORY)

**File location**: `./config/settings.json`

**Field**: `note_styles`

### Step 4: Extract FULL Transcript

**⚠️ 直接运行脚本即可，脚本内部已处理 Cookie 校验 + curl 请求 + auth_key 刷新 + 覆盖度校验。**

Execute:
```bash
python "./scripts/01_extract_transcript.py" "{video_url}" "output"
```

Example:
```bash
python "./scripts/01_extract_transcript.py" "https://www.bilibili.com/video/BV1xxx/?p=8" "output"
```

Single episode:
```bash
python "./scripts/01_extract_transcript.py" "https://www.bilibili.com/video/BV1xxx/" "output"
```

**⚠️ 必须显式传入输出目录参数（第三个参数），否则会写到 cwd。若脚本不支持该参数，请直接改 config/settings.json 的 `output_dir` 字段。**

**脚本失败时的处理**：
- `"该视频没有可用字幕"` → Cookie 可能过期。先确认 config/settings.json 里的 `bilibili_cookie` 是**最新**的，更新后重试
- 连续两个不同视频都返回空字幕 → 大概率 Cookie 过期，主动提示用户更换

**⚠️ VERIFICATION CHECKLIST**:
- [ ] Total segments > 0
- [ ] Last segment end time matches video duration（脚本已自动校验 80%~130%，打印 "覆盖到 Xs / 总长 Ys"）
- [ ] Report to user: "完整字幕：X段，X分钟"

**Output file**: `output/{video_id}_p{page}_transcript_full.json`（分P）或 `{video_id}_transcript_full.json`（单集）

#### 🔄 Audio Fallback（字幕不可用时的降级方案）

**⚠️ CRITICAL: NEVER auto-trigger audio fallback. MUST ask user first.**

If the video has NO subtitles（B站 API 返回 `subtitles: []`）：
1. **DO NOT immediately download audio or use Whisper**
2. **ASK the user** with AskUserQuestion:
   - "该视频未找到字幕。可能原因：Cookie 已过期（最常见）/ 该视频确实未生成AI字幕"
   - 选项 A: 提供新的 Cookie 重试
   - 选项 B: 使用音频降级方案（下载音频 + Whisper 转录，耗时较长，需 ffmpeg + faster-whisper）
3. **只有用户明确选择 B 后**才执行音频降级

If user chooses B, run:
```bash
python "{skill_dir}/scripts/01b_audio_fallback.py" "{video_url}"
```

Prerequisites: `pip install faster-whisper`, `ffmpeg`, `yt-dlp`. Output JSON is marked `"source": "whisper_transcription"`.

### Step 5: Read ALL Subtitle Segments

**You MUST read the ENTIRE transcript file**: `output/{video_id}_p{page}_transcript_full.json`（分P）或 `{video_id}_transcript_full.json`（单集）

Read all segments and analyze the content. If file is too large, use multiple Read calls with offset to cover 100%.

### Step 6: Generate AI-Powered Notes (CRITICAL STEP)

**⚠️ DO NOT just copy-paste subtitles! Use your AI ability to:**

1. **Read** `./config/settings.json` → `note_styles.{selected_style}` to get the exact `structure`, `content_rules`, and `quality_checks`
2. **Follow the structure exactly** — generate ONLY the sections listed for that style, in the order listed
3. **Follow the content_rules exactly** — each section must contain what the rules specify
4. **Apply the quality_checks** (especially for tutorial style which has mandatory checks)

**Timestamp linking convention (ALL styles):**

All timestamps MUST link to the video with seconds calculated from HH:MM:SS:
- Markdown: `[00:11:12](https://www.bilibili.com/video/{video_id}?t=672)`（单集）或 `[00:11:12](https://www.bilibili.com/video/{video_id}?p={page}&t=672)`（合集）
- HTML: `<a href="https://www.bilibili.com/video/{video_id}?t=672"...`（单集）或 `<a href="https://www.bilibili.com/video/{video_id}?p={page}&t=672"...`（合集）
- 合集（有 `?p=` 参数）必须使用 `?p={page}&t={秒数}`，跳转到对应集数的对应时间
- 单集（无 `?p=`）保持 `?t={秒数}`

**Screenshot placeholder convention（图文笔记模式 ONLY）:**

用户选择「图文笔记」时，**文字笔记内容保持不变**，AI 按「画面场景」划分字幕并为每个场景配 1 张截图，通过占位符 `{{SHOT:{秒数}}}` 让脚本把图插回对应位置。

**场景划分算法（AI 判断，结合字幕时间间隔）：**
1. 从字幕第一句开始，逐句向后扫描
2. **相邻句主题关联**（仍在讲同一个命令/页面/画面，如还在讲 gzip 而未切到 bzip）→ 归入当前场景
3. **主题切换**（如从 gzip 切到 bzip、从安装切到配置）→ 开启新场景
4. **最多 4 句**：同一场景累计 4 句后，即使主题看似未切换，也自动认为已换页面，开启新场景
5. 场景边界由「主题关联 + 4 句上限」共同决定；每个场景对应笔记中一个内容块

**每场景 1 张截图，取点位置（3/4 处）：**
- 取该场景**最后一句话**字幕段时间区间 `[start, end]` 的 `start + (end - start) × 3/4`（靠近最后一句、画面对该内容展示最完整处）
- 例：场景末句字幕 `[90s, 94s]` → 截图点 `90 + 4×0.75 = 93s` → `{{SHOT:93}}`（四舍五入取整）

**插入位置：** 截图插在笔记中该场景对应内容处（命令/链接/配置/说明附近），**原文文字不删不改**
**适用范围：** 仅图文笔记模式；纯文字笔记不调用截图，保持现状不变

### Step 7: Save Markdown File (ONLY if MD or Both selected)

Save generated notes to: `note_results/{视频标题}.md`（批量模式：`{NN}_{视频标题}.md`）

**Markdown quality checklist**:
- [ ] Clickable TOC with `[HH:MM:SS](bilibili-url?t=seconds)` links
- [ ] Each chapter has anchor links AND video timestamp links
- [ ] Rich tables (comparisons, options, steps)
- [ ] ` ``` ` code blocks with real commands
- [ ] Command reference grouped by category
- [ ] Learning path + Best practices sections

### Step 8: Generate HTML (ONLY if H or Both selected) ⭐ PRIMARY OUTPUT

**You MUST follow the HTML模板规范 below EXACTLY. This is non-negotiable.**

Save to: `note_results/{视频标题}.html`（批量：`{NN}_{视频标题}.html`）

**⚠️ 文件命名规范（强制执行）**：
- **单集模式**：`{视频标题}.html`（如 `教你写一个比SimpleFOC更好的电机库.html`），标题中的特殊字符需去除（`/ \ : * ? " < > |`）
- **批量模式**：`{NN}_{视频标题}.html`，`NN` 为两位数集号（如 `01_教你写一个比SimpleFOC更好的电机库.html`），确保文件按集数排序
- Markdown 同理：`{视频标题}.md` / `{NN}_{视频标题}.md`

#### 8.1 CSS 模板（必须使用）

```css
/* 全局 */
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
    line-height: 1.8; color: #333;
    background: linear-gradient(135deg, #e94560 0%, #ff6b6b 50%, #533483 100%);
    min-height: 100vh; padding: 20px;
}
.container { max-width: 1200px; margin: 0 auto; background: white; border-radius: 20px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); overflow: hidden; }

/* Header */
.header { background: linear-gradient(135deg, #e94560 0%, #533483 100%); color: white; padding: 60px 40px; text-align: center; }
.header h1 { font-size: 2.5em; margin-bottom: 20px; text-shadow: 2px 2px 4px rgba(0,0,0,0.2); }
.header .meta { display: flex; justify-content: center; gap: 30px; flex-wrap: wrap; margin-top: 20px; }
.header .meta-item { background: rgba(255,255,255,0.2); padding: 10px 20px; border-radius: 25px; backdrop-filter: blur(10px); }

/* Content area */
.content { padding: 40px; }

/* Headings */
h2 { color: #e94560; margin-top: 40px; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 3px solid #e94560; }
h3 { color: #533483; margin-top: 30px; margin-bottom: 15px; }
h4 { color: #555; margin-top: 20px; margin-bottom: 10px; }

/* TOC */
.toc { background: #f8f9fa; padding: 30px; border-radius: 15px; margin-bottom: 40px; border-left: 5px solid #e94560; }
.toc h2 { margin-top: 0; border-bottom: none; }
.toc table { width: 100%; border-collapse: collapse; margin-top: 20px; }
.toc th, .toc td { padding: 12px 15px; text-align: left; border-bottom: 1px solid #e0e0e0; }
.toc th { background: #e94560; color: white; font-weight: 600; }
.toc tr:hover { background: #f0f0f0; }
.toc a { color: #e94560; text-decoration: none; transition: all 0.3s; }
.toc a:hover { color: #533483; text-decoration: underline; }

/* Tables */
table { width: 100%; border-collapse: collapse; margin: 20px 0; box-shadow: 0 2px 10px rgba(0,0,0,0.1); border-radius: 10px; overflow: hidden; }
th { background: linear-gradient(135deg, #e94560 0%, #533483 100%); color: white; padding: 15px; text-align: left; font-weight: 600; }
td { padding: 12px 15px; border-bottom: 1px solid #e0e0e0; }
tr:hover { background: #f8f9fa; }

/* Code */
code { background: #f4f4f4; padding: 2px 8px; border-radius: 4px; font-family: "Fira Code", "Consolas", monospace; color: #e94560; font-size: 0.9em; }
pre { background: #2d2d2d; color: #f8f8f2; padding: 20px; border-radius: 10px; overflow-x: auto; margin: 20px 0; font-family: "Fira Code", "Consolas", monospace; line-height: 1.6; }
pre code { background: none; color: inherit; padding: 0; }

/* Callout boxes */
.highlight { background: linear-gradient(135deg, #e9456020 0%, #53348320 100%); padding: 20px; border-radius: 10px; margin: 20px 0; border-left: 4px solid #e94560; }
.highlight h3 { margin-top: 0; }
.warning { background: #fff3cd; border-left: 4px solid #ffc107; padding: 20px; border-radius: 10px; margin: 20px 0; }
.warning h4 { color: #856404; margin-top: 0; }
.success { background: #d4edda; border-left: 4px solid #28a745; padding: 20px; border-radius: 10px; margin: 20px 0; }

/* Sections */
.section { margin: 40px 0; padding: 30px; background: #fafafa; border-radius: 15px; border: 1px solid #e0e0e0; }
.section h2 { margin-top: 0; }
.anchor { display: block; position: relative; top: -80px; visibility: hidden; }

/* Timestamps */
.timestamp { color: #e94560; font-size: 0.9em; font-weight: 600; text-decoration: none; }
.timestamp:hover { text-decoration: underline; color: #533483; }

/* Screenshot (图文笔记) */
.shot { margin: 20px 0; text-align: center; }
.shot img { max-width: 100%; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.15); }
.shot figcaption { margin-top: 8px; color: #888; font-size: 0.85em; }

/* Footer */
.footer { background: #2d2d2d; color: #999; text-align: center; padding: 30px; }
.footer a { color: #e94560; text-decoration: none; }

/* Responsive */
@media (max-width: 768px) {
    .container { margin: 10px; border-radius: 10px; }
    .header { padding: 40px 20px; }
    .header h1 { font-size: 1.8em; }
    .content { padding: 20px; }
    table { font-size: 0.9em; }
    pre { font-size: 0.85em; }
}
```

#### 8.2 HTML 结构模板（必须遵循）

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{视频标题}</title>
    <style>/* 上面的 CSS 模板 */</style>
</head>
<body>
<div class="container">

<!-- Header -->
<div class="header">
    <h1>{视频标题}</h1>
    <p style="font-size: 1.2em; opacity: 0.9;">{副标题/一句话描述}</p>
    <div class="meta">
        <div class="meta-item">📺 B站 {video_id}</div>
        <div class="meta-item">⏱️ 约{X}分钟</div>
        <div class="meta-item">📚 {styles}</div>
    </div>
</div>

<div class="content">

<!-- TOC - 每条记录同时有视频链接和页面锚点 -->
<div class="toc">
    <h2>📋 课程目录</h2>
    <table>
        <thead><tr><th>章节</th><th>内容预览</th><th>时间戳</th></tr></thead>
        <tbody>
            <tr>
                <td>01</td>
                <td>{章节标题}</td>
                <td>
                    <a href="https://www.bilibili.com/video/{video_id}?p={page}&t={秒数}" target="_blank" title="跳转到视频">{HH:MM:SS}</a>
                    <a href="#{anchor}" style="font-size:0.8em;color:#999" title="页面内定位">↓</a>
                </td>
            </tr>
            <!-- ...更多章节... -->
        </tbody>
    </table>
</div>

<!-- 核心概念速览 -->
<div class="highlight">
    <h3>🎯 核心概念速览</h3>
    <ul>
        <li><strong>{概念}</strong>：{一句话解释}</li>
    </ul>
</div>

<h2>📖 详细教程</h2>

<!-- 每个章节一个 .section -->
<div class="section">
    <span class="anchor" id="{anchor}"></span>
    <h2>{NN} {章节标题}</h2>
    <p><a href="https://www.bilibili.com/video/{video_id}?p={page}&t={秒数}" target="_blank" class="timestamp">⏱️ {HH:MM:SS}</a></p>
    <!-- 图文笔记模式：识别到关键内容（链接/输入/注意/终端）时，在对应描述处插入占位符 -->
    {{SHOT:{秒数}}}
    <!-- 章节内容：h3 子节 + 表格 + 代码块 + callout -->
</div>

<!-- ...更多章节... -->

<!-- 命令速查表 -->
<h2>🔧 常用命令速查表</h2>
<!-- 按类别分组：对话控制 / 文件项目 / 安装部署 / 记忆系统 / 自动化 -->

<!-- 注意事项 -->
<h2>⚠️ 重要注意事项</h2>
<!-- 每个用 .warning 包裹 -->

<!-- 学习路径 -->
<h2>🎓 学习路径建议</h2>

<!-- 最佳实践 -->
<h2>💡 最佳实践</h2>
<div class="success"><h4>✅ 推荐做法</h4>...</div>
<div class="warning"><h4>❌ 避免做法</h4>...</div>

</div><!-- .content -->

<div class="footer">
    <p>📺 视频来源：<a href="https://www.bilibili.com/video/{video_id}">Bilibili {video_id}</a></p>
    <p>👤 视频作者：{作者} | 📍 {定位}</p>
    <p>👥 适用人群：{人群}</p>
    <p style="margin-top:15px;">📅 笔记生成时间: {日期} | 风格: {styles} | 格式: {formats}</p>
</div>

</div><!-- .container -->
</body>
</html>
```

#### 8.3 时间戳链接规范（必须执行）

**All timestamps MUST be clickable links to the video. NO plain text timestamps allowed.**
**合集（多集视频，有 `?p=N` 参数）必须使用 `?p={page}&t={seconds}`，单集保持 `?t={seconds}`。**

- TOC: `<a href="https://www.bilibili.com/video/{video_id}?p={page}&t={seconds}" target="_blank">{HH:MM:SS}</a>`（合集）
- 章节内: `<a href="https://www.bilibili.com/video/{video_id}?p={page}&t={seconds}" target="_blank" class="timestamp">⏱️ {HH:MM:SS}</a>`（合集）
- 单集：`?t={seconds}`（去掉 `?p=`）
- Calculation: seconds = HH×3600 + MM×60 + SS (e.g., `00:11:12` → `?t=672`)

**After generating HTML, run this post-processing to ensure ALL timestamps are linked:**

```bash
python -c "
import re
video_id = '{video_id}'
page = '{page}'  # 集号，如 '3'；单集为空字符串
filepath = r'note_results/{NN}_{视频标题}.html'  # 替换为实际文件名
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()
def link_ts(m):
    h, m_min, s = int(m.group(1)), int(m.group(2)), int(m.group(3))
    total = h * 3600 + m_min * 60 + s
    page_param = f'?p={page}&' if page else '?'
    return f'<a href=\"https://www.bilibili.com/video/{video_id}{page_param}t={total}\" target=\"_blank\" class=\"timestamp\" title=\"跳转到视频\">⏱️ {m.group(1)}:{m.group(2)}:{m.group(3)}</a>'
content = re.sub(r'⏱️ (\d{2}):(\d{2}):(\d{2})', link_ts, content)
with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print('Timestamps linked!')
"
```
**⚠️ 使用 skill 目录下相对路径，不要写到 {cwd}。**

#### 8.4 HTML 质量检查清单

- [ ] 使用规定的 CSS 模板（浅色主题 + 红紫渐变）
- [ ] Header 含视频 ID、时长、风格标签
- [ ] TOC 每条同时有视频链接（新窗口）和页面锚点（↓）
- [ ] 每个 `.section` 以 `<span class="anchor">` + `<h2>` 开头
- [ ] 每个章节第一个 `<p>` 是带 `⏱️` 的可点击时间戳
- [ ] 所有时间戳已通过 post-processing 脚本转换为链接
- [ ] 表格 `<th>` 使用渐变背景
- [ ] 提示用 `.highlight` / `.warning` / `.success`
- [ ] `.footer` 深色背景，含完整视频信息
- [ ] 包含 `@media (max-width: 768px)` 响应式
- [ ] （图文笔记模式）截图插在原文对应内容处，**原文文字未删改**
- [ ] （图文笔记模式）占位符秒数=场景末句字幕时间区间 3/4 处（四舍五入）；无 `{{SHOT:` 残留、每张有 `<figure class="shot">`

#### 8.5 嵌入关键画面截图（图文笔记模式）

**仅当用户选择「图文笔记」时执行。文字笔记模式跳过本步。**

1. **AI 生成 HTML 时**：按 Step 6「Screenshot placeholder convention」的场景算法划分字幕（相邻句主题关联归同场景、主题切换开新场景、最多 4 句），每场景取**末句字幕时间区间 3/4 处**为截图点，在该场景对应内容处插入占位符 `{{SHOT:{秒数}}}`（四舍五入取整秒）。例：场景末句 `[90s, 94s]` → `{{SHOT:93}}`。**原文文字不删不改，仅插入图片。**
2. **运行嵌入脚本**（HTML 生成完毕后）：
   ```bash
   python "./scripts/02_capture_frames.py" "{video_url}" "{html_绝对路径}"
   ```
   例：
   ```bash
   python "./scripts/02_capture_frames.py" "https://www.bilibili.com/video/BV1xxx/?p=3" "note_results/03_视频标题.html"
   ```
   脚本自动完成：解析占位符 → yt-dlp 下载视频（h264≤720，复用 cookie）→ 按**时间点后 1 秒**截帧（缩放宽度 960）→ base64 内嵌为 `<figure class="shot">` → 写回 HTML → 清理临时文件。
3. **校验**：脚本运行后 `{{SHOT:` 占位符应已全部替换；确认每个章节有 `<figure class="shot">`。
4. **耗时提示**：每集需先下载一次视频（约 1-3 分钟），截图越多耗时略增。向用户说明。
5. **失败处理**：若脚本报「视频下载失败」（Cookie 过期/网络），提示用户更新 cookie 后重试；个别时间点截帧失败会自动跳过并替换为空。

### Step 9: Report Completion

```
✅ 完整笔记已生成！
- 视频时长：X分钟
- 处理字幕：X段（完整）
- 风格：X + Y (已应用风格定义)
- 格式：toc+link+summary
- 笔记类型：图文笔记 / 文字笔记
- 截图：N 张（图文笔记模式）
- 输出：Markdown / HTML / Both
- HTML: note_results/{NN}_{视频标题}.html
- Markdown: note_results/{NN}_{视频标题}.md
```

---

## Batch Mode Workflow（批量多集处理）

### Step B1: 拉取分集列表

1. 调用 B站 API 获取所有分集：
```bash
curl -s -H "Cookie: SESSDATA={cookie}" "https://api.bilibili.com/x/web-interface/view?bvid={BV号}"
```
2. 解析 `data.pages`，展示列表（含集数、标题、时长）
3. 如果 > 20 集，只展示前 5 集 + "...共 N 集"

### Step B2: 询问偏好（一次性）

用 AskUserQuestion 收集：
- Q1: 要处理哪几集？（如 1,3,5-8）
- Q2-Q4: 风格/格式/输出（与 Step 2 完全一致）
- Q5: 笔记类型：图文笔记 / 文字笔记（与 Step 2 一致；图文笔记每集都会运行 Step 8.5 嵌入脚本，耗时增加）

#### ⛔ 启动子 Agent 前自查（B2 结束后强制执行）

在进入 B3 或 B4 之前，主 Agent 必须逐项确认：

| # | 检查项 | 验证方法 |
|---|--------|----------|
| 1 | 子 Agent 调用是否包含 `model: haiku`？ | 搜索调用中的 `model` 字段 |
| 2 | 是否设置了 `run_in_background: true`？ | 批量并行必须异步 |
| 3 | 子 Agent 数量是否合理？ | 分批启动，每批 ≤ 7 个 |

**若任一项不满足 → STOP，修正后重新启动。**

### Step B3: 并行提取字幕（CRITICAL）

**⛔ 主 Agent 不参与提取！子 Agent 必须用 Haiku 模型！**

子 Agent 调用签名（复制使用，禁止修改 model）：

```
Agent(model: haiku, run_in_background: true, description: "提取字幕 {BV} p{N}")
```

为每一集启动一个子 Agent，任务描述：
**直接运行提取脚本，不要自己手写 curl 调用 API（会踩 412/过期/错集坑）：**
```bash
python "./scripts/01_extract_transcript.py" "https://www.bilibili.com/video/{BV}?p={N}" "output"
```
脚本内部已处理：curl 请求、Cookie、wbi 签名、auth_key 刷新、分P 选取、覆盖度校验、自动重试。
**⚠️ 验证**：确认输出文件 `{BV}_p{N}_transcript_full.json` 存在于 skill 目录 output/，覆盖度达标。

**⚠️ 与 Step 4 相同：Cookie 检查 + 无字幕时必须先问用户。**

等待全部子 Agent 完成后进入 B4。

### Step B4: 并行生成笔记（CRITICAL）

**⛔ 主 Agent 不参与生成！子 Agent 必须用 Haiku 模型！**

子 Agent 调用签名（复制使用，禁止修改 model）：

```
Agent(model: haiku, run_in_background: true, description: "HTML笔记 {BV} ep{N}")
```

每个子 Agent 执行等同于 Step 5-8 的完整流程（读 JSON → 按 config 风格生成 → 保存 HTML）。

**⚠️ 图文笔记模式（B4 附加步骤）**：若用户选择「图文笔记」，子 Agent 生成 HTML（含 `{{SHOT:秒数}}` 占位符）后，必须对**每一集**运行 Step 8.5 嵌入脚本：
```bash
python "./scripts/02_capture_frames.py" "https://www.bilibili.com/video/{BV}?p={N}" "note_results/{NN}_{视频标题}.html"
```
- 每集独立下载一次视频（约 1-3 分钟），各子 Agent 并行执行
- 校验：脚本无 `{{SHOT:` 残留、每章有 `<figure class="shot">`

**⚠️ 保存路径（子 Agent 强制）**：所有 HTML/MD 必须写入 `note_results/`，字幕 JSON 从 `output/` 读取。禁止写到 {cwd}。

**⚠️ 批量模式文件命名**：必须使用 `{NN}_{视频标题}.html` 格式，`NN` = 两位数集号（如 `01_教你写一个比SimpleFOC更好的电机库.html`），标题中的特殊字符需去除（`/ \ : * ? " < > |`）。直接使用 B站 API 返回的 `pages[].part` 或 `episodes[].title` 作为标题。

**⛔ 禁止使用 `subagent_type` 参数替代 `model`。禁止省略 `model: haiku`。**

### Step B5: 汇总报告

```
✅ 批量生成完成！

| 集数 | 标题 | 时长 | 段数 | 输出文件 |
|------|------|------|------|----------|
| 01 | ... | ... | ... | 01_Codex安装与使用.html |
| 02 | ... | ... | ... | 02_Codex前置准备.html |
```

**⚠️ 文件名格式：`{NN}_{视频标题}.html`（位于 `note_results/`），确保在文件系统中按集数排列。**

**⚠️ 图文笔记模式**：报告末尾追加「截图」列或说明每集嵌入截图张数（如 `01_xxx.html（截图 6 张）`）。

## Style Definition Reference

**Source**: `./config/settings.json` → `note_styles`

| Style | Key Requirements |
|-------|-----------------|
| minimal | Only most important content, concise |
| detailed | Complete content, as much as possible, detailed notes |
| tutorial | Detailed tutorial, key points, conclusion steps |
| academic | Academic report, formal and structured |
| xiaohongshu | Trending keywords, sensational titles, emoji |
| business | Business reports, formal and precise |
| meeting_minutes | Meeting records, clear and organized |

## Portable Deployment

This skill is self-contained. For GitHub deployment:

```
ai-video-notes/               # Repository root
├── SKILL.md                  # Skill definition (REQUIRED in .github/skills/)
├── config/settings.json      # Style definitions (self-contained)
├── scripts/                  # Python scripts
│   ├── 01_extract_transcript.py
│   ├── 02_generate_note.py
│   └── 03_generate_html.py
├── downloaders/              # Downloaders
│   └── bilibili_downloader.py
├── output/                   # Transcript cache (gitignored)
├── note_results/             # Output notes (gitignored)
├── logs/                     # Logs (gitignored)
├── requirements.txt          # Python dependencies
└── README.md                 # Documentation
```

### Setup for End Users

1. Clone repository
2. Update `config/settings.json` with their BiliBili cookie
3. Copy entire folder to `.github/skills/ai-video-notes/`
4. Start using!

## Configuration

### config/settings.json

```json
{
  "bilibili_cookie": "YOUR_COOKIE_HERE",
  "note_styles": {
    "detailed": {
      "description": "Comprehensive coverage",
      "requirements": ["Complete content", "All details"]
    }
  }
}
```
