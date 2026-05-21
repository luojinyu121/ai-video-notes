#!/usr/bin/env python3
"""
Step 1: Extract Transcript
从B站提取完整视频字幕
"""

import sys
import json
import os

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

def extract_transcript(video_url, output_dir=None):
    """提取字幕主函数"""
    config = load_config()
    output_dir = output_dir or config.get('output_dir', './output')

    cookie = config.get('bilibili_cookie', '')

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'downloaders'))
    from bilibili_downloader import BilibiliDownloader

    print(f"🎬 正在提取字幕...")
    print(f"   视频: {video_url}")

    downloader = BilibiliDownloader(cookie=cookie)
    result = downloader.download_subtitles(video_url)

    if not result or not result.segments:
        print("❌ 无法获取字幕")
        print("   可能原因：")
        print("   1. 视频没有上传字幕")
        print("   2. Cookie 已过期或无效")
        print("   3. 需要登录才能获取字幕")
        return None

    video_id = video_url.split('/video/')[-1].split('/')[0].split('?')[0]
    last_segment_end = result.segments[-1].end
    total_duration_minutes = last_segment_end / 60

    print(f"✅ 字幕提取成功!")
    print(f"   视频ID: {video_id}")
    print(f"   字幕段数: {len(result.segments)}")
    print(f"   总时长: {total_duration_minutes:.1f} 分钟")

    os.makedirs(output_dir, exist_ok=True)

    transcript_data = {
        "video_url": video_url,
        "video_id": video_id,
        "duration": last_segment_end,
        "duration_minutes": total_duration_minutes,
        "segments": [
            {"start": s.start, "end": s.end, "text": s.text}
            for s in result.segments
        ]
    }

    output_file = os.path.join(output_dir, f'{video_id}_transcript_full.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(transcript_data, f, ensure_ascii=False, indent=2)

    print(f"   输出文件: {output_file}")
    return output_file

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python 01_extract_transcript.py <视频URL> [输出目录]")
        sys.exit(1)

    video_url = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None

    result = extract_transcript(video_url, output_dir)
    if result:
        print(f"\n字幕已保存到: {result}")
    else:
        print("\n⚠️ 字幕提取失败，请检查：")
        print("1. 视频是否有字幕（可手动上传）")
        print("2. B站 Cookie 是否配置（编辑 config/settings.json）")
        sys.exit(1)
