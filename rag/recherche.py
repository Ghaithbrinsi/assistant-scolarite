from pathlib import Path

import chromadb

from rag.embeddings import embed

DB = Path(__file__).resolve().parent.parent / "chroma_db"
SEUIL = None   # à calibrer : distance max acceptée (voir plus bas)


def chercher(question: str, k: int = 3) -> list[dict]:
    col = chromadb.PersistentClient(path=str(DB)).get_collection("reglement")
    res = col.query(query_embeddings=embed([question]), n_results=k)
    return [
        {"article": m["numero"], "chapitre": m["chapitre"], "texte": d, "distance": dist}
        for d, m, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0])
    ]


def rechercher_reglement(question: str, k: int = 5) -> str:
    """Version pour le modèle : texte des articles les plus proches."""
    resultats = chercher(question, k)
    if SEUIL is not None:
        resultats = [r for r in resultats if r["distance"] <= SEUIL]
    if not resultats:
        return "Aucun article pertinent trouvé dans le règlement."
    resultats.sort(key=lambda r: r["article"])   # ordre des articles, plus lisible
    return "\n\n".join(f"[Article {r['article']}] {r['texte']}" for r in resultats)