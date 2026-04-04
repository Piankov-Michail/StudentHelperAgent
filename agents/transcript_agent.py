from typing import List, Dict, Any
from langchain_ollama import ChatOllama
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from tools.hf_whisper_tool import create_transcribe_video_hf_tool
from .base import BaseAgent, AgentConfig, AgentResult
import logging

logger = logging.getLogger(__name__)


class TranscriptAgent(BaseAgent):
    """Агент для транскрибации видео через HuggingFace Whisper API"""
    
    @property
    def name(self) -> str:
        return "transcript"
    
    @property
    def description(self) -> str:
        return "Транскрибация видео/аудио (HuggingFace Whisper API)"
    
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.llm = ChatOllama(
            base_url=config.base_url,
            model=config.model_name,
            temperature=config.temperature
        )
        # Сохраняем hf_token из конфига для использования в инструменте
        self.hf_token = config.hf_token
        # Инструменты создаются динамически в process() с user_id
        self.tools = []
        self.prompt = ChatPromptTemplate.from_messages([
            ('system', self._get_system_prompt()),
            ('human', '{input}'),
            ('placeholder', '{agent_scratchpad}')
        ])
        self._executor = None
        self._current_user_id: int | None = None
    
    def _get_system_prompt(self) -> str:
        return '''Ты — профессиональный ассистент для создания подробных конспектов видео-лекций.

ТВОИ ЗАДАЧИ:
1. Если пользователь приложил видео/аудио файл — используй инструмент transcribe_video для получения транскрипции
2. На основе транскрипции создавай МАКСИМАЛЬНО ПОДРОБНЫЙ конспект

ТРЕБОВАНИЯ К КОНСПЕКТУ:
- ✅ Не упускай НИКАКОЙ важной информации
- ✅ Сохраняй логическую структуру лекции
- ✅ Выделяй ключевые понятия, определения, термины
- ✅ Отмечай примеры, задания, дедлайны
- ✅ Записывай имена, названия, даты, цифры

ФОРМАТ ОТВЕТА:
Используй четкую структуру с заголовками Markdown.

ВАЖНО:
- Отвечай на русском языке
- Если видео не приложено — отвечай на вопрос пользователя обычным образом'''
    
    def _get_executor(self, tools: list) -> AgentExecutor:
        """Создаёт executor с переданными инструментами"""
        agent = create_tool_calling_agent(self.llm, tools, self.prompt)
        return AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=False,
            handle_parsing_errors=True
        )
    
    async def process(self, message: str, context: Dict[str, Any]) -> AgentResult:
        send_progress = context.get("send_progress")
        user_id = context.get("user_id")
        
        # ✅ Сохраняем user_id для создания инструмента
        self._current_user_id = user_id
        
        if send_progress:
            await send_progress(2, "🔊 Транскрибация через Whisper...")
        
        # ✅ Создаём инструмент с привязанным user_id через фабрику
        # Это решает проблему с functools.partial и LangChain
        tools = [create_transcribe_video_hf_tool(user_id=user_id)]
        
        executor = self._get_executor(tools)
        result = await executor.ainvoke({"input": message})
        
        if send_progress:
            await send_progress(3, "📝 Анализ транскрипции...")
        
        # Собираем информацию об использованных инструментах
        tools_used = []
        if hasattr(result, 'intermediate_steps'):
            for step in result.intermediate_steps:
                tools_used.append(step[0].tool)
        
        return AgentResult(
            output=result['output'],
            model=self.config.model_name,
            metadata={
                "agent_type": "transcript",
                "tools_used": tools_used,
                "context": context,
                "user_id": user_id
            }
        )
    
    async def get_available_models(self) -> List[str]:
        return [self.config.model_name]