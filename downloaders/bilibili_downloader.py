#!/usr/bin/env python3
"""
Bilibili Subtitle Downloader
Standalone module - 不依赖 BiliNote backend
支持分P视频 + AI自动字幕
"""

import re
import time
import hashlib
import urllib.parse
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
        self._wbi_keys = None

    def _fetch_wbi_keys(self):
        """获取 wbi 签名密钥对（从 nav API 的 wbi_img 图片 URL 中提取）"""
        if self._wbi_keys:
            return self._wbi_keys
        try:
            resp = requests.get(
                "https://api.bilibili.com/x/web-interface/nav",
                headers=self.headers,
                timeout=10,
            )
            data = resp.json()
            if data.get("code") == 0:
                wbi_img = data["data"]["wbi_img"]
                # 从图片 URL 中提取 key（文件名去掉扩展名）
                img_key = wbi_img["img_url"].split("/")[-1].replace(".png", "")
                sub_key = wbi_img["sub_url"].split("/")[-1].replace(".png", "")
                # mix_key = img_key 前16位 + sub_key 前16位 = 32位
                mix = img_key[:16] + sub_key[:16]
                keys = {
                    "img_key": img_key,
                    "sub_key": sub_key,
                    "mix_key": mix,
                }
                self._wbi_keys = keys
                return keys
        except Exception as e:
            print(f"   ⚠️ 获取 wbi 密钥失败: {e}")
        return None

    def _wbi_sign(self, params):
        """对请求参数进行 wbi 签名，返回带 w_rid 和 wts 的新参数字典"""
        keys = self._fetch_wbi_keys()
        if not keys:
            return params

        # 添加 wts 时间戳
        signed = dict(params)
        signed["wts"] = int(time.time())

        # 按 key 字母顺序排序
        sorted_keys = sorted(signed.keys())
        # 拼接参数字符串
        query_string = "&".join(
            f"{k}={signed[k]}" for k in sorted_keys
        )
        # 追加 mix_key 后取 MD5
        sign_str = query_string + keys["mix_key"]
        w_rid = hashlib.md5(sign_str.encode("utf-8")).hexdigest()

        signed["w_rid"] = w_rid
        return signed

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

    def _get_video_info_raw(self, bvid):
        """获取视频原始信息（供外部使用）"""
        url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
        try:
            resp = requests.get(url, headers=self.headers, timeout=10)
            return resp.json()
        except Exception:
            return {}

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

        except Exception as e:
            print(f"   ⚠️ 获取视频信息异常: {type(e).__name__}: {e}")
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
        except Exception as e:
            print(f"   ⚠️ 获取视频信息异常: {type(e).__name__}: {e}")
            return None

    def list_subtitles(self, bvid, cid):
        """获取字幕列表（使用 wbi 签名）"""
        params = {"bvid": bvid, "cid": cid}
        signed = self._wbi_sign(params)

        url = f"https://api.bilibili.com/x/player/wbi/v2?{urllib.parse.urlencode(signed)}"
        try:
            resp = requests.get(url, headers=self.headers, timeout=10)
            data = resp.json()
            if data.get("code") != 0:
                print(f"   ⚠️ player API 返回 code={data.get('code')}: {data.get('message', '')}")
                return []
            subtitles = data.get("data", {}).get("subtitle", {}).get("subtitles", [])
            return subtitles or []
        except Exception as e:
            print(f"   ⚠️ 获取字幕列表异常: {type(e).__name__}: {e}")
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
        except Exception as e:
            print(f"   ⚠️ 获取视频信息异常: {type(e).__name__}: {e}")
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
