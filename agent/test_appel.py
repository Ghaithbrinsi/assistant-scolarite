import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(base_url=os.getenv("OLLAMA_BASE_URL"), api_key="ollama")
MODEL = os.getenv("MODEL_LOCAL")

reponse = client.chat.completions.create(
    model=MODEL,
    messages=[{"role": "user", "content": "Explique en 2 phrases ce qu'est un agent IA. /no_think"}],
)
print(reponse.choices[0].message.content)