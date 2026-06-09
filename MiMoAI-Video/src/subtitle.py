"""
SRT / ASS 字幕文件生成与解析。

支持两种格式：
- SRT: 标准字幕格式，兼容性好
- ASS: 高级字幕格式，支持逐字高亮、动画、自定义样式（抖音风格推荐）
"""

import os
import re
from dataclasses import dataclass, field
from typing import List, Optional

from mimo_asr import Segment


# ============================================================================
# 通用时间格式转换
# ============================================================================

def time_to_srt_format(seconds: float) -> str:
    """将秒数转换为 SRT 时间格式 (HH:MM:SS,mmm)。"""
    if seconds < 0:
        seconds = 0
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def time_to_ass_format(seconds: float) -> str:
    """将秒数转换为 ASS 时间格式 (H:MM:SS.CC)。CC = 百分之一秒。"""
    if seconds < 0:
        seconds = 0
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centiseconds = int((seconds % 1) * 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{centiseconds:02d}"


# ============================================================================
# ASS 字幕配置
# ============================================================================

@dataclass
class ASSStyleConfig:
    """ASS 字幕样式配置（抖音风格）。"""
    # 字体
    font_name: str = "Microsoft YaHei"
    font_size: int = 52
    bold: bool = True

    # 颜色 (ASS 格式: &HAABBGGRR, AA=透明度 00=不透明 FF=全透明)
    primary_color: str = "&H00FFFFFF"    # 主色：白色
    secondary_color: str = "&H00FFFF00"  # 副色：黄色（用于高亮）
    outline_color: str = "&H00000000"    # 描边：黑色
    back_color: str = "&H80000000"       # 背景：半透明黑

    # 描边与阴影
    outline_width: int = 3
    shadow_depth: int = 0

    # 位置 (ASS Alignment: 小键盘布局 2=底部居中, 5=中间居中, 8=顶部居中)
    alignment: int = 2
    margin_v: int = 60  # 垂直边距

    # 逐字高亮（卡拉OK效果）
    enable_karaoke: bool = True
    karaoke_highlight_color: str = "&H0000FFFF"  # 高亮色：黄色

    # 淡入淡出
    fade_in_ms: int = 200
    fade_out_ms: int = 200

    @classmethod
    def douyin_default(cls) -> "ASSStyleConfig":
        """抖音风格默认配置：白色大字 + 黑色粗描边 + 底部居中。"""
        return cls()

    @classmethod
    def douyin_highlight(cls) -> "ASSStyleConfig":
        """抖音强调风格：黄色字 + 黑色描边。"""
        return cls(
            primary_color="&H0000FFFF",
            secondary_color="&H00FFFFFF",
            karaoke_highlight_color="&H00FFFFFF",
        )


# ============================================================================
# SRT 生成
# ============================================================================

def segments_to_srt(
    segments: List[Segment],
    output_path: str,
    max_chars_per_line: int = 18,
) -> str:
    """
    将转录片段列表写入 SRT 字幕文件。

    Args:
        segments: 转录片段列表
        output_path: 输出 SRT 文件路径
        max_chars_per_line: 每行最大字符数（中文约18个字）

    Returns:
        输出文件路径
    """
    lines = []
    for idx, seg in enumerate(segments, 1):
        start_t = time_to_srt_format(seg.start_time)
        end_t = time_to_srt_format(seg.end_time)
        text = _split_text_to_lines(seg.text, max_chars_per_line)
        lines.append(f"{idx}\n{start_t} --> {end_t}\n{text}\n")

    srt_content = "\n".join(lines) + "\n"

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(srt_content)

    return output_path


# ============================================================================
# ASS 字幕生成（抖音风格 · 逐字高亮）
# ============================================================================

def segments_to_ass(
    segments: List[Segment],
    output_path: str,
    style_config: Optional[ASSStyleConfig] = None,
    keywords: Optional[List[str]] = None,
    max_chars_per_line: int = 18,
) -> str:
    """
    将转录片段列表写入 ASS 字幕文件（抖音风格，支持逐字高亮）。

    Args:
        segments: 转录片段列表
        output_path: 输出 ASS 文件路径
        style_config: ASS 样式配置，默认使用抖音风格
        keywords: 需要高亮的关键词列表
        max_chars_per_line: 每行最大字符数

    Returns:
        输出文件路径
    """
    if style_config is None:
        style_config = ASSStyleConfig.douyin_default()

    if keywords is None:
        keywords = []

    # 构建 ASS 文件内容
    header = _build_ass_header(style_config)
    events = _build_ass_events(segments, style_config, keywords, max_chars_per_line)

    ass_content = header + events

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(ass_content)

    return output_path


def _build_ass_header(style_config: ASSStyleConfig) -> str:
    """构建 ASS 文件头（脚本信息 + 样式定义）。"""
    # 字体加粗标志：-1=粗体, 0=正常
    bold_flag = -1 if style_config.bold else 0

    header = f"""[Script Info]
Title: MiMo ASR Douyin Subtitle
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{style_config.font_name},{style_config.font_size},{style_config.primary_color},{style_config.secondary_color},{style_config.outline_color},{style_config.back_color},{bold_flag},0,0,0,100,100,0,0,1,{style_config.outline_width},{style_config.shadow_depth},{style_config.alignment},10,10,{style_config.margin_v},1
Style: Highlight,{style_config.font_name},{style_config.font_size},{style_config.karaoke_highlight_color},{style_config.secondary_color},{style_config.outline_color},{style_config.back_color},{bold_flag},0,0,0,100,100,0,0,1,{style_config.outline_width},{style_config.shadow_depth},{style_config.alignment},10,10,{style_config.margin_v},1
Style: Keyword,{style_config.font_name},{int(style_config.font_size * 1.15)},{style_config.karaoke_highlight_color},{style_config.secondary_color},{style_config.outline_color},{style_config.back_color},{-1},0,0,0,100,100,0,0,1,{style_config.outline_width + 1},{style_config.shadow_depth},{style_config.alignment},10,10,{style_config.margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    return header


def _build_ass_events(
    segments: List[Segment],
    style_config: ASSStyleConfig,
    keywords: List[str],
    max_chars_per_line: int,
) -> str:
    """构建 ASS 事件行（逐字高亮 + 关键词强调）。"""
    events = []

    for seg in segments:
        if not seg.text.strip():
            continue

        start_t = time_to_ass_format(seg.start_time)
        end_t = time_to_ass_format(seg.end_time)
        duration_cs = int((seg.end_time - seg.start_time) * 100)  # 百分之一秒

        # 检查是否包含关键词
        has_keyword = keywords and any(kw in seg.text for kw in keywords)

        if style_config.enable_karaoke and duration_cs > 0:
            # 逐字高亮模式（卡拉OK效果）
            text_with_karaoke = _build_karaoke_text(
                seg.text, duration_cs, max_chars_per_line
            )
            # 淡入淡出效果
            fade_tag = ""
            if style_config.fade_in_ms > 0 or style_config.fade_out_ms > 0:
                fade_tag = f"{{\\fad({style_config.fade_in_ms},{style_config.fade_out_ms})}}"

            style_name = "Keyword" if has_keyword else "Default"
            event_line = f"Dialogue: 0,{start_t},{end_t},{style_name},,0,0,0,,{fade_tag}{text_with_karaoke}"
            events.append(event_line)
        else:
            # 普通模式（无逐字高亮）
            text = _split_text_to_lines(seg.text, max_chars_per_line).replace("\n", "\\N")
            fade_tag = ""
            if style_config.fade_in_ms > 0 or style_config.fade_out_ms > 0:
                fade_tag = f"{{\\fad({style_config.fade_in_ms},{style_config.fade_out_ms})}}"

            style_name = "Keyword" if has_keyword else "Default"
            event_line = f"Dialogue: 0,{start_t},{end_t},{style_name},,0,0,0,,{fade_tag}{text}"
            events.append(event_line)

    return "\n".join(events) + "\n"


def _build_karaoke_text(text: str, total_duration_cs: int, max_chars_per_line: int) -> str:
    """
    构建卡拉OK逐字高亮文本。

    使用 ASS \\k<duration> 标签，duration 单位为百分之一秒。
    每个字的高亮时长按字符数均匀分配。

    ASS 卡拉OK标签：
    - \\k<dur>  — 普通填充（逐字变色）
    - \\kf<dur> — 平滑渐变高亮
    - \\ko<dur> — 轮廓高亮

    这里使用 \\kf 实现平滑的逐字高亮效果。
    """
    # 清理文本
    clean_text = text.strip()
    if not clean_text:
        return ""

    # 计算每个字符的显示时长（按字符数分配）
    # 中文字符权重为1.5，英文字符权重为0.5
    chars = []
    for ch in clean_text:
        if re.match(r'[一-鿿　-〿＀-￯]', ch):
            chars.append((ch, 1.5))  # 中文字符
        elif ch.strip():
            chars.append((ch, 0.5))  # 英文/数字/标点
        else:
            chars.append((ch, 0.2))  # 空格

    total_weight = sum(w for _, w in chars)
    if total_weight <= 0:
        return clean_text

    # 构建卡拉OK标签
    karaoke_parts = []
    for ch, weight in chars:
        char_duration = max(1, int(total_duration_cs * weight / total_weight))
        karaoke_parts.append(f"{{\\kf{char_duration}}}{ch}")

    karaoke_text = "".join(karaoke_parts)

    # 处理换行：如果文本过长，在合适位置插入 \\N
    if len(clean_text) > max_chars_per_line:
        # 在卡拉OK文本中按字符数插入换行
        result_lines = []
        current_line = ""
        char_count = 0
        # 解析卡拉OK文本，按可见字符计数
        parts = re.split(r'(\\{[^}]*\\kf\d+\\})', karaoke_text)
        visible_count = 0
        for part in parts:
            if re.match(r'\\{[^}]*\\kf\d+\\}', part):
                current_line += part
            else:
                for ch in part:
                    current_line += ch
                    if ch not in (' ', '\n', '\\'):
                        visible_count += 1
                    if visible_count >= max_chars_per_line:
                        result_lines.append(current_line)
                        current_line = ""
                        visible_count = 0
        if current_line:
            result_lines.append(current_line)
        karaoke_text = "\\N".join(result_lines)

    return karaoke_text


# ============================================================================
# 文本换行工具
# ============================================================================

def _split_text_to_lines(text: str, max_chars: int) -> str:
    """
    将文本按最大字符数自动换行。

    对中文按字数切分，对英文按单词切分。
    """
    if not text:
        return ""

    if len(text) <= max_chars:
        return text

    # 检测是否主要是中文
    chinese_chars = len(re.findall(r'[一-鿿]', text))
    is_chinese = chinese_chars > len(text) * 0.3

    if is_chinese:
        result_lines = []
        current_line = ""
        for char in text:
            current_line += char
            if len(current_line) >= max_chars:
                result_lines.append(current_line)
                current_line = ""
        if current_line:
            result_lines.append(current_line)
        return "\n".join(result_lines)
    else:
        words = text.split()
        result_lines = []
        current_line = ""
        for word in words:
            test_line = f"{current_line} {word}".strip() if current_line else word
            if len(test_line) > max_chars and current_line:
                result_lines.append(current_line)
                current_line = word
            else:
                current_line = test_line
        if current_line:
            result_lines.append(current_line)
        return "\n".join(result_lines)


# ============================================================================
# SRT 解析
# ============================================================================

def parse_srt(srt_path: str) -> List[dict]:
    """
    解析 SRT 文件。

    Returns:
        list of dict: [{"index": 1, "start": "00:00:00,000", "end": "00:00:01,000", "text": "..."}]
    """
    if not os.path.exists(srt_path):
        raise FileNotFoundError(f"SRT 文件不存在: {srt_path}")

    with open(srt_path, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = r'(\d+)\n(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})\n(.*?)(?=\n\n|\n\d+\n|\Z)'
    matches = re.findall(pattern, content, re.DOTALL)

    result = []
    for match in matches:
        index, start, end, text = match
        result.append({
            "index": int(index),
            "start": start.strip(),
            "end": end.strip(),
            "text": text.strip().replace("\n", " "),
        })

    return result


def srt_time_to_seconds(time_str: str) -> float:
    """将 SRT 时间格式 (HH:MM:SS,mmm) 转换为秒数。"""
    match = re.match(r'(\d{2}):(\d{2}):(\d{2}),(\d{3})', time_str)
    if not match:
        return 0.0
    hours, minutes, seconds, millis = match.groups()
    return (
        int(hours) * 3600 +
        int(minutes) * 60 +
        int(seconds) +
        int(millis) / 1000
    )


def parse_ass(ass_path: str) -> List[dict]:
    """
    解析 ASS 文件的事件行。

    Returns:
        list of dict: [{"start": "0:00:00.00", "end": "0:00:01.00", "style": "Default", "text": "..."}]
    """
    if not os.path.exists(ass_path):
        raise FileNotFoundError(f"ASS 文件不存在: {ass_path}")

    with open(ass_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 提取 Events 部分
    events_match = re.search(r'\[Events\]\s*\n(.*?)(?=\[|\Z)', content, re.DOTALL)
    if not events_match:
        return []

    events_text = events_match.group(1)
    result = []

    for line in events_text.strip().split("\n"):
        if line.startswith("Dialogue:"):
            # Dialogue: 0,0:00:00.00,0:00:01.00,Default,,0,0,0,,text
            parts = line.split(",", 9)
            if len(parts) >= 10:
                result.append({
                    "start": parts[1].strip(),
                    "end": parts[2].strip(),
                    "style": parts[3].strip(),
                    "text": parts[9].strip().replace("\\N", "\n").replace("\\n", "\n"),
                })

    return result


def ass_time_to_seconds(time_str: str) -> float:
    """将 ASS 时间格式 (H:MM:SS.CC) 转换为秒数。"""
    match = re.match(r'(\d+):(\d{2}):(\d{2})\.(\d{2})', time_str)
    if not match:
        return 0.0
    hours, minutes, seconds, centiseconds = match.groups()
    return (
        int(hours) * 3600 +
        int(minutes) * 60 +
        int(seconds) +
        int(centiseconds) / 100
    )
