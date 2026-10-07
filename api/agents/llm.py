from langchain_ollama import ChatOllama

from api.config import settings


# swap provider/model here only -- every agent calls this, not a client directly
def get_llm(temperature: float = 0.0) -> ChatOllama:
    return ChatOllama(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        temperature=temperature,
        num_ctx=settings.ollama_num_ctx,
    )
