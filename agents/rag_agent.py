from typing import List, Dict, Any
from langchain_ollama import ChatOllama
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from tools.graphrag_upload_tool import create_graphrag_upload_tool
from tools.graphrag_query_tool import create_graphrag_query_tool
from .base import BaseAgent, AgentConfig, AgentResult
import logging

logger = logging.getLogger(__name__)


class RAGAgent(BaseAgent):
    """RAG агент для работы с графом знаний"""
    
    @property
    def name(self) -> str:
        return "rag"
    
    @property
    def description(self) -> str:
        return "Поиск и синтез знаний из графа (GraphRAG)"
    
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.llm = ChatOllama(
            base_url=config.base_url,
            model=config.model_name,
            temperature=config.temperature
        )
        self.prompt = ChatPromptTemplate.from_messages([
            ('system', self._get_system_prompt()),
            ('human', '{input}'),
            ('placeholder', '{agent_scratchpad}')
        ])
        self._executor = None
        self._current_user_id: int | None = None
    
    def _get_system_prompt(self) -> str:
        return '''Ты — ассистент для работы с базой знаний студента.

ТВОИ ИНСТРУМЕНТЫ:
1. graphrag_upload - загружает конспект в базу знаний (граф)
2. graphrag_query - ищет информацию в базе знаний пользователя

КОГДА ИСПОЛЬЗОВАТЬ:
- Если пользователь просит "загрузить конспект в базу", "сохранить в базу знаний" → используй graphrag_upload
- Если пользователь задает вопрос по материалу ("что такое...", "расскажи про...") → используй graphrag_query

ВАЖНО:
- Отвечай на русском языке
- Для загрузки передавай ПОЛНЫЙ текст конспекта в graphrag_upload
- Для поиска формулируй четкий запрос в graphrag_query'''
    
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
        user_id = context.get("user_id")
        send_progress = context.get("send_progress")
        
        self._current_user_id = user_id
        
        if send_progress:
            await send_progress(2, "🔍 Работа с базой знаний...")
        
        # Создаём инструменты с привязанным user_id
        tools = [
            create_graphrag_upload_tool(user_id=user_id),
            create_graphrag_query_tool(user_id=user_id)
        ]
        
        executor = self._get_executor(tools)
        result = await executor.ainvoke({"input": message})
        
        if send_progress:
            await send_progress(3, "✅ Готово")
        
        # Собираем информацию об использованных инструментах
        tools_used = []
        if hasattr(result, 'intermediate_steps'):
            for step in result.intermediate_steps:
                tools_used.append(step[0].tool)
        
        return AgentResult(
            output=result['output'],
            model=self.config.model_name,
            metadata={
                "agent_type": "rag",
                "tools_used": tools_used,
                "context": context,
                "user_id": user_id
            }
        )
    
    async def process_stream(self, message: str, context: Dict[str, Any]):
        """Streaming версия - сначала выполняет tools, потом стримит финальный ответ LLM"""
        from tools.graphrag_upload_tool import upload_summary_to_graph
        from tools.graphrag_query_tool import query_graph_knowledge
        
        user_id = context.get("user_id")
        send_progress = context.get("send_progress")
        chat_history = context.get("chat_history", [])
        
        self._current_user_id = user_id
        
        # Определяем намерение пользователя
        is_upload_request = any(keyword in message.lower() for keyword in [
            "загрузи", "сохрани", "добавь в базу", "в базу знаний", "upload", "сохранить"
        ])
        
        is_query_request = any(keyword in message.lower() for keyword in [
            "что такое", "расскажи про", "найди", "поиск", "вопрос", "объясни", "как"
        ]) or "?" in message
        
        tool_result = None
        tool_name = None
        
        # Выполняем соответствующий инструмент
        if is_upload_request:
            if send_progress:
                await send_progress(2, "📤 Загрузка в базу знаний...")
            
            tool_name = "graphrag_upload"
            
            # Ищем конспект в истории или в текущем сообщении
            summary_text = message
            
            # Проверяем последние сообщения на наличие конспекта
            for msg in reversed(chat_history[-10:]):
                if msg.role == "assistant" and len(msg.content) > 500:
                    summary_text = msg.content
                    break
            
            tool_result = await upload_summary_to_graph(user_id, summary_text)
            logger.info(f"GraphRAG upload result: {tool_result}")
            
        elif is_query_request:
            if send_progress:
                await send_progress(2, "🔍 Поиск в базе знаний...")
            
            tool_name = "graphrag_query"
            tool_result = await query_graph_knowledge(user_id, message)
            logger.info(f"GraphRAG query result: {tool_result[:100]}...")
        
        if send_progress:
            await send_progress(3, "💬 Формирование ответа...")
        
        # Генерируем финальный ответ со streaming
        system_prompt = self._get_system_prompt()
        
        messages = [SystemMessage(content=system_prompt)]
        
        # Добавляем историю чата
        for msg in chat_history:
            if msg.role == "user":
                messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                messages.append(AIMessage(content=msg.content))
        
        # Добавляем результат инструмента, если есть
        if tool_result:
            final_message = f"{message}\n\nРезультат работы инструмента {tool_name}:\n{tool_result}"
        else:
            final_message = message
        
        messages.append(HumanMessage(content=final_message))
        
        full_response = ""
        
        # Если был результат инструмента, сначала выводим его
        if tool_result:
            yield {"type": "token", "content": tool_result + "\n\n"}
            full_response += tool_result + "\n\n"
        
        try:
            async for chunk in self.llm.astream(messages):
                if hasattr(chunk, 'content') and chunk.content:
                    full_response += chunk.content
                    yield {"type": "token", "content": chunk.content}
        except Exception as e:
            logger.error(f"Ошибка при streaming от LLM: {e}")
            error_message = f"❌ Ошибка подключения к LLM (Ollama). Проверьте настройки OLLAMA_BASE_URL.\n\n"
            if tool_result:
                error_message += f"Результат инструмента:\n{tool_result}"
            yield {"type": "token", "content": error_message}
            full_response += error_message
        
        yield {"type": "complete", "content": full_response}
    
    async def get_available_models(self) -> List[str]:
        return [self.config.model_name]