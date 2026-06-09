"""
抖音风格自动剪辑模块。

功能：
1. 静音检测与移除 - 去掉停顿和无意义的静音
2. 语速优化 - 加快慢节奏部分
3. 黄金3秒优化 - 确保开头抓人眼球
4. 节奏感优化 - 符合抖音快节奏风格
5. 转场效果 - 片段间淡入淡出，消除跳切感
6. 结尾引导 - 添加关注/点赞引导文字
"""

import json
import math
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from config import get_ffmpeg_binary
from mimo_asr import Segment, TranscriptionResult
from video_processor import get_video_info


@dataclass
class SilenceSegment:
    """静音片段。"""
    start_time: float
    end_time: float

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time


@dataclass
class EditSegment:
    """编辑片段（用于重新拼接）。"""
    start_time: float
    end_time: float
    speed: float = 1.0  # 播放速度倍率
    keep: bool = True    # 是否保留

    @property
    def original_duration(self) -> float:
        return self.end_time - self.start_time

    @property
    def output_duration(self) -> float:
        return self.original_duration / self.speed if self.keep else 0


@dataclass
class AutoEditConfig:
    """自动剪辑配置（抖音风格）。"""
    # 静音检测
    silence_threshold: float = -35.0   # 静音阈值 (dB)，越低越严格
    min_silence_duration: float = 0.3  # 最小静音时长（秒），低于此值不处理
    silence_keep_ratio: float = 0.15   # 保留静音的比例（保留一点呼吸感）

    # 语速优化
    enable_speed_up: bool = True       # 是否启用智能加速
    max_speed: float = 1.3             # 最大加速倍率
    slow_threshold: float = 2.0        # 慢节奏阈值（秒），超过此值的片段可能需要加速

    # 节奏优化
    enable_rhythm_optimize: bool = True  # 是否启用节奏优化
    target_clip_duration: float = 3.0    # 目标片段时长（秒）

    # 转场效果
    fade_duration: float = 0.2          # 片段间淡入淡出时长（秒）

    # 黄金3秒
    enable_golden_hook: bool = True     # 是否启用黄金3秒优化
    hook_text: str = ""                 # 开头钩子文字（为空则自动选择）
    hook_duration: float = 3.0          # 钩子文字显示时长（秒）

    # 结尾引导
    ending_text: str = ""               # 结尾引导文字（为空则不添加）
    ending_duration: float = 2.0        # 结尾引导显示时长（秒）

    # 输出设置
    output_aspect: str = "9:16"         # 输出比例
    target_duration: float = 0.0        # 目标时长（秒），0 表示不限制

    @classmethod
    def douyin_style(cls) -> "AutoEditConfig":
        """抖音风格默认配置。"""
        return cls(
            silence_threshold=-35.0,
            min_silence_duration=0.3,
            silence_keep_ratio=0.15,
            enable_speed_up=True,
            max_speed=1.3,
            slow_threshold=2.0,
            enable_rhythm_optimize=True,
            target_clip_duration=3.0,
            output_aspect="9:16",
            fade_duration=0.2,
            enable_golden_hook=True,
            hook_text="",
            ending_text="关注不迷路 ❤️ 点赞+收藏",
            ending_duration=2.0,
        )


def detect_silence(
    audio_path: str,
    threshold: float = -35.0,
    min_duration: float = 0.3,
) -> List[SilenceSegment]:
    """
    使用 FFmpeg 检测音频中的静音片段。

    Args:
        audio_path: 音频文件路径
        threshold: 静音阈值 (dB)
        min_duration: 最小静音时长（秒）

    Returns:
        静音片段列表
    """
    ffmpeg = get_ffmpeg_binary()

    command = [
        ffmpeg,
        "-i", audio_path,
        "-af", f"silencedetect=noise={threshold}dB:d={min_duration}",
        "-f", "null",
        "-",
    ]

    result = subprocess.run(command, capture_output=True, text=True, check=False)
    output = result.stderr or result.stdout or ""

    # 解析静音检测结果
    silence_segments = []
    start_time = None

    for line in output.split("\n"):
        if "silence_start:" in line:
            try:
                start_str = line.split("silence_start:")[1].strip().split()[0]
                start_time = float(start_str)
            except (IndexError, ValueError):
                continue
        elif "silence_end:" in line and start_time is not None:
            try:
                end_str = line.split("silence_end:")[1].strip().split()[0]
                end_time = float(end_str)
                silence_segments.append(SilenceSegment(
                    start_time=start_time,
                    end_time=end_time,
                ))
                start_time = None
            except (IndexError, ValueError):
                continue

    return silence_segments


def analyze_segments_rhythm(
    segments: List[Segment],
    config: AutoEditConfig,
) -> List[EditSegment]:
    """
    分析转录片段的节奏，生成编辑方案。

    根据抖音风格：
    - 移除过长的静音
    - 加快慢节奏片段
    - 确保节奏紧凑
    """
    if not segments:
        return []

    edit_segments = []

    # 检查时间戳是否有效
    has_valid_timestamps = any(seg.start_time > 0 or seg.end_time > 0 for seg in segments)
    if not has_valid_timestamps:
        print("警告: ASR 未返回有效的时间戳，自动剪辑将无法正常工作")
        print("提示: 请确保 ASR 返回包含时间戳的 JSON 格式响应")

    for i, seg in enumerate(segments):
        duration = seg.duration

        # 判断是否需要加速
        speed = 1.0
        if config.enable_speed_up and duration > config.slow_threshold:
            # 计算加速倍率，但不超过最大值
            speed = min(config.max_speed, duration / config.target_clip_duration)
            speed = max(1.0, speed)  # 不减速

        edit_segments.append(EditSegment(
            start_time=seg.start_time,
            end_time=seg.end_time,
            speed=speed,
            keep=True,
        ))

    return edit_segments


def generate_edit_plan(
    video_path: str,
    transcription: TranscriptionResult,
    config: AutoEditConfig,
) -> Tuple[List[EditSegment], dict]:
    """
    生成完整的自动剪辑方案。

    Args:
        video_path: 视频文件路径
        transcription: 转录结果
        config: 剪辑配置

    Returns:
        (编辑片段列表, 统计信息)
    """
    # 获取视频信息
    video_info = get_video_info(video_path)
    total_duration = video_info["duration"]

    # 步骤1: 检测静音
    print("正在检测静音片段...")
    # 提取音频用于静音检测
    temp_dir = tempfile.mkdtemp()
    audio_path = os.path.join(temp_dir, "temp_audio.wav")

    from video_processor import extract_audio
    extract_audio(video_path, audio_path)

    silence_segments = detect_silence(
        audio_path,
        threshold=config.silence_threshold,
        min_duration=config.min_silence_duration,
    )

    # 清理临时文件
    if os.path.exists(audio_path):
        os.remove(audio_path)
    if os.path.exists(temp_dir):
        os.rmdir(temp_dir)

    print(f"检测到 {len(silence_segments)} 个静音片段")

    # 步骤2: 基于转录结果生成编辑片段
    edit_segments = analyze_segments_rhythm(
        transcription.segments, config
    )

    # 步骤3: 标记静音区域为移除或缩短
    for silence in silence_segments:
        # 在静音区域中间插入分割点
        mid_time = (silence.start_time + silence.end_time) / 2

        # 查找包含这个静音的编辑片段
        for seg in edit_segments:
            if seg.start_time <= mid_time <= seg.end_time:
                # 如果静音占片段比例较大，缩短它
                silence_ratio = silence.duration / seg.original_duration
                if silence_ratio > 0.3:
                    # 保留一小部分静音（呼吸感）
                    keep_duration = silence.duration * config.silence_keep_ratio
                    # 调整片段边界
                    new_end = silence.start_time + keep_duration
                    if new_end < seg.end_time:
                        seg.end_time = new_end
                break

    # 步骤4: 优化节奏 - 合并过短的片段
    optimized_segments = _optimize_rhythm(edit_segments, config)

    # 计算统计信息
    original_duration = total_duration
    output_duration = sum(seg.output_duration for seg in optimized_segments if seg.keep)

    stats = {
        "original_duration": original_duration,
        "output_duration": output_duration,
        "removed_duration": original_duration - output_duration,
        "compression_ratio": output_duration / original_duration if original_duration > 0 else 1.0,
        "silence_segments_removed": len(silence_segments),
        "segments_count": len(optimized_segments),
    }

    return optimized_segments, stats


def _optimize_rhythm(
    segments: List[EditSegment],
    config: AutoEditConfig,
) -> List[EditSegment]:
    """
    优化节奏：合并过短片段，拆分过长片段。
    """
    if not segments:
        return []

    optimized = []
    buffer_start = None
    buffer_end = None

    for seg in segments:
        if not seg.keep:
            continue

        if buffer_start is None:
            buffer_start = seg.start_time
            buffer_end = seg.end_time
            continue

        # 如果当前片段与缓冲区连续，合并
        if seg.start_time - buffer_end < 0.1:  # 100ms 以内视为连续
            buffer_end = seg.end_time
        else:
            # 输出缓冲区
            duration = buffer_end - buffer_start
            speed = 1.0
            if config.enable_speed_up and duration > config.slow_threshold:
                speed = min(config.max_speed, duration / config.target_clip_duration)
                speed = max(1.0, speed)

            optimized.append(EditSegment(
                start_time=buffer_start,
                end_time=buffer_end,
                speed=speed,
                keep=True,
            ))
            buffer_start = seg.start_time
            buffer_end = seg.end_time

    # 处理最后一个缓冲区
    if buffer_start is not None and buffer_end is not None and buffer_end > buffer_start:
        duration = buffer_end - buffer_start
        speed = 1.0
        if config.enable_speed_up and duration > config.slow_threshold:
            speed = min(config.max_speed, duration / config.target_clip_duration)
            speed = max(1.0, speed)

        optimized.append(EditSegment(
            start_time=buffer_start,
            end_time=buffer_end,
            speed=speed,
            keep=True,
        ))

    return optimized


def apply_auto_edit(
    video_path: str,
    output_path: str,
    edit_segments: List[EditSegment],
    config: AutoEditConfig,
) -> str:
    """
    应用自动剪辑方案，生成新视频。

    处理流程：
    1. 提取各片段
    2. 加速慢节奏片段
    3. 为每个片段添加淡入淡出（消除跳切感）
    4. 拼接所有片段

    Args:
        video_path: 输入视频路径
        output_path: 输出视频路径
        edit_segments: 编辑片段列表
        config: 剪辑配置

    Returns:
        输出文件路径
    """
    ffmpeg = get_ffmpeg_binary()

    # 过滤掉不需要的片段，并验证时间有效性
    keep_segments = []
    for seg in edit_segments:
        if seg.keep and seg.end_time > seg.start_time:
            keep_segments.append(seg)
        elif seg.keep:
            print(f"警告: 跳过无效片段 (start={seg.start_time}, end={seg.end_time})")

    # 如果没有有效片段，可能是 ASR 没有返回时间戳，直接返回原视频
    if not keep_segments:
        print("警告: 没有有效的时间片段，返回原视频")
        import shutil
        shutil.copy2(video_path, output_path)
        return output_path

    # 如果只有一个片段且不需要加速，直接裁剪
    if len(keep_segments) == 1 and keep_segments[0].speed == 1.0:
        seg = keep_segments[0]
        command = [
            ffmpeg, "-y",
            "-i", video_path,
            "-ss", str(seg.start_time),
            "-to", str(seg.end_time),
            "-c", "copy",
            output_path,
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise RuntimeError(f"视频裁剪失败: {result.stderr}")
        return output_path

    # 多片段情况：提取每个片段，然后拼接
    temp_dir = tempfile.mkdtemp()
    temp_clips = []

    try:
        for i, seg in enumerate(keep_segments):
            # 验证时间有效性
            if seg.end_time <= seg.start_time:
                print(f"警告: 跳过无效片段 {i} (start={seg.start_time}, end={seg.end_time})")
                continue

            clip_path = os.path.join(temp_dir, f"clip_{i:04d}.mp4")

            # 提取片段
            command = [
                ffmpeg, "-y",
                "-i", video_path,
                "-ss", str(seg.start_time),
                "-to", str(seg.end_time),
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "23",
                "-c:a", "aac",
                clip_path,
            ]

            result = subprocess.run(command, capture_output=True, text=True, check=False)
            if result.returncode != 0:
                print(f"警告: 片段 {i} 提取失败: {result.stderr}")
                continue

            # 如果需要加速
            if seg.speed > 1.0:
                sped_path = os.path.join(temp_dir, f"sped_{i:04d}.mp4")
                video_filter = f"setpts={1/seg.speed}*PTS"

                # atempo 链式调用
                audio_filters = []
                remaining = seg.speed
                while remaining > 2.0:
                    audio_filters.append("atempo=2.0")
                    remaining /= 2.0
                audio_filters.append(f"atempo={remaining}")
                audio_filter = ",".join(audio_filters)

                command = [
                    ffmpeg, "-y",
                    "-i", clip_path,
                    "-vf", video_filter,
                    "-af", audio_filter,
                    "-c:v", "libx264",
                    "-preset", "fast",
                    "-crf", "23",
                    sped_path,
                ]

                result = subprocess.run(command, capture_output=True, text=True, check=False)
                if result.returncode == 0:
                    os.remove(clip_path)
                    clip_path = sped_path
                else:
                    print(f"警告: 片段 {i} 加速失败，使用原速")

            temp_clips.append(clip_path)

        # 为每个片段添加淡入淡出（消除跳切感）
        if config.fade_duration > 0 and len(temp_clips) > 1:
            print(f"正在添加淡入淡出效果 (时长: {config.fade_duration}s)...")
            from video_processor import apply_fade_to_clips
            temp_clips = apply_fade_to_clips(
                temp_clips,
                fade_in_duration=config.fade_duration,
                fade_out_duration=config.fade_duration,
                temp_dir=temp_dir,
            )

        # 拼接所有片段
        if len(temp_clips) == 1:
            import shutil
            shutil.copy2(temp_clips[0], output_path)
        elif len(temp_clips) > 1:
            # 创建拼接列表
            list_file = os.path.join(temp_dir, "concat_list.txt")
            with open(list_file, "w", encoding="utf-8") as f:
                for clip in temp_clips:
                    escaped = clip.replace("'", "'\\''")
                    f.write(f"file '{escaped}'\n")

            command = [
                ffmpeg, "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", list_file,
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "23",
                "-c:a", "aac",
                output_path,
            ]

            result = subprocess.run(command, capture_output=True, text=True, check=False)
            if result.returncode != 0:
                raise RuntimeError(f"视频拼接失败: {result.stderr}")
        else:
            raise ValueError("没有成功提取的片段")

    finally:
        # 清理临时文件
        for clip in temp_clips:
            if os.path.exists(clip):
                os.remove(clip)
        if os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    return output_path


def auto_edit_video(
    video_path: str,
    output_path: str,
    transcription: TranscriptionResult,
    config: Optional[AutoEditConfig] = None,
) -> Tuple[str, dict]:
    """
    一键自动剪辑视频（抖音风格）。

    完整流程：
    1. 生成剪辑方案（静音检测 + 节奏分析）
    2. 应用剪辑（提取片段 + 加速 + 淡入淡出 + 拼接）
    3. 黄金3秒优化（可选）
    4. 结尾引导（可选）
    5. 画面比例裁剪（可选）

    Args:
        video_path: 输入视频路径
        output_path: 输出视频路径
        transcription: 转录结果
        config: 剪辑配置，默认使用抖音风格

    Returns:
        (输出路径, 统计信息)
    """
    if config is None:
        config = AutoEditConfig.douyin_style()

    # 生成剪辑方案
    edit_segments, stats = generate_edit_plan(
        video_path, transcription, config
    )

    print(f"剪辑方案: {len(edit_segments)} 个片段")
    print(f"原始时长: {stats['original_duration']:.1f}秒")
    print(f"预计输出: {stats['output_duration']:.1f}秒")
    print(f"压缩比: {stats['compression_ratio']:.1%}")

    # 应用剪辑（含淡入淡出转场）
    current_path = output_path
    apply_auto_edit(video_path, current_path, edit_segments, config)

    # 黄金3秒优化：添加开头钩子文字
    if config.enable_golden_hook and config.hook_text:
        print(f"正在添加黄金3秒钩子: {config.hook_text}")
        try:
            from video_processor import add_video_hook
            hook_path = output_path.replace(".mp4", "_hook.mp4")
            add_video_hook(
                current_path, hook_path,
                hook_text=config.hook_text,
                duration=config.hook_duration,
            )
            if current_path != output_path and os.path.exists(current_path):
                os.remove(current_path)
            current_path = hook_path
        except Exception as e:
            print(f"警告: 黄金3秒钩子添加失败: {e}")

    # 结尾引导
    if config.ending_text:
        print(f"正在添加结尾引导: {config.ending_text}")
        try:
            from video_processor import add_ending_guide
            ending_path = output_path.replace(".mp4", "_ending.mp4")
            add_ending_guide(
                current_path, ending_path,
                guide_text=config.ending_text,
                duration=config.ending_duration,
            )
            if current_path != output_path and os.path.exists(current_path):
                os.remove(current_path)
            current_path = ending_path
        except Exception as e:
            print(f"警告: 结尾引导添加失败: {e}")

    # 画面比例裁剪
    if config.output_aspect and config.output_aspect not in ("", "原始"):
        print(f"正在裁剪画面比例: {config.output_aspect}")
        try:
            from video_processor import crop_to_vertical
            ratio_map = {"9:16": 9/16, "16:9": 16/9, "1:1": 1/1}
            target_ratio = ratio_map.get(config.output_aspect, 9/16)
            crop_path = output_path.replace(".mp4", "_crop.mp4")
            crop_to_vertical(current_path, crop_path, target_ratio)
            if current_path != output_path and os.path.exists(current_path):
                os.remove(current_path)
            current_path = crop_path
        except Exception as e:
            print(f"警告: 画面裁剪失败: {e}")

    # 确保最终输出路径正确
    if current_path != output_path:
        import shutil
        shutil.copy2(current_path, output_path)
        if os.path.exists(current_path) and current_path != output_path:
            os.remove(current_path)

    # 更新统计信息
    if os.path.exists(output_path):
        output_info = get_video_info(output_path)
        stats["actual_output_duration"] = output_info["duration"]

    return output_path, stats


def find_hook_sentence(segments: List[Segment]) -> str:
    """
    从转录文本中找到最适合作为开头钩子的句子。

    选择策略：
    1. 包含疑问句（引发好奇心）
    2. 包含感叹句（制造紧迫感）
    3. 包含数字（具体信息更吸引人）
    4. 包含关键词（如"秘密"、"真相"、"必看"等）
    5. 默认选择第一句
    """
    if not segments:
        return ""

    # 钩子关键词
    hook_keywords = [
        "秘密", "真相", "必看", "震惊", "没想到", "竟然", "居然",
        "为什么", "怎么", "如何", "千万别", "一定要", "最后",
        "secret", "shocking", "amazing", "must see", "why", "how",
    ]

    best_score = 0
    best_text = segments[0].text.strip()

    for seg in segments[:5]:  # 只在前5句中选择
        text = seg.text.strip()
        score = 0

        # 疑问句加分
        if any(ch in text for ch in "？?"):
            score += 3
        # 感叹句加分
        if any(ch in text for ch in "！!"):
            score += 2
        # 数字加分
        if re.search(r'\d+', text):
            score += 1
        # 关键词加分
        for kw in hook_keywords:
            if kw in text.lower():
                score += 2
                break
        # 短句加分（钩子不宜太长）
        if len(text) <= 20:
            score += 1

        if score > best_score:
            best_score = score
            best_text = text

    return best_text
