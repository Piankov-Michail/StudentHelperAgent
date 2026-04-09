from typing import List, Dict, Any
from langchain_ollama import ChatOllama
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from tools.hf_whisper_tool import create_transcribe_video_hf_tool
from tools.groq_api_whisper_tool import create_transcribe_video_groq_tool
from tools.graphrag_upload_tool import create_graphrag_upload_tool
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

ТВОИ ИНСТРУМЕНТЫ:
1. transcribe_video - транскрибирует видео/аудио файл
2. graphrag_upload - загружает конспект в базу знаний

ТВОИ ЗАДАЧИ:
1. Если пользователь приложил видео/аудио файл — используй инструмент transcribe_video для получения транскрипции
2. На основе транскрипции создавай МАКСИМАЛЬНО ПОДРОБНЫЙ конспект
3. Если пользователь просит загрузить конспект в базу знаний — используй graphrag_upload

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
- Если видео не приложено — отвечай на вопрос пользователя обычным образом
- Для загрузки в базу знаний передавай ПОЛНЫЙ текст конспекта в graphrag_upload'''
    
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
        # Приоритет: Groq API > HuggingFace API
        tools = [
            create_transcribe_video_groq_tool(user_id=user_id),
            create_graphrag_upload_tool(user_id=user_id)
        ]
        
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
        from tools.groq_api_whisper_tool import transcribe_video_groq_direct
        from tools.hf_whisper_tool import transcribe_video_direct
        from tools.graphrag_upload_tool import upload_summary_to_graph
        
        send_progress = context.get("send_progress")
        user_id = context.get("user_id")
        file_path = context.get("file_path")
        chat_history = context.get("chat_history", [])
        
        # ✅ Сохраняем user_id для создания инструмента
        self._current_user_id = user_id
        
        # Проверяем, просит ли пользователь загрузить конспект в базу
        is_upload_request = any(keyword in message.lower() for keyword in [
            "загрузи", "сохрани", "добавь в базу", "в базу знаний", "upload", "сохранить"
        ])
        
        upload_result = None
        
        # Если есть файл, сначала транскрибируем его
        transcription = None
        if file_path:
            if send_progress:
                await send_progress(2, "🔊 Транскрибация через Whisper...")
            
            # Пробуем Groq API, если не работает - fallback на HuggingFace
            try:
                transcription = await transcribe_video_groq_direct(file_path, user_id=user_id)
                
                # Если Groq вернул ошибку в тексте, пробуем HF
                if transcription and transcription.startswith("Ошибка"):
                    logger.warning(f"Groq API failed, falling back to HuggingFace: {transcription}")
                    if send_progress:
                        await send_progress(2, "🔊 Переключение на HuggingFace Whisper...")
                    transcription = await transcribe_video_direct(file_path, user_id=user_id)
            except Exception as e:
                logger.warning(f"Groq API exception, falling back to HuggingFace: {e}")
                if send_progress:
                    await send_progress(2, "🔊 Переключение на HuggingFace Whisper...")
                transcription = await transcribe_video_direct(file_path, user_id=user_id)
            
            if send_progress:
                await send_progress(3, "📝 Генерация конспекта...")
            
            # Создаем промпт для генерации конспекта на основе транскрипции
            final_message = f"{message}\n\nТранскрипция:\n{transcription}"
        else:
            # Если файла нет, просто отвечаем на вопрос
            final_message = message
            
            # Если пользователь просит загрузить конспект, ищем его в истории
            if is_upload_request:
                if send_progress:
                    await send_progress(2, "📤 Загрузка конспекта в базу знаний...")
                
                # Ищем последний длинный ответ ассистента (это конспект)
                summary_text = None
                for msg in reversed(chat_history[-10:]):
                    if msg.role == "assistant" and len(msg.content) > 500:
                        summary_text = msg.content
                        break
                
                if summary_text:
                    upload_result = await upload_summary_to_graph(user_id, summary_text)
                    logger.info(f"Upload result: {upload_result}")
                else:
                    upload_result = "❌ Не найден конспект для загрузки. Сначала создайте конспект из видео."
        
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
        
        # Если был результат загрузки, добавляем его в контекст
        if upload_result:
            final_message = f"{message}\n\nРезультат загрузки в базу знаний:\n{upload_result}"
        
        # Добавляем текущее сообщение
        messages.append(HumanMessage(content=final_message))
        
        full_response = ""
        
        # Если была загрузка, сначала выводим результат
        if upload_result:
            yield {"type": "token", "content": upload_result + "\n\n"}
            full_response += upload_result + "\n\n"
        
        try:
            async for chunk in self.llm.astream(messages):
                if hasattr(chunk, 'content') and chunk.content:
                    full_response += chunk.content
                    yield {"type": "token", "content": chunk.content}
        except Exception as e:
            logger.error(f"Ошибка при streaming от LLM: {e}")
            error_message = f"❌ Ошибка подключения к LLM (Ollama). Проверьте настройки OLLAMA_BASE_URL.\n\n"
            if transcription:
                error_message += f"Транскрипция была успешно получена:\n\n{transcription[:500]}..."
            yield {"type": "token", "content": error_message}
            full_response += error_message
        
        yield {"type": "complete", "content": full_response}
    
    async def get_available_models(self) -> List[str]:
        return [self.config.model_name]