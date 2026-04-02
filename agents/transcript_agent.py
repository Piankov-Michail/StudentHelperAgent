from typing import List, Dict, Any
from langchain_ollama import ChatOllama
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from tools.whisper_tool import transcribe_video  # ✅ Локальный Whisper
from .base import BaseAgent, AgentConfig, AgentResult

class TranscriptAgent(BaseAgent):
    """Агент для транскрибации видео через локальный Whisper"""
    
    @property
    def name(self) -> str:
        return "transcript"
    
    @property
    def description(self) -> str:
        return "Транскрибация видео/аудио (локальный Whisper)"
    
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.llm = ChatOllama(
            base_url=config.base_url,
            model=config.model_name,
            temperature=config.temperature
        )
        self.tools = [transcribe_video]  # ✅ Локальный инструмент
        self.prompt = ChatPromptTemplate.from_messages([
            ('system', self._get_system_prompt()),
            ('human', '{input}'),
            ('placeholder', '{agent_scratchpad}')
        ])
        self._executor = None
    
    def _get_system_prompt(self) -> str:
        return '''Ты — профессиональный ассистент для создания подробных конспектов видео-лекций.

ТВОИ ЗАДАЧИ:
1. Если пользователь приложил видео/аудио файл — используй инструмент transcribe_video
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
- Обработка происходит локально — файлы никуда не отправляются'''
    
    def _get_executor(self) -> AgentExecutor:
        if self._executor is None:
            agent = create_tool_calling_agent(self.llm, self.tools, self.prompt)
            self._executor = AgentExecutor(
                agent=agent,
                tools=self.tools,
                verbose=False,
                handle_parsing_errors=True
            )
        return self._executor
    
    async def process(self, message: str, context: Dict[str, Any]) -> AgentResult:
        send_progress = context.get("send_progress")
        
        if send_progress:
            await send_progress(2, "🔊 Транскрибация через Whisper...")
        
        executor = self._get_executor()
        result = await executor.ainvoke({"input": message})
        
        if send_progress:
            await send_progress(3, "📝 Анализ транскрипции...")
        
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
                "context": context
            }
        )
    
    async def get_available_models(self) -> List[str]:
        return [self.config.model_name]