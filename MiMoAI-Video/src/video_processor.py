"""
视频处理模块。

使用 FFmpeg 进行音频提取、字幕叠加、转场效果、钩子文字等操作。
支持 SRT 和 ASS 两种字幕格式。
"""

import json
import os
import subprocess
import sys
import tempfile
from typing import List, Optional

from config import get_ffmpeg_binary


def get_video_info(video_path: str) -> dict:
    """
    获取视频基本信息。

    Returns:
        dict: {"width", "height", "duration", "fps", "codec"}
    """
    ffprobe = get_ffmpeg_binary().replace("ffmpeg", "ffprobe")
    if not os.path.exists(ffprobe):
        ffprobe = "ffprobe"

    command = [
        ffprobe,
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        video_path,
    ]

    try:
        result = subprocess.run(
            command, capture_output=True, text=True, check=True
        )
        data = json.loads(result.stdout)

        # 查找视频流
        video_stream = None
        audio_stream = None
        for stream in data.get("streams", []):
            if stream.get("codec_type") == "video" and not video_stream:
                video_stream = stream
            elif stream.get("codec_type") == "audio" and not audio_stream:
                audio_stream = stream

        if not video_stream:
            raise ValueError("未找到视频流")

        # 提取信息
        width = int(video_stream.get("width", 0))
        height = int(video_stream.get("height", 0))

        # FPS (优先使用 avg_frame_rate，更准确；r_frame_rate 可能不准确)
        fps_str = video_stream.get("avg_frame_rate", video_stream.get("r_frame_rate", "30/1"))
        if "/" in fps_str:
            num, den = fps_str.split("/")
            fps = float(num) / float(den) if float(den) > 0 else 30.0
        else:
            fps = float(fps_str)
        # 合理性检查：FPS 应在 1-240 之间
        if fps > 240 or fps < 1:
            fps_str2 = video_stream.get("r_frame_rate", "30/1")
            if "/" in fps_str2:
                num, den = fps_str2.split("/")
                fps = float(num) / float(den) if float(den) > 0 else 30.0
            if fps > 240 or fps < 1:
                fps = 30.0

        # 时长
        duration = float(data.get("format", {}).get("duration", 0))
        if not duration:
            duration = float(video_stream.get("duration", 0))

        return {
            "width": width,
            "height": height,
            "duration": duration,
            "fps": fps,
            "codec": video_stream.get("codec_name", ""),
            "has_audio": audio_stream is not None,
        }

    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"FFprobe 调用失败: {e.stderr}")
    except (json.JSONDecodeError, KeyError) as e:
        raise RuntimeError(f"解析视频信息失败: {e}")


def extract_audio(
    video_path: str,
    output_path: str,
    sample_rate: int = 16000,
) -> str:
    """
    从视频中提取音频。

    使用 16kHz 单声道 WAV 格式，这是语音识别的推荐格式。
    """
    ffmpeg = get_ffmpeg_binary()

    command = [
        ffmpeg,
        "-y",                    # 覆盖输出文件
        "-i", video_path,
        "-vn",                   # 不要视频流
        "-acodec", "pcm_s16le",  # 16-bit PCM
        "-ar", str(sample_rate), # 采样率
        "-ac", "1",              # 单声道
        output_path,
    ]

    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        error_msg = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"音频提取失败: {error_msg}")

    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        raise RuntimeError(f"提取的音频文件为空: {output_path}")

    return output_path


def overlay_subtitle(
    video_path: str,
    srt_path: str,
    output_path: str,
    font_name: str = "Microsoft YaHei",
    font_size: int = 48,
    font_color: str = "&HFFFFFF",
    outline_color: str = "&H000000",
    outline_width: int = 3,
    position: str = "bottom",
    margin_v: int = 60,
) -> str:
    """
    将字幕叠加到视频上。

    Args:
        video_path: 输入视频路径
        srt_path: SRT 字幕文件路径
        output_path: 输出视频路径
        font_name: 字体名称
        font_size: 字号
        font_color: 字体颜色 (ASS 格式)
        outline_color: 描边颜色 (ASS 格式)
        outline_width: 描边宽度
        position: 位置 ("bottom", "center", "top")
        margin_v: 垂直边距

    Returns:
        输出文件路径
    """
    ffmpeg = get_ffmpeg_binary()

    # 验证输入文件存在
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"视频文件不存在: {video_path}")
    if not os.path.exists(srt_path):
        raise FileNotFoundError(f"字幕文件不存在: {srt_path}")

    # 读取 SRT 内容并验证
    with open(srt_path, "r", encoding="utf-8") as f:
        srt_content = f.read()
    if not srt_content.strip():
        raise ValueError("字幕文件为空")

    print(f"字幕文件内容预览: {srt_content[:200]}...")

    # 转换 SRT 路径为 FFmpeg 兼容格式
    # FFmpeg subtitles 滤镜中，冒号是选项分隔符，需要转义
    # 步骤1: 将反斜杠替换为正斜杠
    srt_escaped = srt_path.replace("\\", "/")
    # 步骤2: 转义冒号（Windows 路径如 C:/...）
    srt_escaped = srt_escaped.replace(":", "\\:")

    # 构建字幕样式
    # ASS 颜色格式: &HBBGGRR (注意顺序是 BGR)
    style = (
        f"FontName={font_name},"
        f"FontSize={font_size},"
        f"PrimaryColour={font_color},"
        f"OutlineColour={outline_color},"
        f"Outline={outline_width},"
        f"Shadow=1,"
        f"Alignment={_get_alignment(position)},"
        f"MarginV={margin_v}"
    )

    # 使用 subtitles 滤镜（注意路径需要用单引号包裹）
    filter_str = f"subtitles='{srt_escaped}':force_style='{style}'"

    print(f"FFmpeg 字幕滤镜: {filter_str}")

    command = [
        ffmpeg,
        "-y",
        "-i", video_path,
        "-vf", filter_str,
        "-c:a", "copy",          # 保持音频不变
        "-c:v", "libx264",       # 视频编码
        "-preset", "medium",
        "-crf", "23",
        output_path,
    ]

    print(f"执行 FFmpeg 命令: {' '.join(command)}")

    result = subprocess.run(command, capture_output=True, text=True, check=False)

    print(f"FFmpeg 返回码: {result.returncode}")
    if result.stdout:
        print(f"FFmpeg stdout: {result.stdout[:500]}")
    if result.stderr:
        print(f"FFmpeg stderr: {result.stderr[:500]}")

    if result.returncode != 0:
        error_msg = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"字幕叠加失败: {error_msg}")

    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        raise RuntimeError(f"输出视频文件为空: {output_path}")

    print(f"字幕视频生成成功: {output_path}")
    return output_path


def _get_alignment(position: str) -> int:
    """
    将位置字符串转换为 ASS 对齐值。

    ASS 对齐值 (小键盘布局):
    7 8 9
    4 5 6
    1 2 3
    """
    alignment_map = {
        "bottom": 2,    # 底部居中
        "center": 5,    # 中间居中
        "top": 8,       # 顶部居中
    }
    return alignment_map.get(position, 2)


def change_video_speed(
    video_path: str,
    output_path: str,
    speed: float = 1.0,
) -> str:
    """
    改变视频播放速度。

    Args:
        speed: 速度倍率，如 1.5 表示 1.5 倍速
    """
    if speed <= 0 or speed > 4:
        raise ValueError("速度倍率必须在 0 到 4 之间")

    ffmpeg = get_ffmpeg_binary()

    # 视频速度: setpts=PTS/speed
    # 音频速度: atempo=speed
    video_filter = f"setpts={1/speed}*PTS"

    # atempo 只支持 0.5-2.0，超出范围需要链式调用
    audio_filters = []
    remaining_speed = speed
    while remaining_speed > 2.0:
        audio_filters.append("atempo=2.0")
        remaining_speed /= 2.0
    while remaining_speed < 0.5:
        audio_filters.append("atempo=0.5")
        remaining_speed /= 0.5
    audio_filters.append(f"atempo={remaining_speed}")

    audio_filter = ",".join(audio_filters)

    command = [
        ffmpeg,
        "-y",
        "-i", video_path,
        "-vf", video_filter,
        "-af", audio_filter,
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        output_path,
    ]

    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        error_msg = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"速度调整失败: {error_msg}")

    return output_path


def concatenate_videos(
    video_paths: list,
    output_path: str,
) -> str:
    """
    拼接多个视频片段。
    """
    if not video_paths:
        raise ValueError("视频列表为空")

    if len(video_paths) == 1:
        import shutil
        shutil.copy2(video_paths[0], output_path)
        return output_path

    ffmpeg = get_ffmpeg_binary()

    # 创建临时文件列表
    list_file = output_path + ".list.txt"
    with open(list_file, "w", encoding="utf-8") as f:
        for path in video_paths:
            # FFmpeg concat 协议需要转义单引号
            escaped = path.replace("'", "'\\''")
            f.write(f"file '{escaped}'\n")

    command = [
        ffmpeg,
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", list_file,
        "-c", "copy",
        output_path,
    ]

    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            error_msg = (result.stderr or result.stdout or "").strip()
            raise RuntimeError(f"视频拼接失败: {error_msg}")
    finally:
        if os.path.exists(list_file):
            os.remove(list_file)

    return output_path


def crop_to_vertical(
    video_path: str,
    output_path: str,
    target_ratio: float = 9 / 16,
) -> str:
    """
    将视频裁剪为竖屏比例（如 9:16）。

    自动从中心裁剪。
    """
    ffmpeg = get_ffmpeg_binary()

    # 获取视频信息
    info = get_video_info(video_path)
    width = info["width"]
    height = info["height"]

    current_ratio = width / height

    if abs(current_ratio - target_ratio) < 0.01:
        # 比例已经正确
        import shutil
        shutil.copy2(video_path, output_path)
        return output_path

    if current_ratio > target_ratio:
        # 视频太宽，需要裁剪宽度
        new_width = int(height * target_ratio)
        crop_filter = f"crop={new_width}:{height}:(iw-{new_width})/2:0"
    else:
        # 视频太高，需要裁剪高度
        new_height = int(width / target_ratio)
        crop_filter = f"crop={width}:{new_height}:0:(ih-{new_height})/2"

    command = [
        ffmpeg,
        "-y",
        "-i", video_path,
        "-vf", crop_filter,
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        "-c:a", "copy",
        output_path,
    ]

    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        error_msg = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"视频裁剪失败: {error_msg}")

    return output_path


# ============================================================================
# ASS 字幕叠加
# ============================================================================

def overlay_ass_subtitle(
    video_path: str,
    ass_path: str,
    output_path: str,
) -> str:
    """
    将 ASS 字幕叠加到视频上。

    使用 FFmpeg 的 ass 滤镜，支持逐字高亮、动画等高级特性。

    Args:
        video_path: 输入视频路径
        ass_path: ASS 字幕文件路径
        output_path: 输出视频路径

    Returns:
        输出文件路径
    """
    ffmpeg = get_ffmpeg_binary()

    if not os.path.exists(video_path):
        raise FileNotFoundError(f"视频文件不存在: {video_path}")
    if not os.path.exists(ass_path):
        raise FileNotFoundError(f"ASS 字幕文件不存在: {ass_path}")

    # 转换路径为 FFmpeg 兼容格式
    ass_escaped = ass_path.replace("\\", "/").replace(":", "\\:")

    filter_str = f"ass='{ass_escaped}'"

    print(f"FFmpeg ASS 滤镜: {filter_str}")

    command = [
        ffmpeg, "-y",
        "-i", video_path,
        "-vf", filter_str,
        "-c:a", "copy",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        output_path,
    ]

    result = subprocess.run(command, capture_output=True, text=True, check=False)

    if result.returncode != 0:
        error_msg = (result.stderr or result.stdout or "").strip()
        # 如果 ass 滤镜失败，回退到 subtitles 滤镜
        print(f"ASS 滤镜失败 ({error_msg})，尝试回退到 subtitles 滤镜...")
        return _fallback_subtitle_overlay(video_path, ass_path, output_path)

    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        raise RuntimeError(f"输出视频文件为空: {output_path}")

    print(f"ASS 字幕视频生成成功: {output_path}")
    return output_path


def _fallback_subtitle_overlay(
    video_path: str,
    subtitle_path: str,
    output_path: str,
) -> str:
    """回退方案：使用 subtitles 滤镜叠加字幕。"""
    ffmpeg = get_ffmpeg_binary()
    sub_escaped = subtitle_path.replace("\\", "/").replace(":", "\\:")
    filter_str = f"subtitles='{sub_escaped}'"

    command = [
        ffmpeg, "-y",
        "-i", video_path,
        "-vf", filter_str,
        "-c:a", "copy",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        output_path,
    ]

    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        error_msg = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"字幕叠加失败: {error_msg}")

    return output_path


# ============================================================================
# 视频转场效果
# ============================================================================

def add_fade_transition(
    video_path: str,
    output_path: str,
    fade_in_duration: float = 0.3,
    fade_out_duration: float = 0.3,
) -> str:
    """
    为视频添加淡入淡出效果。

    Args:
        video_path: 输入视频路径
        output_path: 输出视频路径
        fade_in_duration: 淡入时长（秒）
        fade_out_duration: 淡出时长（秒）

    Returns:
        输出文件路径
    """
    ffmpeg = get_ffmpeg_binary()
    info = get_video_info(video_path)
    duration = info["duration"]

    # 构建滤镜链
    vf_parts = []
    af_parts = []

    if fade_in_duration > 0:
        vf_parts.append(f"fade=t=in:st=0:d={fade_in_duration}")
        af_parts.append(f"afade=t=in:st=0:d={fade_in_duration}")

    if fade_out_duration > 0:
        fade_out_start = max(0, duration - fade_out_duration)
        vf_parts.append(f"fade=t=out:st={fade_out_start}:d={fade_out_duration}")
        af_parts.append(f"afade=t=out:st={fade_out_start}:d={fade_out_duration}")

    vf = ",".join(vf_parts) if vf_parts else None
    af = ",".join(af_parts) if af_parts else None

    command = [ffmpeg, "-y", "-i", video_path]
    if vf:
        command.extend(["-vf", vf])
    if af:
        command.extend(["-af", af])
    command.extend([
        "-c:v", "libx264", "-preset", "medium", "-crf", "23",
        output_path,
    ])

    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        error_msg = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"淡入淡出添加失败: {error_msg}")

    return output_path


def apply_fade_to_clips(
    clip_paths: List[str],
    fade_in_duration: float = 0.2,
    fade_out_duration: float = 0.2,
    temp_dir: str = "",
) -> List[str]:
    """
    为多个视频片段分别添加淡入淡出效果。

    Args:
        clip_paths: 视频片段路径列表
        fade_in_duration: 淡入时长（秒）
        fade_out_duration: 淡出时长（秒）
        temp_dir: 临时目录

    Returns:
        添加效果后的片段路径列表
    """
    if not temp_dir:
        temp_dir = tempfile.mkdtemp()

    result_paths = []
    for i, clip_path in enumerate(clip_paths):
        faded_path = os.path.join(temp_dir, f"faded_{i:04d}.mp4")
        try:
            add_fade_transition(clip_path, faded_path, fade_in_duration, fade_out_duration)
            result_paths.append(faded_path)
        except Exception as e:
            print(f"警告: 片段 {i} 淡入淡出失败 ({e})，使用原片段")
            result_paths.append(clip_path)

    return result_paths


# ============================================================================
# 视频钩子文字（开头吸引力 + 结尾引导）
# ============================================================================

def add_video_hook(
    video_path: str,
    output_path: str,
    hook_text: str = "看到最后，有惊喜！",
    duration: float = 3.0,
    font_size: int = 60,
    font_color: str = "yellow",
    position: str = "center",
) -> str:
    """
    在视频开头添加钩子文字（黄金3秒吸引注意力）。

    使用 FFmpeg drawtext 滤镜在视频开头叠加醒目的文字。

    Args:
        video_path: 输入视频路径
        output_path: 输出视频路径
        hook_text: 钩子文字内容
        duration: 文字显示时长（秒）
        font_size: 字体大小
        font_color: 字体颜色
        position: 位置 ("center", "top", "bottom")

    Returns:
        输出文件路径
    """
    ffmpeg = get_ffmpeg_binary()

    # 位置计算
    if position == "center":
        y_expr = "(h-text_h)/2"
    elif position == "top":
        y_expr = "h*0.15"
    else:  # bottom
        y_expr = "h*0.80"

    # 转义特殊字符
    escaped_text = hook_text.replace("'", "\\'").replace(":", "\\:")
    escaped_text = escaped_text.replace("\\", "\\\\")

    # drawtext 滤镜：前 duration 秒显示文字，带淡入淡出
    filter_str = (
        f"drawtext=text='{escaped_text}'"
        f":fontsize={font_size}"
        f":fontcolor={font_color}"
        f":borderw=3"
        f":bordercolor=black"
        f":x=(w-text_w)/2"
        f":y={y_expr}"
        f":enable='between(t,0,{duration})'"
        f":alpha='if(lt(t,0.3),t/0.3,if(gt(t,{duration-0.3}),(({duration}-t)/0.3),1))'"
    )

    command = [
        ffmpeg, "-y",
        "-i", video_path,
        "-vf", filter_str,
        "-c:a", "copy",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        output_path,
    ]

    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        error_msg = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"钩子文字添加失败: {error_msg}")

    return output_path


def add_ending_guide(
    video_path: str,
    output_path: str,
    guide_text: str = "关注不迷路 ❤️ 点赞+收藏",
    duration: float = 2.0,
    font_size: int = 52,
    font_color: str = "white",
    bg_opacity: float = 0.6,
) -> str:
    """
    在视频结尾添加引导文字（关注、点赞、收藏）。

    Args:
        video_path: 输入视频路径
        output_path: 输出视频路径
        guide_text: 引导文字
        duration: 显示时长（秒）
        font_size: 字体大小
        font_color: 字体颜色
        bg_opacity: 背景透明度

    Returns:
        输出文件路径
    """
    ffmpeg = get_ffmpeg_binary()
    info = get_video_info(video_path)
    video_duration = info["duration"]

    start_time = max(0, video_duration - duration)

    # 转义特殊字符
    escaped_text = guide_text.replace("'", "\\'").replace(":", "\\:")
    escaped_text = escaped_text.replace("\\", "\\\\")

    # 使用 drawbox + drawtext 实现半透明背景 + 文字
    filter_str = (
        f"drawbox=x=0:y=ih*0.35:w=iw:h=ih*0.3"
        f":color=black@{bg_opacity}:t=fill"
        f":enable='between(t,{start_time},{video_duration})',"
        f"drawtext=text='{escaped_text}'"
        f":fontsize={font_size}"
        f":fontcolor={font_color}"
        f":borderw=2"
        f":bordercolor=black"
        f":x=(w-text_w)/2"
        f":y=(h-text_h)/2"
        f":enable='between(t,{start_time},{video_duration})'"
        f":alpha='if(lt(t-{start_time},0.3),(t-{start_time})/0.3,if(gt(t,{video_duration-0.3}),(({video_duration}-t)/0.3),1))'"
    )

    command = [
        ffmpeg, "-y",
        "-i", video_path,
        "-vf", filter_str,
        "-c:a", "copy",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        output_path,
    ]

    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        error_msg = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"结尾引导添加失败: {error_msg}")

    return output_path


# ============================================================================
# 统一字幕叠加接口
# ============================================================================

def overlay_subtitle_auto(
    video_path: str,
    subtitle_path: str,
    output_path: str,
    subtitle_format: str = "ass",
    **kwargs,
) -> str:
    """
    统一字幕叠加接口，根据格式自动选择处理方式。

    Args:
        video_path: 输入视频路径
        subtitle_path: 字幕文件路径（SRT 或 ASS）
        output_path: 输出视频路径
        subtitle_format: 字幕格式 ("srt" 或 "ass")
        **kwargs: 传递给 overlay_subtitle() 的额外参数（仅 SRT 格式时使用）

    Returns:
        输出文件路径
    """
    if subtitle_format.lower() == "ass":
        return overlay_ass_subtitle(video_path, subtitle_path, output_path)
    else:
        return overlay_subtitle(video_path, subtitle_path, output_path, **kwargs)
