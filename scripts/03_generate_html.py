#!/usr/bin/env python3
"""
Step 3: Generate HTML
将 Markdown 笔记转换为带可点击时间戳的 HTML
"""

import sys
import json
import os
import re
import markdown

def load_config():
    """加载配置文件"""
    config_paths = [
        os.path.join(os.path.dirname(__file__), '..', 'config', 'settings.json'),
        os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'settings.json'),
    ]
    for path in config_paths:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
    return {}

def get_note_output_dir(config):
    """获取笔记输出目录"""
    note_dir = config.get('note_output_dir', './note_results')
    note_dir = os.path.expanduser(note_dir)
    note_dir = os.path.abspath(note_dir)
    os.makedirs(note_dir, exist_ok=True)
    return note_dir

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - AI视频笔记</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            min-height: 100vh;
            color: #e8e8e8;
            line-height: 1.8;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
        }}
        header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            border-radius: 16px;
            text-align: center;
            margin-bottom: 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        }}
        header h1 {{
            font-size: 1.8em;
            margin-bottom: 15px;
        }}
        header .meta {{
            display: flex;
            justify-content: center;
            gap: 20px;
            flex-wrap: wrap;
            font-size: 0.9em;
            opacity: 0.9;
        }}
        header .meta span {{
            background: rgba(255,255,255,0.2);
            padding: 5px 15px;
            border-radius: 20px;
        }}
        .video-link {{
            display: inline-block;
            background: white;
            color: #667eea;
            padding: 12px 30px;
            border-radius: 25px;
            text-decoration: none;
            font-weight: bold;
            margin-top: 20px;
            transition: transform 0.3s;
        }}
        .video-link:hover {{
            transform: scale(1.05);
        }}
        .toc {{
            background: rgba(255,255,255,0.1);
            border-radius: 12px;
            padding: 25px;
            margin-bottom: 30px;
        }}
        .toc h2 {{
            color: #667eea;
            margin-bottom: 15px;
            border-left: 4px solid #667eea;
            padding-left: 15px;
        }}
        .toc table {{
            width: 100%;
            border-collapse: collapse;
        }}
        .toc th, .toc td {{
            text-align: left;
            padding: 12px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}
        .toc th {{
            color: #667eea;
        }}
        .timestamp {{
            display: inline-flex;
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            padding: 4px 14px;
            border-radius: 20px;
            font-size: 0.85em;
            text-decoration: none;
            transition: all 0.3s;
        }}
        .timestamp:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }}
        .section {{
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            padding: 25px;
            margin-bottom: 20px;
            border-left: 4px solid #667eea;
        }}
        .section h2 {{
            color: #667eea;
            margin-bottom: 15px;
            border-left: none;
            padding-left: 0;
        }}
        .section h3 {{
            color: #764ba2;
            margin: 20px 0 10px;
        }}
        .content {{
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            padding: 25px;
            margin-bottom: 20px;
        }}
        .content pre {{
            background: rgba(0,0,0,0.3);
            padding: 15px;
            border-radius: 8px;
            overflow-x: auto;
            margin: 10px 0;
        }}
        .content code {{
            font-family: 'Fira Code', monospace;
            font-size: 0.9em;
        }}
        .content pre code {{
            color: #e8e8e8;
        }}
        .footer {{
            text-align: center;
            padding: 30px;
            color: #888;
            font-size: 0.9em;
        }}
        @media (max-width: 600px) {{
            .container {{ padding: 10px; }}
            header {{ padding: 20px; }}
            header h1 {{ font-size: 1.4em; }}
            .meta {{ flex-direction: column; gap: 10px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>{title}</h1>
            <div class="meta">
                <span>⏱️ {duration}分钟</span>
                <span>📝 {style}</span>
                <span>📋 {format_type}</span>
            </div>
            <a href="{video_url}" target="_blank" class="video-link">🎬 观看原片</a>
        </header>

        <div class="toc">
            <h2>📋 课程目录</h2>
            <table>
                <thead>
                    <tr>
                        <th>章节</th>
                        <th>内容预览</th>
                        <th>时间戳</th>
                    </tr>
                </thead>
                <tbody>
                    {toc_rows}
                </tbody>
            </table>
        </div>

        <div class="content">
            {content}
        </div>

        <div class="footer">
            <p>由 BiliNote AI 生成 | {timestamp}</p>
        </div>
    </div>
</body>
</html>
"""

def parse_markdown(md_content):
    """解析 Markdown 内容，提取目录和正文"""
    lines = md_content.split('\n')
    toc_rows = []
    content_lines = []
    in_toc = False
    in_content = False

    for line in lines:
        if '## 📋 课程目录' in line:
            in_toc = True
            continue
        elif in_toc and line.startswith('|') and '---' not in line:
            toc_rows.append(line)
        elif in_toc and (line.startswith('## ') or line.startswith('# ')):
            in_toc = False
            in_content = True
            content_lines.append(line)
        elif in_content:
            content_lines.append(line)

    return toc_rows, '\n'.join(content_lines)

def convert_timestamp_to_link(match):
    """将时间戳转换为可点击链接"""
    ts = match.group(1)
    return f'<a href="{ts}" class="timestamp">{ts}</a>'

def generate_html(note_file, transcript_file=None):
    """生成 HTML 主函数"""
    config = load_config()
    note_dir = get_note_output_dir(config)

    if not os.path.exists(note_file):
        print(f"错误: 笔记文件不存在: {note_file}")
        return None

    with open(note_file, 'r', encoding='utf-8') as f:
        md_content = f.read()

    title = "AI视频笔记"
    duration = "?"
    style = "detailed"
    format_type = "toc+link+summary"

    if transcript_file and os.path.exists(transcript_file):
        with open(transcript_file, 'r', encoding='utf-8') as f:
            td = json.load(f)
            duration = str(int(td.get('duration_minutes', 0)))

    title_match = re.search(r'#\s+(.+?)\s*- AI视频笔记', md_content)
    if title_match:
        title = title_match.group(1)

    style_match = re.search(r'\*\*风格\*\*：(\w+)', md_content)
    if style_match:
        style = style_match.group(1)

    format_match = re.search(r'\*\*格式\*\*：([\w+]+)', md_content)
    if format_match:
        format_type = format_match.group(1)

    toc_rows, content = parse_markdown(md_content)

    toc_html = '\n'.join(toc_rows)

    html_content = markdown.markdown(content, extensions=['tables', 'fenced_code'])

    html_content = re.sub(r'\[([\d:]+)\]\(https?://[^\)]+\?t=(\d+)\)', convert_timestamp_to_link, html_content)

    html = HTML_TEMPLATE.format(
        title=title,
        duration=duration,
        style=style,
        format_type=format_type,
        video_url="",
        toc_rows=toc_html,
        content=html_content,
        timestamp=__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')
    )

    video_url_match = re.search(r'\*\*原片\*\*：\[([^\]]+)\]\(([^\)]+)\)', md_content)
    if video_url_match:
        html = html.replace('href=""', f'href="{video_url_match.group(2)}"')

    output_file = os.path.join(note_dir, os.path.basename(note_file).replace('.md', '.html'))
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"✅ HTML 生成成功!")
    print(f"   输出文件: {output_file}")
    return output_file

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python 03_generate_html.py <笔记MD文件> [字幕JSON文件]")
        sys.exit(1)

    note_file = sys.argv[1]
    transcript_file = sys.argv[2] if len(sys.argv) > 2 else None

    result = generate_html(note_file, transcript_file)
    if result:
        print(f"\nHTML 已保存到: {result}")
    else:
        sys.exit(1)
