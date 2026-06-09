<div align="center">

# 🎬 MiMo ASR - 视频字幕与自动剪辑工具

**中文** | [English](README_EN.md)

基于 MiMo AI 的智能视频处理工具，支持一键生成字幕视频和抖音风格自动剪辑。

A smart video processing tool powered by MiMo AI. One-click subtitle generation and TikTok-style auto editing.

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)](https://streamlit.io)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

</div>

---

## ✨ 功能特性

### 📝 视频字幕

| 功能 | 说明 |
|------|------|
| MiMo ASR | 高精度语音转文字识别 |
| LLM 智能校正 | 自动修正错别字和断句 |
| 字幕样式自定义 | 字号、颜色、描边、位置可调 |
| 多语言支持 | 中文、英文、日语、韩语等 |
| ASS 逐字高亮 | 卡拉OK效果，逐字变色高亮（抖音风格推荐） |

### ✂️ 自动剪辑（抖音风格）

| 功能 | 说明 |
|------|------|
| 静音检测与移除 | 去除停顿和无意义的静音 |
| 智能加速 | 慢节奏片段适当加速，保持节奏紧凑 |
| 呼吸感保留 | 保留 15% 的静音，不会太紧凑 |
| 黄金3秒优化 | 开头内容紧凑，快速抓住观众注意力 |
| 转场效果 | 片段间淡入淡出，消除跳切感 |
| 结尾引导 | 添加关注/点赞引导文字 |

### 📊 抖音合规检查

| 功能 | 说明 |
|------|------|
| 分辨率检查 | 检测是否符合 1080x1920 竖屏要求 |
| 画面比例检查 | 检测是否为 9:16 比例 |
| 时长/帧率/编码检查 | 全方位合规检测 |
| 自动修复 | 一键将视频调整为抖音推荐参数 |

---

## 🚀 快速开始

### 1. 安装依赖

```bash
cd mimo-asr
pip install -r config/requirements.txt
```

### 2. 安装 FFmpeg

**Windows:**
1. 下载 [FFmpeg](https://ffmpeg.org/download.html)
2. 解压后将 `bin` 目录添加到系统 PATH

**macOS:**
```bash
brew install ffmpeg
```

**Linux:**
```bash
sudo apt install ffmpeg
```

### 3. 配置 API Key

编辑 `config/config.toml`：

```toml
api_key = "your-api-key-here"
base_url = "https://api.xiaomimimo.com/v1"
```

或设置环境变量：

```bash
export MIMO_API_KEY="your-api-key-here"
```

### 4. 启动应用

**Windows:**
```bash
scripts\start.bat
```

**Linux / macOS:**
```bash
chmod +x scripts/start.sh
./scripts/start.sh
```

**或直接运行：**
```bash
streamlit run src/app.py
```

浏览器会自动打开 `http://localhost:8501`

---

## 📖 使用说明

### 上传视频

1. 进入「上传视频」标签
2. 选择视频文件或输入路径
3. 支持格式：MP4、MOV、AVI、FLV、MKV、WebM

### 配置参数

| 设置 | 选项 | 说明 |
|------|------|------|
| 语言 | 自动、中文、English、日本語、한국어 | 语音识别语言 |
| 字幕格式 | ASS 逐字高亮 / SRT 标准格式 | ASS 推荐用于抖音 |
| LLM 校正 | 开/关 | 用 LLM 修正 ASR 错误 |
| 字号 | 24-80 | 字幕字号 |
| 字幕颜色 | 颜色选择器 | 字幕文字颜色 |
| 自动剪辑 | 开/关 | 启用抖音风格剪辑 |

### 下载结果

- **字幕视频** - 带有烧录字幕的视频
- **字幕文件** - SRT 或 ASS 格式字幕文件
- **剪辑视频** - 经过自动剪辑优化的视频

---

## 🎯 抖音风格剪辑详解

### 静音检测

| 参数 | 默认值 | 说明 |
|------|--------|------|
| 阈值 | -35dB | 越低越严格 |
| 最短时长 | 0.3s | 低于此值不处理 |
| 保留比例 | 15% | 保留呼吸感 |

### 智能加速

| 参数 | 默认值 | 说明 |
|------|--------|------|
| 最大倍率 | 1.3x | 最大加速倍率 |
| 触发条件 | >2s | 超过此时长触发 |
| 目标时长 | 3s | 抖音理想片段时长 |

### 节奏优化

- 合并过短的连续片段
- 确保每个片段内容完整
- 保持整体节奏紧凑

### 转场效果

- 片段间淡入淡出过渡
- 消除跳切感
- 可自定义淡入淡出时长

---

## 🔧 高级配置

### 环境变量

| 变量名 | 说明 |
|--------|------|
| `MIMO_API_KEY` | MiMo API Key（最高优先级） |
| `MIMO_BASE_URL` | MiMo API 地址 |

### 自定义剪辑参数

在侧边栏调整：

| 参数 | 默认值 | 范围 | 说明 |
|------|--------|------|------|
| 静音阈值 | -35dB | -50 ~ -20 | 检测灵敏度 |
| 最短静音时长 | 0.3s | 0.1 ~ 1.0 | 忽略更短的 |
| 最大加速倍率 | 1.3x | 1.0 ~ 2.0 | 加速上限 |
| 淡入淡出时长 | 0.2s | 0.0 ~ 0.5 | 转场效果时长 |
| 输出比例 | 9:16 | 9:16, 16:9, 1:1 | 输出比例 |

---

## 📁 项目结构

```
mimo-asr/
├── src/                        # 核心源代码
│   ├── __init__.py
│   ├── app.py                  # Streamlit 主界面
│   ├── config.py               # 配置模块
│   ├── mimo_asr.py             # MiMo ASR 客户端
│   ├── subtitle.py             # SRT/ASS 字幕生成
│   ├── video_processor.py      # 视频处理（FFmpeg）
│   ├── auto_editor.py          # 自动剪辑（抖音风格）
│   ├── llm_refine.py           # LLM 转录校正
│   └── douyin_checker.py       # 抖音合规检查
├── tests/                      # 测试脚本
│   ├── test_complete.py        # 完整功能测试
│   ├── test_fix.py             # 修复验证测试
│   └── test_path.py            # 路径转义测试
├── docs/                       # 文档
│   ├── README.md               # 本文档（中文）
│   ├── README_EN.md            # 英文文档
│   └── START_GUIDE.md          # 启动指南
├── scripts/                    # 启动脚本
│   ├── start.bat               # Windows 启动脚本
│   └── start.sh                # Linux/macOS 启动脚本
├── config/                     # 配置文件
│   ├── config.toml             # API 配置
│   └── requirements.txt        # Python 依赖列表
└── Material/                   # 素材目录
    └── weilong.mp4             # 示例素材
```

---

## ❓ 常见问题

### Q: 为什么选择 MiMo ASR 而不是 Whisper？

A: MiMo ASR 是云端服务，不需要下载大模型，识别速度快，且与 MiMo 生态（LLM、TTS）完美集成。

### Q: 支持哪些视频格式？

A: 支持 MP4、MOV、AVI、FLV、MKV、WebM、M4V 等常见格式。

### Q: 自动剪辑会降低视频质量吗？

A: 不会。使用高质量 H.264 编码，CRF 值为 23，视觉上几乎无损。

### Q: 可以调整剪辑的激进程度吗？

A: 可以。在侧边栏调整「静音阈值」和「最大加速倍率」即可。

### Q: ASS 和 SRT 字幕格式有什么区别？

A: ASS 格式支持逐字高亮动画（卡拉OK效果）、自定义样式等高级特性，推荐用于抖音。SRT 是标准格式，兼容性更好。

### Q: 如何获取 MiMo API Key？

A: 访问 [MiMo 平台](https://platform.xiaomimimo.com) 注册并获取 API Key。

---

## 🤝 贡献

欢迎贡献代码！请随时提交 Pull Request。

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

---

## 📄 许可证

MIT License

---

## 🙏 致谢

- [MiMo AI](https://xiaomimimo.com) - 提供 ASR、LLM、TTS 能力
- [Streamlit](https://streamlit.io) - 提供 Web UI 框架
- [FFmpeg](https://ffmpeg.org) - 提供视频处理能力

---

<div align="center">

**Made with ❤️ by MiMo ASR**

</div>
