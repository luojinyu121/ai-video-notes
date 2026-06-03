#!/usr/bin/env python3
"""
Step 1b: Audio Fallback Transcript Extraction
当 B站视频无字幕时，自动下载音频并通过 Whisper 转文字
"""

import sys
import json
import os
import re
import subprocess
import tempfile
import shutil
import time


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


def extract_bvid(video_url):
    """从 URL 提取 BV 号"""
    match = re.search(r'BV[a-zA-Z0-9]+', video_url)
    return match.group(0) if match else None


def get_video_info(video_url):
    """通过 B站 API 获取视频信息（支持 p= 分集参数）"""
    import urllib.request
    import urllib.error

    bvid = extract_bvid(video_url)
    if not bvid:
        return None

    # 提取分集编号
    page_match = re.search(r'[?&]p=(\d+)', video_url)
    page_num = int(page_match.group(1)) if page_match else 1

    config = load_config()
    cookie = config.get('bilibili_cookie', '')

    url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Referer": "https://www.bilibili.com",
    }
    if cookie:
        headers["Cookie"] = f"SESSDATA={cookie}"

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            if data.get("code") == 0:
                d = data["data"]
                pages = d.get("pages", [])

                # 获取指定分集的信息
                if pages and page_num <= len(pages):
                    p_info = pages[page_num - 1]
                    return {
                        "title": d.get("title", ""),
                        "author": d.get("owner", {}).get("name", ""),
                        "duration": p_info.get("duration", d.get("duration", 0)),
                        "bvid": bvid,
                        "cid": p_info.get("cid", d.get("cid", 0)),
                        "page": page_num,
                        "total_pages": len(pages),
                        "part_name": p_info.get("part", ""),
                    }

                return {
                    "title": d.get("title", ""),
                    "author": d.get("owner", {}).get("name", ""),
                    "duration": d.get("duration", 0),
                    "bvid": bvid,
                    "cid": d.get("cid", 0),
                }
    except Exception as e:
        print(f"   ⚠️ 获取视频信息失败: {e}")

    return {"bvid": bvid, "title": "", "author": "", "duration": 0, "cid": 0}


def _find_ytdlp():
    """查找 yt-dlp 二进制路径"""
    # 常见路径
    candidates = [
        os.path.expandvars(r"D:\luojingyu\Scripts\yt-dlp.exe"),
        os.path.expandvars(r"D:\luojingyu\Scripts\yt-dlp"),
        "yt-dlp",
        "yt-dlp.exe",
    ]
    for c in candidates:
        if shutil.which(c) or os.path.exists(c):
            return c if os.path.exists(c) else shutil.which(c)
    # 最终尝试直接用 yt-dlp
    return "yt-dlp"


def download_audio(video_url, output_dir):
    """使用 yt-dlp 下载纯音频"""
    print(f"📥 正在下载音频...")

    bvid = extract_bvid(video_url)
    if not bvid:
        print("❌ 无法解析 BV 号")
        return None

    os.makedirs(output_dir, exist_ok=True)
    audio_path = os.path.join(output_dir, f"{bvid}_audio.m4a")

    # 如果已存在则跳过下载
    if os.path.exists(audio_path) and os.path.getsize(audio_path) > 1000:
        print(f"   ✅ 音频已缓存: {audio_path}")
        print(f"      大小: {os.path.getsize(audio_path) / 1024 / 1024:.1f} MB")
        return audio_path

    cookie_file = None
    config = load_config()
    cookie = config.get('bilibili_cookie', '')
    if cookie:
        cookie_file = os.path.join(output_dir, f".cookies_{bvid}.txt")
        with open(cookie_file, 'w', encoding='utf-8') as f:
            f.write("# Netscape HTTP Cookie File\n")
            f.write(f".bilibili.com\tTRUE\t/\tFALSE\t1799999999\tSESSDATA\t{cookie}\n")

    ytdlp = _find_ytdlp()
    cmd = [
        ytdlp,
        video_url,
        "-f", "bestaudio[ext=m4a]/bestaudio/best",
        "-o", audio_path,
        "--no-playlist",
        "--no-progress",
        "--extract-audio",
        "--audio-format", "m4a",
    ]

    if cookie_file:
        cmd.extend(["--cookies", cookie_file])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            print(f"   ⚠️ yt-dlp 警告: {result.stderr[-300:] if result.stderr else 'unknown'}")

        if os.path.exists(audio_path) and os.path.getsize(audio_path) > 1000:
            size_mb = os.path.getsize(audio_path) / 1024 / 1024
            print(f"   ✅ 音频下载完成: {size_mb:.1f} MB")
            return audio_path
        else:
            # 检查是否生成了其他扩展名的音频文件
            for ext in ['.m4a', '.mp4', '.webm', '.aac', '.mp3', '.opus']:
                alt_path = audio_path.replace('.m4a', ext)
                if os.path.exists(alt_path) and os.path.getsize(alt_path) > 1000:
                    print(f"   ✅ 音频下载完成: {os.path.getsize(alt_path) / 1024 / 1024:.1f} MB (格式: {ext})")
                    return alt_path

            print(f"❌ 音频下载失败")
            if result.stderr:
                print(f"   错误: {result.stderr[-500:]}")
            return None
    except subprocess.TimeoutExpired:
        print(f"❌ 音频下载超时（10分钟）")
        return None
    except Exception as e:
        print(f"❌ 音频下载异常: {e}")
        return None
    finally:
        if cookie_file and os.path.exists(cookie_file):
            os.remove(cookie_file)


def transcribe_with_whisper(audio_path, video_info):
    """使用 faster-whisper 将音频转为文字"""
    print(f"🎙️ 正在语音转文字（Whisper small 模型）...")

    total_duration = video_info.get("duration", 0)
    if total_duration > 0:
        est_time = total_duration * 0.15  # ~15% of video length on CPU
        print(f"   预计耗时: {est_time / 60:.0f} 分 {est_time % 60:.0f} 秒")

    try:
        from faster_whisper import WhisperModel

        # 国内网络设置 HF 镜像
        if not os.environ.get("HF_ENDPOINT"):
            os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

        # 用 small 模型（平衡速度和准确度）
        model_size = "small"
        model = WhisperModel(model_size, device="cpu", compute_type="int8")

        t_start = time.time()
        segments_raw, info = model.transcribe(
            audio_path,
            beam_size=5,
            vad_filter=True,
            vad_parameters=dict(
                min_silence_duration_ms=500,
            ),
        )

        print(f"   检测语言: {info.language} (概率: {info.language_probability:.2f})")

        segments = []
        for seg in segments_raw:
            text = seg.text.strip()
            if text:
                segments.append({
                    "start": round(seg.start, 3),
                    "end": round(seg.end, 3),
                    "text": text,
                })

        elapsed = time.time() - t_start
        print(f"   ✅ 转录完成！{len(segments)} 段，耗时 {elapsed / 60:.1f} 分钟")

        if len(segments) < 5:
            print(f"   ⚠️ 转录段数异常少，可能音频有问题")

        return segments

    except ImportError:
        print(f"❌ 未安装 faster-whisper，请运行: pip install faster-whisper")
        return None
    except Exception as e:
        print(f"❌ 语音转录失败: {e}")
        # 尝试用 OpenAI API 作为降级方案
        print(f"   尝试 OpenAI Whisper API 降级方案...")
        return transcribe_with_openai_api(audio_path, video_info)


def transcribe_with_openai_api(audio_path, video_info):
    """使用 OpenAI Whisper API 转录（降级方案）"""
    try:
        from openai import OpenAI

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            print("   ❌ 未设置 OPENAI_API_KEY 环境变量")
            return None

        client = OpenAI(api_key=api_key)
        file_size = os.path.getsize(audio_path)
        print(f"   音频大小: {file_size / 1024 / 1024:.1f} MB")

        with open(audio_path, "rb") as f:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                response_format="verbose_json",
            )

        segments = []
        for seg in transcript.segments:
            text = seg.get("text", "").strip()
            if text:
                segments.append({
                    "start": round(seg.get("start", 0), 3),
                    "end": round(seg.get("end", 0), 3),
                    "text": text,
                })

        print(f"   ✅ OpenAI API 转录完成: {len(segments)} 段")
        return segments

    except ImportError:
        print("   ❌ 未安装 openai 包")
        return None
    except Exception as e:
        print(f"   ❌ OpenAI API 转录失败: {e}")
        return None


def extract_audio_transcript(video_url, output_dir=None):
    """
    主函数：下载音频 + 语音转文字 → 输出标准转录 JSON
    返回: transcript JSON 文件路径，失败返回 None
    """
    config = load_config()
    output_dir = output_dir or config.get('output_dir', './output')
    os.makedirs(output_dir, exist_ok=True)

    bvid = extract_bvid(video_url)
    if not bvid:
        print("❌ 无法从 URL 提取 BV 号")
        return None

    print(f"🎬 音频降级方案: {video_url}")
    print(f"   BV: {bvid}")

    # 1. 获取视频信息
    video_info = get_video_info(video_url) or {"bvid": bvid, "title": "", "author": "", "duration": 0, "cid": 0}
    if video_info.get("title"):
        print(f"   标题: {video_info['title']}")
    if video_info.get("duration", 0) > 0:
        print(f"   时长: {video_info['duration'] // 60} 分 {video_info['duration'] % 60} 秒")

    # 2. 下载音频
    audio_path = download_audio(video_url, output_dir)
    if not audio_path:
        print("\n❌ 音频下载失败，整体降级方案失败")
        return None

    # 3. 语音转文字
    segments = transcribe_with_whisper(audio_path, video_info)
    if not segments:
        print("\n❌ 语音转文字失败，整体降级方案失败")
        return None

    # 4. 计算时长
    last_end = segments[-1]["end"] if segments else 0
    duration_minutes = last_end / 60

    # 5. 输出标准 JSON
    transcript_data = {
        "video_url": video_url,
        "video_id": bvid,
        "title": video_info.get("title", ""),
        "author": video_info.get("author", ""),
        "duration": round(last_end, 1),
        "duration_minutes": round(duration_minutes, 1),
        "source": "whisper_transcription",
        "segments": segments,
    }

    output_file = os.path.join(output_dir, f'{bvid}_transcript_full.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(transcript_data, f, ensure_ascii=False, indent=2)

    print(f"   ✅ 音频降级转录完成!")
    print(f"   输出文件: {output_file}")
    print(f"   字幕段数: {len(segments)}")
    print(f"   总时长: {duration_minutes:.1f} 分钟")

    # 清理音频文件（可选，保留以便复用）
    # os.remove(audio_path)

    return output_file


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python 01b_audio_fallback.py <视频URL> [输出目录]")
        sys.exit(1)

    video_url = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None

    result = extract_audio_transcript(video_url, output_dir)
    if result:
        print(f"\n✅ 转录文件: {result}")
    else:
        print(f"\n❌ 音频降级方案也失败了")
        sys.exit(1)
