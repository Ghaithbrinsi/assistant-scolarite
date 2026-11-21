"""Usage : python tests/comparer.py resultats_A.json resultats_B.json"""
import json
import sys


def charger(chemin):
    with open(chemin, encoding="utf-8") as f:
        return json.load(f)


a, b = charger(sys.argv[1]), charger(sys.argv[2])
ra, rb = a["resume"], b["resume"]

print(f"| Critère | {a['modele']} | {b['modele']} |")
print("|---|---|---|")
print(f"| Taux de réussite global | {ra['reussis']}/{ra['total']} ({ra['taux']} %) | "
      f"{rb['reussis']}/{rb['total']} ({rb['taux']} %) |")
for cat in ra["par_categorie"]:
    va = ra["par_categorie"][cat]
    vb = rb["par_categorie"].get(cat, {"reussis": 0, "total": 0})
    print(f"| {cat} | {va['reussis']}/{va['total']} | {vb['reussis']}/{vb['total']} |")
print(f"| Temps moyen par question | {ra['temps_moyen_s']} s | {rb['temps_moyen_s']} s |")
print(f"| Questions avec date inventée | {ra['questions_avec_date_inventee']} | {rb['questions_avec_date_inventee']} |")
print(f"| Erreurs d'outils | {ra['erreurs_outils']} | {rb['erreurs_outils']} |")
print(f"| Validation humaine respectée | {ra.get('validation_humaine_refus_ok')} | {rb.get('validation_humaine_refus_ok')} |")

ids_b = {r["id"]: r for r in b["resultats"]}
print("\nQuestions où les deux modèles diffèrent :")
for r in a["resultats"]:
    autre = ids_b.get(r["id"])
    if autre and autre["ok"] != r["ok"]:
        print(f"- #{r['id']} ({r['categorie']}) : {a['modele']} = {'OK' if r['ok'] else 'ÉCHEC'}, "
              f"{b['modele']} = {'OK' if autre['ok'] else 'ÉCHEC'} — {r['question']}")