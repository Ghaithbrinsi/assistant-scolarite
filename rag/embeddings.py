import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
_client = OpenAI(base_url=os.getenv("OLLAMA_BASE_URL"), api_key="ollama")
MODEL_EMBED = os.getenv("MODEL_EMBED", "bge-m3")


def embed(textes: list[str]) -> list[list[float]]:
    """Transforme des textes en vecteurs via Ollama (bge-m3)."""
    rep = _client.embeddings.create(model=MODEL_EMBED, input=textes)
    return [d.embedding for d in rep.data]