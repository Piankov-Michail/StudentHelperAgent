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
    
    async def process_stream(self, message: str, context: Dict[str, Any]):
        """Streaming версия - сначала выполняет tools, потом стримит финальный ответ LLM"""
        from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
        from tools.hf_whisper_tool import transcribe_video_direct
        
        send_progress = context.get("send_progress")
        user_id = context.get("user_id")
        file_path = context.get("file_path")
        chat_history = context.get("chat_history", [])
        
        # ✅ Сохраняем user_id для создания инструмента
        self._current_user_id = user_id
        
        # Если есть файл, сначала транскрибируем его
        transcription = None
        if file_path:
            if send_progress:
                await send_progress(2, "🔊 Транскрибация через Whisper...")
            
            # Вызываем транскрибацию напрямую
            transcription = await transcribe_video_direct(file_path, user_id=user_id)
            
            if send_progress:
                await send_progress(3, "📝 Генерация конспекта...")
            
            # Создаем промпт для генерации конспекта на основе транскрипции
            final_message = f"{message}\n\nТранскрипция:\n{transcription}"
        else:
            # Если файла нет, просто отвечаем на вопрос
            final_message = message
        
        # Генерируем ответ со streaming с учётом истории
        system_prompt = self._get_system_prompt()
        
        # Формируем сообщения с учётом истории
        messages = [SystemMessage(content=system_prompt)]
        
        # Добавляем историю чата (только неудалённые сообщения)
        for msg in chat_history:
            if msg.role == "user":
                messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                messages.append(AIMessage(content=msg.content))
        
        # Добавляем текущее сообщение
        messages.append(HumanMessage(content=final_message))
        
        full_response = ""
        async for chunk in self.llm.astream(messages):
            if hasattr(chunk, 'content') and chunk.content:
                full_response += chunk.content
                yield {"type": "token", "content": chunk.content}
        
        yield {"type": "complete", "content": full_response}
    
    async def get_available_models(self) -> List[str]:
        return [self.config.model_name]