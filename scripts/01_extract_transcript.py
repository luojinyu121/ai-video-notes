#!/usr/bin/env python3
"""
Step 1: Extract Transcript
从B站提取完整视频字幕（curl 版，支持分P + 覆盖度校验 + 自动重试）

用法:
    python 01_extract_transcript.py <视频URL> [输出目录]
"""
import sys
import os
import json
import re

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def load_config():
    """加载配置文件（优先找 skill 目录下的 config/settings.json）"""
    config_paths = [
        os.path.join(os.path.dirname(__file__), "..", "config", "settings.json"),
        os.path.join(os.path.dirname(__file__), "..", "..", "config", "settings.json"),
    ]
    for path in config_paths:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    return {}


def resolve_output_dir(output_dir_arg):
    """解析输出目录：命令行参数 > config.output_dir > 默认 ./output"""
    if output_dir_arg:
        return os.path.abspath(output_dir_arg)
    config = load_config()
    configured = config.get("output_dir")
    if configured:
        return os.path.abspath(configured)
    return os.path.abspath(os.path.join(os.getcwd(), "output"))


def _call_audio_fallback(video_url, output_dir, config):
    """调用音频降级方案脚本（仅当用户明确要求时）"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    fallback_script = os.path.join(script_dir, "01b_audio_fallback.py")
    if not os.path.exists(fallback_script):
        print("   ⚠️ 音频降级脚本不存在")
        return None

    import subprocess
    python_exe = os.path.expandvars(
        r"C:\Users\PC\AppData\Local\Programs\Python\Python313\python.exe"
    )
    if not os.path.exists(python_exe):
        python_exe = sys.executable

    cmd = [python_exe, fallback_script, video_url, output_dir]
    print(f"   🔧 使用: {python_exe}")
    result = subprocess.run(cmd, cwd=os.getcwd())
    if result.returncode != 0:
        return None

    import re
    bvid_match = re.search(r"BV[a-zA-Z0-9]+", video_url)
    if bvid_match:
        bvid = bvid_match.group(0)
        json_path = os.path.join(output_dir, f"{bvid}_transcript_full.json")
        if os.path.exists(json_path):
            return json_path
    return None


def extract_transcript(video_url, output_dir=None):
    """提取字幕主函数，返回 JSON 文件路径"""
    config = load_config()
    output_dir = resolve_output_dir(output_dir)
    cookie = config.get("bilibili_cookie", "")

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "downloaders"))
    from bilibili_downloader import BilibiliDownloader

    downloader = BilibiliDownloader(cookie=cookie)

    import re
    bvid = downloader.extract_bvid(video_url)
    page = downloader.extract_page_param(video_url)

    # 显示分集信息
    try:
        info = downloader.get_video_info(bvid)
        pages = (info or {}).get("data", {}).get("pages", [])
        if page <= len(pages):
            p_info = pages[page - 1]
            part_name = p_info.get("part", "")
            duration = p_info.get("duration", 0)
            print(f"📺 第{page}集: {part_name} ({duration//60}:{duration%60:02d})")
    except Exception:
        pass

    print(f"🎬 正在提取字幕...")
    print(f"   视频: {video_url}")
    print(f"   输出目录: {output_dir}")

    result = downloader.download_subtitles(video_url)

    if not result or not result.segments:
        print("❌ 无法获取字幕")
        print("   可能原因：")
        print("   1. 视频没有上传字幕")
        print("   2. Cookie 已过期或无效")
        print("   3. 需要登录才能获取字幕")
        print("")
        print("🔊 可启动音频降级方案（下载音频 + Whisper 转文字）")
        print("   ⚠️ 必须先征得用户同意再执行！")
        return None

    os.makedirs(output_dir, exist_ok=True)
    transcript_data = {
        "video_url": video_url,
        "video_id": bvid,
        "page": page,
        "duration": result.duration,
        "duration_minutes": result.duration / 60,
        "source": result.source,
        "segments": [
            {"start": s.start, "end": s.end, "text": s.text}
            for s in result.segments
        ],
    }
    # URL 带 ?p= 参数（即使 p=1）→ 用 {bvid}_p{page}_transcript_full.json；
    # 无 ?p= 参数（真正单集）→ 用 {bvid}_transcript_full.json
    if re.search(r"[?&]p=\d+", video_url):
        output_file = os.path.join(output_dir, f"{bvid}_p{page}_transcript_full.json")
    else:
        output_file = os.path.join(output_dir, f"{bvid}_transcript_full.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(transcript_data, f, ensure_ascii=False, indent=2)

    print(f"✅ 字幕提取成功!")
    print(f"   视频ID: {bvid}")
    print(f"   字幕段数: {len(result.segments)}")
    print(f"   总时长: {result.duration / 60:.1f} 分钟")
    print(f"   输出文件: {output_file}")
    return output_file


if __name__ == "__main__":
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
