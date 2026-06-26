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

## 📁 File Paths (Relative to Skill Directory)

```
Skill Directory = ai-video-notes/
├── SKILL.md              # This file
├── config/
│   └── settings.json     # Style definitions & config (fill in your B站 cookie)
├── scripts/
│   ├── 01_extract_transcript.py   # Subtitle extraction (with audio fallback)
│   └── 01b_audio_fallback.py     # Audio download + Whisper transcription
├── downloaders/
│   └── bilibili_downloader.py    # B站 API subtitle downloader
├── output/               # Transcript output
└── note_results/         # Generated notes output
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
- **⚠️ CRITICAL**: Keep the FULL URL with query parameters (especially `?p=`). Do NOT strip to just the BV ID.
- For multi-episode videos (videopod, 合集), the `?p=N` parameter specifies which episode to process.

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

**⚠️ IMPORTANT**: ONLY generate the format(s) user selected. If user picks HTML only, DO NOT generate MD. If user picks MD only, DO NOT generate HTML.

### Step 3: Read Style Definition Document (MANDATORY)

**File location**: `./config/settings.json`

**Field**: `note_styles`

### Step 4: Extract FULL Transcript

**⚠️ Cookie 有效性检查（先验证再提取）**：

Before extraction, verify the cookie is valid:
```bash
curl -s -H "Cookie: SESSDATA={cookie}" "https://api.bilibili.com/x/web-interface/view?bvid={video_id}"
```
- `code != 0` → Cookie 无效，**STOP**，提示用户提供新 Cookie
- `code == 0` 且 `subtitle.list == []` 且 `pages` 有数据 → Cookie 有效但无字幕
- 如果连续两个不同视频都返回空字幕 → 大概率 Cookie 过期，主动提示用户更换

Execute in skill directory with the FULL video URL (including `?p=N` for multi-episode):
```bash
python ./scripts/01_extract_transcript.py "{video_url}"
```

Example:
```bash
python ./scripts/01_extract_transcript.py "https://www.bilibili.com/video/BV1xxx/?p=8"
```

Single episode:
```bash
python ./scripts/01_extract_transcript.py "https://www.bilibili.com/video/BV1xxx/"
```

**⚠️ VERIFICATION CHECKLIST**:
- [ ] Total segments > 0
- [ ] Last segment end time matches video duration
- [ ] Report to user: "完整字幕：X段，X分钟"

**Output file**: `./output/{video_id}_transcript_full.json`

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
python ./scripts/01b_audio_fallback.py "{video_url}"
```

Prerequisites: `pip install faster-whisper`, `ffmpeg`, `yt-dlp`. Output JSON is marked `"source": "whisper_transcription"`.

### Step 5: Read ALL Subtitle Segments

**You MUST read the ENTIRE transcript file**: `./output/{video_id}_transcript_full.json`

Read all segments and analyze the content. If file is too large, use multiple Read calls with offset to cover 100%.

### Step 6: Generate AI-Powered Notes (CRITICAL STEP)

**⚠️ DO NOT just copy-paste subtitles! Use your AI ability to:**

1. **Read** `config/settings.json` → `note_styles.{selected_style}` to get the exact `structure`, `content_rules`, and `quality_checks`
2. **Follow the structure exactly** — generate ONLY the sections listed for that style, in the order listed
3. **Follow the content_rules exactly** — each section must contain what the rules specify
4. **Apply the quality_checks** (especially for tutorial style which has mandatory checks)

**Timestamp linking convention (ALL styles):**

All timestamps MUST link to the video with seconds calculated from HH:MM:SS:
- Markdown: `[00:11:12](https://www.bilibili.com/video/{video_id}?t=672)`
- HTML: `<a href="https://www.bilibili.com/video/{video_id}?t=672" target="_blank" class="timestamp">⏱️ 00:11:12</a>`
- Calculation: seconds = HH×3600 + MM×60 + SS

### Step 7: Save Markdown File (ONLY if MD or Both selected)

Save generated notes to: `./note_results/{视频标题}.md`（批量模式：`{NN}_{视频标题}.md`）

**Markdown quality checklist**:
- [ ] Clickable TOC with `[HH:MM:SS](bilibili-url?t=seconds)` links
- [ ] Each chapter has anchor links AND video timestamp links
- [ ] Rich tables (comparisons, options, steps)
- [ ] ` ``` ` code blocks with real commands
- [ ] Command reference grouped by category
- [ ] Learning path + Best practices sections

### Step 8: Generate HTML (ONLY if H or Both selected) ⭐ PRIMARY OUTPUT

**You MUST follow the HTML模板规范 below EXACTLY. This is non-negotiable.**

Save to: `./note_results/{video_id}_note_full.html`

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
                    <a href="https://www.bilibili.com/video/{video_id}?t={秒数}" target="_blank" title="跳转到视频">{HH:MM:SS}</a>
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
    <p><a href="https://www.bilibili.com/video/{video_id}?t={秒数}" target="_blank" class="timestamp">⏱️ {HH:MM:SS}</a></p>
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

**ALL timestamps MUST be clickable links to the video. NO plain text timestamps allowed.**

- TOC: `<a href="https://www.bilibili.com/video/{video_id}?t={seconds}" target="_blank">{HH:MM:SS}</a>`
- 章节内: `<a href="https://www.bilibili.com/video/{video_id}?t={seconds}" target="_blank" class="timestamp">⏱️ {HH:MM:SS}</a>`
- Calculation: seconds = HH×3600 + MM×60 + SS (e.g., `00:11:12` → `?t=672`)

**After generating HTML, run this post-processing to ensure ALL timestamps are linked:**

```bash
cd {skill_directory} && python -c "
import re
video_id = '{video_id}'
filepath = 'note_results/{video_id}_note_full.html'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()
def link_ts(m):
    h, m, s = int(m.group(1)), int(m.group(2)), int(m.group(3))
    total = h * 3600 + m * 60 + s
    return f'<a href=\"https://www.bilibili.com/video/{video_id}?t={total}\" target=\"_blank\" class=\"timestamp\" title=\"跳转到视频\">⏱️ {m.group(1)}:{m.group(2)}:{m.group(3)}</a>'
content = re.sub(r'⏱️ (\d{2}):(\d{2}):(\d{2})', link_ts, content)
with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print('Timestamps linked!')
"
```

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

### Step 9: Report Completion

```
✅ 完整笔记已生成！
- 视频时长：X分钟
- 处理字幕：X段（完整）
- 风格：X + Y (已应用风格定义)
- 格式：toc+link+summary
- 输出：Markdown / HTML / Both
- HTML: ./note_results/{NN}_{视频标题}.html
- Markdown: ./note_results/{NN}_{视频标题}.md
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

为每一集同时启动一个子 Agent，任务描述：
1. 用 curl + Cookie 调用 view API 获取 CID（从 `pages[N-1]`）
2. 用 curl + Cookie 调用 player API 获取字幕 URL
3. 下载字幕 JSON → 处理为标准格式 → 保存

**⚠️ 与 Step 4 相同：Cookie 检查 + 无字幕时必须先问用户。**

等待全部子 Agent 完成后进入 B4。

### Step B4: 并行生成笔记（CRITICAL）

**⛔ 主 Agent 不参与生成！子 Agent 必须用 Haiku 模型！**

子 Agent 调用签名（复制使用，禁止修改 model）：

```
Agent(model: haiku, run_in_background: true, description: "HTML笔记 {BV} ep{N}")
```

每个子 Agent 执行等同于 Step 5-8 的完整流程（读 JSON → 按 config 风格生成 → 保存 HTML）。

**⚠️ 批量模式文件命名**：必须使用 `{NN}_{视频标题}.html` 格式，`NN` = 两位数集号（如 `01_教你写一个比SimpleFOC更好的电机库.html`），标题中的特殊字符需去除（`/ \ : * ? " < > |`）。直接使用 B站 API 返回的 `pages[].part` 或 `episodes[].title` 作为标题。

**⛔ 禁止使用 `subagent_type` 参数替代 `model`。禁止省略 `model: haiku`。**

### Step B5: 汇总报告

```
✅ 批量生成完成！

| 集数 | 标题 | 时长 | 段数 | 输出文件 |
|------|------|------|------|----------|
| 01 | ... | ... | ... | 01_BVxxx_note_full.html |
| 02 | ... | ... | ... | 02_BVyyy_note_full.html |
```

**⚠️ 文件名格式：`{NN}_{视频标题}.html`，确保在文件系统中按集数排列。**

## Style Definition Reference

**Source**: `config/settings.json` → `note_styles`

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
