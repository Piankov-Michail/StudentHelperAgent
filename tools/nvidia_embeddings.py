"""
NVIDIA Embeddings для GraphRAG
Кастомная реализация для работы с NVIDIA NeMo Retriever
"""
import os
from typing import List, Any
from llama_index.core.embeddings import BaseEmbedding
from openai import OpenAI


class NVIDIAEmbedding(BaseEmbedding):
    """
    Кастомный embedding класс для NVIDIA NeMo Retriever
    Поддерживает разные input_type для passage (загрузка) и query (поиск)
    """
    
    _client: Any = None
    _model: str = "nvidia/llama-3.2-nemoretriever-300m-embed-v1"
    
    def __init__(
        self,
        api_key: str,
        model: str = "nvidia/llama-3.2-nemoretriever-300m-embed-v1",
        **kwargs
    ):
        super().__init__(**kwargs)
        self._client = OpenAI(
            api_key=api_key,
            base_url="https://integrate.api.nvidia.com/v1"
        )
        self._model = model
    
    def _get_query_embedding(self, query: str) -> List[float]:
        """Получить embedding для запроса (query)"""
        response = self._client.embeddings.create(
            input=[query],
            model=self._model,
            encoding_format="float",
            extra_body={"input_type": "query", "truncate": "NONE"}
        )
        return response.data[0].embedding
    
    def _get_text_embedding(self, text: str) -> List[float]:
        """Получить embedding для текста документа (passage)"""
        response = self._client.embeddings.create(
            input=[text],
            model=self._model,
            encoding_format="float",
            extra_body={"input_type": "passage", "truncate": "NONE"}
        )
        return response.data[0].embedding
    
    def _get_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Получить embeddings для нескольких текстов (batch)"""
        response = self._client.embeddings.create(
            input=texts,
            model=self._model,
            encoding_format="float",
            extra_body={"input_type": "passage", "truncate": "NONE"}
        )
        return [item.embedding for item in response.data]
    
    async def _aget_query_embedding(self, query: str) -> List[float]:
        """Async версия получения embedding для запроса"""
        return self._get_query_embedding(query)
    
    async def _aget_text_embedding(self, text: str) -> List[float]:
        """Async версия получения embedding для текста"""
        return self._get_text_embedding(text)
