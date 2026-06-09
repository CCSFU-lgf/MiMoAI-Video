"""
抖音平台合规检查器。

检查视频是否符合抖音平台的上传要求，并提供自动修复建议。

抖音平台规则参考：
- 推荐分辨率：1080x1920（竖屏 9:16）
- 推荐帧率：30fps
- 推荐编码：H.264
- 推荐码率：4-8 Mbps
- 视频时长：15秒-60秒（最佳），最长15分钟
- 文件大小：不超过 128MB
- 音频：AAC，128kbps 以上
"""

import os
import subprocess
from dataclasses import dataclass, field
from typing import List, Tuple

from config import get_ffmpeg_binary
from video_processor import get_video_info


@dataclass
class CheckResult:
    """单项检查结果。"""
    name: str           # 检查项名称
    passed: bool        # 是否通过
    current_value: str  # 当前值
    expected_value: str # 期望值
    severity: str       # 严重程度: "error" / "warning" / "info"
    fix_hint: str       # 修复建议


@dataclass
class ComplianceReport:
    """合规检查报告。"""
    video_path: str
    checks: List[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """是否有 error 级别的问题。"""
        return all(c.passed or c.severity != "error" for c in self.checks)

    @property
    def error_count(self) -> int:
        return sum(1 for c in self.checks if not c.passed and c.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for c in self.checks if not c.passed and c.severity == "warning")

    @property
    def score(self) -> int:
        """合规评分 (0-100)。"""
        if not self.checks:
            return 100
        passed_count = sum(1 for c in self.checks if c.passed)
        return int(passed_count / len(self.checks) * 100)

    def summary(self) -> str:
        """生成检查摘要。"""
        lines = [
            f"📊 抖音合规检查报告",
            f"{'='*40}",
            f"视频: {os.path.basename(self.video_path)}",
            f"评分: {self.score}/100",
            f"错误: {self.error_count} | 警告: {self.warning_count}",
            f"{'='*40}",
        ]

        for check in self.checks:
            icon = "✅" if check.passed else ("❌" if check.severity == "error" else "⚠️")
            lines.append(f"{icon} {check.name}: {check.current_value}")
            if not check.passed and check.fix_hint:
                lines.append(f"   💡 {check.fix_hint}")

        return "\n".join(lines)


def check_compliance(video_path: str) -> ComplianceReport:
    """
    检查视频是否符合抖音平台要求。

    Args:
        video_path: 视频文件路径

    Returns:
        ComplianceReport 合规检查报告
    """
    report = ComplianceReport(video_path=video_path)

    # 获取视频信息
    try:
        info = get_video_info(video_path)
    except Exception as e:
        report.checks.append(CheckResult(
            name="文件读取",
            passed=False,
            current_value=f"错误: {e}",
            expected_value="可读取的视频文件",
            severity="error",
            fix_hint="请确认文件路径正确且文件未损坏",
        ))
        return report

    file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
    width = info["width"]
    height = info["height"]
    duration = info["duration"]
    fps = info["fps"]
    codec = info["codec"]

    # === 1. 分辨率检查 ===
    is_vertical = height > width
    min_dimension = min(width, height)

    if is_vertical and width >= 1080 and height >= 1920:
        report.checks.append(CheckResult(
            name="分辨率",
            passed=True,
            current_value=f"{width}x{height}",
            expected_value="1080x1920 (9:16 竖屏)",
            severity="error",
            fix_hint="",
        ))
    elif is_vertical and min_dimension >= 720:
        report.checks.append(CheckResult(
            name="分辨率",
            passed=True,
            current_value=f"{width}x{height}",
            expected_value=">=720p 竖屏",
            severity="warning",
            fix_hint="建议提升至 1080x1920 以获得最佳画质",
        ))
    else:
        report.checks.append(CheckResult(
            name="分辨率",
            passed=False,
            current_value=f"{width}x{height}",
            expected_value="1080x1920 (9:16 竖屏)",
            severity="error" if not is_vertical else "warning",
            fix_hint="建议裁剪为 9:16 竖屏比例，分辨率至少 720p" if not is_vertical
                     else "建议提升分辨率至 1080x1920",
        ))

    # === 2. 画面比例检查 ===
    if is_vertical:
        ratio = width / height
        if abs(ratio - 9/16) < 0.05:
            report.checks.append(CheckResult(
                name="画面比例",
                passed=True,
                current_value=f"{ratio:.2f} (≈9:16)",
                expected_value="9:16 (0.5625)",
                severity="error",
                fix_hint="",
            ))
        else:
            report.checks.append(CheckResult(
                name="画面比例",
                passed=False,
                current_value=f"{ratio:.2f}",
                expected_value="9:16 (0.5625)",
                severity="warning",
                fix_hint="建议裁剪为标准 9:16 比例",
            ))
    else:
        report.checks.append(CheckResult(
            name="画面比例",
            passed=False,
            current_value=f"{width}x{height} (横屏)",
            expected_value="9:16 竖屏",
            severity="error",
            fix_hint="抖音推荐竖屏视频，使用 crop_to_vertical() 裁剪",
        ))

    # === 3. 时长检查 ===
    if 15 <= duration <= 60:
        report.checks.append(CheckResult(
            name="视频时长",
            passed=True,
            current_value=f"{duration:.1f}秒",
            expected_value="15-60秒（最佳）",
            severity="warning",
            fix_hint="",
        ))
    elif 60 < duration <= 300:
        report.checks.append(CheckResult(
            name="视频时长",
            passed=True,
            current_value=f"{duration:.1f}秒",
            expected_value="15-60秒（最佳），最长5分钟",
            severity="warning",
            fix_hint="时长超过60秒可能影响完播率，建议精简内容",
        ))
    elif duration > 900:
        report.checks.append(CheckResult(
            name="视频时长",
            passed=False,
            current_value=f"{duration:.1f}秒 ({duration/60:.1f}分钟)",
            expected_value="不超过15分钟",
            severity="error",
            fix_hint="视频超出抖音最长时长限制，请剪辑缩短",
        ))
    elif duration < 15:
        report.checks.append(CheckResult(
            name="视频时长",
            passed=False,
            current_value=f"{duration:.1f}秒",
            expected_value="至少15秒",
            severity="warning",
            fix_hint="视频太短可能影响推荐，建议至少15秒",
        ))
    else:
        report.checks.append(CheckResult(
            name="视频时长",
            passed=True,
            current_value=f"{duration:.1f}秒",
            expected_value="15-900秒",
            severity="error",
            fix_hint="",
        ))

    # === 4. 帧率检查 ===
    if fps >= 24:
        report.checks.append(CheckResult(
            name="帧率",
            passed=True,
            current_value=f"{fps:.1f} FPS",
            expected_value=">=24 FPS",
            severity="warning",
            fix_hint="",
        ))
    else:
        report.checks.append(CheckResult(
            name="帧率",
            passed=False,
            current_value=f"{fps:.1f} FPS",
            expected_value=">=24 FPS",
            severity="warning",
            fix_hint="帧率过低会导致画面卡顿，建议至少 24fps",
        ))

    # === 5. 编码格式检查 ===
    h264_codecs = ["h264", "avc1", "x264"]
    if any(c in codec.lower() for c in h264_codecs):
        report.checks.append(CheckResult(
            name="视频编码",
            passed=True,
            current_value=codec,
            expected_value="H.264",
            severity="warning",
            fix_hint="",
        ))
    else:
        report.checks.append(CheckResult(
            name="视频编码",
            passed=False,
            current_value=codec,
            expected_value="H.264",
            severity="warning",
            fix_hint="建议转码为 H.264 以确保兼容性",
        ))

    # === 6. 文件大小检查 ===
    if file_size_mb <= 128:
        report.checks.append(CheckResult(
            name="文件大小",
            passed=True,
            current_value=f"{file_size_mb:.1f} MB",
            expected_value="<=128 MB",
            severity="error",
            fix_hint="",
        ))
    else:
        report.checks.append(CheckResult(
            name="文件大小",
            passed=False,
            current_value=f"{file_size_mb:.1f} MB",
            expected_value="<=128 MB",
            severity="error",
            fix_hint="文件超出抖音上传限制，请降低码率或缩短时长",
        ))

    # === 7. 码率检查 ===
    if duration > 0:
        bitrate_kbps = (file_size_mb * 8 * 1024) / duration
        if 2000 <= bitrate_kbps <= 10000:
            report.checks.append(CheckResult(
                name="码率",
                passed=True,
                current_value=f"{bitrate_kbps:.0f} kbps",
                expected_value="2000-10000 kbps",
                severity="warning",
                fix_hint="",
            ))
        elif bitrate_kbps > 10000:
            report.checks.append(CheckResult(
                name="码率",
                passed=False,
                current_value=f"{bitrate_kbps:.0f} kbps",
                expected_value="4000-8000 kbps（推荐）",
                severity="warning",
                fix_hint="码率过高会增大文件体积，建议适当降低",
            ))
        else:
            report.checks.append(CheckResult(
                name="码率",
                passed=False,
                current_value=f"{bitrate_kbps:.0f} kbps",
                expected_value=">=2000 kbps",
                severity="warning",
                fix_hint="码率过低会导致画质模糊，建议提升",
            ))

    # === 8. 音频检查 ===
    if info["has_audio"]:
        report.checks.append(CheckResult(
            name="音频轨",
            passed=True,
            current_value="有音频",
            expected_value="包含音频",
            severity="error",
            fix_hint="",
        ))
    else:
        report.checks.append(CheckResult(
            name="音频轨",
            passed=False,
            current_value="无音频",
            expected_value="包含音频",
            severity="error",
            fix_hint="抖音视频必须包含音频轨道",
        ))

    return report


def auto_comply(
    video_path: str,
    output_path: str,
    target_aspect: str = "9:16",
    target_resolution: Tuple[int, int] = (1080, 1920),
    max_duration: float = 60.0,
) -> str:
    """
    自动将视频调整为抖音推荐参数。

    处理步骤：
    1. 裁剪为竖屏比例
    2. 调整分辨率
    3. 如果超长，截取前 max_duration 秒

    Args:
        video_path: 输入视频路径
        output_path: 输出视频路径
        target_aspect: 目标比例 ("9:16", "16:9", "1:1")
        target_resolution: 目标分辨率 (宽, 高)
        max_duration: 最大时长（秒）

    Returns:
        输出文件路径
    """
    ffmpeg = get_ffmpeg_binary()
    from video_processor import crop_to_vertical

    ratio_map = {"9:16": 9/16, "16:9": 16/9, "1:1": 1/1}
    target_ratio = ratio_map.get(target_aspect, 9/16)

    info = get_video_info(video_path)
    current_path = video_path
    temp_files = []

    try:
        # Step 1: 裁剪比例
        current_ratio = info["width"] / info["height"]
        if abs(current_ratio - target_ratio) > 0.05:
            crop_path = output_path + ".crop.mp4"
            crop_to_vertical(current_path, crop_path, target_ratio)
            temp_files.append(crop_path)
            current_path = crop_path
            print(f"✅ 已裁剪为 {target_aspect} 比例")

        # Step 2: 调整分辨率
        crop_info = get_video_info(current_path)
        if crop_info["width"] != target_resolution[0] or crop_info["height"] != target_resolution[1]:
            scale_path = output_path + ".scale.mp4"
            command = [
                ffmpeg, "-y",
                "-i", current_path,
                "-vf", f"scale={target_resolution[0]}:{target_resolution[1]}",
                "-c:v", "libx264", "-preset", "medium", "-crf", "23",
                "-c:a", "aac",
                scale_path,
            ]
            result = subprocess.run(command, capture_output=True, text=True, check=False)
            if result.returncode == 0:
                temp_files.append(scale_path)
                current_path = scale_path
                print(f"✅ 已调整分辨率为 {target_resolution[0]}x{target_resolution[1]}")

        # Step 3: 截取时长
        if info["duration"] > max_duration:
            trim_path = output_path + ".trim.mp4"
            command = [
                ffmpeg, "-y",
                "-i", current_path,
                "-t", str(max_duration),
                "-c", "copy",
                trim_path,
            ]
            result = subprocess.run(command, capture_output=True, text=True, check=False)
            if result.returncode == 0:
                temp_files.append(trim_path)
                current_path = trim_path
                print(f"✅ 已截取前 {max_duration} 秒")

        # 最终输出
        import shutil
        if current_path != output_path:
            shutil.copy2(current_path, output_path)

    finally:
        # 清理临时文件
        for f in temp_files:
            if os.path.exists(f) and f != output_path:
                os.remove(f)

    return output_path
