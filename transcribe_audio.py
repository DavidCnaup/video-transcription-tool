#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
音视频转录脚本 - 智能分段生成Markdown

功能：
    1. 支持单个视频/音频文件处理
    2. 支持文件夹批量处理
    3. 自动视频转音频（使用ffmpeg）
    4. 智能分段，带时间戳
    5. 繁体转简体，自动添加标点

使用方法:
    # 处理单个文件
    python transcribe_audio.py video.mp4
    python transcribe_audio.py audio.wav
    
    # 处理文件夹（批量）
    python transcribe_audio.py ./videos/
    
    # 指定模型（默认 base）
    python transcribe_audio.py video.mp4 --model tiny
    
    # 指定输出目录
    python transcribe_audio.py video.mp4 --output ./output/

依赖:
    pip install opencc-python-reimplemented tqdm
    
    # 安装whisper（优先使用uv tool）
    uv tool install openai-whisper
    # 或
    pip install openai-whisper
    
    # 安装ffmpeg
    winget install Gyan.FFmpeg
"""

import subprocess
import os
import re
import sys
import argparse
from pathlib import Path
from datetime import timedelta
from typing import List, Tuple, Optional, Union

# 尝试导入进度条
try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    print("[提示] 安装 tqdm 可显示进度条: pip install tqdm")

# 尝试导入opencc用于繁体转简体
try:
    import opencc
    CONVERTER_T2S = opencc.OpenCC('t2s')
    print("[信息] 已加载繁体转简体功能 (OpenCC)")
except ImportError:
    CONVERTER_T2S = None
    print("[警告] 未安装 opencc，繁体转简体功能不可用")
    print("       安装命令: pip install opencc-python-reimplemented")

# ==================== 全局配置 ====================
# 默认使用的whisper模型，可选: tiny, base, small, medium, large
DEFAULT_MODEL = "base"

# 支持的音频格式
AUDIO_EXTENSIONS = {'.wav', '.mp3', '.m4a', '.flac', '.ogg', '.aac', '.wma'}

# 支持的视频格式
VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm'}

# 所有支持的格式
ALL_EXTENSIONS = AUDIO_EXTENSIONS | VIDEO_EXTENSIONS

# 智能分段参数
SEGMENT_GAP_THRESHOLD = 1.0      # 时间间隔阈值（秒）- 降低以捕捉更多停顿
MAX_PARAGRAPH_DURATION = 45      # 最大段落时长（秒）- 降低以产生更多段落
MAX_PARAGRAPH_SEGMENTS = 15      # 最大片段数 - 降低以产生更多段落

# 全局开关：是否启用智能分段（默认False，不启用）
# True:  启用智能分段（根据内容信号、停顿、长度智能判断）
# False: 简单分段（每30秒或每10个片段分一段）
ENABLE_SMART_SEGMENT = False
# =================================================


def setup_ffmpeg_path() -> bool:
    """设置ffmpeg路径"""
    local_appdata = os.environ.get('LOCALAPPDATA', '')
    possible_paths = [
        Path(local_appdata) / "Microsoft" / "WinGet" / "Packages" / "Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe" / "ffmpeg-8.0.1-full_build" / "bin",
        Path(local_appdata) / "Microsoft" / "WinGet" / "Packages" / "Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe" / "ffmpeg-7.1-full_build" / "bin",
        Path("C:/Program Files/ffmpeg/bin"),
        Path("C:/ffmpeg/bin"),
    ]
    
    for path in possible_paths:
        if path.exists() and (path / "ffmpeg.exe").exists():
            os.environ['PATH'] = str(path) + os.pathsep + os.environ.get('PATH', '')
            return True
    
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, check=False)
        return result.returncode == 0
    except FileNotFoundError:
        pass
    
    return False


# 启动时设置ffmpeg路径
if not setup_ffmpeg_path():
    print("[警告] 未找到ffmpeg，请确保ffmpeg已安装")
    print("       安装命令: winget install Gyan.FFmpeg")


def format_timestamp(seconds: float) -> str:
    """转换为 [HH:MM:SS] 格式"""
    td = timedelta(seconds=int(seconds))
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"[{hours:02d}:{minutes:02d}:{seconds:02d}]"


def parse_srt_time(time_str: str) -> float:
    """解析SRT时间格式为秒数"""
    parts = time_str.replace(',', '.').split(':')
    hours = int(parts[0])
    minutes = int(parts[1])
    seconds = float(parts[2])
    return hours * 3600 + minutes * 60 + seconds


def convert_to_simplified(text: str) -> str:
    """繁体转简体"""
    if CONVERTER_T2S:
        converted = CONVERTER_T2S.convert(text)
        # 调试：显示转换前后对比（仅首次）
        if not hasattr(convert_to_simplified, '_debug_shown'):
            if converted != text:
                print(f"       [繁体转简体] 示例: '{text[:30]}...' -> '{converted[:30]}...'")
            convert_to_simplified._debug_shown = True
        return converted
    return text


def is_sentence_end(text: str) -> bool:
    """判断文本是否以句子结尾"""
    if not text:
        return False
    text = text.strip()
    if not text:
        return False
    
    sentence_endings = ['。', '？', '！', '；', '?', '!', ';', '"', '"', ''', ''', '】', '」', '』', '...', '…']
    return any(text.endswith(end) for end in sentence_endings)


def extract_audio(video_path: Path, output_dir: Path) -> Optional[Path]:
    """
    从视频提取音频为wav格式
    
    Args:
        video_path: 视频文件路径
        output_dir: 输出目录
    
    Returns:
        提取的音频文件路径，失败返回None
    """
    audio_path = output_dir / f"{video_path.stem}_audio.wav"
    
    # 如果已存在，直接返回
    if audio_path.exists():
        print(f"  [提示] 音频文件已存在: {audio_path.name}")
        return audio_path
    
    print(f"  [提取] 从视频提取音频: {video_path.name}")
    
    cmd = [
        'ffmpeg',
        '-i', str(video_path),
        '-vn',                    # 不处理视频
        '-acodec', 'pcm_s16le',   # PCM 16位小端
        '-ar', '16000',           # 16kHz采样率
        '-ac', '1',               # 单声道
        '-y',                     # 覆盖已存在文件
        str(audio_path)
    ]
    
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )
        
        if result.returncode == 0 and audio_path.exists():
            print(f"  [完成] 音频提取完成: {audio_path.name}")
            return audio_path
        else:
            print(f"  [错误] 音频提取失败")
            return None
            
    except Exception as e:
        print(f"  [错误] 执行ffmpeg出错: {e}")
        return None


def transcribe_audio(audio_path: Path, output_dir: Path, model: str = DEFAULT_MODEL) -> Optional[Path]:
    """
    使用whisper转录音频
    
    Args:
        audio_path: 音频文件路径
        output_dir: 输出目录
        model: whisper模型名称
    
    Returns:
        SRT文件路径，失败返回None
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    srt_path = output_dir / f"{audio_path.stem}.srt"
    
    # 检查是否已存在
    if srt_path.exists():
        print(f"  [提示] 转录文件已存在: {srt_path.name}")
        return srt_path
    
    print(f"  [转录] 使用模型 '{model}': {audio_path.name}")
    
    cmd = [
        "whisper",
        str(audio_path),
        "--model", model,
        "--language", "zh",
        "--output_format", "srt",
        "--output_dir", str(output_dir),
    ]
    
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )
        
        # 实时输出关键信息
        for line in process.stdout:
            line = line.strip()
            if line and any(x in line for x in ['Detecting', 'Detected', 'Loading', 'Transcribing']):
                print(f"       {line}")
        
        process.wait()
        
        if process.returncode != 0:
            print(f"  [错误] 转录失败")
            return None
        
        if srt_path.exists():
            print(f"  [完成] 转录完成: {srt_path.name}")
            return srt_path
        else:
            print(f"  [错误] 未找到生成的SRT文件")
            return None
            
    except Exception as e:
        print(f"  [错误] 执行出错: {e}")
        return None


def parse_srt(srt_path: Path) -> List[Tuple[float, float, str]]:
    """解析SRT文件，返回(开始时间, 结束时间, 文本)列表"""
    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    segments = []
    blocks = re.split(r'\n\n+', content.strip())
    
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) >= 3:
            time_line = lines[1]
            time_match = re.match(r'(\d{2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,.]\d{3})', time_line)
            if time_match:
                start_time = parse_srt_time(time_match.group(1))
                end_time = parse_srt_time(time_match.group(2))
                text = ' '.join(lines[2:]).strip()
                text = convert_to_simplified(text)  # 繁体转简体
                text = post_process(text)  # 清理标点和空格
                if text:
                    segments.append((start_time, end_time, text))
    
    return segments


def is_new_paragraph_point(prev_text: str, curr_text: str, prev_end: float, curr_start: float) -> bool:
    """智能判断是否新段落"""
    curr_clean = curr_text.strip()
    prev_clean = prev_text.strip() if prev_text else ""
    
    # 1. 时间间隔较大 + 前句完整结束
    if curr_start - prev_end > SEGMENT_GAP_THRESHOLD:
        if is_sentence_end(prev_clean):
            return True
    
    # 2. 明显的段落引导词
    strong_starters = [
        '首先', '第一', '第二', '第三', '第四', '第五',
        '接下来', '下面', '我们来看', '现在我',
        '第一部分', '第二部分', '第三步',
        '操作流程', '授权提交', '申请进度',
    ]
    
    if any(curr_clean.startswith(s) for s in strong_starters):
        return True
    
    # 3. 主题/场景转换词（需前句完整结束）
    if is_sentence_end(prev_clean):
        topic_shifts = [
            '那么', '好的', '好，', '那我们',
            '另外', '此外', '除此之外', '另一方面',
            '其实', '实际上', '事实上',
            '总结', '总的来说', '综上所述', '最后', '总之', '最终',
        ]
        if any(curr_clean.startswith(s) for s in topic_shifts):
            return True
        
        module_indicators = [
            '业务申请', '交易记录', '授权', '附件信息', 
            '财务信息', '基本信息', '小技巧', '注意', '提示',
            '现在演示', '接下来演示',
        ]
        if any(s in curr_clean[:10] for s in module_indicators):
            return True
    
    return False


def should_force_new_paragraph(current_para_segments: List[str], current_para_start: float, 
                               current_para_end: float) -> bool:
    """强制分段检查：防止段落过长"""
    if current_para_segments:
        last_text = current_para_segments[-1]
        if not is_sentence_end(last_text):
            return False
    
    if current_para_end - current_para_start > MAX_PARAGRAPH_DURATION:
        return True
    
    if len(current_para_segments) >= MAX_PARAGRAPH_SEGMENTS:
        return True
    
    return False


def smart_segment(segments: List[Tuple[float, float, str]]) -> List[Tuple[float, float, str]]:
    """
    智能分段：结合内容分析和长度控制
    
    根据全局变量 ENABLE_SMART_SEGMENT 决定是否启用智能分段：
    - True: 启用智能分段（根据内容信号、停顿时间、长度控制）
    - False: 简单分段（仅按固定时长30秒或固定片段数10个分段）
    """
    if not segments:
        return []
    
    # 如果未启用智能分段，使用简单分段策略
    if not ENABLE_SMART_SEGMENT:
        return simple_segment(segments)
    
    paragraphs = []
    current_texts = []
    current_start = None
    current_end = None
    pending_split = False
    
    # 统计整体文本的标点情况
    all_text = ''.join([s[2] for s in segments])
    has_punctuation = any(p in all_text for p in ['。', '？', '！', '；'])
    
    for i, (start, end, text) in enumerate(segments):
        if current_start is None:
            current_start = start
            current_end = end
            current_texts.append(text)
        else:
            prev_text = current_texts[-1] if current_texts else ""
            
            need_new_para = False
            
            # 1. 强信号判断
            curr_clean = text.strip()
            strong_starters = [
                # 顺序词
                '首先', '第一', '第二', '第三', '第四', '第五', '接下来', '下面', '最后', '最终',
                # 流程词
                '操作流程', '授权提交', '申请进度', '小技巧', '温馨提示', '注意',
                # 业务词（银行/金融场景）
                '服务简介', '交易', '业务申请', '信用证', '进口', '出口', '开立',
                # 动作词
                '点击', '选择', '填写', '上传', '提交', '确认', '查看',
                # 演示词
                '现在我们演示', '现在演示', '接下来演示', '例如', '比如',
            ]
            if any(curr_clean.startswith(s) for s in strong_starters):
                need_new_para = True
            
            # 2. 停顿时间判断
            if not need_new_para:
                time_gap = start - current_end
                if time_gap > SEGMENT_GAP_THRESHOLD and is_sentence_end(prev_text):
                    need_new_para = True
            
            # 3. 长度检查 - 强制分段防止段落过长
            if not need_new_para:
                para_duration = end - current_start
                para_segments_count = len(current_texts)
                
                # 超过最大时长或片段数，强制分段
                if para_duration > MAX_PARAGRAPH_DURATION or para_segments_count >= MAX_PARAGRAPH_SEGMENTS:
                    need_new_para = True
            
            # 4. 处理待分段请求
            if pending_split:
                if has_punctuation:
                    if is_sentence_end(prev_text):
                        need_new_para = True
                        pending_split = False
                else:
                    need_new_para = True
                    pending_split = False
            
            if need_new_para:
                if is_sentence_end(prev_text):
                    para_text = ''.join(current_texts)
                    paragraphs.append((current_start, current_end, para_text))
                    current_start = start
                    current_texts = [text]
                    current_end = end
                else:
                    current_texts.append(text)
                    current_end = end
            else:
                current_texts.append(text)
                current_end = end
    
    if current_texts:
        para_text = ''.join(current_texts)
        paragraphs.append((current_start, current_end, para_text))
    
    return paragraphs


def simple_segment(segments: List[Tuple[float, float, str]]) -> List[Tuple[float, float, str]]:
    """
    简单分段策略：仅按固定时长或固定片段数分段
    默认每30秒或每10个片段分一段（以先达到的为准）
    """
    SIMPLE_SEGMENT_DURATION = 30    # 秒
    SIMPLE_SEGMENT_COUNT = 10       # 片段数
    
    paragraphs = []
    current_texts = []
    current_start = None
    current_end = None
    
    for start, end, text in segments:
        if current_start is None:
            current_start = start
            current_end = end
            current_texts.append(text)
        else:
            current_texts.append(text)
            current_end = end
            
            # 检查是否达到分段条件：时长或片段数
            duration = current_end - current_start
            count = len(current_texts)
            
            if duration >= SIMPLE_SEGMENT_DURATION or count >= SIMPLE_SEGMENT_COUNT:
                para_text = ''.join(current_texts)
                paragraphs.append((current_start, current_end, para_text))
                # 重置
                current_start = None
                current_texts = []
                current_end = None
    
    # 处理剩余的片段
    if current_texts:
        para_text = ''.join(current_texts)
        paragraphs.append((current_start, current_end, para_text))
    
    return paragraphs


def add_punctuation(text: str) -> str:
    """简单的标点恢复处理 - 仅清理和补充句尾标点"""
    result = text
    
    # 清理重复标点
    result = re.sub(r'，\s*，+', '，', result)
    result = re.sub(r'，\s*。', '。', result)
    result = re.sub(r'。\s*，', '。', result)
    
    # 句尾加句号（如果没有标点）
    if not is_sentence_end(result):
        result += '。'
    
    return result


def post_process(text: str) -> str:
    """文本后处理：统一标点、清理空格"""
    # 先移除所有多余空格（中文文本不需要空格）
    text = re.sub(r'\s+', '', text)
    
    # 英文标点转中文标点
    text = text.replace(',', '，')
    text = text.replace('.', '。')
    text = text.replace('?', '？')
    text = text.replace('!', '！')
    text = text.replace(':', '：')
    text = text.replace(';', '；')
    text = text.replace('(', '（')
    text = text.replace(')', '）')
    
    # 清理重复标点
    text = re.sub(r'，+', '，', text)
    text = re.sub(r'。+', '。', text)
    
    # 确保段落结尾有句号
    if text and not is_sentence_end(text):
        text += '。'
    
    return text


def generate_markdown(audio_name: str, paragraphs: List[Tuple[float, float, str]], 
                      output_path: Path) -> Path:
    """生成Markdown文件"""
    lines = [
        f"# {audio_name} - 语音转录文稿\n",
        f"**段落数**: {len(paragraphs)}\n",
        "---\n"
    ]
    
    for start, end, text in paragraphs:
        timestamp = format_timestamp(start)
        # 文本已在parse_srt中处理过，这里只做最终清理
        clean_text = post_process(text) if text else ""
        if clean_text:
            lines.append(f"{timestamp}\n")
            lines.append(f"{clean_text}\n")
            lines.append("")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    return output_path


def process_single_file(input_path: Path, output_dir: Path, model: str = DEFAULT_MODEL,
                        keep_temp: bool = False) -> Optional[Path]:
    """
    处理单个文件（视频或音频）
    
    Args:
        input_path: 输入文件路径
        output_dir: 输出目录
        model: whisper模型名称
        keep_temp: 是否保留临时文件
    
    Returns:
        生成的Markdown文件路径，失败返回None
    """
    print(f"\n{'='*60}")
    print(f"处理文件: {input_path.name}")
    print(f"{'='*60}")
    
    # 创建临时目录
    temp_dir = output_dir / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    # 判断文件类型
    if input_path.suffix.lower() in VIDEO_EXTENSIONS:
        # 视频文件：先提取音频
        audio_path = extract_audio(input_path, temp_dir)
        if not audio_path:
            print(f"[失败] 音频提取失败: {input_path.name}")
            return None
    elif input_path.suffix.lower() in AUDIO_EXTENSIONS:
        # 音频文件：直接使用
        audio_path = input_path
    else:
        print(f"[失败] 不支持的文件格式: {input_path.suffix}")
        return None
    
    # 转录
    srt_path = transcribe_audio(audio_path, output_dir, model)
    if not srt_path:
        print(f"[失败] 转录失败: {input_path.name}")
        return None
    
    # 解析并分段
    print(f"  [分段] 解析SRT文件...")
    segments = parse_srt(srt_path)
    print(f"       原始片段: {len(segments)} 个")
    
    paragraphs = smart_segment(segments)
    segment_mode = "智能分段" if ENABLE_SMART_SEGMENT else "简单分段"
    print(f"       {segment_mode}: {len(paragraphs)} 个段落")
    
    # 生成Markdown
    md_path = output_dir / f"{input_path.stem}_transcription.md"
    generate_markdown(input_path.stem, paragraphs, md_path)
    print(f"[完成] Markdown已保存: {md_path.name}")
    
    # 清理临时文件
    if not keep_temp and input_path.suffix.lower() in VIDEO_EXTENSIONS and audio_path.exists():
        audio_path.unlink()
        print(f"  [清理] 已删除临时音频文件")
    
    return md_path


def process_batch(input_dir: Path, output_dir: Path, model: str = DEFAULT_MODEL,
                  keep_temp: bool = False) -> List[Path]:
    """
    批量处理文件夹
    
    Args:
        input_dir: 输入文件夹路径
        output_dir: 输出目录
        model: whisper模型名称
        keep_temp: 是否保留临时文件
    
    Returns:
        成功生成的Markdown文件路径列表
    """
    # 查找所有支持的文件
    files = [f for f in input_dir.iterdir() 
             if f.is_file() and f.suffix.lower() in ALL_EXTENSIONS]
    
    if not files:
        print(f"[警告] 在 {input_dir} 中未找到支持的视频/音频文件")
        return []
    
    print(f"\n{'='*60}")
    print(f"批量处理: 找到 {len(files)} 个文件")
    print(f"模型: {model}")
    print(f"{'='*60}")
    
    results = []
    
    # 使用进度条
    if TQDM_AVAILABLE:
        iterator = tqdm(enumerate(files, 1), total=len(files), desc="处理进度")
    else:
        iterator = enumerate(files, 1)
    
    for i, file_path in iterator:
        if not TQDM_AVAILABLE:
            print(f"\n[{i}/{len(files)}] ", end="")
        
        result = process_single_file(file_path, output_dir, model, keep_temp)
        if result:
            results.append(result)
    
    # 打印汇总
    print(f"\n{'='*60}")
    print(f"批量处理完成!")
    print(f"成功: {len(results)}/{len(files)}")
    print(f"输出目录: {output_dir.absolute()}")
    print(f"{'='*60}")
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description='音视频转录脚本 - 智能分段生成Markdown',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python transcribe_audio.py video.mp4                    # 处理单个视频
  python transcribe_audio.py audio.wav                    # 处理单个音频
  python transcribe_audio.py ./videos/                    # 批量处理文件夹
  python transcribe_audio.py video.mp4 --model tiny       # 使用tiny模型
  python transcribe_audio.py ./videos/ --output ./out/    # 指定输出目录
        """
    )
    
    parser.add_argument('input', help='输入文件或文件夹路径')
    parser.add_argument('--model', '-m', default=DEFAULT_MODEL,
                       choices=['tiny', 'base', 'small', 'medium', 'large'],
                       help=f'whisper模型名称 (默认: {DEFAULT_MODEL})')
    parser.add_argument('--output', '-o', default='./transcriptions',
                       help='输出目录 (默认: ./transcriptions)')
    parser.add_argument('--keep-temp', action='store_true',
                       help='保留临时音频文件')
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if not input_path.exists():
        print(f"[错误] 路径不存在: {input_path}")
        return
    
    if input_path.is_file():
        # 处理单个文件
        result = process_single_file(input_path, output_dir, args.model, args.keep_temp)
        if result:
            print(f"\n[成功] 输出文件: {result}")
        else:
            print(f"\n[失败] 处理失败")
    
    elif input_path.is_dir():
        # 批量处理文件夹
        process_batch(input_path, output_dir, args.model, args.keep_temp)


if __name__ == "__main__":
    main()
