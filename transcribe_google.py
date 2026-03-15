#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用 Google Speech Recognition 转录音频
优点：免费、无需下载模型、支持中文
缺点：需要联网、有请求频率限制（适合短视频）
"""

import speech_recognition as sr
from pathlib import Path
from datetime import timedelta
from pydub import AudioSegment
import math

def format_timestamp(seconds):
    """转换为 [HH:MM:SS] 格式"""
    td = timedelta(seconds=int(seconds))
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"[{hours:02d}:{minutes:02d}:{seconds:02d}]"

def split_audio(audio_path, chunk_length_ms=30000):
    """
    将音频分割成小块（Google API 限制约 60 秒）
    chunk_length_ms: 每段长度（毫秒），默认 30 秒
    """
    audio = AudioSegment.from_wav(audio_path)
    
    chunks = []
    for i in range(0, len(audio), chunk_length_ms):
        chunk = audio[i:i + chunk_length_ms]
        chunks.append((i / 1000, chunk))  # (开始时间秒, 音频段)
    
    return chunks

def transcribe_audio_google(audio_path, language="zh-CN"):
    """
    使用 Google Speech Recognition 转录音频
    """
    recognizer = sr.Recognizer()
    audio_file = Path(audio_path)
    
    print(f"Loading audio: {audio_file.name}")
    
    # 分割音频（Google API 限制音频长度）
    print("Splitting audio into chunks...")
    chunks = split_audio(audio_path, chunk_length_ms=25000)  # 25 秒一段
    print(f"Total chunks: {len(chunks)}")
    
    results = []
    
    for i, (start_time, chunk) in enumerate(chunks, 1):
        print(f"\nProcessing chunk {i}/{len(chunks)}...")
        
        # 将音频段导出为临时文件
        temp_path = Path("temp_chunk.wav")
        chunk.export(temp_path, format="wav")
        
        try:
            # 识别
            with sr.AudioFile(str(temp_path)) as source:
                audio_data = recognizer.record(source)
            
            # 使用 Google API（免费，需要联网）
            text = recognizer.recognize_google(audio_data, language=language)
            
            if text:
                result = {
                    'start': start_time,
                    'end': start_time + len(chunk) / 1000,
                    'text': text
                }
                results.append(result)
                print(f"  [{format_timestamp(start_time)}] {text}")
            
        except sr.UnknownValueError:
            print(f"  [Chunk {i}] Could not understand audio")
        except sr.RequestError as e:
            print(f"  [Chunk {i}] API error: {e}")
        except Exception as e:
            print(f"  [Chunk {i}] Error: {e}")
        finally:
            # 清理临时文件
            if temp_path.exists():
                temp_path.unlink()
    
    return results

def generate_markdown(title, results, output_path):
    """生成带时间戳的 Markdown 文档"""
    lines = []
    lines.append(f"# {title} - 语音转录文稿\n")
    lines.append(f"**音频文件**: {title}.wav\n")
    lines.append(f"**识别片段数**: {len(results)}\n")
    lines.append("---\n")
    
    # 合并相近的时间段为段落
    paragraph_gap = 30  # 30秒内合并
    current_text = ""
    current_start = None
    last_end = 0
    
    for r in results:
        text = r['text'].strip()
        if not text:
            continue
        
        if current_start is None:
            current_start = r['start']
            current_text = text
            last_end = r['end']
        elif r['start'] - last_end > paragraph_gap:
            # 保存当前段落
            timestamp = format_timestamp(current_start)
            lines.append(f"{timestamp}\n")
            lines.append(f"{current_text}\n")
            # 新段落
            current_start = r['start']
            current_text = text
            last_end = r['end']
        else:
            current_text += " " + text
            last_end = r['end']
    
    # 最后一个段落
    if current_text:
        timestamp = format_timestamp(current_start)
        lines.append(f"{timestamp}\n")
        lines.append(f"{current_text}\n")
    
    # 保存
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    
    print(f"\nMarkdown saved: {output_path}")

def main():
    audio_dir = Path("D:/codework space/audio")
    output_dir = Path("D:/codework space")
    
    # 获取所有音频文件
    audio_files = list(audio_dir.glob("*.wav"))
    print(f"Found {len(audio_files)} audio files")
    
    if not audio_files:
        print("No audio files found!")
        return
    
    print("\n" + "=" * 60)
    print("Google Speech Recognition Transcription")
    print("=" * 60)
    print("Note: Requires internet connection")
    print("      Free to use, but has rate limits")
    print("=" * 60)
    
    for audio_path in audio_files:
        print(f"\nProcessing: {audio_path.name}")
        print("-" * 40)
        
        results = transcribe_audio_google(audio_path)
        
        if results:
            output_md = output_dir / f"{audio_path.stem}_transcription.md"
            generate_markdown(audio_path.stem, results, output_md)
            print(f"\n✓ Done: {audio_path.name}")
        else:
            print(f"\n✗ Failed: {audio_path.name}")
    
    print("\n" + "=" * 60)
    print("All done!")
    print("=" * 60)

if __name__ == "__main__":
    main()
