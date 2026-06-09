[README_EN.md](https://github.com/user-attachments/files/28740342/README_EN.md)
<div align="center">

# 🎬 MiMo ASR - Video Subtitle & Auto Editing Tool

**English** | [中文](README.md)

基于 MiMo AI 的智能视频处理工具，支持一键生成字幕视频和抖音风格自动剪辑。

A smart video processing tool powered by MiMo AI. One-click subtitle generation and TikTok-style auto editing.

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)](https://streamlit.io)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

</div>

---

## ✨ Features / 功能特性

### 📝 Video Subtitles / 视频字幕

| Feature | Description |
|---------|-------------|
| MiMo ASR | High-precision speech-to-text recognition / 高精度语音转文字 |
| LLM Correction | Auto-fix typos and sentence breaks / 自动修正错别字和断句 |
| Custom Styles | Font size, color, outline, position / 字号、颜色、描边、位置可调 |
| Multi-language | Chinese, English, Japanese, Korean, etc. / 中文、英文、日语、韩语等 |
| ASS Karaoke | Per-character highlight animation (recommended for TikTok) / 逐字高亮动画（抖音推荐） |

### ✂️ Auto Editing (TikTok Style) / 自动剪辑（抖音风格）

| Feature | Description |
|---------|-------------|
| Silence Removal | Remove pauses and meaningless silence / 去除停顿和无意义的静音 |
| Smart Speed Up | Accelerate slow-paced clips / 慢节奏片段适当加速 |
| Breathing Space | Keep 15% silence for natural feel / 保留 15% 静音，保持自然感 |
| Golden 3 Seconds | Compact opening to grab attention / 开头内容紧凑，快速抓住注意力 |
| Transitions | Fade in/out between clips for smooth flow / 片段间淡入淡出，消除跳切感 |
| Ending Guide | Add follow/like call-to-action / 添加关注/点赞引导文字 |

### 📊 Douyin Compliance Check / 抖音合规检查

| Feature | Description |
|---------|-------------|
| Resolution Check | Verify 1080x1920 vertical format / 检测是否符合竖屏要求 |
| Aspect Ratio Check | Verify 9:16 ratio / 检测是否为 9:16 比例 |
| Duration/FPS/Codec | Full compliance detection / 全方位合规检测 |
| Auto Fix | One-click adjust to Douyin recommended settings / 一键调整为抖音推荐参数 |

---

## 🚀 Quick Start / 快速开始

### 1. Install Dependencies / 安装依赖

```bash
cd mimo-asr
pip install -r config/requirements.txt
```

### 2. Install FFmpeg / 安装 FFmpeg

**Windows:**
1. Download from [ffmpeg.org](https://ffmpeg.org/download.html)
2. Extract and add `bin` folder to PATH

**macOS:**
```bash
brew install ffmpeg
```

**Linux:**
```bash
sudo apt install ffmpeg
```

### 3. Configure API Key / 配置 API Key

Edit `config/config.toml` / 编辑 `config/config.toml`：

```toml
api_key = "your-api-key-here"
base_url = "https://api.xiaomimimo.com/v1"
```

Or set environment variable / 或设置环境变量：

```bash
export MIMO_API_KEY="your-api-key-here"
```

### 4. Launch App / 启动应用

**Windows:**
```bash
scripts\start.bat
```

**Linux / macOS:**
```bash
chmod +x scripts/start.sh
./scripts/start.sh
```

**Or directly / 或直接运行：**
```bash
streamlit run src/app.py
```

Open browser at `http://localhost:8501` / 浏览器自动打开 `http://localhost:8501`

---

## 📖 Usage / 使用说明

### Upload Video / 上传视频

1. Go to "Upload Video" tab / 进入「上传视频」标签
2. Select video file or enter path / 选择视频文件或输入路径
3. Supported formats / 支持格式：MP4, MOV, AVI, FLV, MKV, WebM

### Configure Settings / 配置参数

| Setting | Options | Description |
|---------|---------|-------------|
| Language | Auto, 中文, English, 日本語, 한국어 | Speech recognition language / 识别语言 |
| Subtitle Format | ASS Karaoke / SRT Standard | ASS recommended for TikTok / ASS 推荐用于抖音 |
| LLM Correction | On/Off | Fix ASR errors with LLM / 用 LLM 修正 ASR 错误 |
| Font Size | 24-80 | Subtitle font size / 字幕字号 |
| Subtitle Color | Color picker | Subtitle text color / 字幕颜色 |
| Auto Edit | On/Off | Enable TikTok-style editing / 启用抖音风格剪辑 |

### Download Results / 下载结果

- **Subtitle Video** - Video with burned-in subtitles / 带字幕的视频
- **Subtitle File** - SRT or ASS format / SRT 或 ASS 格式字幕文件
- **Edited Video** - Auto-edited video / 自动剪辑后的视频

---

## 🎯 TikTok-Style Editing Details / 抖音风格剪辑详解

### Silence Detection / 静音检测

| Parameter | Default | Description |
|-----------|---------|-------------|
| Threshold | -35dB | Lower = stricter / 越低越严格 |
| Min Duration | 0.3s | Ignore shorter silence / 低于此值不处理 |
| Keep Ratio | 15% | Keep some breathing space / 保留呼吸感 |

### Smart Speed Up / 智能加速

| Parameter | Default | Description |
|-----------|---------|-------------|
| Max Speed | 1.3x | Maximum acceleration / 最大加速倍率 |
| Trigger | >2s | Clips longer than this / 超过此时长触发 |
| Target | 3s | Ideal TikTok clip length / 抖音理想片段时长 |

### Rhythm Optimization / 节奏优化

- Merge short consecutive clips / 合并过短的连续片段
- Ensure complete content per clip / 确保每个片段内容完整
- Maintain compact rhythm / 保持整体节奏紧凑

### Transitions / 转场效果

- Fade in/out between clips / 片段间淡入淡出过渡
- Eliminate jump cuts / 消除跳切感
- Customizable fade duration / 可自定义淡入淡出时长

---

## 🔧 Advanced Configuration / 高级配置

### Environment Variables / 环境变量

| Variable | Description |
|----------|-------------|
| `MIMO_API_KEY` | MiMo API Key (highest priority / 最高优先级) |
| `MIMO_BASE_URL` | MiMo API endpoint / MiMo API 地址 |

### Custom Edit Parameters / 自定义剪辑参数

Adjust in sidebar / 在侧边栏调整：

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| Silence Threshold | -35dB | -50 ~ -20 | Detection sensitivity / 检测灵敏度 |
| Min Silence Duration | 0.3s | 0.1 ~ 1.0 | Ignore shorter / 忽略更短的 |
| Max Speed | 1.3x | 1.0 ~ 2.0 | Acceleration limit / 加速上限 |
| Fade Duration | 0.2s | 0.0 ~ 0.5 | Transition duration / 转场效果时长 |
| Output Aspect | 9:16 | 9:16, 16:9, 1:1 | Output ratio / 输出比例 |

---

## 📁 Project Structure / 项目结构

```
mimo-asr/
├── src/                        # Core source code / 核心源代码
│   ├── __init__.py
│   ├── app.py                  # Streamlit main UI / 主界面
│   ├── config.py               # Configuration / 配置模块
│   ├── mimo_asr.py             # MiMo ASR client / ASR 客户端
│   ├── subtitle.py             # SRT/ASS generation / 字幕生成
│   ├── video_processor.py      # Video processing (FFmpeg) / 视频处理
│   ├── auto_editor.py          # Auto editing (TikTok style) / 自动剪辑
│   ├── llm_refine.py           # LLM refinement / LLM 校正
│   └── douyin_checker.py       # Douyin compliance check / 抖音合规检查
├── tests/                      # Test scripts / 测试脚本
│   ├── test_complete.py        # Full feature test / 完整功能测试
│   ├── test_fix.py             # Fix verification / 修复验证测试
│   └── test_path.py            # Path escaping test / 路径转义测试
├── docs/                       # Documentation / 文档
│   ├── README.md               # Chinese documentation / 中文文档
│   ├── README_EN.md            # This file / 本文档
│   └── START_GUIDE.md          # Startup guide / 启动指南
├── scripts/                    # Launch scripts / 启动脚本
│   ├── start.bat               # Windows launcher / Windows 启动脚本
│   └── start.sh                # Linux/macOS launcher / Linux/macOS 启动脚本
├── config/                     # Configuration files / 配置文件
│   ├── config.toml             # API configuration / API 配置
│   └── requirements.txt        # Python dependencies / Python 依赖列表
└── Material/                   # Assets directory / 素材目录
    └── weilong.mp4             # Sample asset / 示例素材
```

---

## ❓ FAQ / 常见问题

### Q: Why MiMo ASR instead of Whisper?

A: MiMo ASR is a cloud service. No need to download large models, fast recognition speed, and seamless integration with MiMo ecosystem (LLM, TTS).

MiMo ASR 是云端服务，无需下载大模型，识别速度快，且与 MiMo 生态（LLM、TTS）完美集成。

### Q: What video formats are supported?

A: MP4, MOV, AVI, FLV, MKV, WebM, M4V and other common formats.

支持 MP4、MOV、AVI、FLV、MKV、WebM、M4V 等常见格式。

### Q: Does auto editing reduce video quality?

A: No. We use high-quality H.264 encoding with CRF 23, which is visually lossless.

不会。使用高质量 H.264 编码，CRF 值为 23，视觉上几乎无损。

### Q: Can I adjust the editing aggressiveness?

A: Yes. Adjust "Silence Threshold" and "Max Speed" in the sidebar.

可以。在侧边栏调整「静音阈值」和「最大加速倍率」即可。

### Q: What's the difference between ASS and SRT subtitle formats?

A: ASS supports per-character highlight animation (karaoke effect) and custom styles, recommended for TikTok. SRT is a standard format with better compatibility.

ASS 格式支持逐字高亮动画（卡拉OK效果）、自定义样式等高级特性，推荐用于抖音。SRT 是标准格式，兼容性更好。

### Q: How to get MiMo API Key?

A: Visit [MiMo Platform](https://platform.xiaomimimo.com) to register and get API Key.

访问 [MiMo 平台](https://platform.xiaomimimo.com) 注册并获取 API Key。

---

## 🤝 Contributing / 贡献

Contributions are welcome! Please feel free to submit a Pull Request.

欢迎贡献代码！请随时提交 Pull Request。

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License / 许可证

MIT License

---

## 🙏 Acknowledgments / 致谢

- [MiMo AI](https://xiaomimimo.com) - ASR, LLM, TTS capabilities / 提供 ASR、LLM、TTS 能力
- [Streamlit](https://streamlit.io) - Web UI framework / 提供 Web UI 框架
- [FFmpeg](https://ffmpeg.org) - Video processing / 提供视频处理能力

---

<div align="center">
**特别感谢小米❤️-长春师范大学罗贵峰**
</div>
<div align="center">
**Special thanks to Xiaomi ❤️ - Luo Guifeng, Changchun Normal University**
</div>
