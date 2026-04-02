from langchain_ollama import ChatOllama
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from tools import transcribe_video

prompt = '''Ты — профессиональный ассистент для создания подробных конспектов видео-лекций.
ТВОИ ЗАДАЧИ:
1. Если пользователь приложил видео/аудио файл — обязательно используй инструмент transcribe_video для получения транскрипции
2. На основе транскрипции создавай МАКСИМАЛЬНО ПОДРОБНЫЙ конспект
ТРЕБОВАНИЯ К КОНСПЕКТУ:
- ✅ Не упускай НИКАКОЙ важной информации
- ✅ Сохраняй логическую структуру лекции
- ✅ Выделяй ключевые понятия, определения, термины
- ✅ Отмечай примеры, которые приводит лектор
- ✅ Фиксируй задания, домашние работы, дедлайны
- ✅ Записывай имена, названия, даты, цифры
- ✅ Сохраняй контекст и связи между темами
ФОРМАТ ОТВЕТА:
Используй четкую структуру с заголовками.
ВАЖНО:
- Отвечай на русском языке
- Если видео не приложено — отвечай на вопрос пользователя обычным образом
- Будь точным и подробным, но без воды'''

class AgentManager:
    def __init__(self, model_name, base_url):
        self.llm = ChatOllama(base_url=base_url, model=model_name, temperature=0.8)
        self.tools = [transcribe_video]
        self.prompt = ChatPromptTemplate.from_messages([
            ('system', prompt),
            ('human', '{input}'),
            ('placeholder', '{agent_scratchpad}')
        ])
        self._executor = None
    
    def _get_executor(self):
        if self._executor is None:
            agent = create_tool_calling_agent(self.llm, self.tools, self.prompt)
            self._executor = AgentExecutor(agent=agent, tools=self.tools, verbose=False, handle_parsing_errors=True)
        return self._executor
        
    async def run(self, input_message: str) -> str:
        executor = self._get_executor()
        result = await executor.ainvoke({"input": input_message})
        return result['output']