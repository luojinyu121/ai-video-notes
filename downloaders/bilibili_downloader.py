#!/usr/bin/env python3
"""
Bilibili Subtitle Downloader
Standalone module - 不依赖 BiliNote backend
支持分P视频 + AI自动字幕

⚠️ 关键设计（踩坑后修复）：
1. 所有 B站 API 调用走 curl subprocess（Python requests/urllib 会被 412 拦截）
2. 字幕 URL 的 auth_key 有时限（几分钟过期 → 403/空内容），每次下载前必须重新调 player API 刷新
3. 下载后校验字幕覆盖度：最后一段 end 时间 vs 视频 duration（80%~130% 为合格），不合格自动重试
4. 分P视频按 ?p=N 选取对应 CID 和字幕，防止拿到错集字幕
"""

import re
import os
import sys
import json
import time
import subprocess

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


class SubtitleSegment:
    def __init__(self, start, end, text):
        self.start = start
        self.end = end
        self.text = text


class SubtitleResult:
    def __init__(self, segments=None, source="subtitle"):
        self.segments = segments or []
        self.source = source

    @property
    def duration(self):
        """字幕覆盖的最终时间（秒）"""
        if not self.segments:
            return 0
        return self.segments[-1].end


class BilibiliDownloader:
    """B站字幕下载器（curl 版，支持分P + 自动重试）"""

    def __init__(self, cookie=None, curl_bin="curl"):
        self.cookie = cookie or ""
        self.curl_bin = curl_bin
        self._base_headers = [
            "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Referer: https://www.bilibili.com",
            "Accept: application/json, text/plain, */*",
        ]
        if self.cookie:
            self._base_headers.append(f"Cookie: SESSDATA={self.cookie}")

    # ---------- HTTP 基础（curl subprocess，避开 412） ----------

    def _curl_get(self, url, timeout=15):
        """用 curl 发起 GET 请求，返回 (status_code, text)。失败返回 (None, None)。"""
        cmd = [self.curl_bin, "-s", "-L", "--max-time", str(timeout),
               "-H", self._base_headers[0],
               "-H", self._base_headers[1],
               "-H", self._base_headers[2]]
        for h in self._base_headers[3:]:
            cmd += ["-H", h]
        cmd.append(url)
        try:
            proc = subprocess.run(cmd, capture_output=True, timeout=timeout + 5)
            text = proc.stdout.decode("utf-8", errors="replace")
            return (proc.returncode, text)
        except Exception as e:
            print(f"   ⚠️ curl 请求失败: {type(e).__name__}: {e}")
            return (None, None)

    def _curl_get_json(self, url, timeout=15):
        """curl GET + 解析 JSON，失败返回 None"""
        code, text = self._curl_get(url, timeout=timeout)
        if not text:
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None

    # ---------- 视频信息 ----------

    def extract_bvid(self, url):
        m = re.search(r"BV[a-zA-Z0-9]+", url)
        return m.group(0) if m else None

    def extract_page_param(self, url):
        m = re.search(r"[?&]p=(\d+)", url)
        return int(m.group(1)) if m else 1

    def get_video_info(self, bvid):
        """view API 原始返回"""
        url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
        return self._curl_get_json(url)

    def get_cid_by_url(self, video_url, bvid):
        """按 URL 的 ?p=N 选取对应 CID；无分P取主 CID"""
        page = self.extract_page_param(video_url)
        data = self.get_video_info(bvid)
        if not data or data.get("code") != 0:
            return None
        pages = data.get("data", {}).get("pages", [])
        if not pages:
            return data.get("data", {}).get("cid")
        if page <= len(pages):
            return pages[page - 1].get("cid")
        return pages[0].get("cid")

    def get_cid(self, bvid):
        return self.get_cid_by_url(f"https://www.bilibili.com/video/{bvid}", bvid)

    # ---------- 字幕 ----------

    def _list_subtitles(self, bvid, cid):
        """
        调 player 接口获取字幕列表。
        ⚠️ 关键：wbi/v2 接口对部分视频会返回空字幕（即使视频有字幕），
        此时必须回退到无签名的 player/v2 再试一次，否则会漏掉字幕。
        """
        # 先试带 wbi 签名
        signed = self._wbi_sign({"bvid": bvid, "cid": cid})
        url = f"https://api.bilibili.com/x/player/wbi/v2?{signed}"
        data = self._curl_get_json(url)
        if data and data.get("code") == 0:
            subs = data.get("data", {}).get("subtitle", {}).get("subtitles", [])
            if subs:
                return subs
            # wbi 返回空 → 回退到无签名老接口（部分视频只有老接口能拿到字幕）
        url = f"https://api.bilibili.com/x/player/v2?bvid={bvid}&cid={cid}"
        data = self._curl_get_json(url)
        if data and data.get("code") == 0:
            subs = data.get("data", {}).get("subtitle", {}).get("subtitles", [])
            if subs:
                return subs
        return []

    def _list_subtitles_with_retry(self, bvid, cid, retries=3):
        for i in range(retries):
            subs = self._list_subtitles(bvid, cid)
            if subs:
                return subs
            if i < retries - 1:
                time.sleep(1.5)
        return []

    def pick_subtitle(self, subtitles):
        """选择字幕轨（优先级：人工中文 > AI中文 > 任意）"""
        if not subtitles:
            return None

        def is_zh(s):
            lan = (s.get("lan") or "").lower()
            return lan.startswith("zh") or lan == "ai-zh"

        for s in subtitles:
            if is_zh(s) and not s.get("ai_type"):
                return s
        for s in subtitles:
            if is_zh(s):
                return s
        return subtitles[0] if subtitles else None

    def _fetch_body(self, subtitle_url):
        """下载字幕 JSON body，失败返回 None"""
        if not subtitle_url:
            return None
        if subtitle_url.startswith("//"):
            subtitle_url = "https:" + subtitle_url
        data = self._curl_get_json(subtitle_url, timeout=20)
        if data:
            return data.get("body") or []
        return None

    # ---------- wbi 签名 ----------

    def _wbi_sign(self, params):
        """wbi 签名；失败时返回未签名 query string（走回退）"""
        keys = self._fetch_wbi_keys()
        if not keys:
            return "&".join(f"{k}={params[k]}" for k in params)
        signed = dict(params)
        signed["wts"] = int(time.time())
        query_string = "&".join(f"{k}={signed[k]}" for k in sorted(signed.keys()))
        w_rid = _md5(query_string + keys["mix_key"])
        signed["w_rid"] = w_rid
        return "&".join(f"{k}={signed[k]}" for k in sorted(signed.keys()))

    def _fetch_wbi_keys(self):
        """从 nav 接口的 wbi_img 图片 URL 提取密钥对"""
        try:
            data = self._curl_get_json("https://api.bilibili.com/x/web-interface/nav")
            if data and data.get("code") == 0:
                wbi_img = data["data"]["wbi_img"]
                img_key = wbi_img["img_url"].split("/")[-1].split(".")[0]
                sub_key = wbi_img["sub_url"].split("/")[-1].split(".")[0]
                return {
                    "img_key": img_key,
                    "sub_key": sub_key,
                    "mix_key": img_key[:16] + sub_key[:16],
                }
        except Exception:
            pass
        return None

    # ---------- 主流程 ----------

    def download_subtitles(self, video_url, max_retries=4):
        """
        下载字幕。核心逻辑：
        1. 解析 BV + CID（按 ?p=N）
        2. 每次尝试都重新调 player 接口拿【新鲜】字幕 URL（auth_key 有时限）
        3. 下载 body → 校验覆盖度 → 不合格重试（可能是错集/过期数据）
        返回 SubtitleResult 或 None
        """
        bvid = self.extract_bvid(video_url)
        if not bvid:
            print(f"无法解析BV号: {video_url}")
            return None

        page = self.extract_page_param(video_url)
        cid = self.get_cid_by_url(video_url, bvid)
        if not cid:
            print("无法获取视频CID（可能 Cookie 无效或视频不存在）")
            return None

        duration = self._get_duration(bvid, page)
        subs = self._list_subtitles_with_retry(bvid, cid)
        if not subs:
            print("该视频没有可用字幕（player API 返回空字幕列表）")
            return None

        track = self.pick_subtitle(subs)
        if not track:
            print("无法选择字幕轨")
            return None

        # 每次下载前刷新 player 接口，保证 auth_key 新鲜
        for attempt in range(1, max_retries + 1):
            fresh_subs = self._list_subtitles_with_retry(bvid, cid)
            fresh_track = self.pick_subtitle(fresh_subs) if fresh_subs else track
            body = self._fetch_body(fresh_track.get("subtitle_url"))
            if not body:
                print(f"   ⚠️ 第{attempt}次：字幕内容为空/过期（auth_key 可能失效），重试...")
                time.sleep(2)
                continue

            segments = []
            for item in body:
                text = (item.get("content") or "").strip()
                if not text:
                    continue
                segments.append(SubtitleSegment(
                    start=float(item.get("from", 0)),
                    end=float(item.get("to", 0)),
                    text=text,
                ))
            if not segments:
                print(f"   ⚠️ 第{attempt}次：body 解析出 0 段，重试...")
                time.sleep(2)
                continue

            result = SubtitleResult(segments)
            coverage = self._coverage_ratio(result.duration, duration)
            if coverage is None or 0.8 <= coverage <= 1.3:
                if coverage is not None and not (0.8 <= coverage <= 1.3):
                    print(f"   ⚠️ 第{attempt}次：覆盖度 {coverage:.0%} 异常，重试...")
                    time.sleep(2)
                    continue
                print(f"✅ 字幕获取成功！共 {len(segments)} 段，覆盖到 {result.duration:.0f}s / 总长 {duration}s")
                return result
            else:
                print(f"   ⚠️ 第{attempt}次：覆盖度 {coverage:.0%}（预期 80%~130%），可能错集/部分，重试...")
                time.sleep(2)

        print("❌ 多次重试后仍无法获取完整字幕")
        return None

    def _get_duration(self, bvid, page=1):
        """
        获取对应分P的时长。
        ⚠️ 关键：B站 view API 的 data.duration 是【整个合集】的总时长，
        分P视频必须取 data.pages[page-1].duration，否则覆盖度校验会误判。
        """
        data = self.get_video_info(bvid)
        if not data or data.get("code") != 0:
            return 0
        d = data.get("data", {})
        pages = d.get("pages") or []
        if pages and page <= len(pages):
            return pages[page - 1].get("duration", 0)
        return d.get("duration", 0)

    def _coverage_ratio(self, last_end, duration):
        """返回 last_end / duration。duration 未知时返回 None（跳过校验）"""
        if not duration:
            return None
        if not last_end:
            return 0.0
        return last_end / duration


def _md5(s):
    import hashlib
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def download_transcript(video_url, output_dir, cookie=None, curl_bin="curl"):
    """
    便捷函数：提取字幕 → 保存为 {video_id}_transcript_full.json
    返回 JSON 文件路径；失败返回 None。
    """
    dl = BilibiliDownloader(cookie=cookie, curl_bin=curl_bin)
    bvid = dl.extract_bvid(video_url)
    if not bvid:
        return None
    page = dl.extract_page_param(video_url)

    result = dl.download_subtitles(video_url)
    if not result or not result.segments:
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
        out_path = os.path.join(output_dir, f"{bvid}_p{page}_transcript_full.json")
    else:
        out_path = os.path.join(output_dir, f"{bvid}_transcript_full.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(transcript_data, f, ensure_ascii=False, indent=2)
    return out_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python bilibili_downloader.py <视频URL> [输出目录] [Cookie]")
        sys.exit(1)
    url = sys.argv[1]
    out_dir = sys.argv[2] if len(sys.argv) > 2 else None
    cookie = sys.argv[3] if len(sys.argv) > 3 else None
    if out_dir:
        path = download_transcript(url, out_dir, cookie=cookie)
        if path:
            print(f"字幕已保存到: {path}")
        else:
            sys.exit(1)
    else:
        dl = BilibiliDownloader(cookie=cookie)
        result = dl.download_subtitles(url)
        if result:
            print(f"成功获取 {len(result.segments)} 段字幕")
        else:
            print("获取字幕失败")
