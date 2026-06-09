"""
MiMo ASR - 视频字幕与自动剪辑工具

基于 MiMo AI 的视频处理工具：
1. 上传视频 → 自动语音识别 → 生成带字幕的视频（支持 SRT/ASS 逐字高亮）
2. 抖音风格自动剪辑 - 去除静音、智能加速、节奏优化、转场效果
3. 抖音合规检查 - 检查视频是否符合抖音平台要求
"""

import os
import sys
import tempfile
import time
from datetime import datetime

import streamlit as st

# 添加当前目录到 sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from auto_editor import AutoEditConfig, auto_edit_video, find_hook_sentence
from config import load_config
from douyin_checker import check_compliance, auto_comply
from mimo_asr import MiMoASR, Segment, TranscriptionResult
from subtitle import ASSStyleConfig, segments_to_ass, segments_to_srt
from video_processor import (
    crop_to_vertical,
    extract_audio,
    get_video_info,
    overlay_ass_subtitle,
    overlay_subtitle,
)

# ============================================================================
# 页面配置
# ============================================================================

st.set_page_config(
    page_title="MiMo ASR - 视频字幕与自动剪辑",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 自定义样式
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        background: linear-gradient(90deg, #FF6B6B, #4ECDC4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        padding: 1rem 0;
    }
    .feature-card {
        background: #f8f9fa;
        border-radius: 10px;
        padding: 1.5rem;
        margin: 0.5rem 0;
    }
    .stat-value {
        font-size: 2rem;
        font-weight: bold;
        color: #FF6B6B;
    }
    .stat-label {
        font-size: 0.9rem;
        color: #666;
    }
    .check-pass { color: #28a745; }
    .check-fail { color: #dc3545; }
    .check-warn { color: #ffc107; }

    /* ---- 将 Streamlit 顶部菜单英文翻译为中文 ---- */
    /* 主菜单(≡)下拉项翻译 — 按位置匹配 */
    [data-testid="stHeader"] ul li:nth-child(1) > * { font-size: 0 !important; }
    [data-testid="stHeader"] ul li:nth-child(1) > *::after { content: "重新运行" !important; font-size: 14px !important; }
    [data-testid="stHeader"] ul li:nth-child(2) > * { font-size: 0 !important; }
    [data-testid="stHeader"] ul li:nth-child(2) > *::after { content: "设置" !important; font-size: 14px !important; }
    [data-testid="stHeader"] ul li:nth-child(3) > * { font-size: 0 !important; }
    [data-testid="stHeader"] ul li:nth-child(3) > *::after { content: "关于" !important; font-size: 14px !important; }
    [data-testid="stHeader"] ul li:nth-child(4) > * { font-size: 0 !important; }
    [data-testid="stHeader"] ul li:nth-child(4) > *::after { content: "录制屏幕" !important; font-size: 14px !important; }
    [data-testid="stHeader"] ul li:nth-child(5) > * { font-size: 0 !important; }
    [data-testid="stHeader"] ul li:nth-child(5) > *::after { content: "清除缓存" !important; font-size: 14px !important; }
    /* 三点菜单(⋮)下拉项翻译 */
    [data-testid="stMainMenu"] ul li:nth-child(1) > * { font-size: 0 !important; }
    [data-testid="stMainMenu"] ul li:nth-child(1) > *::after { content: "报告问题" !important; font-size: 14px !important; }
    [data-testid="stMainMenu"] ul li:nth-child(2) > * { font-size: 0 !important; }
    [data-testid="stMainMenu"] ul li:nth-child(2) > *::after { content: "获取帮助" !important; font-size: 14px !important; }
    [data-testid="stMainMenu"] ul li:nth-child(3) > * { font-size: 0 !important; }
    [data-testid="stMainMenu"] ul li:nth-child(3) > *::after { content: "由 Streamlit 社区云托管" !important; font-size: 14px !important; }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# Session State 初始化
# ============================================================================

if "transcription" not in st.session_state:
    st.session_state.transcription = None
if "subtitle_video_path" not in st.session_state:
    st.session_state.subtitle_video_path = None
if "edited_video_path" not in st.session_state:
    st.session_state.edited_video_path = None
if "edit_stats" not in st.session_state:
    st.session_state.edit_stats = None
if "srt_path" not in st.session_state:
    st.session_state.srt_path = None
if "compliance_report" not in st.session_state:
    st.session_state.compliance_report = None


# ============================================================================
# 辅助函数
# ============================================================================

def save_uploaded_file(uploaded_file) -> str:
    """保存上传的文件到临时目录。"""
    temp_dir = tempfile.mkdtemp()
    file_path = os.path.join(temp_dir, uploaded_file.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getvalue())
    return file_path


def get_asr_client() -> MiMoASR:
    """获取 MiMo ASR 客户端。"""
    config = load_config()
    return MiMoASR(
        api_key=config["api_key"],
        base_url=config["base_url"],
    )


def hex_to_ass(hex_color: str) -> str:
    """将 Hex 颜色转换为 ASS 格式 (&HBBGGRR)。"""
    hex_color = hex_color.lstrip("#")
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    return f"&H{b:02X}{g:02X}{r:02X}"


# ============================================================================
# 侧边栏配置
# ============================================================================

with st.sidebar:
    st.markdown("## ⚙️ 配置")

    # API 状态检查
    st.markdown("### 🔑 MiMo API 状态")
    config = load_config()
    if config["api_key"]:
        st.success("✅ API Key 已配置")
    else:
        st.error("❌ API Key 未配置")
        st.markdown("""
        请通过以下方式之一配置：
        1. 设置环境变量 `MIMO_API_KEY`
        2. 在项目根目录的 `config.toml` 中配置
        """)

    st.divider()

    # ASR 设置
    st.markdown("### 🎙️ 语音识别设置")
    language = st.selectbox(
        "识别语言",
        options=["", "zh", "en", "ja", "ko", "fr", "de", "es"],
        format_func=lambda x: "自动检测" if x == "" else {
            "zh": "中文", "en": "英文", "ja": "日语",
            "ko": "韩语", "fr": "法语", "de": "德语",
            "es": "西班牙语",
        }.get(x, x),
        index=0,
    )

    llm_refine = st.checkbox(
        "启用 LLM 校正",
        value=True,
        help="使用 MiMo LLM 校正转录文本中的错别字和断句",
    )

    st.divider()

    # 字幕样式
    st.markdown("### 📝 字幕样式")

    subtitle_format = st.radio(
        "字幕格式",
        options=["ass", "srt"],
        format_func=lambda x: {
            "ass": "ASS 逐字高亮 ✨",
            "srt": "SRT 标准格式",
        }.get(x),
        index=0,
        help="ASS 格式支持逐字高亮动画（卡拉OK效果），推荐用于抖音",
    )

    font_size = st.slider("字号", 24, 80, 52 if subtitle_format == "ass" else 48, 4)
    font_color = st.color_picker("字幕颜色", "#FFFFFF")
    outline_color = st.color_picker("描边颜色", "#000000")
    outline_width = st.slider("描边宽度", 0, 6, 3 if subtitle_format == "ass" else 2)
    subtitle_position = st.selectbox(
        "字幕位置",
        options=["bottom", "center", "top"],
        format_func=lambda x: {"bottom": "底部", "center": "居中", "top": "顶部"}.get(x),
    )

    # ASS 专属选项
    if subtitle_format == "ass":
        enable_karaoke = st.checkbox(
            "逐字高亮（卡拉OK效果）",
            value=True,
            help="字幕文字逐字变色高亮，增强视觉吸引力",
        )
        keywords_input = st.text_input(
            "高亮关键词",
            placeholder="用逗号分隔，如: 重要,关键,必看",
            help="这些词会以更大更醒目的样式显示",
        )
        keywords = [kw.strip() for kw in keywords_input.split(",") if kw.strip()] if keywords_input else []
    else:
        enable_karaoke = False
        keywords = []

    st.divider()

    # 自动剪辑设置
    st.markdown("### ✂️ 自动剪辑（抖音风格）")
    enable_auto_edit = st.checkbox(
        "启用自动剪辑",
        value=True,
        help="去除静音、智能加速、优化节奏",
    )

    if enable_auto_edit:
        st.markdown("**静音处理**")
        silence_threshold = st.slider(
            "静音阈值", -50.0, -20.0, -35.0, 1.0,
            help="越低越严格，会检测更安静的片段为静音"
        )
        min_silence = st.slider(
            "最短静音时长(秒)", 0.1, 1.0, 0.3, 0.1,
            help="低于此时长的静音不会被处理"
        )

        st.markdown("**语速优化**")
        max_speed = st.slider(
            "最大加速倍率", 1.0, 2.0, 1.3, 0.1,
            help="慢节奏片段的最大加速倍率"
        )

        st.markdown("**转场效果**")
        fade_duration = st.slider(
            "淡入淡出时长(秒)", 0.0, 0.5, 0.2, 0.05,
            help="片段间的淡入淡出过渡，消除跳切感"
        )

        st.markdown("**黄金3秒**")
        enable_golden_hook = st.checkbox(
            "启用黄金3秒优化",
            value=True,
            help="在视频开头添加吸引注意力的钩子文字",
        )
        hook_text = ""
        if enable_golden_hook:
            hook_mode = st.radio(
                "钩子文字",
                options=["auto", "custom", "none"],
                format_func=lambda x: {
                    "auto": "🤖 自动选择",
                    "custom": "✏️ 自定义",
                    "none": "❌ 不添加",
                }.get(x),
                horizontal=True,
            )
            if hook_mode == "custom":
                hook_text = st.text_input(
                    "钩子文字内容",
                    placeholder="如: 看到最后有惊喜！",
                )
            elif hook_mode == "none":
                enable_golden_hook = False

        st.markdown("**结尾引导**")
        ending_mode = st.radio(
            "结尾引导",
            options=["default", "custom", "none"],
            format_func=lambda x: {
                "default": "📌 默认引导",
                "custom": "✏️ 自定义",
                "none": "❌ 不添加",
            }.get(x),
            horizontal=True,
        )
        if ending_mode == "default":
            ending_text = "关注不迷路 ❤️ 点赞+收藏"
        elif ending_mode == "custom":
            ending_text = st.text_input(
                "结尾引导文字",
                placeholder="如: 关注不迷路，下期更精彩！",
            )
        else:
            ending_text = ""

        st.markdown("**输出设置**")
        output_aspect = st.selectbox(
            "输出比例",
            options=["9:16", "16:9", "1:1", "原始"],
            help="抖音推荐 9:16 竖屏"
        )
    else:
        fade_duration = 0.2
        enable_golden_hook = False
        hook_text = ""
        ending_text = ""
        output_aspect = "9:16"


# ============================================================================
# 主界面
# ============================================================================

st.markdown('<h1 class="main-header">🎬 MiMo ASR - 视频字幕与自动剪辑</h1>', unsafe_allow_html=True)
st.markdown(
    '<p style="text-align: center; color: #666;">基于 MiMo AI 的智能视频处理工具 · ASS逐字高亮 · 抖音风格自动剪辑 · 合规检查</p>',
    unsafe_allow_html=True
)

# 主要功能区域
tab1, tab2, tab3, tab4 = st.tabs(["📤 上传视频", "📝 字幕结果", "✂️ 剪辑结果", "📊 抖音合规检查"])

# ============================================================================
# Tab 1: 上传视频
# ============================================================================

with tab1:
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("### 📹 选择视频")

        # 视频上传方式选择
        upload_method = st.radio(
            "上传方式",
            options=["上传文件", "输入路径"],
            horizontal=True,
        )

        video_path = None

        if upload_method == "上传文件":
            uploaded_video = st.file_uploader(
                "拖拽或点击上传视频",
                type=["mp4", "mov", "avi", "flv", "mkv", "webm", "m4v"],
                help="支持 MP4、MOV、AVI、FLV、MKV、WebM 格式",
            )
            if uploaded_video:
                video_path = save_uploaded_file(uploaded_video)
                st.video(uploaded_video)
        else:
            path_input = st.text_input(
                "输入视频文件路径",
                placeholder="例如: C:/Users/Administrator/Videos/test.mp4",
            )
            if path_input and os.path.exists(path_input):
                video_path = path_input
                st.video(path_input)
            elif path_input:
                st.warning("⚠️ 文件不存在，请检查路径")

    with col2:
        st.markdown("### 📊 视频信息")
        if video_path:
            try:
                info = get_video_info(video_path)
                st.markdown(f"""
                - **分辨率**: {info['width']} x {info['height']}
                - **时长**: {info['duration']:.1f} 秒
                - **帧率**: {info['fps']:.1f} FPS
                - **编码**: {info['codec']}
                - **音频**: {'✅ 有' if info['has_audio'] else '❌ 无'}
                """)
            except Exception as e:
                st.error(f"获取视频信息失败: {e}")

    # 开始处理按钮
    st.divider()

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button(
            "🚀 开始处理",
            type="primary",
            use_container_width=True,
            disabled=video_path is None,
        ):
            if not video_path:
                st.error("请先选择视频文件")
            elif not config["api_key"]:
                st.error("请先配置 MiMo API Key")
            else:
                # 进度显示
                progress_bar = st.progress(0)
                status_text = st.empty()

                try:
                    # Step 1: 提取音频
                    status_text.markdown("🔊 **Step 1/4**: 提取音频...")
                    progress_bar.progress(10)

                    temp_dir = tempfile.mkdtemp()
                    audio_path = os.path.join(temp_dir, "audio.wav")
                    extract_audio(video_path, audio_path)
                    progress_bar.progress(20)

                    # Step 2: ASR 转录
                    status_text.markdown("🎙️ **Step 2/4**: MiMo ASR 语音识别...")
                    progress_bar.progress(30)

                    asr_client = get_asr_client()
                    transcription = asr_client.transcribe(
                        audio_path, language=language
                    )

                    if not transcription.segments:
                        st.error("❌ 语音识别未返回结果，请检查视频是否有声音")
                        st.stop()

                    st.session_state.transcription = transcription
                    progress_bar.progress(50)

                    # Step 3: (可选) LLM 校正
                    if llm_refine:
                        status_text.markdown("🤖 **Step 3/4**: LLM 校正转录文本...")
                        progress_bar.progress(60)
                        try:
                            from llm_refine import refine_transcription
                            transcription.segments = refine_transcription(
                                transcription.segments
                            )
                        except Exception as e:
                            st.warning(f"LLM 校正失败，使用原始转录: {e}")
                    else:
                        status_text.markdown("⏭️ **Step 3/4**: 跳过 LLM 校正...")

                    progress_bar.progress(70)

                    # Step 4: 生成字幕视频
                    status_text.markdown(f"🎬 **Step 4/4**: 生成字幕视频 ({subtitle_format.upper()} 格式)...")
                    progress_bar.progress(80)

                    # 生成字幕文件
                    if subtitle_format == "ass":
                        # ASS 格式（逐字高亮）
                        ass_path = os.path.join(temp_dir, "subtitle.ass")
                        ass_color = hex_to_ass(font_color)
                        ass_outline = hex_to_ass(outline_color)

                        position_map = {"bottom": 2, "center": 5, "top": 8}
                        ass_alignment = position_map.get(subtitle_position, 2)

                        style_config = ASSStyleConfig(
                            font_name="Microsoft YaHei",
                            font_size=font_size,
                            bold=True,
                            primary_color=ass_color,
                            outline_color=ass_outline,
                            outline_width=outline_width,
                            alignment=ass_alignment,
                            enable_karaoke=enable_karaoke,
                            karaoke_highlight_color="&H0000FFFF",
                        )

                        segments_to_ass(
                            transcription.segments, ass_path,
                            style_config=style_config,
                            keywords=keywords,
                        )
                        st.session_state.srt_path = ass_path

                        # 叠加 ASS 字幕
                        subtitle_video_path = os.path.join(temp_dir, "subtitle_video.mp4")
                        overlay_ass_subtitle(video_path, ass_path, subtitle_video_path)
                    else:
                        # SRT 格式（标准）
                        srt_path = os.path.join(temp_dir, "subtitle.srt")
                        segments_to_srt(transcription.segments, srt_path)
                        st.session_state.srt_path = srt_path

                        # 叠加 SRT 字幕
                        subtitle_video_path = os.path.join(temp_dir, "subtitle_video.mp4")
                        ass_color = hex_to_ass(font_color)
                        ass_outline = hex_to_ass(outline_color)
                        overlay_subtitle(
                            video_path, srt_path, subtitle_video_path,
                            font_size=font_size,
                            font_color=ass_color,
                            outline_color=ass_outline,
                            outline_width=outline_width,
                            position=subtitle_position,
                        )

                    st.session_state.subtitle_video_path = subtitle_video_path
                    progress_bar.progress(100)
                    status_text.markdown("✅ **处理完成！**")

                    st.success(f"🎉 字幕视频生成成功！转录了 {len(transcription.segments)} 个片段")
                    st.rerun()

                except Exception as e:
                    st.error(f"❌ 处理失败: {e}")
                    import traceback
                    st.code(traceback.format_exc())

# ============================================================================
# Tab 2: 字幕结果
# ============================================================================

with tab2:
    if st.session_state.transcription:
        transcription = st.session_state.transcription

        col1, col2 = st.columns([2, 1])

        with col1:
            st.markdown("### 🎬 带字幕的视频")
            if st.session_state.subtitle_video_path and os.path.exists(st.session_state.subtitle_video_path):
                st.video(st.session_state.subtitle_video_path)

                # 下载按钮
                with open(st.session_state.subtitle_video_path, "rb") as f:
                    st.download_button(
                        "📥 下载字幕视频",
                        data=f,
                        file_name=f"subtitle_video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4",
                        mime="video/mp4",
                        use_container_width=True,
                    )

        with col2:
            st.markdown("### 📊 转录信息")
            st.markdown(f"""
            - **语言**: {transcription.language or '自动检测'}
            - **片段数**: {len(transcription.segments)}
            - **识别耗时**: {transcription.elapsed_seconds:.1f} 秒
            """)

            # 字幕文件下载
            if st.session_state.srt_path and os.path.exists(st.session_state.srt_path):
                ext = os.path.splitext(st.session_state.srt_path)[1]
                with open(st.session_state.srt_path, "r", encoding="utf-8") as f:
                    srt_content = f.read()
                st.download_button(
                    f"📥 下载字幕文件 ({ext.upper()})",
                    data=srt_content,
                    file_name=f"subtitle_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}",
                    mime="text/plain",
                    use_container_width=True,
                )

        # 转录文本
        st.markdown("### 📝 转录文本")
        full_text = transcription.full_text
        st.text_area("", value=transcription.full_text, height=200, disabled=True)

        # 片段详情
        with st.expander("📋 片段详情", expanded=False):
            for i, seg in enumerate(transcription.segments, 1):
                st.markdown(f"**{i}** [{seg.start_time:.2f}s - {seg.end_time:.2f}s] {seg.text}")

    else:
        st.info("📤 请先在「上传视频」标签中上传并处理视频")

# ============================================================================
# Tab 3: 剪辑结果
# ============================================================================

with tab3:
    if st.session_state.transcription and st.session_state.subtitle_video_path:
        transcription = st.session_state.transcription

        if enable_auto_edit:
            st.markdown("### ✂️ 抖音风格自动剪辑")

            col1, col2 = st.columns([2, 1])

            with col1:
                if st.button("🎬 开始自动剪辑", type="primary", use_container_width=True):
                    with st.spinner("正在分析和剪辑视频..."):
                        try:
                            # 自动选择钩子文字
                            final_hook_text = hook_text
                            if enable_golden_hook and not final_hook_text:
                                final_hook_text = find_hook_sentence(transcription.segments)
                                if final_hook_text:
                                    st.info(f"🤖 自动选择钩子: {final_hook_text}")

                            # 剪辑配置
                            edit_config = AutoEditConfig(
                                silence_threshold=silence_threshold,
                                min_silence_duration=min_silence,
                                max_speed=max_speed,
                                fade_duration=fade_duration,
                                enable_golden_hook=enable_golden_hook,
                                hook_text=final_hook_text or "",
                                ending_text=ending_text or "",
                                ending_duration=2.0,
                                output_aspect=output_aspect if output_aspect != "原始" else "",
                            )

                            # 输出路径
                            temp_dir = tempfile.mkdtemp()
                            edited_path = os.path.join(temp_dir, "edited_video.mp4")

                            # 执行剪辑
                            edited_path, stats = auto_edit_video(
                                st.session_state.subtitle_video_path,
                                edited_path,
                                transcription,
                                edit_config,
                            )

                            st.session_state.edited_video_path = edited_path
                            st.session_state.edit_stats = stats

                            st.success("🎉 自动剪辑完成！")
                            st.rerun()

                        except Exception as e:
                            st.error(f"❌ 剪辑失败: {e}")
                            import traceback
                            st.code(traceback.format_exc())

                # 显示剪辑结果
                if st.session_state.edited_video_path and os.path.exists(st.session_state.edited_video_path):
                    st.video(st.session_state.edited_video_path)

                    with open(st.session_state.edited_video_path, "rb") as f:
                        st.download_button(
                            "📥 下载剪辑后的视频",
                            data=f,
                            file_name=f"edited_video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4",
                            mime="video/mp4",
                            use_container_width=True,
                        )

            with col2:
                st.markdown("### 📊 剪辑统计")
                if st.session_state.edit_stats:
                    stats = st.session_state.edit_stats

                    st.markdown(f"""
                    <div style="text-align: center; padding: 1rem; background: #f8f9fa; border-radius: 10px;">
                        <div class="stat-value">{stats['original_duration']:.1f}s → {stats['output_duration']:.1f}s</div>
                        <div class="stat-label">原始时长 → 输出时长</div>
                    </div>
                    """, unsafe_allow_html=True)

                    st.markdown(f"""
                    - **压缩比**: {stats['compression_ratio']:.1%}
                    - **移除静音**: {stats['silence_segments_removed']} 处
                    - **处理片段**: {stats['segments_count']} 个
                    """)

                    # 计算节省的时间
                    saved = stats['original_duration'] - stats['output_duration']
                    if saved > 0:
                        st.success(f"⏱️ 节省了 {saved:.1f} 秒")
                else:
                    st.info("点击「开始自动剪辑」查看统计信息")

            # 抖音风格说明
            st.divider()
            st.markdown("""
            ### 🎯 抖音风格剪辑特点

            1. **去除静音** - 自动检测并移除停顿和无意义的静音
            2. **智能加速** - 慢节奏片段适当加速，保持节奏紧凑
            3. **呼吸感保留** - 不会完全删除所有静音，保留自然的呼吸感
            4. **转场效果** - 片段间淡入淡出过渡，消除跳切感
            5. **黄金3秒** - 开头内容紧凑，快速抓住观众注意力
            6. **结尾引导** - 添加关注/点赞引导，提升互动率
            """)
        else:
            st.info("⚙️ 请在侧边栏启用「自动剪辑」功能")
    else:
        st.info("📤 请先在「上传视频」标签中上传并处理视频")

# ============================================================================
# Tab 4: 抖音合规检查
# ============================================================================

with tab4:
    st.markdown("### 📊 抖音平台合规检查")

    # 确定要检查的视频
    check_video_path = None
    check_options = []

    if st.session_state.edited_video_path and os.path.exists(st.session_state.edited_video_path):
        check_options.append("剪辑后的视频")
    if st.session_state.subtitle_video_path and os.path.exists(st.session_state.subtitle_video_path):
        check_options.append("字幕视频")
    check_options.append("原始视频")

    if check_options:
        selected_check = st.selectbox("选择要检查的视频", options=check_options)

        if selected_check == "剪辑后的视频":
            check_video_path = st.session_state.edited_video_path
        elif selected_check == "字幕视频":
            check_video_path = st.session_state.subtitle_video_path
        elif selected_check == "原始视频":
            # 尝试从上传的视频获取路径
            if "video_path" in dir() and video_path:
                check_video_path = video_path

    col1, col2 = st.columns([2, 1])

    with col1:
        if st.button("🔍 开始合规检查", type="primary", use_container_width=True, disabled=check_video_path is None):
            with st.spinner("正在检查视频合规性..."):
                try:
                    report = check_compliance(check_video_path)
                    st.session_state.compliance_report = report
                    st.rerun()
                except Exception as e:
                    st.error(f"检查失败: {e}")

        # 显示检查结果
        if st.session_state.compliance_report:
            report = st.session_state.compliance_report

            # 评分
            score = report.score
            if score >= 80:
                st.success(f"✅ 合规评分: {score}/100")
            elif score >= 60:
                st.warning(f"⚠️ 合规评分: {score}/100")
            else:
                st.error(f"❌ 合规评分: {score}/100")

            # 详细结果
            for check in report.checks:
                if check.passed:
                    st.markdown(f"✅ **{check.name}**: {check.current_value}")
                elif check.severity == "error":
                    st.markdown(f"❌ **{check.name}**: {check.current_value} (期望: {check.expected_value})")
                    if check.fix_hint:
                        st.caption(f"💡 {check.fix_hint}")
                else:
                    st.markdown(f"⚠️ **{check.name}**: {check.current_value} (期望: {check.expected_value})")
                    if check.fix_hint:
                        st.caption(f"💡 {check.fix_hint}")

    with col2:
        st.markdown("### 📋 抖音平台要求")
        st.markdown("""
        | 项目 | 推荐值 |
        |------|--------|
        | 比例 | 9:16 竖屏 |
        | 分辨率 | 1080x1920 |
        | 时长 | 15-60秒 |
        | 帧率 | ≥24 FPS |
        | 编码 | H.264 |
        | 码率 | 4-8 Mbps |
        | 文件 | ≤128 MB |
        | 音频 | 必须有 |
        """)

        # 自动修复按钮
        if st.session_state.compliance_report and not st.session_state.compliance_report.passed:
            st.divider()
            if st.button("🔧 自动修复", use_container_width=True, disabled=check_video_path is None):
                with st.spinner("正在自动修复..."):
                    try:
                        fixed_path = check_video_path.replace(".mp4", "_fixed.mp4")
                        auto_comply(check_video_path, fixed_path)
                        st.success(f"✅ 修复完成: {fixed_path}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"修复失败: {e}")

# ============================================================================
# 页脚
# ============================================================================

st.divider()
st.markdown(
    '<p style="text-align: center; color: #999; font-size: 0.8rem;">'
    'Powered by MiMo AI · Built with Streamlit · 支持 ASS 逐字高亮 · 抖音合规检查</p>',
    unsafe_allow_html=True
)
