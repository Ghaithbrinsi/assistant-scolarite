import json
import sys

chemin = sys.argv[1] if len(sys.argv) > 1 else "tests/resultats_openai_gpt-oss-20b.json"
with open(chemin, encoding="utf-8") as f:
    data = json.load(f)

for r in data["resultats"]:
    if not r["ok"]:
        print(f"#{r['id']} [{r['categorie']}] {r['question']}")
        print("   Raisons :", r["raisons"])
        print("   Outils  :", r["outils"])
        print("   Réponse :", r["reponse"])
        print()