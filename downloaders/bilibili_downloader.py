#!/usr/bin/env python3
"""
Bilibili Subtitle Downloader
Standalone module - 不依赖 BiliNote backend
支持分P视频 + AI自动字幕
"""

import re
import requests

class SubtitleSegment:
    def __init__(self, start, end, text):
        self.start = start
        self.end = end
        self.text = text

class SubtitleResult:
    def __init__(self, segments=None):
        self.segments = segments or []

class BilibiliDownloader:
    """B站字幕下载器（独立版本）"""

    def __init__(self, cookie=None):
        self.cookie = cookie or ""
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Referer": "https://www.bilibili.com",
        }
        if self.cookie:
            self.headers["Cookie"] = f"SESSDATA={self.cookie}"

    def download_subtitles(self, video_url):
        """下载字幕"""
        bvid = self.extract_bvid(video_url)
        if not bvid:
            print(f"无法解析BV号: {video_url}")
            return None

        print(f"正在获取视频信息: {bvid}")

        cid = self.get_cid_by_url(video_url, bvid)
        if not cid:
            print("无法获取视频CID")
            return None

        print(f"使用 cid={cid}")

        subtitles = self.list_subtitles(bvid, cid)
        if not subtitles:
            print("该视频没有可用字幕")
            return None

        track = self.pick_subtitle(subtitles)
        if not track:
            print("无法选择字幕轨")
            return None

        body = self.fetch_body(track.get("subtitle_url"))
        if not body:
            print("无法获取字幕内容")
            return None

        segments = []
        for item in body:
            text = (item.get("content") or "").strip()
            if not text:
                continue
            segments.append(SubtitleSegment(
                start=float(item.get("from", 0)),
                end=float(item.get("to", 0)),
                text=text
            ))

        if not segments:
            return None

        print(f"✅ 字幕获取成功！共 {len(segments)} 段")
        return SubtitleResult(segments)

    def extract_bvid(self, url):
        """从URL提取BV号"""
        patterns = [
            r'BV[a-zA-Z0-9]+',
            r'bv[a-zA-Z0-9]+',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(0)
        return None

    def extract_page_param(self, url):
        """从URL提取分P编号（p=8 表示第8个分P）"""
        match = re.search(r'[?&]p=(\d+)', url)
        if match:
            return int(match.group(1))
        return 1

    def get_cid_by_url(self, video_url, bvid):
        """根据URL中的分P参数获取正确的CID"""
        page = self.extract_page_param(video_url)

        url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
        try:
            resp = requests.get(url, headers=self.headers, timeout=10)
            data = resp.json()
            if data.get("code") != 0:
                return None

            pages = data.get("data", {}).get("pages", [])
            if not pages:
                return data.get("data", {}).get("cid")

            if page <= len(pages):
                return pages[page - 1].get("cid")
            return pages[0].get("cid")

        except:
            return None

    def get_cid(self, bvid):
        """获取主视频CID（第一个分P）"""
        url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
        try:
            resp = requests.get(url, headers=self.headers, timeout=10)
            data = resp.json()
            if data.get("code") != 0:
                return None
            cid = data.get("data", {}).get("cid")
            return cid
        except:
            return None

    def list_subtitles(self, bvid, cid):
        """获取字幕列表"""
        url = f"https://api.bilibili.com/x/player/wbi/v2?bvid={bvid}&cid={cid}"
        try:
            resp = requests.get(url, headers=self.headers, timeout=10)
            data = resp.json()
            if data.get("code") != 0:
                return []
            subtitles = data.get("data", {}).get("subtitle", {}).get("subtitles", [])
            return subtitles or []
        except:
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

    def fetch_body(self, subtitle_url):
        """获取字幕内容"""
        if not subtitle_url:
            return None
        if subtitle_url.startswith("//"):
            subtitle_url = "https:" + subtitle_url
        try:
            resp = requests.get(subtitle_url, headers=self.headers, timeout=15)
            data = resp.json()
            return data.get("body") or []
        except:
            return None

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法: python bilibili_downloader.py <视频URL>")
        sys.exit(1)

    downloader = BilibiliDownloader()
    result = downloader.download_subtitles(sys.argv[1])

    if result:
        print(f"成功获取 {len(result.segments)} 段字幕")
    else:
        print("获取字幕失败")
