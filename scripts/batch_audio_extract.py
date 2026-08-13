#!/usr/bin/env python3
"""
批量音频降级转录脚本（修复分集文件名冲突）
对指定分集下载音频 + faster-whisper 转录 -> {bvid}_p{N}_transcript_full.json
"""
import sys
import json
import os
import re
import subprocess
import shutil
import time


def load_config():
    config_paths = [
        os.path.join(os.path.dirname(__file__), '..', 'config', 'settings.json'),
        os.path.join(os.path.dirname(__file__), 'config', 'settings.json'),
    ]
    for path in config_paths:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
    return {}


def get_video_info(bvid, page_num):
    import urllib.request
    config = load_config()
    cookie = config.get('bilibili_cookie', '')
    url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Referer": "https://www.bilibili.com",
    }
    if cookie:
        headers["Cookie"] = f"SESSDATA={cookie}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
    if data.get("code") != 0:
        raise RuntimeError(f"API error: {data.get('message')}")
    d = data["data"]
    pages = d.get("pages", [])
    if page_num > len(pages):
        raise RuntimeError(f"page {page_num} > total {len(pages)}")
    p_info = pages[page_num - 1]
    return {
        "title": d.get("title", ""),
        "author": d.get("owner", {}).get("name", ""),
        "duration": p_info.get("duration", 0),
        "bvid": bvid,
        "cid": p_info.get("cid", 0),
        "page": page_num,
        "part_name": p_info.get("part", ""),
    }


def _bili_headers():
    config = load_config()
    cookie = config.get('bilibili_cookie', '')
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.bilibili.com",
        "Accept": "*/*",
        "Accept-Language": "zh-CN,zh;q=0.9",
    }
    if cookie:
        headers["Cookie"] = f"SESSDATA={cookie}; buvid3=D5496C12-851D-31FE-878C-D7E830B6E63913565infoc"
    return headers


def _get_buvid3():
    """获取 buvid3 用于反爬"""
    try:
        import urllib.request
        req = urllib.request.Request("https://api.bilibili.com/x/frontend/finger/spi",
                                     headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            d = json.loads(resp.read())
        if d.get("code") == 0:
            return d["data"]["b_3"]
    except Exception:
        pass
    return "D5496C12-851D-31FE-878C-D7E830B6E63913565infoc"


def _get_playurl_durl(bvid, cid, page_num, headers, max_attempts=5):
    """调用 playurl API 获取渐进式 MP4 durl（非分片，可完整解码）。失败则回退 DASH。带重试。"""
    import urllib.request
    import time as _t
    last_err = None
    for attempt in range(max_attempts):
        try:
            api_url = f"https://api.bilibili.com/x/player/playurl?bvid={bvid}&cid={cid}&qn=32&fnval=0&platform=pc"
            req = urllib.request.Request(api_url, headers=headers)
            with urllib.request.urlopen(req, timeout=20) as resp:
                pdata = json.loads(resp.read())
            if pdata.get("code") == 0 and pdata["data"].get("durl"):
                u = pdata["data"]["durl"][0]
                return {
                    "url": u["url"],
                    "backup_urls": u.get("backup_url", []),
                    "size": u.get("size", 0),
                    "fmt": "mp4",
                }
            # 回退 DASH
            api_url2 = f"https://api.bilibili.com/x/player/playurl?bvid={bvid}&cid={cid}&qn=16&fnval=16&fnver=0&platform=pc"
            req2 = urllib.request.Request(api_url2, headers=headers)
            with urllib.request.urlopen(req2, timeout=20) as resp2:
                pdata2 = json.loads(resp2.read())
            if pdata2.get("code") == 0 and pdata2["data"].get("dash"):
                audio = pdata2["data"]["dash"]["audio"]
                audio.sort(key=lambda a: a.get("bandwidth", 0), reverse=True)
                return {
                    "url": audio[0]["baseUrl"],
                    "backup_urls": audio[0].get("backupUrl", []),
                    "size": 0,
                    "fmt": "m4s",
                }
            last_err = f"API code: {pdata.get('message') or pdata2.get('message')}"
        except Exception as e:
            last_err = str(e)
            print(f"   [p{page_num}] playurl API attempt {attempt+1} failed: {e}")
        _t.sleep(2)
    raise RuntimeError(f"playurl API failed after {max_attempts} attempts: {last_err}")


def _curl_download(url, dest, expected_size, page_num, max_attempts=10):
    """用 curl 下载，带 retry + resume(-C -)，校验大小。处理 B站 连接重置。"""
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    for attempt in range(max_attempts):
        cmd = [
            "curl", "-sS", "--retry", "5", "--retry-delay", "3", "--retry-all-errors",
            "-C", "-",  # resume
            "-H", f"Referer: https://www.bilibili.com",
            "-H", f"User-Agent: {ua}",
            "-o", dest, url,
        ]
        try:
            subprocess.run(cmd, timeout=300, check=False)
        except subprocess.TimeoutExpired:
            print(f"   [p{page_num}] curl timeout (attempt {attempt+1})")
        size = os.path.getsize(dest) if os.path.exists(dest) else 0
        if expected_size and size >= expected_size:
            return True
        if not expected_size and size > 1000:
            # 无预期大小（DASH），至少有数据且 curl 无错误则接受；再尝试校验时长
            return True
        print(f"   [p{page_num}] partial: {size}/{expected_size or '?'} (attempt {attempt+1}), resuming...")
    return False


def download_audio(bvid, page_num, cid, output_dir):
    """通过 playurl API 获取渐进式 MP4 + curl 断点续传下载（解决连接重置导致的截断）"""
    os.makedirs(output_dir, exist_ok=True)
    audio_path = os.path.join(output_dir, f"{bvid}_p{page_num}_audio.mp4")
    if os.path.exists(audio_path) and os.path.getsize(audio_path) > 1000:
        print(f"   [p{page_num}] audio cached: {os.path.getsize(audio_path)/1024/1024:.1f} MB")
        return audio_path

    import urllib.request
    config = load_config()
    cookie = config.get('bilibili_cookie', '')
    buvid3 = _get_buvid3()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": f"https://www.bilibili.com/video/{bvid}/?p={page_num}",
    }
    if cookie:
        headers["Cookie"] = f"SESSDATA={cookie}; buvid3={buvid3}"

    info = _get_playurl_durl(bvid, cid, page_num, headers)
    urls_to_try = [info["url"]] + info["backup_urls"]
    for url in urls_to_try:
        if _curl_download(url, audio_path, info["size"], page_num):
            size = os.path.getsize(audio_path)
            print(f"   [p{page_num}] audio downloaded: {size/1024/1024:.1f} MB ({info['fmt']})")
            return audio_path
        print(f"   [p{page_num}] trying backup url...")
    print(f"   [p{page_num}] audio download FAILED (all urls)")
    return None


def convert_to_wav(audio_path, page_num):
    """将下载的 .m4s/.m4a 转为 16kHz 单声道 WAV，确保 faster-whisper 能完整解码"""
    wav_path = audio_path.rsplit('.', 1)[0] + '.wav'
    if os.path.exists(wav_path) and os.path.getsize(wav_path) > 1000:
        return wav_path
    cmd = [
        "ffmpeg", "-y", "-i", audio_path,
        "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le",
        "-nostdin", "-nostats", "-loglevel", "error",
        wav_path,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            print(f"   [p{page_num}] ffmpeg warn: {result.stderr[-200:] if result.stderr else 'unknown'}")
        if os.path.exists(wav_path) and os.path.getsize(wav_path) > 1000:
            print(f"   [p{page_num}] converted to WAV: {os.path.getsize(wav_path)/1024/1024:.1f} MB")
            return wav_path
        print(f"   [p{page_num}] ffmpeg conversion FAILED")
        return None
    except Exception as e:
        print(f"   [p{page_num}] ffmpeg error: {e}")
        return None


def transcribe(audio_path, video_info):
    from faster_whisper import WhisperModel
    if not os.environ.get("HF_ENDPOINT"):
        os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
    cpu_threads = int(os.environ.get("CPU_THREADS", "0") or "0")
    model_size = os.environ.get("WHISPER_MODEL", "small")
    kwargs = {"device": "cpu", "compute_type": "int8"}
    if cpu_threads > 0:
        kwargs["cpu_threads"] = cpu_threads
    print(f"   [p{video_info['page']}] whisper {model_size} threads={cpu_threads or 'auto'}")
    model = WhisperModel(model_size, **kwargs)
    t0 = time.time()
    segments_raw, info = model.transcribe(
        audio_path, beam_size=5, vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500),
    )
    print(f"   [p{video_info['page']}] lang={info.language} ({info.language_probability:.2f})")
    segs = []
    for seg in segments_raw:
        text = seg.text.strip()
        if text:
            segs.append({"start": round(seg.start, 3), "end": round(seg.end, 3), "text": text})
    elapsed = time.time() - t0
    print(f"   [p{video_info['page']}] transcribed {len(segs)} segs in {elapsed/60:.1f} min")
    return segs


def process_episode(bvid, page_num, output_dir):
    video_url = f"https://www.bilibili.com/video/{bvid}/?p={page_num}"
    print(f"\n=== Episode p{page_num} ===")
    info = get_video_info(bvid, page_num)
    print(f"   title: {info['part_name']} ({info['duration']//60}m{info['duration']%60}s)")
    audio = download_audio(bvid, page_num, info["cid"], output_dir)
    if not audio:
        return None
    wav = convert_to_wav(audio, page_num)
    if not wav:
        return None
    segs = transcribe(wav, info)
    if not segs:
        return None
    # 覆盖率校验：转录应覆盖视频时长的 60% 以上，否则判为不完整
    last_end = segs[-1]["end"] if segs else 0
    expected = info.get("duration", 0)
    if expected > 0 and last_end < expected * 0.6:
        print(f"   [p{page_num}] WARN: coverage {last_end:.0f}s / {expected}s < 60%, transcript may be incomplete")
    last_end = segs[-1]["end"] if segs else 0
    out = {
        "video_url": video_url,
        "video_id": bvid,
        "page": page_num,
        "cid": info["cid"],
        "title": info["title"],
        "part_name": info["part_name"],
        "author": info["author"],
        "duration": round(last_end, 1),
        "duration_minutes": round(last_end / 60, 1),
        "source": "whisper_transcription",
        "segments": segs,
    }
    out_file = os.path.join(output_dir, f"{bvid}_p{page_num}_transcript_full.json")
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"   [p{page_num}] saved: {out_file} ({len(segs)} segs, {last_end/60:.1f} min)")
    return out_file


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("用法: python batch_audio_extract.py <BV> <output_dir> <page1> [page2 ...]")
        sys.exit(1)
    bvid = sys.argv[1]
    output_dir = sys.argv[2]
    pages = [int(p) for p in sys.argv[3:]]
    for p in pages:
        try:
            process_episode(bvid, p, output_dir)
        except Exception as e:
            print(f"   [p{p}] ERROR: {e}")
            import traceback; traceback.print_exc()
