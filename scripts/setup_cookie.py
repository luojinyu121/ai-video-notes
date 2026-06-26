#!/usr/bin/env python3
"""
ai-video-notes: 自动从浏览器提取 B站 Cookie
用法: python scripts/setup_cookie.py [浏览器名称]
支持: chrome, edge, firefox, brave, opera

自动读取浏览器中的 bilibili.com SESSDATA cookie → 写入 config/settings.json
"""
import sys
import json
import os
import subprocess
import re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
CONFIG_PATH = os.path.join(PROJECT_DIR, "config", "settings.json")
TEMP_FILE = os.path.join(PROJECT_DIR, "output", ".cookies_export.txt")

BROWSERS = ["chrome", "edge", "firefox", "brave", "opera", "chromium"]


def find_browser():
    """尝试找到可用的浏览器"""
    for browser in BROWSERS:
        # Check if yt-dlp can access cookies from this browser
        try:
            result = subprocess.run(
                ["yt-dlp", "--cookies-from-browser", browser, "--print", "cookies", "https://www.bilibili.com"],
                capture_output=True, text=True, timeout=15
            )
            if "SESSDATA" in result.stdout or "SESSDATA" in result.stderr:
                return browser
        except Exception:
            continue
    return None


def extract_cookie(browser):
    """从浏览器提取 B站 SESSDATA cookie"""
    os.makedirs(os.path.dirname(TEMP_FILE), exist_ok=True)

    print(f"🔍 正在从 {browser} 浏览器读取 B站 Cookie...")

    # 方法1：直接用 yt-dlp 导出
    cmd = [
        "yt-dlp",
        "--cookies-from-browser", browser,
        "--cookies", TEMP_FILE,
        "--print", "cookies",
        "https://www.bilibili.com",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        output = result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        print(f"❌ 超时 - 请关闭浏览器后重试")
        return None
    except Exception as e:
        print(f"❌ 调用 yt-dlp 失败: {e}")
        return None

    # 从输出或 cookie 文件中提取 SESSDATA
    sessdata = None

    # 尝试从 Netscape cookie 文件读取
    if os.path.exists(TEMP_FILE):
        with open(TEMP_FILE, "r") as f:
            for line in f:
                if line.startswith("#"):
                    continue
                parts = line.strip().split("\t")
                if len(parts) >= 7 and parts[5] == "SESSDATA":
                    sessdata = parts[6]
                    break

    # 尝试从 stdout 中解析
    if not sessdata:
        match = re.search(r"SESSDATA[= ]+([^;\s]+)", output)
        if match:
            sessdata = match.group(1)

    # 清理临时文件
    if os.path.exists(TEMP_FILE):
        os.remove(TEMP_FILE)

    return sessdata


def update_config(sessdata):
    """写入 config/settings.json"""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)

    old_cookie = config.get("bilibili_cookie", "")
    config["bilibili_cookie"] = sessdata

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    print(f"✅ Cookie 已更新到 {CONFIG_PATH}")

    # 验证
    if old_cookie and old_cookie[:10] != sessdata[:10]:
        print(f"   (已替换旧 Cookie)")
    return True


def main():
    browser = sys.argv[1] if len(sys.argv) > 1 else None

    if browser:
        sessdata = extract_cookie(browser)
    else:
        print("🔍 自动检测浏览器...")
        browser = find_browser()
        if not browser:
            print("❌ 未找到已登录 B站的浏览器")
            print(f"   尝试手动指定: python {__file__} chrome")
            print(f"   支持的浏览器: {', '.join(BROWSERS)}")
            return 1
        print(f"   检测到: {browser}")
        sessdata = extract_cookie(browser)

    if not sessdata:
        print("❌ 无法提取 SESSDATA Cookie")
        print("   请确保：")
        print("   1. 浏览器已安装且是受支持的类型")
        print("   2. 浏览器中已登录 bilibili.com")
        print("   3. Chrome/Edge 需要关闭浏览器才能读取（Firefox 不需要）")
        return 1

    print(f"   SESSDATA: {sessdata[:20]}...")
    update_config(sessdata)
    print("\n🎉 完成！现在可以开始使用 ai-video-notes 了")
    return 0


if __name__ == "__main__":
    sys.exit(main())
