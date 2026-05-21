---
name: "ai-video-notes"
description: "Generates AI video notes from Bilibili URLs. Invoke when user provides a Bilibili video URL and asks for notes, summary, or tutorial. CRITICAL: Always read FULL transcript - never partial."
---

# Bilibili Video Note Generator

Generates structured, styled video notes from Bilibili video URLs with AI-powered analysis.

## ⚠️ CRITICAL RULES (MUST FOLLOW)

1. **ALWAYS read FULL transcript** - NEVER stop at 50%, 80% or any partial amount
2. **ALWAYS verify duration** - Check the LAST subtitle segment's end time to confirm full coverage
3. **NEVER skip asking preferences** - Always ask style + format BEFORE generating
4. **ALWAYS generate BOTH outputs** - Markdown (.md) AND HTML (.html)
5. **ALWAYS read style definition first** - Read `./config/settings.json` to get exact style requirements
6. **⚠️ CRITICAL: Use YOUR OWN AI ability to generate notes** - Do NOT rely on scripts that just copy-paste subtitles. You MUST analyze the content and generate structured notes with AI-powered insights.

## 📁 File Paths (Relative to Skill Directory)

```
Skill Directory = ai-video-notes/
├── SKILL.md              # This file
├── config/
│   └── settings.json     # Style definitions & config
├── scripts/
│   ├── 01_extract_transcript.py
│   ├── 02_generate_note.py
│   └── 03_generate_html.py
├── downloaders/
│   └── bilibili_downloader.py
├── output/               # Transcript output
└── note_results/         # Generated notes output
```

## Workflow

### Step 1: Extract Video URL
Parse video ID from URL (e.g., `https://www.bilibili.com/video/BV1xxx/` → `BV1xxx`)

### Step 2: Ask User Preferences (MANDATORY - NEVER SKIP)

Use AskUserQuestion tool with multiSelect: true

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

### Step 3: Read Style Definition Document (MANDATORY)

**File location**: `./config/settings.json`

**Field**: `note_styles`

### Step 4: Extract FULL Transcript

Execute in skill directory:
```bash
python ./scripts/01_extract_transcript.py {video_id}
```

Example:
```bash
python ./scripts/01_extract_transcript.py BV1xxx
```

**⚠️ VERIFICATION CHECKLIST**:
- [ ] Total segments > 0
- [ ] Last segment end time matches video duration
- [ ] Report to user: "完整字幕：X段，X分钟"

**Output file**: `./output/{video_id}_transcript_full.json`

### Step 5: Read ALL Subtitle Segments

**You MUST read the ENTIRE transcript file**: `./output/{video_id}_transcript_full.json`

Read all segments and analyze the content.

### Step 6: Generate AI-Powered Notes (CRITICAL STEP)

**⚠️ DO NOT just copy-paste subtitles! Use your AI ability to:**

1. **Analyze the full transcript content**
2. **Identify core concepts, key points, and important details**
3. **Structure the notes according to selected style and format**
4. **Generate meaningful summaries, not just raw transcript**

**Output must include (depending on style/format):**
- Core concept summary
- Key insights and important points
- Structured outline/TOC
- Clickable timestamps for key sections (link to video: `https://www.bilibili.com/video/{video_id}?t={seconds}`)
- Relevant examples or code snippets (if applicable)
- Practical tips or actionable takeaways

**Apply style requirements from config/settings.json:**
- **detailed**: Comprehensive coverage, all details documented
- **tutorial**: Step-by-step guide, key points highlighted
- **academic**: Formal structure, citations
- **minimal**: Only essential points
- etc.

### Step 7: Save Markdown File

Save generated notes to: `./note_results/{video_id}_note_full.md`

### Step 8: Generate HTML

Generate beautiful HTML page with proper styling:
- Include header with video info
- Include clickable table of contents
- Include timestamp links
- Include styled content sections
- Include footer

Save to: `./note_results/{video_id}_note_full.html`

### Step 9: Report Completion

```
✅ 完整笔记已生成！
- 视频时长：X分钟
- 处理字幕：X段（完整）
- 风格：X + Y (已应用风格定义)
- 格式：Z (目录+时间戳+AI总结)
- Markdown: ./note_results/{id}_note_full.md
- HTML: ./note_results/{id}_note_full.html
```

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
