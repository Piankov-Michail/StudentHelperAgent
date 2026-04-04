from typing import Dict, Callable, List

class ToolRegistry:
    """Реестр инструментов для агентов"""
    
    _tools: Dict[str, Callable] = {}
    
    @classmethod
    def register(cls, name: str, tool: Callable):
        cls._tools[name] = tool
    
    @classmethod
    def get(cls, name: str) -> Callable:
        if name not in cls._tools:
            raise ValueError(f"Инструмент {name} не найден")
        return cls._tools[name]
    
    @classmethod
    def get_all(cls) -> List[Callable]:
        return list(cls._tools.values())
    
    @classmethod
    def get_names(cls) -> List[str]:
        return list(cls._tools.keys())

# Регистрация инструментов
from tools.whisper_tool import transcribe_video_hf
ToolRegistry.register("transcribe_video", transcribe_video_hf)