#!/usr/bin/env python3
"""
ai-video-notes Hook: 检查 HTML/MD 文件命名规范
触发时机: Write 工具调用前
检查内容: note_results/ 下的文件是否遵循 {NN}_{视频标题}.html 命名
"""
import sys
import json
import re
import os

try:
    tool_input = json.loads(sys.stdin.read())
except Exception:
    sys.exit(0)

file_path = tool_input.get("file_path", "")

# 只检查 note_results 下的 .html 和 .md 文件
if not re.search(r'note_results[/\\].+\.(html|md)$', file_path, re.IGNORECASE):
    sys.exit(0)

filename = os.path.basename(file_path)

# 检查是否符合命名规范: {NN}_{标题}.html 或 {标题}.html
# 合法格式1: 数字编号_标题.html (批量模式)
# 合法格式2: 纯标题.html (单集模式)
# 非法格式: 包含 BV 号的旧格式

if re.match(r'^\d{2}_.+\.(html|md)$', filename):
    # 符合批量命名规范 {NN}_{标题}.html
    sys.exit(0)

if re.match(r'^BV[a-zA-Z0-9]+.*\.(html|md)$', filename) or re.match(r'^[a-zA-Z0-9]+_note_full\.(html|md)$', filename):
    # ❌ 使用了 BV ID 旧格式
    print(
        f"⛔⛔⛔ [ai-video-notes 命名 Hook] ⛔⛔⛔\n\n"
        f"检测到即将写入的文件名不符合命名规范：\n"
        f"  当前：{filename}\n"
        f"  要求：{{NN}}_{{视频标题}}.html\n\n"
        f"❌ 禁止使用 BV ID 作为文件名！\n"
        f"✅ 正确格式：01_教你写一个比SimpleFOC更好的电机库.html\n"
        f"✅ 标题来自 B站 API pages[].part 或 episodes[].title\n\n"
        f"请修改 file_path 后重试。",
        file=sys.stderr
    )
    sys.exit(1)

# 未匹配任何规则，放行
sys.exit(0)
