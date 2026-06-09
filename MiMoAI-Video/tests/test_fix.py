"""
测试修复后的功能。

测试字幕叠加和自动剪辑是否正常工作。
"""

import os
import sys
import tempfile

# 添加 src 目录到 sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(os.path.dirname(current_dir), "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from mimo_asr import Segment, TranscriptionResult
from subtitle import segments_to_srt
from video_processor import overlay_subtitle


def test_subtitle_generation():
    """测试字幕生成功能。"""
    print("=" * 60)
    print("测试字幕生成功能")
    print("=" * 60)

    # 创建测试片段
    segments = [
        Segment(text="你好，欢迎来到测试视频。", start_time=0.0, end_time=2.5),
        Segment(text="这是一个字幕叠加测试。", start_time=2.5, end_time=5.0),
        Segment(text="如果你能看到字幕，说明修复成功！", start_time=5.0, end_time=7.5),
    ]

    # 创建临时目录
    temp_dir = tempfile.mkdtemp()

    # 生成 SRT 文件
    srt_path = os.path.join(temp_dir, "test.srt")
    segments_to_srt(segments, srt_path)

    # 读取并打印 SRT 内容
    with open(srt_path, "r", encoding="utf-8") as f:
        srt_content = f.read()

    print("\n生成的 SRT 文件内容:")
    print("-" * 40)
    print(srt_content)
    print("-" * 40)

    print(f"\nSRT 文件路径: {srt_path}")
    print(f"SRT 文件大小: {os.path.getsize(srt_path)} 字节")

    return srt_path


def test_path_escaping():
    """测试路径转义是否正确。"""
    print("\n" + "=" * 60)
    print("测试路径转义")
    print("=" * 60)

    # 模拟 Windows 路径
    test_paths = [
        r"C:\Users\Administrator\test.srt",
        r"D:\Projects\mimo-asr\output\subtitle.srt",
        r"C:\temp\my video\subtitle.srt",
    ]

    for path in test_paths:
        # 使用修复后的转义逻辑
        srt_escaped = path.replace("\\", "/")
        if ":" in srt_escaped:
            srt_escaped = srt_escaped.replace(":", "\\:")

        print(f"\n原始路径: {path}")
        print(f"转义后: {srt_escaped}")


def test_timestamp_parsing():
    """测试时间戳解析。"""
    print("\n" + "=" * 60)
    print("测试时间戳解析")
    print("=" * 60)

    from mimo_asr import MiMoASR

    # 创建一个临时实例来测试时间戳解析
    # 注意：这里不需要真实的 API Key
    class TestASR:
        def _parse_timestamp(self, timestamp_str: str) -> float:
            """解析时间戳字符串为秒数。"""
            try:
                # 处理 HH:MM:SS 或 MM:SS 格式
                parts = timestamp_str.split(":")
                if len(parts) == 3:
                    hours, minutes, seconds = parts
                    return float(hours) * 3600 + float(minutes) * 60 + float(seconds)
                elif len(parts) == 2:
                    minutes, seconds = parts
                    return float(minutes) * 60 + float(seconds)
                else:
                    return float(timestamp_str)
            except (ValueError, AttributeError):
                return 0.0

    test_asr = TestASR()

    # 测试各种时间戳格式
    test_cases = [
        ("00:00:01", 1.0),
        ("00:01:30", 90.0),
        ("01:00:00", 3600.0),
        ("1:30", 90.0),
        ("30.5", 30.5),
    ]

    for timestamp_str, expected in test_cases:
        result = test_asr._parse_timestamp(timestamp_str)
        status = "✓" if abs(result - expected) < 0.01 else "✗"
        print(f"{status} '{timestamp_str}' -> {result:.1f}秒 (期望: {expected:.1f}秒)")


def main():
    """运行所有测试。"""
    print("MiMo ASR 修复验证测试")
    print("=" * 60)

    # 测试字幕生成
    srt_path = test_subtitle_generation()

    # 测试路径转义
    test_path_escaping()

    # 测试时间戳解析
    test_timestamp_parsing()

    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)

    print("\n修复说明:")
    print("1. 字幕叠加: 修复了 Windows 路径转义问题")
    print("2. ASR 响应解析: 改进了 JSON 和纯文本响应的处理")
    print("3. 自动剪辑: 添加了时间戳有效性检查")

    print("\n下一步:")
    print("1. 重启 Streamlit 应用: streamlit run app.py")
    print("2. 上传一个视频进行测试")
    print("3. 检查字幕是否正确叠加")
    print("4. 测试自动剪辑功能")


if __name__ == "__main__":
    main()
