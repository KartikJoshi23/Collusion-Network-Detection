from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    openai_api_key: str = ""
    openai_model_name: str = "gpt-5.4"

    qdrant_url: str = "http://qdrant:6333"
    qdrant_collection: str = "technova_docs"

    redis_url: str = "redis://redis:6379"

    langfuse_host: str | None = None
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None

    duckdb_path: str = "/data/db/technova.duckdb"
    structured_data_dir: str = "/data/structured"
    unstructured_data_dir: str = "/data/unstructured"
    schema_yaml_path: str = "/app/app/data/schema.yaml"

    embedding_model: str = "nomic-ai/nomic-embed-text-v1.5"
    reranker_model: str = "BAAI/bge-reranker-base"
    embedding_dim: int = 768

    retrieve_top_k_dense: int = 20
    retrieve_top_k_bm25: int = 20
    rerank_top_k: int = 5
    rrf_k: int = 60


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
