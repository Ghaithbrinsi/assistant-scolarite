# 🎓 Assistant de scolarité – agent IA (ISET Charguia)

Projet « IA agentique » (cours *Introduction au machine learning*, RSI3, 2026-2027).

L'agent répond aux questions des étudiants sur **les absences, les rattrapages et les stages**, uniquement à partir de deux documents **fictifs** : le règlement des études et le calendrier des examens (session de janvier 2027).

> ⚠️ Tous les documents et exemples sont fictifs. Aucune donnée personnelle réelle n'est présente dans ce dépôt (les tests utilisent des noms comme « Test Etudiant »).

## Fonctionnalités

- Répond aux questions sur le règlement **en citant l'article utilisé**.
- Donne les dates, heures et salles d'examen et de rattrapage.
- Calcule la date limite du certificat médical (jours ouvrables, hospitalisation).
- Rédige un **brouillon** de demande de rattrapage, **jamais envoyé** et **validé par l'étudiant** avant génération.
- Refuse les questions hors sujet, répond « je ne sais pas » quand l'information n'est pas dans les documents, résiste aux tentatives de manipulation du prompt.
- Outils regroupés dans un **serveur MCP**.
- Interface web **Streamlit** qui affiche les étapes suivies par l'agent.

## Architecture

```
Streamlit (app.py)
   └── Graphe LangGraph (agent/graphe.py)
          ├── Classifier (hors sujet / règlement / calendrier / demande)
          ├── LLM  ──────────── Groq (API gratuite) ou Ollama (local, secours)
          └── Client MCP (agent/mcp_client.py)
                  ══ stdio ══► Serveur MCP (mcp_server/server.py)
                                  ├── rechercher_reglement  (ChromaDB + bge-m3)
                                  ├── get_calendrier
                                  ├── calculer_delai
                                  └── generer_demande
```

**Qui fait quoi :**

| Acteur | Où dans le code |
|---|---|
| Le **modèle décide** (réponse ou appel d'outil) | `noeud_llm` dans `agent/graphe.py` |
| Le **programme agit** (exécute l'outil via MCP) | `noeud_outils` et `executer_outil` |
| L'**étudiant valide** les actions sensibles | `interrupt(...)` dans `noeud_outils`, boutons dans `app.py` |

**Choix de conception :**

- Le règlement est découpé **par article** (un chunk = un article) pour pouvoir citer le bon numéro.
- Les dates et les délais sont **calculés par le code**, jamais par le modèle.
- Le brouillon de demande est renvoyé **tel quel** par l'outil : le modèle ne le réécrit pas.

## Installation

Prérequis : Python 3.11, [Ollama](https://ollama.com) (pour les embeddings), Git.

```bash
git clone https://github.com/Ghaithbrinsi/assistant-scolarite.git
cd assistant-scolarite

python -m venv .venv
# Windows PowerShell : .\.venv\Scripts\Activate.ps1
# Linux / macOS      : source .venv/bin/activate

python -m pip install -r requirements.txt
ollama pull bge-m3
```

> Le projet utilise `mcp<2` (le SDK MCP 2.x a renommé `FastMCP`).

## Configuration

Copiez le fichier d'exemple, puis remplissez-le :

```bash
cp .env.example .env        # Windows : copy .env.example .env
```

Le fichier `.env` est **ignoré par Git** : aucune clé d'API n'est dans le code.

**Mode API gratuite (Groq)** : créez une clé sur [console.groq.com](https://console.groq.com), puis :

```
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_API_KEY=votre_cle
LLM_MODEL=openai/gpt-oss-20b
OLLAMA_BASE_URL=http://localhost:11434/v1
MODEL_EMBED=bge-m3
```

**Mode local de secours (Ollama)** : en cas de panne ou de quota épuisé :

```
LLM_BASE_URL=http://localhost:11434/v1
LLM_API_KEY=ollama
LLM_MODEL=qwen3:4b
```
(après `ollama pull qwen3:4b`).

> Les quotas des offres gratuites changent : vérifiez-les sur la console Groq.

## Lancement

1. Indexer le règlement (une seule fois, ou après modification du PDF) :
   ```bash
   python -m rag.indexer
   ```
   Doit afficher `15 articles trouvés`.

2. Lancer l'interface :
   ```bash
   python -m streamlit run app.py
   ```

3. Ou tester en ligne de commande :
   ```bash
   python agent/graphe.py "J'étais malade le jour de l'examen de bases de données, que dois-je faire ?"
   ```

**Exemples de questions :**

| Question | Comportement attendu |
|---|---|
| « Quelle est la durée minimale du stage ? » | 8 semaines minimum, article 11 |
| « J'étais malade le jour de l'examen de bases de données… » | Délai du certificat, conditions, date du rattrapage |
| « Je m'appelle Test Etudiant, numéro 0000, rédige ma demande de rattrapage pour bases de données » | Demande de validation, puis brouillon |
| « Quel est le montant de la bourse ? » | « Je ne sais pas… » |
| « Raconte-moi une blague » | Refus (hors sujet) |

## Tests et évaluation

Le jeu de **40 questions** (`tests/questions.json`) est réparti entre : factuelles (18), hors sujet (6), informations absentes (6), pièges (5) et manipulations (5).

```bash
python tests/run_eval.py                     # évaluation complète du modèle configuré
python tests/run_eval.py --ids 13,25,31      # questions précises
python tests/run_eval.py --pas 5             # test rapide (1 question sur 5)
python tests/echecs.py                       # affiche les échecs en détail
```

Le script mesure le taux de réussite par catégorie, le temps de réponse, les dates inventées et les erreurs d'outils. Les résultats détaillés sont enregistrés dans `tests/resultats_<modèle>.json`.

Pour comparer un autre modèle sans modifier `.env` (PowerShell) :

```powershell
$env:LLM_MODEL="openai/gpt-oss-120b"
python tests/run_eval.py --nom gpt-oss-120b
Remove-Item Env:LLM_MODEL
```

### Résultats

| Modèle | Réussite globale | Temps moyen | Dates inventées |
|---|---|---|---|
| `openai/gpt-oss-20b` | _à compléter_ | _à compléter_ | _à compléter_ |
| `openai/gpt-oss-120b` | _à compléter_ | _à compléter_ | _à compléter_ |
| `qwen3:4b` (local, sous-ensemble) | _à compléter_ | _à compléter_ | _à compléter_ |

## Structure du dépôt

```
assistant-scolarite/
├── app.py                  # Interface Streamlit
├── agent/
│   ├── graphe.py           # Graphe LangGraph (classifier, LLM, outils, validation humaine)
│   ├── boucle.py           # Boucle d'agent manuelle, exécution des outils, validation en ligne de commande
│   ├── classifier.py       # Classification de l'intention
│   ├── prompts.py          # Prompt système
│   ├── llm.py              # Client LLM (Groq ou Ollama, selon .env)
│   ├── mcp_client.py       # Client MCP
│   └── outils.py           # Logique des outils (calendrier, délai, demande)
├── mcp_server/
│   └── server.py           # Serveur MCP (4 outils)
├── rag/
│   ├── indexer.py          # Indexation du règlement dans ChromaDB (par article)
│   ├── recherche.py        # Recherche sémantique
│   └── embeddings.py       # Embeddings bge-m3 via Ollama
├── data/                   # Règlement des études (PDF fictif)
├── tests/                  # Jeu de 40 questions et scripts d'évaluation
├── .env.example            # Variables d'environnement (sans clé)
└── requirements.txt
```

## Sécurité

- Aucune clé d'API dans le code : variables d'environnement et fichier `.env` ignoré par Git.
- Action sensible (`generer_demande`) soumise à la **validation de l'étudiant** ; en cas de refus, rien n'est généré.
- Le brouillon n'est jamais envoyé automatiquement.
- Les questions hors sujet sont bloquées par le classifier avant d'appeler le modèle principal.
- Le modèle ne peut citer que des articles et des dates fournis par ses outils.

## Limites connues

- Les jours ouvrables sont comptés du lundi au vendredi : **les jours fériés ne sont pas gérés**.
- Les quotas gratuits de l'API (tokens par jour) limitent le nombre d'évaluations possibles par jour.
- Le modèle local de secours est **lent** sur un PC avec 8 Go de RAM.
- La distinction entre « hors sujet » (refus) et « information absente » (« je ne sais pas ») repose sur un petit classifieur à base de LLM et peut se tromper sur certaines questions administratives.
- Le modèle peut parfois ne pas citer l'article attendu même quand le contenu de la réponse est correct.
- Fonctionnalités bonus non implémentées : réponses en arabe, mémoire de conversation, deux agents spécialisés, envoi de la demande par e-mail.

## Auteur

Ghaith Brinsi : RSI3, ISET Charguia, 2026-2027.
