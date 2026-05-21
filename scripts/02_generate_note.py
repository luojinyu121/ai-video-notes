#!/usr/bin/env python3
"""
Step 2: Generate Note
根据字幕生成 Markdown 笔记
"""

import sys
import json
import os
import re

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

def find_backend_path():
    """查找 backend 路径"""
    config = load_config()

    if config.get('backend_path'):
        bp = config['backend_path']
        if os.path.isabs(bp):
            return bp
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base, bp)

    search_paths = [
        os.path.join(os.path.dirname(__file__), '..', '..', 'backend'),
        os.path.join(os.path.dirname(__file__), '..', '..', '..', 'backend'),
        os.path.join(os.getcwd(), 'backend'),
        os.path.join(os.getcwd(), '..', 'backend'),
    ]

    for path in search_paths:
        if os.path.exists(path) and os.path.exists(os.path.join(path, 'app')):
            return path

    return None

def get_note_output_dir(config):
    """获取笔记输出目录"""
    note_dir = config.get('note_output_dir', './note_results')
    note_dir = os.path.expanduser(note_dir)
    note_dir = os.path.abspath(note_dir)
    os.makedirs(note_dir, exist_ok=True)
    return note_dir

def detect_chapters(segments, duration):
    """检测章节（每3分钟一个章节）"""
    chapters = []
    chapter_duration = 180
    num_chapters = int(duration / chapter_duration) + 1

    for i in range(num_chapters):
        start = i * chapter_duration
        end = min((i + 1) * chapter_duration, duration)

        chapter_segments = [s for s in segments if start <= s['start'] < end]
        if chapter_segments:
            first_text = chapter_segments[0]['text'][:50]
            chapters.append({
                'start': start,
                'end': end,
                'title': f'第{i+1}部分',
                'preview': first_text
            })

    return chapters

def format_timestamp(seconds):
    """格式化时间戳"""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"

def generate_note(transcript_file, style='detailed', format_type='toc+link+summary'):
    """生成笔记主函数"""
    config = load_config()
    note_dir = get_note_output_dir(config)

    if not os.path.exists(transcript_file):
        print(f"错误: 字幕文件不存在: {transcript_file}")
        return None

    with open(transcript_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    video_url = data['video_url']
    video_id = data['video_id']
    duration = data.get('duration', 0)
    duration_minutes = data.get('duration_minutes', duration / 60)
    segments = data['segments']

    print(f"📖 正在生成笔记...")
    print(f"   视频: {video_url}")
    print(f"   时长: {duration_minutes:.1f} 分钟")
    print(f"   字幕段数: {len(segments)}")
    print(f"   风格: {style}")
    print(f"   格式: {format_type}")
    print(f"   输出目录: {note_dir}")

    chapters = detect_chapters(segments, duration)

    style_sections = {
        'detailed': ['AI总结', '完整目录', '章节详情', '关键命令', '资源链接'],
        'tutorial': ['学习目标', '前置知识', '操作步骤', '实战练习', '常见问题'],
        'academic': ['摘要', '背景介绍', '核心概念', '技术细节', '参考文献'],
        'minimal': ['一句话总结', '核心要点', '时间戳速查'],
    }
    sections = style_sections.get(style, style_sections['detailed'])

    md_content = f"""# {video_id} - AI视频笔记

**原片**：[{video_url}]({video_url}) | **时长**：{duration_minutes:.0f}分钟 | **风格**：{style} | **格式**：{format_type}

---

## 📋 课程目录

| 章节 | 内容 | 时间戳 |
|------|------|--------|
"""

    for i, ch in enumerate(chapters):
        ts = format_timestamp(ch['start'])
        md_content += f"| {ch['title']} | {ch['preview']}... | [{ts}]({video_url}?t={ch['start']}) |\n"

    if 'AI总结' in sections or 'summary' in format_type:
        md_content += f"""

---

## 📝 AI智能总结

**视频总时长**：{duration_minutes:.1f} 分钟
**字幕段数**：{len(segments)} 段
**章节数**：{len(chapters)} 个

"""

    if '章节详情' in sections or 'toc' in format_type:
        for i, ch in enumerate(chapters):
            ts = format_timestamp(ch['start'])
            chapter_segments = [s for s in segments if ch['start'] <= s['start'] < ch['end']]
            chapter_text = ' '.join([s['text'] for s in chapter_segments])

            md_content += f"""

## {ch['title']} - [{ts}]({video_url}?t={ch['start']})

{chapter_text[:500]}...

"""

    output_file = os.path.join(note_dir, f'{video_id}_note_full.md')
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(md_content)

    print(f"✅ 笔记生成成功!")
    print(f"   输出文件: {output_file}")
    return output_file

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python 02_generate_note.py <字幕JSON文件> [风格] [格式]")
        print("示例: python 02_generate_note.py ./output/BV1xxx_transcript_full.json detailed toc+link+summary")
        sys.exit(1)

    transcript_file = sys.argv[1]
    style = sys.argv[2] if len(sys.argv) > 2 else 'detailed'
    format_type = sys.argv[3] if len(sys.argv) > 3 else 'toc+link+summary'

    result = generate_note(transcript_file, style, format_type)
    if result:
        print(f"\n笔记已保存到: {result}")
    else:
        sys.exit(1)
