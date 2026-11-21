import os
import time

from dotenv import load_dotenv
load_dotenv()

print("LLM_BASE_URL =", os.getenv("LLM_BASE_URL"))
print("LLM_MODEL    =", os.getenv("LLM_MODEL"))
print("Clé présente =", bool(os.getenv("LLM_API_KEY")))

# Test 1 : le modèle seul (Groq)
from llm import client, MODEL
t = time.time()
try:
    r = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": "Dis bonjour en une phrase."}],
        max_tokens=200,
    )
    print(f"[1] LLM OK en {time.time() - t:.1f}s :", r.choices[0].message.content)
except Exception as e:
    print(f"[1] LLM ERREUR après {time.time() - t:.1f}s :", e)

# Test 2 : embeddings (Ollama local, bge-m3)
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rag.embeddings import embed
t = time.time()
try:
    v = embed(["test"])
    print(f"[2] Embedding OK en {time.time() - t:.1f}s (dimension {len(v[0])})")
except Exception as e:
    print(f"[2] Embedding ERREUR après {time.time() - t:.1f}s :", e)

# Test 3 : recherche dans le règlement
from rag.recherche import chercher
t = time.time()
try:
    res = chercher("durée du stage")
    print(f"[3] Recherche OK en {time.time() - t:.1f}s : articles", [r["article"] for r in res])
except Exception as e:
    print(f"[3] Recherche ERREUR après {time.time() - t:.1f}s :", e)