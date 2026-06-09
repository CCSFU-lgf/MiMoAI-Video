"""
MiMo ASR 配置模块。

从环境变量或本地 config.toml 读取 MiMo API 配置。
"""

import os
import sys

# MiMo API 默认配置
MIMO_DEFAULT_BASE_URL = "https://api.xiaomimimo.com/v1"
MIMO_DEFAULT_MODEL = "mimo-v2.5-asr"  # MiMo ASR 模型名

# 从环境变量读取（优先级最高）
MIMO_API_KEY = os.environ.get("MIMO_API_KEY", "")
MIMO_BASE_URL = os.environ.get("MIMO_BASE_URL", "")


def load_config() -> dict:
    """
    加载 MiMo API 配置。

    优先级：环境变量 > 本地 config.toml > 默认值
    """
    api_key = MIMO_API_KEY
    base_url = MIMO_BASE_URL

    # 如果环境变量没有设置，尝试从本地 config.toml 读取
    if not api_key:
        try:
            import tomllib  # Python 3.11+
        except ImportError:
            try:
                import tomli as tomllib  # Python 3.10
            except ImportError:
                tomllib = None

        if tomllib:
            # 优先读取 config/config.toml（相对于项目根目录）
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_path = os.path.join(project_root, "config", "config.toml")
            if not os.path.exists(config_path):
                # 兼容旧路径：当前目录下的 config.toml
                config_path = os.path.join(os.path.dirname(__file__), "config.toml")
            if os.path.exists(config_path):
                with open(config_path, "rb") as f:
                    config = tomllib.load(f)
                    api_key = api_key or config.get("api_key", "")
                    base_url = base_url or config.get("base_url", "")

    # 使用默认值
    if not base_url:
        base_url = MIMO_DEFAULT_BASE_URL

    return {
        "api_key": api_key,
        "base_url": base_url,
        "model": MIMO_DEFAULT_MODEL,
    }


def get_ffmpeg_binary() -> str:
    """获取 FFmpeg 可执行文件路径。"""
    # 检查系统 PATH
    import shutil
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        return ffmpeg

    # Windows 常见路径
    if sys.platform == "win32":
        common_paths = [
            r"C:\ffmpeg\bin\ffmpeg.exe",
            r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
            os.path.expanduser(r"~\ffmpeg\bin\ffmpeg.exe"),
        ]
        for path in common_paths:
            if os.path.exists(path):
                return path

    return "ffmpeg"  # 默认返回，让系统自己找
