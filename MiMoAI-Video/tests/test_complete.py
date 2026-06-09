"""
完整功能测试脚本。

测试字幕叠加和自动剪辑功能。
"""

import os
import sys
import tempfile
import subprocess

# 添加 src 目录到 sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(os.path.dirname(current_dir), "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from mimo_asr import Segment, TranscriptionResult
from subtitle import segments_to_srt
from video_processor import overlay_subtitle, get_ffmpeg_binary


def create_test_video():
    """创建一个简单的测试视频。"""
    print("创建测试视频...")

    ffmpeg = get_ffmpeg_binary()
    temp_dir = tempfile.mkdtemp()
    video_path = os.path.join(temp_dir, "test_video.mp4")

    # 创建一个5秒的测试视频（带音频）
    command = [
        ffmpeg, "-y",
        "-f", "lavfi", "-i", "color=c=blue:s=640x480:d=5",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=5",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
        "-c:a", "aac",
        "-shortest",
        video_path,
    ]

    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        print(f"创建测试视频失败: {result.stderr}")
        return None

    print(f"测试视频创建成功: {video_path}")
    return video_path


def test_subtitle_overlay(video_path):
    """测试字幕叠加功能。"""
    print("\n" + "=" * 60)
    print("测试字幕叠加功能")
    print("=" * 60)

    # 创建测试片段
    segments = [
        Segment(text="你好，欢迎来到测试视频。", start_time=0.0, end_time=2.0),
        Segment(text="这是一个字幕叠加测试。", start_time=2.0, end_time=4.0),
        Segment(text="如果你能看到字幕，说明修复成功！", start_time=4.0, end_time=5.0),
    ]

    # 创建临时目录
    temp_dir = tempfile.mkdtemp()

    # 生成 SRT 文件
    srt_path = os.path.join(temp_dir, "test.srt")
    segments_to_srt(segments, srt_path)

    print(f"SRT 文件: {srt_path}")

    # 读取并打印 SRT 内容
    with open(srt_path, "r", encoding="utf-8") as f:
        srt_content = f.read()

    print("\nSRT 内容:")
    print("-" * 40)
    print(srt_content)
    print("-" * 40)

    # 测试字幕叠加
    output_path = os.path.join(temp_dir, "output_with_subtitle.mp4")

    try:
        overlay_subtitle(
            video_path,
            srt_path,
            output_path,
            font_size=36,
            font_color="&HFFFFFF",  # 白色
            outline_color="&H000000",  # 黑色
            outline_width=2,
            position="bottom",
        )

        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(f"\n[OK] 字幕视频生成成功!")
            print(f"  输出路径: {output_path}")
            print(f"  文件大小: {file_size} 字节")
            return output_path
        else:
            print("\n[FAIL] 字幕视频生成失败: 文件不存在")
            return None

    except Exception as e:
        print(f"\n[FAIL] 字幕叠加失败: {e}")
        return None


def test_auto_edit_logic():
    """测试自动剪辑逻辑。"""
    print("\n" + "=" * 60)
    print("测试自动剪辑逻辑")
    print("=" * 60)

    from auto_editor import AutoEditConfig, analyze_segments_rhythm

    # 测试用例1: 有效时间戳
    segments_valid = [
        Segment(text="片段1", start_time=0.0, end_time=2.0),
        Segment(text="片段2", start_time=2.0, end_time=4.0),
        Segment(text="片段3", start_time=4.0, end_time=6.0),
    ]

    config = AutoEditConfig.douyin_style()
    edit_segments = analyze_segments_rhythm(segments_valid, config)

    print("\n测试用例1: 有效时间戳")
    print(f"  输入片段数: {len(segments_valid)}")
    print(f"  输出编辑片段数: {len(edit_segments)}")
    if edit_segments:
        print(f"  第一个片段: {edit_segments[0].start_time:.1f}s - {edit_segments[0].end_time:.1f}s")

    # 测试用例2: 无效时间戳（都是0）
    segments_invalid = [
        Segment(text="片段1", start_time=0.0, end_time=0.0),
        Segment(text="片段2", start_time=0.0, end_time=0.0),
    ]

    print("\n测试用例2: 无效时间戳")
    edit_segments_invalid = analyze_segments_rhythm(segments_invalid, config)
    print(f"  输入片段数: {len(segments_invalid)}")
    print(f"  输出编辑片段数: {len(edit_segments_invalid)}")

    return len(edit_segments) > 0


def main():
    """运行所有测试。"""
    print("MiMo ASR 功能测试")
    print("=" * 60)

    # 创建测试视频
    video_path = create_test_video()
    if not video_path:
        print("无法创建测试视频，跳过后续测试")
        return

    # 测试字幕叠加
    subtitle_video = test_subtitle_overlay(video_path)

    # 测试自动剪辑逻辑
    auto_edit_ok = test_auto_edit_logic()

    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    if subtitle_video:
        print("[OK] 字幕叠加: 成功")
    else:
        print("[FAIL] 字幕叠加: 失败")

    if auto_edit_ok:
        print("[OK] 自动剪辑逻辑: 正常")
    else:
        print("[FAIL] 自动剪辑逻辑: 异常")

    print("\n修复说明:")
    print("1. 修复了 Windows 路径转义问题（使用正斜杠）")
    print("2. 改进了 ASR 响应解析（支持多种格式）")
    print("3. 添加了时间戳有效性检查")

    print("\n下一步:")
    print("1. 重启 Streamlit 应用: streamlit run app.py")
    print("2. 上传一个视频进行测试")
    print("3. 检查字幕是否正确叠加")


if __name__ == "__main__":
    main()
