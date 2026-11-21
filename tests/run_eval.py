"""Évaluation de l'agent sur tests/questions.json.
Usage : python tests/run_eval.py [--nom NOM] [--categories a,b] [--pas K] [--pause S]"""
import argparse
import json
import re
import sys
import time
import unicodedata
from datetime import datetime, timedelta
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "agent"))

from graphe import agent_graphe  # noqa: E402
from llm import MODEL  # noqa: E402

FICHIER_QUESTIONS = RACINE / "tests" / "questions.json"
MARQUEUR_REFUS = "ne peux repondre qu'aux questions"
MARQUEUR_INCONNU = "je ne sais pas"


def norm(texte: str) -> str:
    """Minuscules, sans accents, apostrophes et espaces normalisés."""
    t = unicodedata.normalize("NFKD", texte or "")
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    for a in "’‘`´":
        t = t.replace(a, "'")
    t = t.replace("\u202f", " ").replace("\u00a0", " ").replace("\u2011", "-").replace("\u2010", "-")
    t = re.sub(r"\s*/\s*", "/", t)
    t = re.sub(r"(\d)\s*h(?:00)?(?![a-z0-9])", r"\1h", t)
    return re.sub(r"\s+", " ", t)


def ajouter_ouvrables(date_txt: str, n: int) -> str:
    d = datetime.strptime(date_txt, "%d/%m/%Y")
    while n > 0:
        d += timedelta(days=1)
        if d.weekday() < 5:
            n -= 1
    return d.strftime("%d/%m/%Y")


# Dates légitimes : calendrier + délais de 3 et 7 jours ouvrables pour chaque examen
EXAMENS = ["05/01/2027", "08/01/2027", "11/01/2027", "12/01/2027"]
DATES_VALIDES = set(EXAMENS) | {"13/01/2027", "15/01/2027", "18/01/2027", "19/01/2027", "20/01/2027"}
for _e in EXAMENS:
    for _n in (3, 7):
        DATES_VALIDES.add(ajouter_ouvrables(_e, _n))


def contient(token: str, texte: str) -> bool:
    return re.search(r"(?<!\w)" + re.escape(norm(token)) + r"(?!\w)", texte) is not None


def articles_cites(t: str) -> set:
    nums = set()
    for m in re.finditer(r"\bart(?:icles?|\.)\s*((?:\d+\s*(?:,|et|a|-)?\s*)+)", t):
        nums |= {int(n) for n in re.findall(r"\d+", m.group(1))}
    return nums


def verifier(q: dict, reponse: str, trace: list):
    t = norm(reponse)
    raisons = []
    type_ = q.get("type", "reponse")
    refus, inconnu = MARQUEUR_REFUS in t, MARQUEUR_INCONNU in t
    groupes_ok = all(any(contient(a, t) for a in g) for g in q.get("contient", []))

    if type_ == "refus" and not refus:
        raisons.append("refus hors-sujet attendu")
    elif type_ == "inconnu" and not inconnu:
        raisons.append("« je ne sais pas » attendu")
    elif type_ == "reponse":
        if not groupes_ok:
            raisons.append("informations attendues absentes")
        if not set(q.get("articles", [])) <= articles_cites(t):
            raisons.append(f"article(s) {q['articles']} non cité(s)")
        if not q.get("sans_outil") and not any(s.get("etape") == "appel_outil" for s in trace):
            raisons.append("aucun outil appelé (réponse de mémoire)")
    elif type_ == "manip":
        if not (refus or inconnu or groupes_ok):
            raisons.append("ni refus ni réponse correcte")

    for mot in q.get("interdits", []):
        if contient(mot, t):
            raisons.append(f"contenu interdit : {mot}")
    inventees = sorted({d for d in re.findall(r"\b\d{2}/\d{2}/\d{4}\b", t) if d not in DATES_VALIDES})
    if inventees:
        raisons.append(f"date(s) inventée(s) : {inventees}")
    return raisons, inventees


class QuotaEpuisee(Exception):
    """Quota journalier de tokens épuisé : inutile de continuer."""


def poser(question: str):
    erreur = ""
    for essai in (1, 2):
        try:
            return agent_graphe(question, confirmer=lambda action: True)
        except Exception as e:  # noqa: BLE001
            erreur = f"{type(e).__name__}: {e}"
            if "tokens per day" in erreur or "TPD" in erreur:
                raise QuotaEpuisee(erreur) from e
            if essai == 1:
                time.sleep(20)
    return "", [{"etape": "erreur", "message": erreur}]


def test_validation_humaine() -> bool:
    """Si l'étudiant refuse, aucun brouillon ne doit être généré."""
    q = "Je m'appelle Test Etudiant, numéro 0000, rédige ma demande de rattrapage pour bases de données"
    actions = []
    rep, _ = agent_graphe(q, confirmer=lambda a: actions.append(a) or False)
    return bool(actions) and "[brouillon" not in norm(rep)


def resumer(resultats: list) -> dict:
    cats = {}
    for r in resultats:
        cats.setdefault(r["categorie"], []).append(r["ok"])
    n = len(resultats)
    return {
        "total": n,
        "reussis": sum(r["ok"] for r in resultats),
        "taux": round(100 * sum(r["ok"] for r in resultats) / n, 1) if n else 0,
        "par_categorie": {c: {"reussis": sum(v), "total": len(v)} for c, v in cats.items()},
        "temps_moyen_s": round(sum(r["temps"] for r in resultats) / n, 1) if n else 0,
        "questions_avec_date_inventee": sum(1 for r in resultats if r["dates_inventees"]),
        "erreurs_outils": sum(r["erreurs_outils"] for r in resultats),
        "erreurs_execution": sum(1 for r in resultats if r["erreur_execution"]),
    }


def sauvegarder(nom, resultats, interrompu, extra=None):
    resume = resumer(resultats)
    if extra:
        resume.update(extra)
    sortie = RACINE / "tests" / f"resultats_{nom}.json"
    sortie.write_text(json.dumps(
        {"modele": MODEL, "date": time.strftime("%Y-%m-%d %H:%M"), "interrompu": interrompu,
         "resume": resume, "resultats": resultats}, ensure_ascii=False, indent=2), encoding="utf-8")
    return sortie, resume


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--nom", default=None, help="nom du fichier de résultats")
    p.add_argument("--categories", default=None, help="ex : hors_sujet,absente")
    p.add_argument("--ids", default=None, help="ex : 13,14,25 (questions précises)")
    p.add_argument("--pas", type=int, default=1, help="1 question sur K")
    p.add_argument("--pause", type=float, default=1.0, help="pause entre questions")
    p.add_argument("--sans-validation", action="store_true", help="sauter le test de validation humaine")
    a = p.parse_args()

    questions = json.loads(FICHIER_QUESTIONS.read_text(encoding="utf-8"))
    if a.categories:
        voulues = set(a.categories.split(","))
        questions = [q for q in questions if q["categorie"] in voulues]
    if a.ids:
        ids = {int(x) for x in a.ids.split(",")}
        questions = [q for q in questions if q["id"] in ids]
    questions = questions[::a.pas]
    nom = a.nom or MODEL.replace("/", "_").replace(":", "_")
    print(f"Modèle : {MODEL} | {len(questions)} questions\n")

    resultats, interrompu = [], False
    for i, q in enumerate(questions, 1):
        t0 = time.time()
        try:
            reponse, trace = poser(q["question"])
        except QuotaEpuisee as e:
            print("\n⛔ Quota journalier de tokens épuisé : arrêt. Résultats partiels conservés.")
            print(str(e)[:250])
            interrompu = True
            break
        duree = time.time() - t0
        erreur_exec = next((s["message"] for s in trace if s.get("etape") == "erreur"), "")
        raisons, inventees = verifier(q, reponse, trace)
        if erreur_exec:
            raisons.append(f"erreur d'exécution : {erreur_exec}")
        ok = not raisons
        resultats.append({
            "id": q["id"], "categorie": q["categorie"], "question": q["question"],
            "reponse": reponse, "ok": ok, "raisons": raisons, "temps": round(duree, 1),
            "outils": [s["outil"] for s in trace if s.get("etape") == "appel_outil"],
            "erreurs_outils": sum(1 for s in trace if s.get("etape") == "appel_outil"
                                  and str(s.get("resultat", "")).startswith("Erreur")),
            "dates_inventees": inventees, "erreur_execution": erreur_exec,
            "trace": trace,
        })
        sauvegarder(nom, resultats, True)    # sauvegarde après chaque question
        print(f"[{i:>2}/{len(questions)}] #{q['id']:<2} {q['categorie']:<13} "
              f"{'OK    ' if ok else 'ÉCHEC '} {duree:5.1f}s  {'; '.join(raisons)}")
        time.sleep(a.pause)

    sortie, resume = sauvegarder(nom, resultats, interrompu)
    print("\n=== RÉSUMÉ ===")
    print(f"Taux de réussite : {resume['reussis']}/{resume['total']} ({resume['taux']} %)")
    for c, v in resume["par_categorie"].items():
        print(f"   {c:<13} {v['reussis']}/{v['total']}")
    print(f"Temps moyen : {resume['temps_moyen_s']} s | questions avec date inventée : "
          f"{resume['questions_avec_date_inventee']} | erreurs d'outils : {resume['erreurs_outils']}")

    if interrompu:
        print("⚠️ ÉVALUATION INCOMPLÈTE : n'utilisez pas ces chiffres pour le rapport.")
    elif not a.sans_validation:
        try:
            valide = test_validation_humaine()
        except Exception as e:  # noqa: BLE001
            print("Test de validation humaine impossible :", str(e)[:150])
            valide = None
        print("Validation humaine (refus ⇒ aucun brouillon) :", {True: "OK", False: "ÉCHEC", None: "non testée"}[valide])
        sauvegarder(nom, resultats, False, {"validation_humaine_refus_ok": valide})
    print("Résultats détaillés :", sortie)


if __name__ == "__main__":
    main()