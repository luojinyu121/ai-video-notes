#!/usr/bin/env python3
"""
BiliNote Workflow - 完整的B站视频笔记生成工具
根据用户选择的风格生成定制化笔记
"""

import sys
import json
import os
import re
import argparse
from datetime import datetime

class BiliNoteWorkflow:
    """B站视频笔记生成工作流"""
    
    # 风格定义（来自 prompt_builder.py）
    STYLE_DEFINITIONS = {
        'minimal': {
            'name': '精简',
            'description': '仅记录最重要的内容，简洁明了',
            'keywords': []
        },
        'detailed': {
            'name': '详细',
            'description': '包含完整的内容和每个部分的详细讨论，需要尽可能多的记录视频内容',
            'keywords': []
        },
        'academic': {
            'name': '学术',
            'description': '适合学术报告，正式且结构化',
            'keywords': []
        },
        'tutorial': {
            'name': '教程',
            'description': '尽可能详细的记录教程，特别是关键点和一些重要的结论步骤',
            'keywords': ['步骤', '关键', '重点', '结论', '技巧', '方法']
        },
        'xiaohongshu': {
            'name': '小红书',
            'description': '爆款风格',
            'keywords': [
                '好用到哭', '大数据', '教科书般', '小白必看', '宝藏', '绝绝子',
                '都给我冲', '划重点', '笑不活了', 'YYDS', '秘方', '我不允许',
                '压箱底', '建议收藏', '停止摆烂', '上天在提醒你', '挑战全网',
                '手把手', '揭秘', '普通女生', '沉浸式', '有手就能做',
                '好用哭了', '搞钱必看', '狠狠搞钱', '打工人', '吐血整理',
                '家人们', '隐藏', '高级感', '治愈', '破防了', '万万没想到',
                '爆款', '永远可以相信', '手残党必备', '正确姿势'
            ],
            'writing_tips': [
                '使用惊叹号、省略号等标点符号增强表达力，营造紧迫感和惊喜感',
                '使用emoji表情符号，来增加文字的活力',
                '采用具有挑战性和悬念的表述',
                '利用正面刺激和负面激励，诱发读者的本能需求',
                '融入热点话题和实用工具，提高文章的实用性',
                '描述具体的成果和效果，强调标题中的关键词',
                '使用吸引人的标题'
            ]
        },
        'life_journal': {
            'name': '生活向',
            'description': '记录个人生活感悟，情感化表达',
            'keywords': ['感悟', '心情', '体会', '感受', '想法']
        },
        'task_oriented': {
            'name': '任务导向',
            'description': '强调任务、目标，适合工作和待办事项',
            'keywords': ['任务', '目标', '待办', '完成', '执行']
        },
        'business': {
            'name': '商业风格',
            'description': '适合商业报告、会议纪要，正式且精准',
            'keywords': []
        },
        'meeting_minutes': {
            'name': '会议纪要',
            'description': '适合商业报告、会议纪要，正式且精准',
            'keywords': []
        }
    }
    
    def __init__(self, project_root=None):
        self.project_root = project_root or self._find_project_root()
        self.config = self._load_config()
        self.downloader = self._init_downloader()
    
    def _find_project_root(self):
        """查找项目根目录"""
        current = os.path.dirname(os.path.abspath(__file__))
        for _ in range(5):
            if os.path.exists(os.path.join(current, 'config')):
                return current
            current = os.path.dirname(current)
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    def _load_config(self):
        """加载配置文件"""
        config_paths = [
            os.path.join(self.project_root, 'config', 'settings.json'),
            os.path.join(self.project_root, '..', 'config', 'settings.json'),
        ]
        for path in config_paths:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        return {
            'bilibili_cookie': '',
            'output_dir': './output',
            'note_output_dir': './note_results'
        }
    
    def _init_downloader(self):
        """初始化下载器"""
        sys.path.insert(0, os.path.join(self.project_root, 'downloaders'))
        from bilibili_downloader import BilibiliDownloader
        cookie = self.config.get('bilibili_cookie', '')
        return BilibiliDownloader(cookie=cookie)
    
    def extract_transcript(self, video_url):
        """提取字幕"""
        print(f"🎬 正在提取字幕...")
        print(f"   视频: {video_url}")
        
        result = self.downloader.download_subtitles(video_url)
        
        if not result or not result.segments:
            print("❌ 无法获取字幕")
            return None
        
        video_id = video_url.split('/video/')[-1].split('/')[0].split('?')[0]
        last_segment_end = result.segments[-1].end
        total_duration_minutes = last_segment_end / 60
        
        print(f"✅ 字幕提取成功!")
        print(f"   视频ID: {video_id}")
        print(f"   字幕段数: {len(result.segments)}")
        print(f"   总时长: {total_duration_minutes:.1f} 分钟")
        
        output_dir = os.path.join(self.project_root, self.config.get('output_dir', './output'))
        os.makedirs(output_dir, exist_ok=True)
        
        transcript_data = {
            "video_url": video_url,
            "video_id": video_id,
            "duration": last_segment_end,
            "duration_minutes": total_duration_minutes,
            "segments": [
                {"start": s.start, "end": s.end, "text": s.text}
                for s in result.segments
            ]
        }
        
        output_file = os.path.join(output_dir, f'{video_id}_transcript_full.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(transcript_data, f, ensure_ascii=False, indent=2)
        
        print(f"   输出文件: {output_file}")
        return output_file
    
    def extract_key_points(self, transcript_file):
        """提取关键时间节点"""
        print(f"🔍 正在分析字幕，提取关键节点...")
        
        with open(transcript_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        segments = data['segments']
        video_url = data['video_url']
        
        key_patterns = [
            (r'(第一步|第一步我们|首先)', '第一步'),
            (r'(第二步|第二步我们|其次)', '第二步'),
            (r'(第三步|第三步我们|最后)', '第三步'),
            (r'(下一步|下一步我们|接着)', '下一步骤'),
            (r'(关键|重点|核心|重点强调)', '关键点'),
            (r'(结论|总结|总的来说)', '结论总结'),
            (r'(技巧|方法|窍门|妙招)', '技巧方法'),
            (r'(注意|提醒|警告|千万)', '注意事项'),
            (r'(举个例子|例如|比如)', '举例说明'),
            (r'(但是|然而|不过|实际上)', '转折对比'),
            (r'(所以|因此|于是|结果)', '因果关系'),
        ]
        
        key_points = []
        seen_timestamps = set()
        
        for seg in segments:
            for pattern, label in key_patterns:
                if re.search(pattern, seg['text']):
                    ts = int(seg['start'])
                    if ts not in seen_timestamps and len(key_points) < 30:
                        key_points.append({
                            'timestamp': ts,
                            'label': label,
                            'text': seg['text'][:60]
                        })
                        seen_timestamps.add(ts)
                    break
        
        key_points.sort(key=lambda x: x['timestamp'])
        
        print(f"✅ 找到 {len(key_points)} 个关键节点")
        for kp in key_points[:10]:
            ts = kp['timestamp']
            print(f"   {ts//60:02d}:{ts%60:02d} - {kp['label']}: {kp['text'][:30]}...")
        
        return key_points
    
    def _format_timestamp(self, seconds):
        """格式化时间戳"""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"
    
    def generate_markdown_note(self, transcript_file, style='detailed', 
                             format_type='toc+link+summary', key_points=None):
        """生成Markdown笔记 - 根据风格定制"""
        
        print(f"📖 正在生成{style}风格Markdown笔记...")
        
        with open(transcript_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        video_url = data['video_url']
        video_id = data['video_id']
        duration = data.get('duration', 0)
        duration_minutes = data.get('duration_minutes', duration / 60)
        segments = data['segments']
        
        note_dir = os.path.join(self.project_root, self.config.get('note_output_dir', './note_results'))
        os.makedirs(note_dir, exist_ok=True)
        
        style_info = self.STYLE_DEFINITIONS.get(style, self.STYLE_DEFINITIONS['detailed'])
        print(f"   风格: {style_info['name']} - {style_info['description']}")
        
        if style == 'detailed':
            md_content = self._generate_detailed_content(data, format_type, key_points)
        elif style == 'tutorial':
            md_content = self._generate_tutorial_content(data, format_type, key_points)
        elif style == 'xiaohongshu':
            md_content = self._generate_xiaohongshu_content(data, format_type, key_points)
        elif style == 'minimal':
            md_content = self._generate_minimal_content(data, format_type, key_points)
        elif style == 'academic':
            md_content = self._generate_academic_content(data, format_type, key_points)
        elif style == 'business':
            md_content = self._generate_business_content(data, format_type, key_points)
        elif style == 'meeting_minutes':
            md_content = self._generate_meeting_content(data, format_type, key_points)
        elif style == 'life_journal':
            md_content = self._generate_life_journal_content(data, format_type, key_points)
        elif style == 'task_oriented':
            md_content = self._generate_task_oriented_content(data, format_type, key_points)
        else:
            md_content = self._generate_detailed_content(data, format_type, key_points)
        
        output_file = os.path.join(note_dir, f'{video_id}_note_{style}.md')
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        print(f"✅ Markdown笔记生成成功!")
        print(f"   输出文件: {output_file}")
        return output_file
    
    def _generate_detailed_content(self, data, format_type, key_points):
        """detailed风格 - 完整详细记录"""
        video_url = data['video_url']
        video_id = data['video_id']
        duration_minutes = data.get('duration_minutes', 0)
        segments = data['segments']
        
        md = f"""# {video_id} - 详细笔记

**原片**：[{video_url}]({video_url})
**时长**：{duration_minutes:.0f}分钟
**风格**：详细记录
**字幕段数**：{len(segments)}段

---

"""
        
        if 'summary' in format_type:
            md += f"""## AI智能总结

本视频共 **{len(segments)}** 个字幕段落，时长 **{duration_minutes:.1f}** 分钟。
内容涵盖完整视频讲解，建议仔细阅读每个部分以获得完整信息。

---

"""
        
        if 'toc' in format_type:
            md += """## 目录

"""
            chapter_size = 180
            num_chapters = int(data['duration'] / chapter_size) + 1
            for i in range(num_chapters):
                start = i * chapter_size
                ts = self._format_timestamp(start)
                md += f"- [第{i+1}部分 - {ts}](#第{i+1}部分-{ts.replace(':', '')}s)\n"
            md += "\n---\n\n"
        
        if key_points:
            md += "## 关键时间节点\n\n"
            for kp in key_points[:20]:
                ts = self._format_timestamp(kp['timestamp'])
                md += f"- **{ts}** [{kp['label']}]({video_url}?t={kp['timestamp']}): {kp['text']}...\n"
            md += "\n---\n\n"
        
        chapter_size = 180
        num_chapters = int(data['duration'] / chapter_size) + 1
        
        for i in range(num_chapters):
            start = i * chapter_size
            end = min((i + 1) * chapter_size, data['duration'])
            ts = self._format_timestamp(start)
            
            chapter_segments = [s for s in segments if start <= s['start'] < end]
            chapter_text = ' '.join([s['text'] for s in chapter_segments])
            
            md += f"## 第{i+1}部分 - {ts}\n\n"
            if 'link' in format_type:
                md += f"*Content-[{ts}]\n\n"
            md += f"{chapter_text}\n\n"
        
        return md
    
    def _generate_tutorial_content(self, data, format_type, key_points):
        """tutorial风格 - 教程风格，突出结论步骤"""
        video_url = data['video_url']
        video_id = data['video_id']
        duration_minutes = data.get('duration_minutes', 0)
        segments = data['segments']
        
        md = f"""# 🎯 {video_id} 教程笔记

**原片**：[{video_url}]({video_url})
**时长**：{duration_minutes:.0f}分钟
**风格**：教程风格
**学习目标**：掌握关键步骤、结论和重要技巧

---

"""
        
        if 'summary' in format_type:
            md += """## 📌 学习目标

本教程涵盖以下核心内容：

"""
            if key_points:
                steps = [kp for kp in key_points if '步' in kp['label'] or '关键' in kp['label']]
                if steps:
                    md += "- **核心步骤**：\n"
                    for step in steps[:5]:
                        md += f"  - {step['label']}: {step['text'][:30]}...\n"
            md += "\n---\n\n"
        
        if key_points:
            md += """## 🔥 关键结论

> **重要提示**：以下结论是本教程的核心要点，请务必记住！

"""
            conclusions = [kp for kp in key_points if '结论' in kp['label'] or '关键' in kp['label']]
            for kp in conclusions[:10]:
                ts = self._format_timestamp(kp['timestamp'])
                md += f"1. **{kp['label']}** ([{ts}]({video_url}?t={kp['timestamp']}))\n   {kp['text']}\n\n"
            
            tips = [kp for kp in key_points if '技巧' in kp['label'] or '方法' in kp['label']]
            if tips:
                md += "### 💡 实用技巧\n\n"
                for kp in tips[:5]:
                    ts = self._format_timestamp(kp['timestamp'])
                    md += f"- 💡 **{kp['text']}** ([{ts}]({video_url}?t={kp['timestamp']}))\n"
                md += "\n"
            
            md += "---\n\n"
        
        if 'toc' in format_type:
            md += """## 📚 教程目录

"""
            step_count = 0
            for kp in key_points:
                if '步' in kp['label']:
                    step_count += 1
                    ts = self._format_timestamp(kp['timestamp'])
                    md += f"- [步骤{step_count}: {kp['label']} - {ts}](#步骤{step_count}---{ts.replace(':', '')}s)\n"
            md += "\n---\n\n"
        
        step_count = 0
        current_section = ""
        for kp in key_points:
            if '步' in kp['label']:
                step_count += 1
                ts = self._format_timestamp(kp['timestamp'])
                
                related_segments = [s for s in segments 
                                  if kp['timestamp'] <= s['start'] < kp['timestamp'] + 180]
                section_text = ' '.join([s['text'] for s in related_segments])
                
                md += f"## 步骤{step_count} - {ts}\n\n"
                if 'link' in format_type:
                    md += f"*Content-[{ts}]\n\n"
                md += f"{section_text}\n\n"
        
        if not step_count:
            chapter_size = 180
            num_chapters = int(data['duration'] / chapter_size) + 1
            for i in range(num_chapters):
                start = i * chapter_size
                ts = self._format_timestamp(start)
                
                chapter_segments = [s for s in segments if start <= s['start'] < start + chapter_size]
                chapter_text = ' '.join([s['text'] for s in chapter_segments])
                
                md += f"## 第{i+1}部分 - {ts}\n\n"
                if 'link' in format_type:
                    md += f"*Content-[{ts}]\n\n"
                md += f"{chapter_text}\n\n"
        
        md += """---

## ⚠️ 注意事项

"""
        warnings = [kp for kp in key_points if '注意' in kp['label']]
        for kp in warnings[:5]:
            ts = self._format_timestamp(kp['timestamp'])
            md += f"- ⚠️ **{kp['text']}** ([{ts}]({video_url}?t={kp['timestamp']}))\n"
        
        return md
    
    def _generate_xiaohongshu_content(self, data, format_type, key_points):
        """xiaohongshu风格 - 小红书爆款风格"""
        video_url = data['video_url']
        video_id = data['video_id']
        duration_minutes = data.get('duration_minutes', 0)
        segments = data['segments']
        
        style_info = self.STYLE_DEFINITIONS['xiaohongshu']
        
        md = f"""# 😱 {duration_minutes:.0f}分钟搞定！宝藏教程绝绝子！👇

✨ **{video_id}** | {duration_minutes:.0f}分钟 | 小白必看 | 吐血整理 | YYDS

姐妹们👭！家人们！今天的视频真的太绝了😭

**宝藏工具**！**绝绝子**！**好用哭了**！打工人必须冲💪

👉 [观看原片]({video_url})

---

"""
        
        if key_points:
            highlight_points = key_points[:10]
            
            md += """## 🔥 划重点！必看！👇

"""
            for i, kp in enumerate(highlight_points, 1):
                ts = self._format_timestamp(kp['timestamp'])
                md += f"{i}. 💡 **{kp['text']}**\n   ⏰ [{ts}]({video_url}?t={kp['timestamp']})\n\n"
            
            md += "---\n\n"
        
        md += """## 📦 超好用的神器推荐！

"""
        
        tools_keywords = ['安装', '配置', '设置', '使用']
        for kp in key_points[:5]:
            for kw in tools_keywords:
                if kw in kp['text']:
                    ts = self._format_timestamp(kp['timestamp'])
                    md += f"✅ **{kp['text']}**\n   📍 [{ts}]({video_url}?t={kp['timestamp']})\n\n"
                    break
        
        md += """## 💡 好用到哭！沉浸式教程！

"""
        
        chapter_size = 120
        num_chapters = min(3, int(data['duration'] / chapter_size) + 1)
        
        for i in range(num_chapters):
            start = i * chapter_size
            ts = self._format_timestamp(start)
            
            chapter_segments = [s for s in segments if start <= s['start'] < start + chapter_size]
            chapter_text = ' '.join([s['text'] for s in chapter_segments])
            
            md += f"### {i+1}️⃣ **核心内容** - {ts}\n\n"
            md += f"{chapter_text[:300]}...\n\n"
        
        md += """---

## ✨ 评论区福利！

🎁 回复"**领取资源**"获取所有资料！

👍 **点赞** + **收藏** + **关注**

💬 **评论区**告诉我你的想法！

👉 **@** 你的好朋友一起看！

---

*永远可以相信的宝藏教程！停止摆烂！都给我冲！* 🚀
"""
        
        return md
    
    def _generate_minimal_content(self, data, format_type, key_points):
        """minimal风格 - 极简风格"""
        video_url = data['video_url']
        video_id = data['video_id']
        duration_minutes = data.get('duration_minutes', 0)
        segments = data['segments']
        
        md = f"""# {video_id}

**链接**: {video_url} | {duration_minutes:.0f}分钟

---

"""
        
        if key_points:
            md += "## 要点\n\n"
            for kp in key_points[:10]:
                ts = self._format_timestamp(kp['timestamp'])
                md += f"- **{kp['label']}**: {kp['text'][:40]}... [{ts}]({video_url}?t={kp['timestamp']})\n"
            md += "\n"
        
        md += """## 内容

"""
        chapter_size = 180
        num_chapters = int(data['duration'] / chapter_size) + 1
        
        for i in range(num_chapters):
            start = i * chapter_size
            ts = self._format_timestamp(start)
            
            chapter_segments = [s for s in segments if start <= s['start'] < start + chapter_size]
            chapter_text = ' '.join([s['text'] for s in chapter_segments])
            
            md += f"### {ts}\n\n"
            md += f"{chapter_text[:200]}...\n\n"
        
        return md
    
    def _generate_academic_content(self, data, format_type, key_points):
        """academic风格 - 学术报告格式"""
        video_url = data['video_url']
        video_id = data['video_id']
        duration_minutes = data.get('duration_minutes', 0)
        segments = data['segments']
        
        md = f"""# 学术报告：{video_id}

## 基本信息

- **视频来源**: Bilibili
- **视频链接**: {video_url}
- **时长**: {duration_minutes:.0f}分钟
- **字幕段数**: {len(segments)}段
- **生成日期**: {datetime.now().strftime('%Y-%m-%d')}

## 研究概述

本视频时长{duration_minutes:.1f}分钟，共{len(segments)}个字幕段落。

"""
        
        if key_points:
            md += "## 关键论点\n\n"
            for i, kp in enumerate(key_points[:15], 1):
                ts = self._format_timestamp(kp['timestamp'])
                md += f"{i}. **{kp['label']}**\n   - 时间戳: [{ts}]({video_url}?t={kp['timestamp']})\n   - 内容: {kp['text']}\n\n"
            md += "\n"
        
        md += "## 详细内容\n\n"
        
        chapter_size = 180
        num_chapters = int(data['duration'] / chapter_size) + 1
        
        for i in range(num_chapters):
            start = i * chapter_size
            end = min((i + 1) * chapter_size, data['duration'])
            ts_start = self._format_timestamp(start)
            ts_end = self._format_timestamp(end)
            
            chapter_segments = [s for s in segments if start <= s['start'] < end]
            chapter_text = ' '.join([s['text'] for s in chapter_segments])
            
            md += f"### 第{i+1}章: {ts_start} - {ts_end}\n\n"
            md += f"{chapter_text}\n\n"
        
        md += """## 参考文献

本笔记基于视频字幕内容整理生成，仅供学习参考。

---

*本报告由BiliNote自动生成*
"""
        
        return md
    
    def _generate_business_content(self, data, format_type, key_points):
        """business风格 - 商业报告格式"""
        video_url = data['video_url']
        video_id = data['video_id']
        duration_minutes = data.get('duration_minutes', 0)
        segments = data['segments']
        
        md = f"""# 商业分析报告：{video_id}

## 执行摘要

| 项目 | 内容 |
|------|------|
| 视频标题 | {video_id} |
| 来源平台 | Bilibili |
| 时长 | {duration_minutes:.0f}分钟 |
| 信息密度 | {len(segments)}段落 |
| 生成时间 | {datetime.now().strftime('%Y-%m-%d %H:%M')} |

## 核心发现

"""
        
        if key_points:
            for kp in key_points[:10]:
                ts = self._format_timestamp(kp['timestamp'])
                md += f"### {kp['label']}\n- **时间戳**: [{ts}]({video_url}?t={kp['timestamp']})\n- **描述**: {kp['text']}\n\n"
        
        md += "\n## 详细分析\n\n"
        
        chapter_size = 180
        num_chapters = int(data['duration'] / chapter_size) + 1
        
        for i in range(num_chapters):
            start = i * chapter_size
            ts = self._format_timestamp(start)
            
            chapter_segments = [s for s in segments if start <= s['start'] < start + chapter_size]
            chapter_text = ' '.join([s['text'] for s in chapter_segments])
            
            md += f"### {i+1}. 分析时段: {ts}\n\n"
            md += f"{chapter_text}\n\n"
        
        md += """## 结论与建议

基于以上分析，建议关注视频中提到的核心要点。

---

*本报告由BiliNote商业版生成*
"""
        
        return md
    
    def _generate_meeting_content(self, data, format_type, key_points):
        """meeting_minutes风格 - 会议纪要格式"""
        video_url = data['video_url']
        video_id = data['video_id']
        duration_minutes = data.get('duration_minutes', 0)
        segments = data['segments']
        
        md = f"""# 会议纪要

## 基本信息

| 项目 | 内容 |
|------|------|
| 会议主题 | {video_id} |
| 来源 | Bilibili视频 |
| 会议时长 | {duration_minutes:.0f}分钟 |
| 记录时间 | {datetime.now().strftime('%Y-%m-%d %H:%M')} |

## 议程

"""
        
        if key_points:
            md += "### 主要议题\n\n"
            for i, kp in enumerate(key_points[:10], 1):
                ts = self._format_timestamp(kp['timestamp'])
                md += f"{i}. {kp['label']}: {kp['text'][:50]}...\n   - 时间: [{ts}]({video_url}?t={kp['timestamp']})\n\n"
        
        md += "\n## 会议内容\n\n"
        
        chapter_size = 180
        num_chapters = int(data['duration'] / chapter_size) + 1
        
        for i in range(num_chapters):
            start = i * chapter_size
            ts = self._format_timestamp(start)
            
            chapter_segments = [s for s in segments if start <= s['start'] < start + chapter_size]
            chapter_text = ' '.join([s['text'] for s in chapter_segments])
            
            md += f"### 时段{i+1}: {ts}\n\n"
            md += f"{chapter_text}\n\n"
        
        md += """## 行动项

暂无

## 下次会议

待定

---

*本纪要由BiliNote会议版生成*
"""
        
        return md
    
    def _generate_life_journal_content(self, data, format_type, key_points):
        """life_journal风格 - 生活感悟风格"""
        video_url = data['video_url']
        video_id = data['video_id']
        duration_minutes = data.get('duration_minutes', 0)
        segments = data['segments']
        
        md = f"""# 📖 生活感悟笔记：{video_id}

✨ 今天看了一个{duration_minutes:.0f}分钟的视频，有一些感悟想记录下来...

**视频链接**: [{video_url}]({video_url})

---

## 💭 触动我的瞬间

"""
        
        if key_points:
            for kp in key_points[:8]:
                ts = self._format_timestamp(kp['timestamp'])
                md += f"💡 **{kp['text']}**\n   - 触动时刻: [{ts}]({video_url}?t={kp['timestamp']})\n\n"
        
        md += "\n## 🌱 我的感悟\n\n"
        
        chapter_size = 180
        num_chapters = min(3, int(data['duration'] / chapter_size) + 1)
        
        for i in range(num_chapters):
            start = i * chapter_size
            ts = self._format_timestamp(start)
            
            chapter_segments = [s for s in segments if start <= s['start'] < start + chapter_size]
            chapter_text = ' '.join([s['text'] for s in chapter_segments])
            
            md += f"### 🌟 片段{i+1} - {ts}\n\n"
            md += f"{chapter_text[:300]}...\n\n"
        
        md += """---

## 📝 写在最后

今天又是收获满满的一天✨

*记录于 {datetime.now().strftime('%Y-%m-%d %H:%M')}*
"""
        
        return md
    
    def _generate_task_oriented_content(self, data, format_type, key_points):
        """task_oriented风格 - 任务导向风格"""
        video_url = data['video_url']
        video_id = data['video_id']
        duration_minutes = data.get('duration_minutes', 0)
        segments = data['segments']
        
        md = f"""# 📋 任务清单：{video_id}

**目标视频**: [{video_url}]({video_url})
**预计时长**: {duration_minutes:.0f}分钟

---

## ✅ 任务目标

"""
        
        if key_points:
            md += "### 待完成事项\n\n"
            for i, kp in enumerate(key_points[:10], 1):
                ts = self._format_timestamp(kp['timestamp'])
                md += f"[ ] {i}. **{kp['label']}**: {kp['text'][:50]}...\n   ⏰ 时间: [{ts}]({video_url}?t={kp['timestamp']})\n\n"
        
        md += "\n## 📖 任务详情\n\n"
        
        chapter_size = 180
        num_chapters = int(data['duration'] / chapter_size) + 1
        
        for i in range(num_chapters):
            start = i * chapter_size
            ts = self._format_timestamp(start)
            
            chapter_segments = [s for s in segments if start <= s['start'] < start + chapter_size]
            chapter_text = ' '.join([s['text'] for s in chapter_segments])
            
            md += f"### 任务块{i+1}: {ts}\n\n"
            md += f"{chapter_text[:300]}...\n\n"
        
        md += """## 📊 进度追踪

- [ ] 开始学习
- [ ] 完成关键点1
- [ ] 完成关键点2
- [ ] 全部完成

---

*任务创建于 {datetime.now().strftime('%Y-%m-%d %H:%M')}*
"""
        
        return md
    
    def generate_html_note(self, markdown_file, style='detailed'):
        """生成HTML笔记"""
        print(f"🎨 正在生成HTML笔记...")
        
        note_dir = os.path.join(self.project_root, self.config.get('note_output_dir', './note_results'))
        os.makedirs(note_dir, exist_ok=True)
        
        with open(markdown_file, 'r', encoding='utf-8') as f:
            md_content = f.read()
        
        html = self._build_html_from_markdown(md_content, style)
        
        output_file = os.path.join(note_dir, f'{os.path.basename(markdown_file).replace(".md", ".html")}')
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"✅ HTML笔记生成成功!")
        print(f"   输出文件: {output_file}")
        return output_file
    
    def _build_html_from_markdown(self, md_content, style):
        """从Markdown构建HTML"""
        
        style_colors = {
            'detailed': ('#667eea', '#764ba2'),
            'tutorial': ('#11998e', '#38ef7d'),
            'xiaohongshu': ('#ff6b6b', '#feca57'),
            'minimal': ('#2c3e50', '#34495e'),
            'academic': ('#8e44ad', '#9b59b6'),
            'business': ('#2980b9', '#3498db'),
            'meeting_minutes': ('#27ae60', '#2ecc71'),
            'life_journal': ('#e91e63', '#f48fb1'),
            'task_oriented': ('#ff9800', '#ffc107')
        }
        
        primary, secondary = style_colors.get(style, ('#667eea', '#764ba2'))
        
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BiliNote - AI视频笔记</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            min-height: 100vh;
            color: #e8e8e8;
            line-height: 1.8;
        }}
        .container {{ max-width: 1000px; margin: 0 auto; padding: 20px; }}
        header {{
            background: linear-gradient(135deg, {primary} 0%, {secondary} 100%);
            color: white;
            padding: 40px;
            border-radius: 16px;
            text-align: center;
            margin-bottom: 30px;
        }}
        header h1 {{ font-size: 2em; margin-bottom: 15px; }}
        .meta {{ display: flex; justify-content: center; gap: 20px; flex-wrap: wrap; font-size: 0.9em; opacity: 0.9; }}
        .meta span {{ background: rgba(255,255,255,0.2); padding: 8px 20px; border-radius: 20px; }}
        .video-link {{ display: inline-block; background: white; color: {primary}; padding: 15px 35px; border-radius: 25px; text-decoration: none; font-weight: bold; margin-top: 20px; }}
        .video-link:hover {{ transform: scale(1.05); }}
        .content {{ background: rgba(255,255,255,0.05); border-radius: 12px; padding: 30px; margin-bottom: 25px; }}
        .content h1, .content h2, .content h3 {{ color: {primary}; margin: 25px 0 15px; }}
        .content h1 {{ font-size: 1.8em; border-bottom: 2px solid {primary}; padding-bottom: 10px; }}
        .content h2 {{ font-size: 1.5em; border-left: 4px solid {primary}; padding-left: 15px; }}
        .content h3 {{ font-size: 1.2em; color: {secondary}; }}
        .content p {{ margin: 15px 0; }}
        .content ul, .content ol {{ padding-left: 25px; margin: 15px 0; }}
        .content li {{ margin: 8px 0; }}
        .content blockquote {{ background: rgba(0,0,0,0.2); border-left: 4px solid {primary}; padding: 15px 20px; margin: 20px 0; border-radius: 8px; }}
        .content pre {{ background: rgba(0,0,0,0.4); padding: 15px; border-radius: 8px; overflow-x: auto; margin: 15px 0; }}
        .content code {{ font-family: 'Fira Code', monospace; background: rgba(0,0,0,0.3); padding: 2px 8px; border-radius: 4px; }}
        .content table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        .content th, .content td {{ text-align: left; padding: 12px; border-bottom: 1px solid rgba(255,255,255,0.1); }}
        .content th {{ background: rgba({primary.replace('#', '')}, 0.3); color: {primary}; }}
        .content tr:hover {{ background: rgba(255,255,255,0.05); }}
        .timestamp {{ display: inline-flex; background: linear-gradient(135deg, {primary}, {secondary}); color: white; padding: 4px 14px; border-radius: 20px; font-size: 0.85em; text-decoration: none; transition: all 0.3s; }}
        .timestamp:hover {{ transform: translateY(-2px); box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4); }}
        .footer {{ text-align: center; padding: 30px; color: #888; font-size: 0.9em; }}
        @media (max-width: 768px) {{ .container {{ padding: 15px; }} header {{ padding: 25px; }} header h1 {{ font-size: 1.5em; }} }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📚 AI视频笔记</h1>
            <div class="meta">
                <span>🎨 {style}风格</span>
                <span>⏱️ {datetime.now().strftime('%Y-%m-%d')}</span>
            </div>
        </header>
        <div class="content">
            {self._markdown_to_html(md_content)}
        </div>
        <div class="footer">
            <p>由 BiliNote AI 生成 | {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        </div>
    </div>
</body>
</html>
"""
        return html
    
    def _markdown_to_html(self, md):
        """简单的Markdown转HTML"""
        import re
        
        html = md
        
        html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
        html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
        html = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', html)
        
        lines = html.split('\n')
        result = []
        in_list = False
        list_type = None
        
        for line in lines:
            if re.match(r'^[-*] ', line):
                if not in_list or list_type != 'ul':
                    if in_list:
                        result.append(f'</{list_type}>')
                    result.append('<ul>')
                    in_list = True
                    list_type = 'ul'
                result.append(f'<li>{line[2:]}</li>')
            elif re.match(r'^\d+\. ', line):
                if not in_list or list_type != 'ol':
                    if in_list:
                        result.append(f'</{list_type}>')
                    result.append('<ol>')
                    in_list = True
                    list_type = 'ol'
                cleaned_line = re.sub(r'^\d+\. ', '', line)
                result.append(f'<li>{cleaned_line}</li>')
            else:
                if in_list:
                    result.append(f'</{list_type}>')
                    in_list = False
                    list_type = None
                result.append(f'<p>{line}</p>' if line.strip() else '')
        
        if in_list:
            result.append(f'</{list_type}>')
        
        return '\n'.join(result)
    
    def run_workflow(self, video_url, style='detailed', format_type='toc+link+summary', 
                    skip_extract=False, transcript_file=None):
        """运行完整工作流"""
        print(f"\n{'='*60}")
        print(f"🚀 BiliNote Workflow 开始")
        print(f"{'='*60}")
        print(f"📌 风格: {style}")
        print(f"📋 格式: {format_type}")
        print(f"{'='*60}\n")
        
        if not skip_extract:
            transcript_file = self.extract_transcript(video_url)
            if not transcript_file:
                print("\n❌ 字幕提取失败，退出")
                return None
        
        if not transcript_file:
            print("\n❌ 需要提供字幕文件路径")
            return None
        
        key_points = self.extract_key_points(transcript_file)
        
        md_file = self.generate_markdown_note(transcript_file, style, format_type, key_points)
        
        html_file = self.generate_html_note(md_file, style)
        
        print(f"\n{'='*60}")
        print(f"✅ 工作流完成！")
        print(f"{'='*60}")
        print(f"\n生成文件：")
        print(f"  📝 Markdown: {md_file}")
        print(f"  🌐 HTML: {html_file}")
        print(f"\n")
        
        return {
            'transcript': transcript_file,
            'markdown': md_file,
            'html': html_file,
            'key_points': key_points,
            'style': style,
            'format': format_type
        }


def main():
    parser = argparse.ArgumentParser(description='BiliNote Workflow - B站视频笔记生成工具')
    parser.add_argument('video_url', help='B站视频URL')
    parser.add_argument('--style', default='detailed', 
                       choices=['detailed', 'tutorial', 'minimal', 'academic', 'xiaohongshu', 
                               'life_journal', 'task_oriented', 'business', 'meeting_minutes'],
                       help='笔记风格')
    parser.add_argument('--format', default='toc+link+summary', 
                       help='输出格式')
    parser.add_argument('--skip-extract', action='store_true',
                       help='跳过字幕提取')
    parser.add_argument('--transcript', 
                       help='已有字幕JSON文件路径')
    
    args = parser.parse_args()
    
    workflow = BiliNoteWorkflow()
    result = workflow.run_workflow(
        args.video_url,
        style=args.style,
        format_type=args.format,
        skip_extract=args.skip_extract,
        transcript_file=args.transcript
    )
    
    if result:
        print(f"\n✨ 成功！已生成 {result['style']} 风格的笔记")
    else:
        print(f"\n❌ 失败")
        sys.exit(1)


if __name__ == '__main__':
    main()
