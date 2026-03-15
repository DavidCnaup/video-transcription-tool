# 视频语音转录工具

基于 OpenAI Whisper 的音视频转录工具，支持智能分段、繁体转简体、批量处理等功能。

## ✨ 功能特性

- 🎬 **多格式支持** - 支持 MP4、AVI、MKV、MOV 等视频格式，以及 WAV、MP3、M4A 等音频格式
- 📝 **智能分段** - 根据语音停顿自动分段，生成带时间戳的文稿
- 🔄 **繁简转换** - 自动将繁体中文转换为简体中文
- 📁 **批量处理** - 支持单个文件或整个文件夹批量转录
- 🎯 **多种模型** - 支持 tiny、base、small、medium、large 等多种精度模型
- 📄 **多种输出** - 生成 Markdown 文稿、SRT 字幕文件

## 🚀 快速开始

### 安装依赖

```bash
# 1. 安装 Python 依赖
pip install openai-whisper opencc-python-reimplemented tqdm

# 2. 安装 FFmpeg（Windows）
winget install Gyan.FFmpeg

# 或使用 chocolatey
choco install ffmpeg

# 或使用 scoop
scoop install ffmpeg
```

### 使用方法

#### 主脚本 - 智能分段生成 Markdown（推荐）

```bash
# 处理单个文件
python transcribe_audio.py video.mp4
python transcribe_audio.py audio.wav

# 处理文件夹（批量）
python transcribe_audio.py ./videos/

# 指定模型（默认 base，可选: tiny, base, small, medium, large）
python transcribe_audio.py video.mp4 --model small

# 指定输出目录
python transcribe_audio.py video.mp4 --output ./output/

# 显示帮助
python transcribe_audio.py --help
```

#### 从视频提取音频

```bash
# 修改脚本中的路径后运行
python extract_audio.py
```

#### 其他转录脚本

```bash
# 简化版转录
python transcribe_simple.py

# 快速转录（使用 faster-whisper）
python transcribe_faster.py

# Google Speech API 转录（需要 API Key）
python transcribe_google.py

# 视频转 Markdown（旧版）
python video_to_markdown.py
```

## 📁 项目结构

```
.
├── audio/                      # 音频文件目录（.gitignore 忽略）
├── transcriptions/             # 转录输出目录
│   ├── temp/                   # 临时文件
│   ├── *.md                    # 生成的 Markdown 文稿
│   └── *.srt                   # 生成的字幕文件
├── test_output/                # 测试输出目录
├── extract_audio.py            # 从视频提取音频
├── transcribe_audio.py         # 主转录脚本（推荐）
├── transcribe_simple.py        # 简化版转录
├── transcribe_faster.py        # 快速转录（faster-whisper）
├── transcribe_google.py        # Google Speech API 转录
├── video_to_markdown.py        # 视频转 Markdown（旧版）
├── .gitignore                  # Git 忽略配置
└── README.md                   # 本文件
```

## 📄 输出格式示例

### Markdown 文稿

```markdown
# video - 语音转录文稿

**源文件**: video.mp4
**识别片段数**: 42

---

[00:00:05]
大家好，欢迎收看本期视频。今天我们要讨论的是...

[00:00:35]
首先让我们来看一下第一个要点。这个要点非常重要...

[00:01:12]
接下来我们看第二个部分。这里有几个需要注意的地方...
```

### SRT 字幕文件

```srt
1
00:00:05,000 --> 00:00:30,000
大家好，欢迎收看本期视频。

2
00:00:35,000 --> 00:01:10,000
首先让我们来看一下第一个要点。
```

## ⚙️ 配置说明

### 模型选择

| 模型 | 大小 | 速度 | 准确度 | 适用场景 |
|------|------|------|--------|----------|
| tiny | 39 MB | 最快 | 一般 | 快速测试 |
| base | 74 MB | 快 | 较好 | 日常使用 |
| small | 244 MB | 中等 | 好 | 推荐 |
| medium | 769 MB | 慢 | 很好 | 高精度需求 |
| large | 1550 MB | 最慢 | 最好 | 专业使用 |

### 环境变量（可选）

```bash
# 设置 FFmpeg 路径（如果需要）
set FFMPEG_PATH=C:\path\to\ffmpeg.exe
```

## 📝 文件说明

| 文件 | 说明 |
|------|------|
| `extract_audio.py` | 使用 FFmpeg 从视频中提取音频（16kHz, 单声道, 16bit PCM） |
| `transcribe_audio.py` | 功能最完整的转录脚本，支持智能分段、批量处理、繁简转换 |
| `transcribe_simple.py` | 简化版，基础转录功能 |
| `transcribe_faster.py` | 使用 faster-whisper，速度更快 |
| `transcribe_google.py` | 使用 Google Speech-to-Text API |
| `video_to_markdown.py` | 旧版视频转 Markdown 脚本 |

## ⚠️ 注意事项

1. **首次运行**会自动下载 Whisper 模型到本地缓存（约 74MB-1.5GB）
2. **GPU 加速**：如果安装了 PyTorch CUDA 版本，会自动使用 GPU 加速
3. **内存需求**：large 模型需要约 4GB 内存
4. **音频质量**：清晰的音频会获得更好的转录效果
5. **中文支持**：OpenAI Whisper 对中文支持良好，但方言效果可能不佳

## 🔧 常见问题

### Q: 提示 "ffmpeg not found"
A: 请确保 FFmpeg 已安装并在系统 PATH 中，或在脚本中指定 FFmpeg 路径。

### Q: 转录速度很慢
A: 
- 使用更快的模型（如 base 替代 large）
- 确保安装了 PyTorch CUDA 版本以启用 GPU 加速
- 使用 `transcribe_faster.py` 配合 faster-whisper

### Q: 繁简转换无效
A: 安装 opencc：
```bash
pip install opencc-python-reimplemented
```

### Q: 如何更新模型？
A: 删除缓存目录中的模型文件，下次运行会自动重新下载：
- Windows: `%USERPROFILE%\.cache\whisper\`
- Linux/Mac: `~/.cache/whisper/`

## 📜 许可证

MIT License

## 🙏 致谢

- [OpenAI Whisper](https://github.com/openai/whisper) - 开源语音识别模型
- [Faster Whisper](https://github.com/SYSTRAN/faster-whisper) - 更快的 Whisper 实现
- [OpenCC](https://github.com/BYVoid/OpenCC) - 中文繁简转换
