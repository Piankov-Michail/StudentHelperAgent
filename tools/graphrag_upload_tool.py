"""
GraphRAG Upload Tool - загрузка конспектов в граф знаний Neo4j
"""
import os
import logging
from typing import Optional
from langchain_core.tools import tool
from llama_index.core import Document, PropertyGraphIndex, Settings
from llama_index.core.indices.property_graph import SimpleLLMPathExtractor
from llama_index.graph_stores.neo4j import Neo4jPropertyGraphStore
from llama_index.llms.openai import OpenAI
from tools.nvidia_embeddings import NVIDIAEmbedding

logger = logging.getLogger(__name__)

# Глобальный индекс для переиспользования
_graph_index: Optional[PropertyGraphIndex] = None


def get_graph_index(user_id: int) -> PropertyGraphIndex:
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
        
        # Настраиваем LLM для извлечения сущностей (OpenAI-совместимый API)
        ollama_base_url = os.getenv("OLLAMA_BASE_URL", "https://ollama.com")
        ollama_api_key = os.getenv("OLLAMA_API_KEY", "ollama")
        
        # Ollama Cloud использует OpenAI-совместимый API
        llm = OpenAI(
            model=os.getenv("DEFAULT_MODEL", "gpt-oss:20b-cloud"),
            api_base=f"{ollama_base_url}/v1",
            api_key=ollama_api_key,
            temperature=0.1,
            timeout=180.0
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
        
        # Создаем индекс с экстрактором сущностей
        # Используем SchemaLLMPathExtractor с явной схемой для лучшего извлечения
        from llama_index.core.indices.property_graph import SchemaLLMPathExtractor
        
        # Определяем схему сущностей и связей для образовательного контента
        entities = ["PERSON", "TECHNOLOGY", "COMPANY", "CONCEPT", "DATE", "EVENT", "PRODUCT"]
        relations = ["CREATED_BY", "WORKS_FOR", "RELATED_TO", "HAPPENED_ON", "PART_OF", "USES", "IMPROVES"]
        
        kg_extractor = SchemaLLMPathExtractor(
            llm=llm,
            possible_entities=entities,
            possible_relations=relations,
            kg_validation_schema=None,
            strict=False,  # Не строгий режим для большей гибкости
            num_workers=1
        )
        
        logger.info(f"Создан SchemaLLMPathExtractor с entities={entities}, relations={relations}")
        
        _graph_index = PropertyGraphIndex(
            nodes=[],
            property_graph_store=graph_store,
            kg_extractors=[kg_extractor],
            show_progress=True
        )
        
        logger.info(f"PropertyGraphIndex создан для Neo4j: {neo4j_uri}")
    
    return _graph_index


async def upload_summary_to_graph(user_id: int, summary_text: str) -> str:
    """
    Загружает конспект в граф знаний с привязкой к user_id
    
    Args:
        user_id: ID пользователя
        summary_text: Текст конспекта для загрузки
        
    Returns:
        Сообщение о результате загрузки
    """
    try:
        logger.info(f"Начало загрузки конспекта для user_id={user_id}, длина текста={len(summary_text)}")
        
        if not summary_text or len(summary_text.strip()) < 50:
            logger.warning(f"Текст слишком короткий: {len(summary_text)} символов")
            return "❌ Ошибка: Текст конспекта слишком короткий для загрузки в базу знаний (минимум 50 символов)."
        
        # Получаем индекс
        logger.info("Получение PropertyGraphIndex...")
        index = get_graph_index(user_id)
        
        # Создаем документ с метаданными пользователя
        logger.info("Создание документа с метаданными...")
        document = Document(
            text=summary_text,
            metadata={
                "user_id": user_id,
                "doc_type": "lecture_summary",
                "source": "transcript_agent"
            }
        )
        
        # Добавляем документ в индекс (это запустит извлечение сущностей и связей)
        logger.info("Добавление документа в индекс (извлечение сущностей)...")
        # Используем синхронный метод, так как llama_index внутри вызывает asyncio.run()
        # что конфликтует с уже запущенным event loop
        import asyncio
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, index.insert, document)
        
        # Проверяем, сколько сущностей и связей было создано
        try:
            graph_store = index.property_graph_store
            # Подсчитываем узлы и связи для этого пользователя
            query_nodes = """
            MATCH (n {user_id: $user_id})
            RETURN count(n) as node_count
            """
            query_rels = """
            MATCH (n {user_id: $user_id})-[r]->(m)
            RETURN count(r) as rel_count
            """
            
            # Выполняем запросы через Neo4j драйвер
            with graph_store._driver.session(database=graph_store._database) as session:
                node_result = session.run(query_nodes, user_id=user_id)
                node_count = node_result.single()["node_count"] if node_result.peek() else 0
                
                rel_result = session.run(query_rels, user_id=user_id)
                rel_count = rel_result.single()["rel_count"] if rel_result.peek() else 0
            
            logger.info(f"✅ Конспект загружен: {node_count} узлов, {rel_count} связей для user_id={user_id}")
            
            if node_count == 0 or rel_count == 0:
                logger.warning(f"⚠️ Извлечено мало данных: узлов={node_count}, связей={rel_count}. Возможно, LLM не извлекает сущности корректно.")
                return f"⚠️ Конспект загружен в базу знаний, но извлечено мало сущностей ({node_count} узлов, {rel_count} связей). Возможно, требуется настройка LLM для извлечения сущностей."
            
            return f"✅ Конспект успешно загружен в базу знаний! Извлечено {node_count} узлов и {rel_count} связей. Теперь вы можете задавать вопросы по этому материалу."
        except Exception as count_error:
            logger.warning(f"Не удалось подсчитать узлы/связи: {count_error}")
            return f"✅ Конспект успешно загружен в базу знаний! Извлечены сущности и связи. Теперь вы можете задавать вопросы по этому материалу."
        
    except Exception as e:
        logger.error(f"❌ Ошибка при загрузке конспекта в граф: {e}", exc_info=True)
        return f"❌ Ошибка при загрузке в базу знаний: {str(e)}"


def create_graphrag_upload_tool(user_id: int):
    """Фабрика для создания tool с привязанным user_id"""
    
    @tool
    async def graphrag_upload(summary_text: str) -> str:
        """
        Загружает конспект лекции в базу знаний (граф).
        Используй этот инструмент, когда пользователь просит сохранить или загрузить конспект в базу знаний.
        
        Args:
            summary_text: Полный текст конспекта для загрузки
            
        Returns:
            Сообщение о результате загрузки
        """
        return await upload_summary_to_graph(user_id, summary_text)
    
    return graphrag_upload
