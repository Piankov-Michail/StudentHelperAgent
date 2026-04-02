from faster_whisper import WhisperModel
from langchain_core.tools import tool

import subprocess

import os
import sys

_model = None

cuda_path = os.path.join(sys.prefix, 'lib', 'python3.10', 'site-packages', 'nvidia', 'cublas', 'lib')
if os.path.exists(cuda_path):
    os.environ["LD_LIBRARY_PATH"] = cuda_path + ":" + os.environ.get("LD_LIBRARY_PATH", "")

def get_model():
    global _model
    if _model is None:
        _model = WhisperModel("tiny", device="cpu", compute_type="int8")
    return _model

def extract_audio(video_path: str) -> str:
    ext = os.path.splitext(video_path)[1].lower()
    
    if ext in ['.mp3', '.wav', '.m4a', '.flac']:
        return video_path
        
    audio_path = video_path.replace(ext, "_converted.mp3")
    
    command = [
        'ffmpeg', '-i', video_path,
        '-vn', '-acodec', 'libmp3lame', '-ar', '16000', '-ac', '1',
        audio_path, '-y'
    ]
    
    subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    return audio_path

def compress_audio(input_path: str, output_path: str, bitrate: str = "32k"):
    """Сжать аудио для ускорения транскрибации"""
    command = [
        'ffmpeg', '-i', input_path,
        '-b:a', bitrate,
        '-ar', '16000',
        '-ac', '1',
        output_path, '-y'
    ]
    subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    return output_path

@tool
def transcribe_video(video_path: str) -> str:
    '''Транскрибация видео/аудио через локальный Whisper'''
    if not os.path.exists(video_path):
        return "Ошибка: Файл не найден."
    
    try:
        audio_path = extract_audio(video_path)
        ext = os.path.splitext(audio_path)[1].lower()
        audio_path = compress_audio(audio_path, audio_path.replace(ext, "_compressed.mp3"))
        model = WhisperModel("small", device="cpu", compute_type="int8")
        
        segments, info = model.transcribe(
            audio_path,
            beam_size=5,
            language="ru",
            vad_filter=True
        )
        
        full_text = []
        for segment in segments:
            full_text.append(segment.text)
        
        if audio_path != video_path:
            os.remove(audio_path)
        
        return " ".join(full_text)
        
    except Exception as e:
        return f"Ошибка при обработке видео: {str(e)}"