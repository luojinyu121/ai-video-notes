#!/bin/bash
# ai-video-notes 插件安装脚本
# 用法: bash install.sh [--global]
#   --global  安装到用户级 ~/.claude/（全局可用）
#   默认      安装到当前项目的 .claude/ 和 .github/skills/

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_NAME="ai-video-notes"

echo "📦 安装 ai-video-notes 插件..."

# ── 1. 安装 SKILL.md ──
if [ "$1" = "--global" ]; then
    SKILL_DIR="$HOME/.claude/skills/$SKILL_NAME"
    SETTINGS_FILE="$HOME/.claude/settings.json"
    echo "   → 全局模式: $SKILL_DIR"
else
    SKILL_DIR="$(pwd)/.github/skills/$SKILL_NAME"
    SETTINGS_FILE="$(pwd)/.claude/settings.json"
    echo "   → 项目模式: $SKILL_DIR"
fi

mkdir -p "$SKILL_DIR"
cp "$SCRIPT_DIR/SKILL.md" "$SKILL_DIR/"
cp -r "$SCRIPT_DIR/config" "$SKILL_DIR/"
cp -r "$SCRIPT_DIR/scripts" "$SKILL_DIR/"
cp -r "$SCRIPT_DIR/downloaders" "$SKILL_DIR/"
echo "   ✅ SKILL.md + 脚本已安装到 $SKILL_DIR"

# ── 2. 安装 Hook 配置 ──
HOOK_BLOCK=$(cat "$SCRIPT_DIR/.claude/hook-config.json")

mkdir -p "$(dirname "$SETTINGS_FILE")"

if [ -f "$SETTINGS_FILE" ]; then
    # 检查是否已存在同名 hook
    if grep -q "ai-video-notes Hook" "$SETTINGS_FILE" 2>/dev/null; then
        echo "   ⏭️  Hook 已存在，跳过"
    else
        # 合并 hook 到现有 settings
        python3 -c "
import json
with open('$SETTINGS_FILE', 'r') as f:
    settings = json.load(f)
hook_block = json.loads('''$HOOK_BLOCK''')
settings.setdefault('hooks', {}).setdefault('PostToolUse', [])
existing_matchers = [h.get('matcher') for h in settings['hooks']['PostToolUse']]
if 'AskUserQuestion' not in existing_matchers:
    settings['hooks']['PostToolUse'].append(hook_block['hooks']['PostToolUse'][0])
    with open('$SETTINGS_FILE', 'w') as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)
    print('   ✅ Hook 已合并到 $SETTINGS_FILE')
" 2>&1
    fi
else
    # 新建 settings.json
    echo "$HOOK_BLOCK" > "$SETTINGS_FILE"
    echo "   ✅ 新建 $SETTINGS_FILE 含 Hook"
fi

echo ""
echo "✅ 安装完成！"
echo "   Skill: /skill ai-video-notes"
echo "   Hook:  AskUserQuestion 后自动提醒使用 haiku 模型"
echo ""
echo "⚠️  别忘了编辑 config/settings.json 填入你的 B站 Cookie！"
