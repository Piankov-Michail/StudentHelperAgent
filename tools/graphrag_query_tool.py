"""
GraphRAG Query Tool - запросы к графу знаний с фильтрацией по user_id
"""
import os
import logging
from typing import Optional
from langchain_core.tools import tool
from llama_index.core import PropertyGraphIndex, Settings
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.graph_stores.neo4j import Neo4jPropertyGraphStore
from llama_index.llms.openai import OpenAI
from tools.nvidia_embeddings import NVIDIAEmbedding

logger = logging.getLogger(__name__)

# Глобальный индекс для переиспользования
_graph_index: Optional[PropertyGraphIndex] = None


def get_graph_index() -> PropertyGraphIndex:
    """Получить или создать PropertyGraphIndex для работы с Neo4j"""
    global _graph_index
    
    if _graph_index is None:
        # Настройки подключения к Neo4j
        neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        neo4j_password = os.getenv("NEO4J_PASSWORD", "your_neo4j_password_here")
        
        # Создаем graph store
        graph_store = Neo4jPropertyGraphStore(
            username=neo4j_user,
            password=neo4j_password,
            url=neo4j_uri,
            database="neo4j"
        )
        
        # Настраиваем LLM (OpenAI-совместимый API)
        ollama_base_url = os.getenv("OLLAMA_BASE_URL", "https://ollama.com")
        ollama_api_key = os.getenv("OLLAMA_API_KEY", "ollama")
        
        # Ollama Cloud использует OpenAI-совместимый API
        llm = OpenAI(
            model=os.getenv("DEFAULT_MODEL", "gpt-oss:20b-cloud"),
            api_base=f"{ollama_base_url}/v1",
            api_key=ollama_api_key,
            temperature=0.1,
            timeout=120.0
        )
        
        # Настраиваем embeddings
        # Пробуем использовать NVIDIA, если не работает - fallback на OpenAI
        nvidia_api_key = os.getenv("NVIDIA_API_KEY", "")
        
        if nvidia_api_key:
            try:
                embed_model = NVIDIAEmbedding(
                    api_key=nvidia_api_key,
                    model="nvidia/llama-3.2-nemoretriever-300m-embed-v1"
                )
                logger.info("Используем NVIDIA embeddings")
            except Exception as e:
                logger.warning(f"NVIDIA embeddings недоступны: {e}, используем OpenAI")
                from llama_index.embeddings.openai import OpenAIEmbedding
                embed_model = OpenAIEmbedding(
                    api_key=ollama_api_key,
                    api_base=f"{ollama_base_url}/v1",
                    model="text-embedding-3-small"
                )
        else:
            logger.info("NVIDIA_API_KEY не установлен, используем OpenAI embeddings")
            from llama_index.embeddings.openai import OpenAIEmbedding
            embed_model = OpenAIEmbedding(
                api_key=ollama_api_key,
                api_base=f"{ollama_base_url}/v1",
                model="text-embedding-3-small"
            )
        
        Settings.llm = llm
        Settings.embed_model = embed_model
        Settings.chunk_size = 512
        Settings.chunk_overlap = 50
        
        # Создаем индекс из существующего графа
        _graph_index = PropertyGraphIndex.from_existing(
            property_graph_store=graph_store,
            show_progress=True
        )
        
        logger.info(f"PropertyGraphIndex загружен из Neo4j: {neo4j_uri} с NVIDIA embeddings")
    
    return _graph_index


async def query_graph_knowledge(user_id: int, query_text: str) -> str:
    """
    Выполняет запрос к графу знаний с фильтрацией по user_id
    
    Args:
        user_id: ID пользователя
        query_text: Текст запроса
        
    Returns:
        Ответ на основе графа знаний пользователя
    """
    try:
        logger.info(f"Начало запроса к графу для user_id={user_id}, запрос: {query_text[:100]}...")
        
        if not query_text or len(query_text.strip()) < 3:
            logger.warning("Запрос слишком короткий")
            return "❌ Ошибка: Запрос слишком короткий."
        
        # Получаем индекс
        logger.info("Получение PropertyGraphIndex...")
        index = get_graph_index()
        
        # Создаем query engine с фильтрацией по user_id
        # Используем metadata фильтр для поиска только по документам пользователя
        from llama_index.core.vector_stores import MetadataFilters, ExactMatchFilter
        
        logger.info(f"Создание фильтра по user_id={user_id}...")
        filters = MetadataFilters(
            filters=[
                ExactMatchFilter(key="user_id", value=str(user_id))
            ]
        )
        
        # Создаем retriever с фильтрами
        logger.info("Создание retriever с фильтрами...")
        retriever = index.as_retriever(
            similarity_top_k=5,
            filters=filters
        )
        
        # Создаем query engine
        logger.info("Создание query engine...")
        query_engine = RetrieverQueryEngine.from_args(
            retriever=retriever,
            response_mode="tree_summarize"
        )
        
        # Выполняем запрос
        logger.info("Выполнение запроса к графу...")
        response = await query_engine.aquery(query_text)
        
        if not response or not response.response:
            logger.warning("Информация не найдена в графе")
            return "К сожалению, я не нашел информации по вашему запросу в базе знаний. Возможно, вы еще не загружали конспекты по этой теме."
        
        logger.info(f"✅ Запрос к графу выполнен успешно для user_id={user_id}")
        
        return response.response
        
    except Exception as e:
        logger.error(f"❌ Ошибка при запросе к графу: {e}", exc_info=True)
        return f"❌ Ошибка при поиске в базе знаний: {str(e)}"


def create_graphrag_query_tool(user_id: int):
    """Фабрика для создания tool с привязанным user_id"""
    
    @tool
    async def graphrag_query(query_text: str) -> str:
        """
        Ищет информацию в базе знаний пользователя (граф конспектов).
        Используй этот инструмент, когда пользователь задает вопрос по ранее загруженным конспектам.
        
        Args:
            query_text: Вопрос или запрос для поиска в базе знаний
            
        Returns:
            Ответ на основе найденной информации в графе
        """
        return await query_graph_knowledge(user_id, query_text)
    
    return graphrag_query
