#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用 faster-whisper 的视频转录脚本
"""

from faster_whisper import WhisperModel
from pathlib import Path
from datetime import timedelta
import os

# 设置模型缓存路径
os.environ['HF_HOME'] = str(Path.home() / '.cache' / 'huggingface')

def format_timestamp(seconds):
    """转换为 [HH:MM:SS] 格式"""
    td = timedelta(seconds=int(seconds))
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"[{hours:02d}:{minutes:02d}:{seconds:02d}]"

def main():
    video_dir = Path("D:/FFOutput")
    output_dir = Path("D:/codework space")
    
    # 获取所有mp4文件
    video_files = list(video_dir.glob("*.mp4"))
    print(f"找到 {len(video_files)} 个视频文件")
    
    # 加载模型 - 使用 tiny 模型，INT8 量化，自动下载
    print("加载 faster-whisper tiny 模型 (首次使用会自动下载)...")
    print("模型大小约 39MB，请耐心等待...")
    
    try:
        # 使用 CPU 和 INT8 量化
        model = WhisperModel("tiny", device="cpu", compute_type="int8")
        print("模型加载完成！")
    except Exception as e:
        print(f"模型加载失败: {e}")
        print("如果下载失败，请检查网络连接")
        return
    
    for video_path in video_files:
        print(f"\n{'='*60}")
        print(f"正在处理: {video_path.name}")
        print(f"{'='*60}")
        
        try:
            # 转录 - 返回生成器
            segments, info = model.transcribe(
                str(video_path),
                language="zh",
                beam_size=5,
                condition_on_previous_text=True
            )
            
            print(f"检测到语言: {info.language}, 概率: {info.language_probability:.2f}")
            
            # 收集所有片段
            segments_list = list(segments)
            print(f"共 {len(segments_list)} 个语音片段")
            
            if not segments_list:
                print("未检测到语音内容，跳过")
                continue
            
            # 生成 Markdown
            lines = []
            lines.append(f"# {video_path.stem} - 语音转录文稿\n")
            lines.append(f"**视频文件**: {video_path.name}\n")
            lines.append(f"**语音片段数**: {len(segments_list)}\n")
            lines.append("---\n")
            
            # 按时间组织段落 - 30秒内内容合并为一段
            paragraph_gap = 30
            current_text = ""
            current_start = None
            last_end = 0
            
            for seg in segments_list:
                text = seg.text.strip()
                if not text:
                    continue
                
                # 如果是新段落（时间间隔较大）
                if current_start is None:
                    current_start = seg.start
                    current_text = text
                    last_end = seg.end
                elif seg.start - last_end > paragraph_gap:
                    # 保存当前段落
                    timestamp = format_timestamp(current_start)
                    lines.append(f"{timestamp}\n")
                    lines.append(f"{current_text}\n")
                    # 开始新段落
                    current_start = seg.start
                    current_text = text
                    last_end = seg.end
                else:
                    # 继续当前段落
                    current_text += " " + text
                    last_end = seg.end
            
            # 添加最后一个段落
            if current_text:
                timestamp = format_timestamp(current_start)
                lines.append(f"{timestamp}\n")
                lines.append(f"{current_text}\n")
            
            # 保存文件
            output_path = output_dir / f"{video_path.stem}_transcription.md"
            with open(output_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            
            print(f"✓ 已保存: {output_path}")
            
        except Exception as e:
            print(f"处理 {video_path.name} 时出错: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*60}")
    print("所有视频处理完成！")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
