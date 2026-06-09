"""
MiMo ASR 客户端实现。

使用 MiMo 的 Chat Completions API 进行语音识别。
API 文档: https://platform.xiaomimimo.com/docs/zh-CN/api/audio/Speech-Recognition
"""

import base64
import os
import time
from dataclasses import dataclass, field
from typing import List, Optional

from openai import OpenAI

from config import load_config


@dataclass
class Segment:
    """转录结果片段。"""
    text: str
    start_time: float  # 秒
    end_time: float    # 秒

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time


@dataclass
class TranscriptionResult:
    """完整转录结果。"""
    segments: List[Segment] = field(default_factory=list)
    language: str = ""
    language_probability: float = 0.0
    elapsed_seconds: float = 0.0

    @property
    def full_text(self) -> str:
        return "".join(seg.text for seg in self.segments)


class MiMoASR:
    """
    MiMo ASR 客户端。

    使用 MiMo Chat Completions API 进行语音识别。
    API 端点: https://api.xiaomimimo.com/v1/chat/completions
    模型: mimo-v2.5-asr
    """

    def __init__(self, api_key: str = "", base_url: str = "", model: str = ""):
        config = load_config()
        self.api_key = api_key or config["api_key"]
        self.base_url = base_url or config["base_url"]
        self.model = model or config["model"]

        if not self.api_key:
            raise ValueError(
                "MiMo API Key 未配置。\n"
                "请设置环境变量 MIMO_API_KEY 或在 config.toml 中配置 mimo_api_key"
            )

        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def transcribe(
        self,
        audio_file: str,
        language: str = "",
        max_retries: int = 3,
    ) -> TranscriptionResult:
        """
        转录音频文件。

        Args:
            audio_file: 音频文件路径（WAV/MP3）
            language: 语言提示（"zh"=中文, "en"=英文, ""=自动检测）
            max_retries: 最大重试次数

        Returns:
            TranscriptionResult 包含带时间戳的文本片段
        """
        if not os.path.exists(audio_file):
            raise FileNotFoundError(f"音频文件不存在: {audio_file}")

        start_time = time.time()
        last_error = None

        for attempt in range(max_retries):
            try:
                result = self._call_api(audio_file, language)
                elapsed = time.time() - start_time
                result.elapsed_seconds = elapsed
                return result
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait = 2 ** attempt
                    print(f"ASR 调用失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                    print(f"等待 {wait} 秒后重试...")
                    time.sleep(wait)

        raise RuntimeError(
            f"MiMo ASR 调用失败，已重试 {max_retries} 次: {last_error}"
        )

    def _call_api(self, audio_file: str, language: str) -> TranscriptionResult:
        """
        调用 MiMo ASR API。

        使用 Chat Completions API 格式:
        POST https://api.xiaomimimo.com/v1/chat/completions
        """
        # 读取音频文件并 base64 编码
        with open(audio_file, "rb") as f:
            audio_data = base64.b64encode(f.read()).decode("utf-8")

        # 获取文件扩展名来确定 MIME 类型
        ext = os.path.splitext(audio_file)[1].lower().lstrip(".")
        mime_map = {
            "wav": "audio/wav",
            "mp3": "audio/mpeg",
        }
        mime_type = mime_map.get(ext, "audio/wav")

        # 构建 data URL
        audio_url = f"data:{mime_type};base64,{audio_data}"

        # 调用 Chat Completions API
        # 注意：ASR 请求不能包含文本部分，文本提示由网关自动注入
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_audio",
                            "input_audio": {
                                "data": audio_url,
                            },
                        },
                    ],
                }
            ],
            # ASR 配置选项
            extra_body={
                "asr_options": {
                    "language": language if language else "auto",
                }
            },
        )

        return self._parse_response(response)

    def _parse_response(self, response) -> TranscriptionResult:
        """解析 API 响应。"""
        content = ""
        if response.choices:
            content = response.choices[0].message.content or ""

        # 尝试解析 JSON 格式的响应
        import json
        import re

        segments = []
        language = ""

        # 尝试从响应中提取 JSON
        try:
            # 尝试提取 JSON 部分（有时响应可能包含其他文本）
            json_match = re.search(r'\{[\s\S]*\}|\[[\s\S]*\]', content)
            if json_match:
                json_str = json_match.group()
                data = json.loads(json_str)
            else:
                data = json.loads(content)

            if isinstance(data, dict):
                segments_data = data.get("segments", [])
                language = data.get("language", "")
                for seg in segments_data:
                    text = seg.get("text", "").strip()
                    start_time = seg.get("start", seg.get("start_time", 0.0))
                    end_time = seg.get("end", seg.get("end_time", 0.0))
                    if text:
                        segments.append(Segment(
                            text=text,
                            start_time=float(start_time),
                            end_time=float(end_time),
                        ))
            elif isinstance(data, list):
                for seg in data:
                    if isinstance(seg, dict):
                        text = seg.get("text", "").strip()
                        start_time = seg.get("start", seg.get("start_time", 0.0))
                        end_time = seg.get("end", seg.get("end_time", 0.0))
                        if text:
                            segments.append(Segment(
                                text=text,
                                start_time=float(start_time),
                                end_time=float(end_time),
                            ))
                    elif isinstance(seg, str) and seg.strip():
                        # 如果是字符串列表，无法确定时间戳
                        segments.append(Segment(
                            text=seg.strip(),
                            start_time=0.0,
                            end_time=0.0,
                        ))
        except (json.JSONDecodeError, AttributeError) as e:
            # 非 JSON 格式，尝试从文本中提取时间戳
            print(f"警告: ASR 响应不是标准 JSON 格式，尝试解析纯文本: {e}")

            # 尝试匹配常见的时间戳格式，如 [00:00:00 - 00:00:01] 或 (0.0-1.0)
            timestamp_pattern = r'[\[\(](\d+[:.]?\d*[:.]?\d*)\s*[-–]\s*(\d+[:.]?\d*[:.]?\d*)[\]\)]\s*(.+)'
            matches = re.findall(timestamp_pattern, content)

            if matches:
                for match in matches:
                    start_str, end_str, text = match
                    # 解析时间戳
                    start_time = self._parse_timestamp(start_str)
                    end_time = self._parse_timestamp(end_str)
                    if text.strip():
                        segments.append(Segment(
                            text=text.strip(),
                            start_time=start_time,
                            end_time=end_time,
                        ))
            else:
                # 无法解析时间戳，将整个内容作为一个片段
                text = content.strip()
                if text:
                    print("警告: 无法从响应中提取时间戳，自动剪辑可能无法正常工作")
                    segments.append(Segment(
                        text=text,
                        start_time=0.0,
                        end_time=0.0,
                    ))

        return TranscriptionResult(
            segments=segments,
            language=language,
            language_probability=1.0,
        )

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


def create_asr_client(**kwargs) -> MiMoASR:
    """创建 MiMo ASR 客户端实例。"""
    return MiMoASR(**kwargs)
