# 🚀 MiMo ASR 启动指南

## 快速开始

### 方式一：使用启动脚本（推荐）

**Windows:**
```bash
cd mimo-asr
scripts\start.bat
```

**Linux / macOS:**
```bash
cd mimo-asr
chmod +x scripts/start.sh
./scripts/start.sh
```

### 方式二：手动启动

```bash
# 1. 进入目录
cd mimo-asr

# 2. 安装依赖
pip install -r config/requirements.txt

# 3. 启动应用
streamlit run src/app.py
```

浏览器会自动打开 `http://localhost:8501`

---

## 环境配置

### 1. Python 3.8+

检查 Python 版本：
```bash
python --version
```

如果未安装，请从 [python.org](https://python.org) 下载安装。

### 2. FFmpeg（必需）

FFmpeg 用于视频处理和音频提取。

**Windows:**
1. 下载 [FFmpeg](https://ffmpeg.org/download.html)
2. 解压到 `C:\ffmpeg`
3. 将 `C:\ffmpeg\bin` 添加到系统 PATH：
   - 右键「此电脑」→「属性」→「高级系统设置」→「环境变量」
   - 在「系统变量」中找到 `Path`，编辑添加 `C:\ffmpeg\bin`

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu / Debian:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**CentOS / RHEL:**
```bash
sudo yum install epel-release
sudo yum install ffmpeg
```

验证安装：
```bash
ffmpeg -version
```

### 3. MiMo API Key

**方式一：配置文件（推荐）**

编辑 `config/config.toml`：
```toml
api_key = "your-api-key-here"
base_url = "https://api.xiaomimimo.com/v1"
```

**方式二：环境变量**

```bash
# Linux / macOS
export MIMO_API_KEY="your-api-key-here"

# Windows CMD
set MIMO_API_KEY=your-api-key-here

# Windows PowerShell
$env:MIMO_API_KEY="your-api-key-here"
```

---

## 启动选项

### 指定端口

```bash
streamlit run src/app.py --server.port 8502
```

### 局域网访问

```bash
streamlit run src/app.py --server.address 0.0.0.0
```

### 后台运行

**Linux:**
```bash
nohup streamlit run src/app.py > mimo-asr.log 2>&1 &
```

**Windows:**
```bash
start /B streamlit run src/app.py > mimo-asr.log 2>&1
```

---

## 故障排查

### 问题：`ModuleNotFoundError: No module named 'openai'`

解决：
```bash
pip install -r config/requirements.txt
```

### 问题：`FFmpeg not found` 或 `ffmpeg: command not found`

解决：
1. 确认 FFmpeg 已安装
2. 确认 FFmpeg 已添加到系统 PATH
3. 重启终端后再试

### 问题：`MiMo API Key 未配置`

解决：
1. 检查 `config/config.toml` 中是否正确配置了 `api_key`
2. 或者设置环境变量 `MIMO_API_KEY`

### 问题：`Connection refused` 或 API 调用失败

解决：
1. 检查网络连接
2. 确认 API Key 是否有效
3. 确认 `base_url` 是否正确

### 问题：字幕显示乱码

解决：
1. 确保 SRT/ASS 文件使用 UTF-8 编码
2. 确保系统安装了中文字体（推荐 Microsoft YaHei）

---

## 目录结构

```
mimo-asr/
├── src/                        # 核心源代码
│   ├── __init__.py
│   ├── app.py                  # Streamlit 主界面
│   ├── config.py               # 配置模块
│   ├── mimo_asr.py             # MiMo ASR 客户端
│   ├── subtitle.py             # SRT/ASS 字幕生成
│   ├── video_processor.py      # 视频处理
│   ├── auto_editor.py          # 自动剪辑
│   ├── llm_refine.py           # LLM 转录校正
│   └── douyin_checker.py       # 抖音合规检查
├── tests/                      # 测试脚本
│   ├── test_complete.py
│   ├── test_fix.py
│   └── test_path.py
├── docs/                       # 文档
│   ├── README.md               # 项目说明（中文）
│   ├── README_EN.md            # 项目说明（英文）
│   └── START_GUIDE.md          # 本文档
├── scripts/                    # 启动脚本
│   ├── start.bat               # Windows 启动脚本
│   └── start.sh                # Linux/macOS 启动脚本
├── config/                     # 配置文件
│   ├── config.toml             # API 配置
│   └── requirements.txt        # Python 依赖
└── Material/                   # 素材目录
```

---

## 更多帮助

- 查看 [README.md](README.md) 了解功能详情（中文）
- 查看 [README_EN.md](README_EN.md) 了解功能详情（English）
- 提交 Issue 反馈问题
