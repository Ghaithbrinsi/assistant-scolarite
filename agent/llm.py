import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

MODEL = os.getenv("LLM_MODEL", os.getenv("MODEL_LOCAL"))

client = OpenAI(
    base_url=os.getenv("LLM_BASE_URL", os.getenv("OLLAMA_BASE_URL")),
    api_key=os.getenv("LLM_API_KEY", "ollama"),
    timeout=120,
    max_retries=1,
)