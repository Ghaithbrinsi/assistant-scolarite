"""Usage : python tests/fusionner.py sortie.json entree1.json entree2.json ..."""
import json
import sys
import time

sortie, entrees = sys.argv[1], sys.argv[2:]
if not entrees:
    sys.exit("Usage : python tests/fusionner.py sortie.json entree1.json entree2.json")

resultats, modele, valid = [], None, None
for chemin in entrees:
    d = json.load(open(chemin, encoding="utf-8"))
    if d.get("interrompu"):
        sys.exit(f"{chemin} est INTERROMPU : relancez les questions manquantes avant de fusionner.")
    modele = modele or d["modele"]
    if d["modele"] != modele:
        sys.exit("Les fichiers ne viennent pas du même modèle.")
    for r in d["resultats"]:
        resultats = [x for x in resultats if x["id"] != r["id"]] + [r]
    valid = d["resume"].get("validation_humaine_refus_ok", valid)

resultats.sort(key=lambda r: r["id"])
n = len(resultats)
cats = {}
for r in resultats:
    cats.setdefault(r["categorie"], []).append(r["ok"])
resume = {
    "total": n,
    "reussis": sum(r["ok"] for r in resultats),
    "taux": round(100 * sum(r["ok"] for r in resultats) / n, 1),
    "par_categorie": {c: {"reussis": sum(v), "total": len(v)} for c, v in cats.items()},
    "temps_moyen_s": round(sum(r["temps"] for r in resultats) / n, 1),
    "questions_avec_date_inventee": sum(1 for r in resultats if r["dates_inventees"]),
    "erreurs_outils": sum(r["erreurs_outils"] for r in resultats),
    "erreurs_execution": sum(1 for r in resultats if r["erreur_execution"]),
    "validation_humaine_refus_ok": valid,
}
json.dump({"modele": modele, "date": time.strftime("%Y-%m-%d %H:%M"), "interrompu": False,
           "resume": resume, "resultats": resultats},
          open(sortie, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"{sortie} : {resume['reussis']}/{n} ({resume['taux']} %)")