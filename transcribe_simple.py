#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版视频转录脚本
"""

import whisper
import os
from pathlib import Path
from datetime import timedelta

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
    
    # 加载模型
    print("加载 Whisper tiny 模型...")
    model = whisper.load_model("tiny")
    print("模型加载完成！")
    
    for video_path in video_files:
        print(f"\n正在处理: {video_path.name}")
        
        # 转录
        result = model.transcribe(
            str(video_path),
            language="zh",
            verbose=True  # 显示进度
        )
        
        # 生成 Markdown
        lines = []
        lines.append(f"# {video_path.stem} - 语音转录文稿\n")
        lines.append("---\n")
        
        # 按时间戳组织段落
        current_text = ""
        current_start = None
        paragraph_gap = 30  # 30秒间隔分段
        
        for seg in result["segments"]:
            if current_start is None:
                current_start = seg["start"]
                current_text = seg["text"].strip()
            elif seg["start"] - result["segments"][result["segments"].index(seg)-1]["end"] > paragraph_gap:
                # 新段落
                timestamp = format_timestamp(current_start)
                lines.append(f"{timestamp}\n")
                lines.append(f"{current_text}\n")
                current_start = seg["start"]
                current_text = seg["text"].strip()
            else:
                current_text += " " + seg["text"].strip()
        
        # 添加最后一个段落
        if current_text:
            timestamp = format_timestamp(current_start)
            lines.append(f"{timestamp}\n")
            lines.append(f"{current_text}\n")
        
        # 保存
        output_path = output_dir / f"{video_path.stem}_transcription.md"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        
        print(f"已保存: {output_path}")

if __name__ == "__main__":
    main()
