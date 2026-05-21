#!/usr/bin/env python3
"""
Bilibili Video Note Workflow - 一键运行脚本
用法: python run_workflow.py <视频URL> [风格] [格式]
"""

import sys
import os
import json
import subprocess

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'settings.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def main():
    if len(sys.argv) < 2:
        print("用法: python run_workflow.py <视频URL> [风格] [格式]")
        print("示例: python run_workflow.py https://www.bilibili.com/video/BV1xxx/ detailed toc+link+summary")
        sys.exit(1)

    video_url = sys.argv[1]
    style = sys.argv[2] if len(sys.argv) > 2 else None
    format_type = sys.argv[3] if len(sys.argv) > 3 else None

    config = load_config()
    style = style or config.get('default_style', 'detailed')
    format_type = format_type or config.get('default_format', 'toc+link+summary')

    print("=" * 60)
    print("BiliNote 工作流")
    print("=" * 60)
    print(f"视频URL: {video_url}")
    print(f"风格: {style}")
    print(f"格式: {format_type}")
    print("=" * 60)

    script_dir = os.path.dirname(__file__)

    print("\n[Step 1/3] 提取字幕...")
    result = subprocess.run([
        sys.executable,
        os.path.join(script_dir, '01_extract_transcript.py'),
        video_url
    ])

    if result.returncode != 0:
        print("字幕提取失败!")
        sys.exit(1)

    video_id = video_url.split('/video/')[-1].split('/')[0].split('?')[0]
    transcript_file = os.path.join(os.path.dirname(script_dir), 'output', f'{video_id}_transcript_full.json')

    print("\n[Step 2/3] 生成笔记...")
    result = subprocess.run([
        sys.executable,
        os.path.join(script_dir, '02_generate_note.py'),
        transcript_file,
        style,
        format_type
    ])

    if result.returncode != 0:
        print("笔记生成失败!")
        sys.exit(1)

    print("\n[Step 3/3] 生成HTML...")
    result = subprocess.run([
        sys.executable,
        os.path.join(script_dir, '03_generate_html.py'),
        transcript_file.replace('_transcript_full.json', '_note_full.md')
    ])

    if result.returncode != 0:
        print("HTML生成失败!")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("✅ 完成!")
    print(f"Markdown: {transcript_file.replace('_transcript_full.json', '_note_full.md')}")
    print(f"HTML: {transcript_file.replace('_transcript_full.json', '_note_full.html')}")
    print("=" * 60)

if __name__ == '__main__':
    main()
