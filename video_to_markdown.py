#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频语音转录工具
将视频中的语音转换为带时间戳的 Markdown 文档
"""

import os
import sys
import whisper
from datetime import timedelta
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# 设置 Hugging Face 镜像（如果需要下载模型）
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'


def format_timestamp(seconds):
    """将秒数转换为 [HH:MM:SS] 格式"""
    td = timedelta(seconds=int(seconds))
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"[{hours:02d}:{minutes:02d}:{seconds:02d}]"


def transcribe_video(video_path, model):
    """
    使用已加载的 Whisper 模型转录视频语音
    返回带时间戳的段落列表
    """
    print(f"正在转录: {video_path.name}")
    
    # 转录音频，获取带时间戳的结果
    result = model.transcribe(
        str(video_path),
        language="zh",  # 指定中文
        verbose=False,
        condition_on_previous_text=True
    )
    
    return result["segments"]


def organize_into_paragraphs(segments, paragraph_interval=30):
    """
    将短片段组织成段落长文结构
    paragraph_interval: 多少秒内的内容合并为一个段落
    """
    if not segments:
        return []
    
    paragraphs = []
    current_paragraph = {
        "start": segments[0]["start"],
        "end": segments[0]["end"],
        "text": segments[0]["text"].strip()
    }
    
    for segment in segments[1:]:
        # 如果时间间隔较小，合并到当前段落
        if segment["start"] - current_paragraph["end"] < paragraph_interval:
            current_paragraph["end"] = segment["end"]
            current_paragraph["text"] += " " + segment["text"].strip()
        else:
            # 时间间隔较大，开启新段落
            paragraphs.append(current_paragraph)
            current_paragraph = {
                "start": segment["start"],
                "end": segment["end"],
                "text": segment["text"].strip()
            }
    
    # 添加最后一个段落
    if current_paragraph["text"]:
        paragraphs.append(current_paragraph)
    
    return paragraphs


def clean_and_improve_text(text):
    """
    整理文本，使其更通顺
    """
    # 移除多余的空格
    text = " ".join(text.split())
    # 移除重复的标点
    text = text.replace("。。", "。")
    text = text.replace("，，", "，")
    text = text.replace("  ", " ")
    # 确保句子结尾有标点
    if text and text[-1] not in "。！？":
        text += "。"
    return text


def generate_markdown(video_name, paragraphs):
    """
    生成 Markdown 格式的文档
    """
    lines = []
    lines.append(f"# {video_name} - 语音转录文稿\n")
    lines.append(f"**视频名称**: {video_name}\n")
    lines.append(f"**段落数**: {len(paragraphs)}\n")
    lines.append("---\n")
    
    for i, para in enumerate(paragraphs, 1):
        timestamp = format_timestamp(para["start"])
        text = clean_and_improve_text(para["text"])
        
        # 跳过空段落
        if not text:
            continue
            
        # 时间戳单独一行，后面换行另起段落
        lines.append(f"{timestamp}\n")
        lines.append(f"{text}\n")
    
    return "\n".join(lines)


def process_video(video_path, output_dir, model):
    """
    处理单个视频文件
    """
    video_path = Path(video_path)
    video_name = video_path.stem
    
    print(f"\n{'='*60}")
    print(f"处理视频: {video_name}")
    print(f"{'='*60}")
    
    # 转录音频
    segments = transcribe_video(video_path, model)
    
    if not segments:
        print("未检测到语音内容")
        return None
    
    print(f"转录完成，共 {len(segments)} 个片段")
    
    # 组织成段落
    print("正在组织段落结构...")
    paragraphs = organize_into_paragraphs(segments)
    print(f"组织完成，共 {len(paragraphs)} 个段落")
    
    # 生成 Markdown
    markdown_content = generate_markdown(video_name, paragraphs)
    
    # 保存文件
    output_path = Path(output_dir) / f"{video_name}_transcription.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(markdown_content)
    
    print(f"已保存到: {output_path}")
    return output_path


def main():
    # 视频文件夹路径
    video_dir = Path("D:/FFOutput")
    # 输出文件夹
    output_dir = Path("D:/codework space")
    
    # 支持的视频格式
    video_extensions = {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm"}
    
    # 查找所有视频文件
    video_files = [
        f for f in video_dir.iterdir() 
        if f.is_file() and f.suffix.lower() in video_extensions
    ]
    
    if not video_files:
        print(f"在 {video_dir} 中未找到视频文件")
        return
    
    print(f"找到 {len(video_files)} 个视频文件:")
    for vf in video_files:
        print(f"  - {vf.name}")
    
    # 加载模型 - 使用 tiny 模型更快下载
    model_size = "tiny"
    print(f"\n正在加载 Whisper 模型 ({model_size})...")
    print("首次运行需要下载模型，请耐心等待...")
    
    try:
        model = whisper.load_model(model_size)
        print("模型加载完成！")
    except Exception as e:
        print(f"模型加载失败: {e}")
        print("请检查网络连接，或手动下载模型到 ~/.cache/whisper/ 目录")
        return
    
    # 处理每个视频
    processed_files = []
    for video_file in video_files:
        try:
            output_path = process_video(video_file, output_dir, model)
            if output_path:
                processed_files.append(output_path)
        except Exception as e:
            print(f"处理 {video_file.name} 时出错: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*60}")
    print(f"处理完成！共生成 {len(processed_files)} 个文档:")
    for pf in processed_files:
        print(f"  - {pf}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
