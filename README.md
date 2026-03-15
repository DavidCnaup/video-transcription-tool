# 视频语音转录工具

## 已完成的工作

### 1. 音频提取 ✓
已使用 FFmpeg 从视频中提取音频：
- 视频1.wav (15.9 MB)
- 视频2.wav (7.43 MB)

音频参数：16kHz, 单声道, 16bit PCM - 适合语音识别

### 2. 转录方案（三选一）

#### 方案 A: Azure 语音服务（推荐，免费额度）
**优点**: 准确度高，每月5小时免费，中文支持好
**缺点**: 需要注册 Azure 账号

```bash
cd "D:\codework space"
python azure_transcribe.py
```

**获取密钥步骤**：
1. 访问 https://portal.azure.com/
2. 搜索并创建 "Speech Services" 资源
3. 定价层选择 **F0 (Free)**
4. 等待资源创建完成
5. 进入资源 → "密钥和终结点" → 复制 **密钥1**
6. 运行脚本并粘贴密钥

#### 方案 B: 本地 Whisper（无需联网，但需下载模型）
**优点**: 完全免费，无需联网（下载后），隐私性好
**缺点**: 首次下载模型需要较长时间（72MB，当前网络约需数小时）

```bash
cd "D:\codework space"
pip install -q openai-whisper
python transcribe_simple.py
```

#### 方案 C: 在线转录服务
使用其他在线工具转录音频，然后使用我提供的文本整理工具：
- 通义听悟: https://tingwu.aliyun.com/
- 讯飞听见: https://www.iflyrec.com/
- 剪映（免费）

## 使用方法

### 快速开始（推荐方案 A）

1. **注册 Azure 账号**（如果已有微软账号可直接登录）
   - 访问 https://portal.azure.com/
   - 新用户有 200 美元免费额度

2. **创建 Speech Services**
   - 搜索 "Speech Services" → 创建
   - 定价层: **F0 (Free)**
   - 区域: 选择 East Asia 或 West US 2

3. **运行转录脚本**
   ```bash
   cd "D:\codework space"
   python azure_transcribe.py
   ```
   - 按提示输入密钥
   - 等待转录完成

4. **查看结果**
   - 生成的 Markdown 文件保存在同一目录
   - 格式: `[时间戳]\n段落内容`

## 输出格式示例

```markdown
# 视频1 - 语音转录文稿

**音频文件**: 视频1.wav
**识别片段数**: 42

---

[00:00:05]
大家好，欢迎收看本期视频。今天我们要讨论的是...

[00:00:35]
首先让我们来看一下第一个要点。这个要点非常重要...

[00:01:12]
接下来我们看第二个部分。这里有几个需要注意的地方...
```

## 文件说明

| 文件 | 说明 |
|------|------|
| `extract_audio.py` | 提取视频音频（已完成） |
| `azure_transcribe.py` | Azure 语音转录（推荐） |
| `transcribe_simple.py` | 本地 Whisper 转录 |
| `audio/视频1.wav` | 提取的音频文件1 |
| `audio/视频2.wav` | 提取的音频文件2 |

## 注意事项

1. **音频文件已准备好**，可以直接用于任何转录服务
2. **Azure F0 免费层** 每月限制 5 小时音频，两个视频约 5-10 分钟，完全够用
3. **时间戳格式** 为 `[HH:MM:SS]`，符合你的要求
4. **段落结构** 会自动合并 30 秒内的内容为一个段落

## 下一步

请告诉我你想使用哪个方案，我可以提供更详细的指导！
