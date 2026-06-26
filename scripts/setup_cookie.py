#!/usr/bin/env python3
"""
ai-video-notes: 从浏览器提取 B站 Cookie（Windows DPAPI 解密）
用法: python scripts/setup_cookie.py [chrome|edge]

原理：直接读取 Chrome/Edge 的加密 Cookie 数据库 → win32crypt 解密 → 写入 config
无需 yt-dlp，无需手动 F12。浏览器必须关闭（Cookie 数据库被锁）。
"""
import sys
import json
import os
import sqlite3
import shutil
import tempfile
from pathlib import Path

try:
    import win32crypt
except ImportError:
    print("❌ 需要 pywin32: pip install pywin32")
    sys.exit(1)

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
CONFIG_PATH = PROJECT_DIR / "config" / "settings.json"

# 浏览器 Cookie 数据库路径 (Windows)
BROWSER_PATHS = {
    "chrome": [
        Path.home() / "AppData/Local/Google/Chrome/User Data/Default/Network/Cookies",
        Path.home() / "AppData/Local/Google/Chrome/User Data/Default/Cookies",
    ],
    "edge": [
        Path.home() / "AppData/Local/Microsoft/Edge/User Data/Default/Network/Cookies",
        Path.home() / "AppData/Local/Microsoft/Edge/User Data/Default/Cookies",
    ],
}


def find_cookie_db(browser):
    """查找浏览器 Cookie 数据库"""
    paths = BROWSER_PATHS.get(browser, [])
    for p in paths:
        if p.exists():
            return p
    return None


def extract_sessdata(browser):
    """从浏览器加密 Cookie 中提取 B站 SESSDATA"""
    db_path = find_cookie_db(browser)
    if not db_path:
        print(f"❌ 未找到 {browser} Cookie 数据库")
        return None

    print(f"🔍 读取 {browser} Cookie: {db_path}")

    # 复制数据库（浏览器必须关闭，否则数据库被锁定）
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        try:
            shutil.copy2(db_path, tmp.name)
        except PermissionError:
            print(f"❌ Cookie 数据库被 {browser} 浏览器锁定")
            print(f"   请关闭 {browser} 浏览器所有窗口后重试")
            return None

    try:
        conn = sqlite3.connect(tmp.name)
        cursor = conn.cursor()
        # 查找 bilibili.com 的 SESSDATA
        cursor.execute(
            "SELECT name, encrypted_value FROM cookies WHERE host_key LIKE '%bilibili%' AND name = 'SESSDATA'"
        )
        row = cursor.fetchone()
        conn.close()
    except sqlite3.OperationalError as e:
        print(f"❌ 数据库读取失败: {e}")
        os.unlink(tmp.name)
        return None
    finally:
        os.unlink(tmp.name)

    if not row:
        print(f"❌ 未在 {browser} 中找到 bilibili.com 的 SESSDATA Cookie")
        print("   请确保已在浏览器中登录 B站")
        return None

    name, encrypted_value = row
    try:
        # Windows DPAPI 解密
        decrypted = win32crypt.CryptUnprotectData(encrypted_value, None, None, None, 0)[1]
        sessdata = decrypted.decode("utf-8")
        return sessdata
    except Exception as e:
        print(f"❌ Cookie 解密失败: {e}")
        return None


def update_config(sessdata):
    """写入 config/settings.json"""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)

    config["bilibili_cookie"] = sessdata

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    print(f"✅ Cookie 已写入 {CONFIG_PATH}")


def verify_cookie(sessdata):
    """验证 Cookie 是否有效"""
    import urllib.request
    try:
        req = urllib.request.Request(
            "https://api.bilibili.com/x/web-interface/nav",
            headers={
                "User-Agent": "Mozilla/5.0",
                "Cookie": f"SESSDATA={sessdata}",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            if data.get("code") == 0:
                uname = data.get("data", {}).get("uname", "未知")
                print(f"✅ Cookie 有效！已登录: {uname}")
                return True
            else:
                print(f"⚠️  Cookie 可能无效: code={data.get('code')}")
                return True  # 仍然保存
    except Exception as e:
        print(f"⚠️  无法验证 Cookie: {e}")
        return True


def main():
    browser = sys.argv[1] if len(sys.argv) > 1 else None

    BROWSERS = ["chrome", "edge"]

    if browser and browser not in BROWSERS:
        print(f"❌ 不支持的浏览器: {browser}")
        print(f"   支持: {', '.join(BROWSERS)}")
        return 1

    sessdata = None

    if browser:
        sessdata = extract_sessdata(browser)
    else:
        for b in BROWSERS:
            sessdata = extract_sessdata(b)
            if sessdata:
                browser = b
                break

    if not sessdata:
        print("\n❌ 无法提取 SESSDATA Cookie")
        print("   手动方法：浏览器 F12 → Application → Cookies → bilibili.com → SESSDATA → 复制 Value")
        print("   粘贴到 config/settings.json 的 bilibili_cookie 字段")
        return 1

    print(f"   SESSDATA: {sessdata[:25]}...")
    update_config(sessdata)
    verify_cookie(sessdata)
    print("\n🎉 完成！可以开始使用 ai-video-notes 了")
    return 0


if __name__ == "__main__":
    sys.exit(main())
