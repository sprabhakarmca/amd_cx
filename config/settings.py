import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent


class Settings:
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "ollama")
    EMBEDDING_PROVIDER: str = os.getenv("EMBEDDING_PROVIDER", "ollama")

    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")

    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.2:1b")
    OLLAMA_EMBEDDING_MODEL: str = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")

    VLLM_BASE_URL: str = os.getenv("VLLM_BASE_URL", "http://localhost:8001")
    VLLM_MODEL: str = os.getenv("VLLM_MODEL", "Qwen/Qwen2.5-7B-Instruct")

    CHROMA_PERSIST_DIR: str = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    OPENAI_LLM_MODEL: str = "gpt-4o-mini"
    GOOGLE_LLM_MODEL: str = "gemini-2.0-flash"

    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    GOOGLE_EMBEDDING_MODEL: str = "text-embedding-004"

    CATEGORIES_FILE: str = str(BASE_DIR / "categories.json")

    @classmethod
    def validate(cls):
        if cls.LLM_PROVIDER == "google":
            if not cls.GOOGLE_API_KEY:
                raise ValueError("GOOGLE_API_KEY is required. Please set it in .env file")

        if cls.LLM_PROVIDER == "openai":
            if not cls.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY is required. Please set it in .env file")

        if cls.EMBEDDING_PROVIDER == "openai":
            if not cls.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY is required for OpenAI embeddings. Please set it in .env file")

        if cls.EMBEDDING_PROVIDER == "google":
            if not cls.GOOGLE_API_KEY:
                raise ValueError("GOOGLE_API_KEY is required for Google embeddings. Please set it in .env file")

        if cls.LLM_PROVIDER == "vllm":
            import requests
            try:
                response = requests.get(f"{cls.VLLM_BASE_URL}/v1/models", timeout=10)
                if response.status_code != 200:
                    raise ValueError("vLLM server is not responding correctly. Please ensure vLLM is running.")
            except requests.exceptions.ConnectionError:
                raise ValueError(f"Cannot connect to vLLM at {cls.VLLM_BASE_URL}. Run: vllm serve {cls.VLLM_MODEL}")
            except requests.exceptions.Timeout:
                raise ValueError("vLLM connection timed out.")

        if cls.LLM_PROVIDER == "ollama" or cls.EMBEDDING_PROVIDER == "ollama":
            import requests
            try:
                response = requests.get(f"{cls.OLLAMA_BASE_URL}/api/tags", timeout=5)
                if response.status_code != 200:
                    raise ValueError("Ollama server is not responding correctly. Please ensure Ollama is running.")
                
                models = response.json().get("models", [])
                model_names = [m.get("name", "").split(":")[0] for m in models]
                
                if cls.LLM_PROVIDER == "ollama":
                    llama_model = cls.OLLAMA_MODEL.split(":")[0]
                    if llama_model not in model_names:
                        raise ValueError(f"Ollama model '{cls.OLLAMA_MODEL}' not found. Please run: ollama pull {cls.OLLAMA_MODEL}")
                
                if cls.EMBEDDING_PROVIDER == "ollama":
                    embed_model = cls.OLLAMA_EMBEDDING_MODEL.split(":")[0]
                    if embed_model not in model_names:
                        raise ValueError(f"Ollama embedding model '{cls.OLLAMA_EMBEDDING_MODEL}' not found. Please run: ollama pull {cls.OLLAMA_EMBEDDING_MODEL}")
                        
            except requests.exceptions.ConnectionError:
                raise ValueError("Cannot connect to Ollama. Please ensure Ollama server is running with: ollama serve")
            except requests.exceptions.Timeout:
                raise ValueError("Ollama connection timed out. Please ensure Ollama server is running.")


settings = Settings()