"""测试路径转义。"""

# 测试 Windows 路径
path = r"C:\Users\Administrator\test.srt"
print("原始路径:", path)

# 方法1: 只使用正斜杠
escaped1 = path.replace("\\", "/")
print("方法1 (正斜杠):", escaped1)

# 方法2: 正斜杠 + 转义冒号
escaped2 = escaped1.replace(":", "\\:")
print("方法2 (转义冒号):", escaped2)

# 方法3: 使用 FFmpeg 的路径格式
# FFmpeg 在 Windows 上可以接受正斜杠
escaped3 = path.replace("\\", "/")
print("方法3 (FFmpeg格式):", escaped3)

# 测试 FFmpeg 命令
print("\nFFmpeg 字幕滤镜示例:")
print(f"subtitles='{escaped3}':force_style='FontSize=24'")

# 测试特殊字符
path_with_spaces = r"C:\My Videos\test video.srt"
escaped_spaces = path_with_spaces.replace("\\", "/")
print("\n带空格的路径:")
print("原始:", path_with_spaces)
print("转义后:", escaped_spaces)
