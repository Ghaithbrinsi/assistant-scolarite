from rag.recherche import chercher

QUESTIONS = [
    "Quel est le délai pour le certificat médical ?",      # attendu : art. 4
    "Que se passe-t-il en cas d'hospitalisation ?",       # attendu : art. 6
    "Combien de temps dure le stage ?",                   # attendu : art. 11
    "Combien d'absences avant d'être exclu de l'examen ?",# attendu : art. 1
    "Quel est le montant de la bourse ?",                 # absent du règlement
    "Raconte-moi une blague",                             # hors sujet
]

for q in QUESTIONS:
    print("\nQ:", q)
    for r in chercher(q):
        print(f"   art.{r['article']:>2}  distance={r['distance']:.2f}")