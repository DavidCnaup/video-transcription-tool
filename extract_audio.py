#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
提取视频音频
"""

import subprocess
from pathlib import Path
import imageio_ffmpeg

def extract_audio(video_path, output_dir):
    """提取视频音频为 WAV 格式"""
    video_path = Path(video_path)
    output_path = Path(output_dir) / f"{video_path.stem}.wav"
    
    ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
    
    # 使用 FFmpeg 提取音频：16kHz, 单声道, 16bit
    cmd = [
        ffmpeg_path,
        "-i", str(video_path),
        "-vn",  # 不处理视频
        "-acodec", "pcm_s16le",  # PCM 16位
        "-ac", "1",  # 单声道
        "-ar", "16000",  # 16kHz 采样率
        "-y",  # 覆盖已有文件
        str(output_path)
    ]
    
    print(f"Extracting audio: {video_path.name}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"[OK] Audio saved: {output_path}")
        return output_path
    else:
        print(f"Error: {result.stderr}")
        return None

def main():
    video_dir = Path("D:/FFOutput")
    output_dir = Path("D:/codework space/audio")
    output_dir.mkdir(exist_ok=True)
    
    # 获取所有视频
    video_files = list(video_dir.glob("*.mp4"))
    print(f"Found {len(video_files)} video files\n")
    
    audio_files = []
    for video_path in video_files:
        audio_path = extract_audio(video_path, output_dir)
        if audio_path:
            audio_files.append(audio_path)
    
    print(f"\nTotal extracted: {len(audio_files)} audio files")
    return audio_files

if __name__ == "__main__":
    main()
