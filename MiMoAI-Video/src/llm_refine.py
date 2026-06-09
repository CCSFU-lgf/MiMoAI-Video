"""
LLM 转录校正模块。

使用 MiMo LLM 对 ASR 转录结果进行校正，修正错别字和优化断句。
"""

import os
import re
import sys
from typing import List

from openai import OpenAI

from config import load_config
from mimo_asr import Segment


def refine_transcription(
    segments: List[Segment],
    max_retries: int = 2,
) -> List[Segment]:
    """
    用 LLM 校正 ASR 转录结果。

    将转录片段拼接成文本发送给 LLM，让其修正错别字、优化断句，
    然后按原文断句位置重新切分校正后的文本，保持时间戳不变。

    Args:
        segments: 转录片段列表
        max_retries: 最大重试次数

    Returns:
        校正后的片段列表（时间戳不变，文本可能被修正）
    """
    if not segments:
        return segments

    config = load_config()
    api_key = config["api_key"]
    base_url = config["base_url"]

    if not api_key:
        print("警告: MiMo API Key 未配置，跳过 LLM 校正")
        return segments

    client = OpenAI(api_key=api_key, base_url=base_url)

    # 拼接转录文本，用特殊标记分隔不同片段
    separator = " ||| "
    combined_text = separator.join(seg.text for seg in segments)

    prompt = f"""# Role: Transcription Proofreader

## Goal
Correct errors in an ASR (speech-to-text) transcription result. Fix typos, improve sentence breaks, and make the text more natural while preserving the original meaning.

## Constraints
1. Return ONLY the corrected text. No explanations, no markdown.
2. Keep the exact same structure: segments separated by " ||| ".
3. Do NOT merge or split segments. The number of " ||| " separators must remain identical.
4. Fix obvious ASR errors (homophones, missing/extra characters).
5. Keep the language the same as the input.
6. Do NOT add or remove content, only correct errors.

## Input Transcription
{combined_text}"""

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=config.get("model", "mimo-v2.5-pro"),
                messages=[{"role": "user", "content": prompt}],
            )

            content = response.choices[0].message.content if response.choices else ""
            if not content:
                continue

            # 解析校正后的文本
            corrected_parts = content.split("|||")
            corrected_parts = [part.strip() for part in corrected_parts]

            if len(corrected_parts) != len(segments):
                print(
                    f"警告: 片段数量不匹配 (期望 {len(segments)}, "
                    f"实际 {len(corrected_parts)})，跳过校正"
                )
                continue

            # 用校正后的文本替换原文，保持时间戳
            refined = []
            for i, seg in enumerate(segments):
                corrected_text = corrected_parts[i] if corrected_parts[i] else seg.text
                refined.append(Segment(
                    text=corrected_text,
                    start_time=seg.start_time,
                    end_time=seg.end_time,
                ))

            print(f"✅ LLM 校正完成，{len(refined)} 个片段")
            return refined

        except Exception as e:
            print(f"LLM 校正失败 (尝试 {attempt + 1}/{max_retries}): {e}")

    print("⚠️ LLM 校正失败，返回原始转录")
    return segments
