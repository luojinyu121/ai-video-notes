#!/usr/bin/env python3
"""
Step 2: Capture Frames → Embed into HTML（图文笔记截图嵌入）
解析 HTML 中的 {{SHOT:秒数}} 占位符 → yt-dlp 下载视频（h264≤720，复用 cookie）
→ ffmpeg 按该时间点后 1 秒截帧 → base64 内嵌回 HTML（<figure class="shot">），
图片不额外存储文件。

用法:
    python 02_capture_frames.py <视频URL> <HTML文件> [--width 960] [--jpeg] [--keep-video]
"""
import sys
import json
import os
import re
import time
import shutil
import base64
import subprocess
import tempfile

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

SHOT_PATTERN = re.compile(r"\{\{SHOT:(\d+)\}\}")


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


def _find_bin(names):
    """按常见路径 + PATH 查找可执行文件"""
    candidates = []
    for n in names:
        candidates.append(n)
        candidates.append(n + ".exe")
    for c in candidates:
        if os.path.exists(c):
            return c
        if shutil.which(c):
            return shutil.which(c)
    return None


def find_ytdlp():
    return _find_bin(["yt-dlp"]) or "yt-dlp"


def find_ffmpeg():
    return _find_bin(["ffmpeg"]) or "ffmpeg"


def find_ffprobe():
    return _find_bin(["ffprobe"]) or None


def _format_ts(total_seconds):
    total_seconds = max(int(total_seconds), 0)
    return f"{total_seconds // 3600:02d}:{(total_seconds % 3600) // 60:02d}:{total_seconds % 60:02d}"


def _write_cookie_file(cookie, tmpdir, bvid):
    """写 Netscape cookie 文件（复用 01b 格式）"""
    path = os.path.join(tmpdir, f".cookies_{bvid}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write("# Netscape HTTP Cookie File\n")
        f.write(f".bilibili.com\tTRUE\t/\tFALSE\t1799999999\tSESSDATA\t{cookie}\n")
    return path


def download_video(video_url, tmpdir, cookie, timeout=600):
    """yt-dlp 下载纯视频流（h264≤720 优先），返回本地视频路径；失败返回 None"""
    print("📥 正在下载视频（仅视频流，h264≤720）...")
    ytdlp = find_ytdlp()
    cookie_file = _write_cookie_file(cookie, tmpdir, "bili")
    out_tmpl = os.path.join(tmpdir, "video.%(ext)s")

    fmt = (
        "bv*[height<=720][vcodec!=av01][vcodec!=hvc1]/"
        "bv*[vcodec!=av01][vcodec!=hvc1]/"
        "b[height<=720]/"
        "b"
    )
    cmd = [
        ytdlp,
        video_url,
        "-f", fmt,
        "-o", out_tmpl,
        "--no-playlist",
        "--no-progress",
        "--cookies", cookie_file,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        print("   ❌ 视频下载超时（10分钟）")
        return None
    except Exception as e:
        print(f"   ❌ 视频下载异常: {e}")
        return None

    if result.returncode != 0:
        print(f"   ⚠️ yt-dlp 警告: {result.stderr[-500:] if result.stderr else 'unknown'}")
    # yt-dlp 可能产出 mp4/m4s/webm 等扩展名
    for name in os.listdir(tmpdir):
        if name.startswith("video.") and not name.endswith(".txt"):
            return os.path.join(tmpdir, name)
    return None


def probe_duration(video_path):
    """返回视频时长（秒），失败返回 None"""
    ffprobe = find_ffprobe()
    if ffprobe:
        try:
            r = subprocess.run(
                [ffprobe, "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", video_path],
                capture_output=True, text=True, timeout=60,
            )
            dur = float(r.stdout.strip())
            if dur > 0:
                return dur
        except Exception:
            pass
    try:
        ffmpeg = find_ffmpeg()
        r = subprocess.run([ffmpeg, "-i", video_path], capture_output=True,
                           text=True, timeout=60)
        m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.?\d*)", r.stderr)
        if m:
            return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    except Exception:
        pass
    return None


def capture_frame(video_path, seek_sec, tmpdir, width, image_format):
    """ffmpeg 截一帧，返回 PNG/JPEG 文件路径；失败返回 None"""
    ffmpeg = find_ffmpeg()
    ext = "jpg" if image_format == "jpeg" else "png"
    out_path = os.path.join(tmpdir, f"frame_{int(seek_sec)}.{ext}")
    cmd = [ffmpeg, "-y", "-ss", str(seek_sec), "-i", video_path,
           "-frames:v", "1", "-vf", f"scale=min({width}\\,iw):-2"]
    if image_format == "jpeg":
        cmd += ["-q:v", "3"]
    cmd.append(out_path)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        if r.returncode == 0 and os.path.exists(out_path) and os.path.getsize(out_path) > 0:
            return out_path
    except Exception as e:
        print(f"   ⚠️ 截帧异常: {e}")
    return None


def build_figure(seconds, b64, image_format):
    ts = _format_ts(seconds)
    mime = "image/jpeg" if image_format == "jpeg" else "image/png"
    return (
        f'\n<figure class="shot">\n'
        f'<img src="data:{mime};base64,{b64}" alt="关键画面 @ {ts}">\n'
        f'<figcaption>⏱️ {ts} 关键画面</figcaption>\n'
        f'</figure>\n'
    )


def embed_shots(video_url, html_path, width=960, image_format="png", keep_video=False):
    """主流程：解析占位符 → 下载 → 截帧 → base64 替换 → 写回"""
    if not os.path.exists(html_path):
        print(f"❌ HTML 文件不存在: {html_path}")
        return 1
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    seconds = sorted({int(s) for s in SHOT_PATTERN.findall(html)})
    if not seconds:
        print("ℹ️ 未发现 {{SHOT:秒数}} 占位符，跳过截图嵌入")
        return 0

    print(f"🎬 检测到 {len(seconds)} 个截图占位符: {seconds}")

    config = load_config()
    cookie = config.get("bilibili_cookie", "")
    tmpdir = tempfile.mkdtemp(prefix="bili_shots_")
    t0 = time.time()
    video_path = None

    try:
        video_path = download_video(video_url, tmpdir, cookie)
        if not video_path:
            print("❌ 视频下载失败，无法截图")
            return 1

        duration = probe_duration(video_path)
        if duration:
            print(f"   📺 视频时长 {duration:.0f}s")
        size_mb = os.path.getsize(video_path) / 1024 / 1024
        print(f"   ✅ 视频下载完成: {size_mb:.1f} MB（{time.time() - t0:.0f}s）")

        base64_map = {}
        for s in seconds:
            # 占位符秒数即精确截图点（AI 已按场景末句 3/4 处算好），只需 clamp 到视频范围内
            if duration:
                seek = max(0, min(s, int(duration) - 2))
            else:
                seek = max(0, s)
            frame = capture_frame(video_path, seek, tmpdir, width, image_format)
            if frame:
                with open(frame, "rb") as fh:
                    base64_map[s] = base64.b64encode(fh.read()).decode("ascii")
            else:
                base64_map[s] = None
                print(f"   ⚠️ 时间点 {_format_ts(s)} 截帧失败")

        def _replace(m):
            s = int(m.group(1))
            b64 = base64_map.get(s)
            if not b64:
                print(f"   ⚠️ {_format_ts(s)} 截图缺失，已跳过")
                return ""
            return build_figure(s, b64, image_format)

        new_html = SHOT_PATTERN.sub(_replace, html)
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(new_html)

        ok = [s for s in seconds if base64_map.get(s)]
        fail = [s for s in seconds if not base64_map.get(s)]
        total_kb = sum(len(base64_map[s]) for s in ok) / 1024 if ok else 0
        print(f"\n✅ 截图嵌入完成: 成功 {len(ok)} 张, 失败 {len(fail)} 张")
        print(f"   总 base64 大小: {total_kb:.0f} KB, 耗时 {time.time() - t0:.0f}s")
        for s in ok:
            kb = len(base64_map[s]) / 1024
            print(f"   - {_format_ts(s)}: {kb:.0f} KB")
        if fail:
            print("   ⚠️ 失败的占位符已替换为空，请检查对应章节")
        return 0
    finally:
        if keep_video and video_path and os.path.exists(video_path):
            print(f"   📁 保留视频文件: {video_path}")
        else:
            shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python 02_capture_frames.py <视频URL> <HTML文件> [--width 960] [--jpeg] [--keep-video]")
        sys.exit(1)

    video_url = sys.argv[1]
    html_path = sys.argv[2]
    width = 960
    image_format = "png"
    keep_video = False
    for i, arg in enumerate(sys.argv[3:], start=3):
        if arg == "--width" and i + 1 < len(sys.argv):
            width = int(sys.argv[i + 1])
        elif arg == "--jpeg":
            image_format = "jpeg"
        elif arg == "--keep-video":
            keep_video = True

    sys.exit(embed_shots(video_url, html_path, width=width,
                         image_format=image_format, keep_video=keep_video))
