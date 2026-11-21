import re
from pathlib import Path

import chromadb
import pypdf

from rag.embeddings import embed

RACINE = Path(__file__).resolve().parent.parent
PDF = next((RACINE / "data").glob("Reglement*.pdf"))
DB = RACINE / "chroma_db"


def extraire_articles(chemin) -> list[dict]:
    lignes = []
    for page in pypdf.PdfReader(chemin).pages:
        lignes += (page.extract_text() or "").splitlines()

    articles, chapitre, courant = [], "", None
    for ligne in lignes:
        l = ligne.strip()
        if not l or "(document fictif) Page" in l:
            continue                       # en-tête de page
        if l.startswith("Calendrier des examens"):
            break                          # le calendrier n'est pas indexé
        if l.startswith("Chapitre"):
            chapitre, courant = l, None
            continue
        m = re.match(r"Article (\d+)\.", l)
        if m:
            courant = {"numero": int(m.group(1)), "chapitre": chapitre, "texte": l}
            articles.append(courant)
        elif courant:
            courant["texte"] += " " + l    # suite de l'article sur la ligne suivante
    return articles


def indexer():
    articles = extraire_articles(PDF)
    print(f"{len(articles)} articles trouvés (attendu : 15)")

    client = chromadb.PersistentClient(path=str(DB))
    try:
        client.delete_collection("reglement")
    except Exception:
        pass
    col = client.create_collection("reglement", metadata={"hnsw:space": "cosine"})

    docs = [f"{a['chapitre']} | {a['texte']}" for a in articles]
    col.add(
        ids=[f"art{a['numero']}" for a in articles],
        documents=docs,
        embeddings=embed(docs),
        metadatas=[{"numero": a["numero"], "chapitre": a["chapitre"]} for a in articles],
    )
    print("Indexation terminée dans", DB)


if __name__ == "__main__":
    indexer()