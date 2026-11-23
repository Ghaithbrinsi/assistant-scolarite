import base64
import json
import re 
import sys
import time
import uuid
from pathlib import Path

import streamlit as st

RACINE = Path(__file__).resolve().parent
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "agent"))

from graphe import lancer, reprendre  # noqa: E402

# --- Doit être la première commande Streamlit, et appelée une seule fois ---
st.set_page_config(page_title="ISET Charguia - Assistant de scolarité",
                   page_icon="🎓", layout="wide",
                   initial_sidebar_state="expanded")

st.markdown("""
<style>
.block-container {padding-top: 2rem; max-width: 1000px;}
.banniere {
    display: flex; align-items: center; gap: 1.2rem;
    background: linear-gradient(135deg, #C0392B 0%, #8E2A20 100%);
    color: white; padding: 1.2rem 1.6rem; border-radius: 16px;
    margin-bottom: 1.2rem;
}
.banniere img {height: 64px; background: white; border-radius: 10px; padding: 4px;}
.banniere h1 {font-size: 1.7rem; margin: 0; padding: 0; color: white;}
.banniere p {margin: .3rem 0 0 0; opacity: .9; font-size: .9rem;}
.stButton > button {border-radius: 12px; transition: all .15s;}
.stButton > button:hover {border-color: #C0392B; color: #C0392B;}
</style>
""", unsafe_allow_html=True)


def afficher_banniere():
    img = ""
    if LOGO and Path(LOGO).exists():
        mime = "jpeg" if Path(LOGO).suffix.lower() in (".jpg", ".jpeg") else "png"
        b64 = base64.b64encode(Path(LOGO).read_bytes()).decode()
        img = f'<img src="data:image/{mime};base64,{b64}">'
    st.markdown(f"""
<div class="banniere">
  {img}
  <div>
    <h1>🎓 Assistant de scolarité</h1>
    <p>ISET Charguia • Règlement • Absences • Certificats • Examens • Rattrapages • Stages</p>
  </div>
</div>
""", unsafe_allow_html=True)

LOGO = next(iter((RACINE / "assets").glob("isetch.*")), None)
CHAT_DIR = RACINE / "saved_chats"
CHAT_DIR.mkdir(exist_ok=True)


# --- Conversations sauvegardées ---
def save_chat(chat_id, messages):
    titre = next((m["content"][:40] for m in messages if m["role"] == "user"),
                 "Nouvelle conversation")
    (CHAT_DIR / f"{chat_id}.json").write_text(
        json.dumps({"id": chat_id, "title": titre, "updated": time.time(),
                    "messages": messages}, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8")


def load_chat(chat_id):
    data = json.loads((CHAT_DIR / f"{chat_id}.json").read_text(encoding="utf-8"))
    return data["messages"]


def list_chats():
    chats = []
    for f in CHAT_DIR.glob("*.json"):
        try:
            chats.append(json.loads(f.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            pass
    return sorted(chats, key=lambda c: c.get("updated", 0), reverse=True)

def conversation_en_texte(messages):
    lignes = []
    for m in messages:
        qui = "Étudiant" if m["role"] == "user" else "Assistant"
        lignes.append(f"{qui} : {m['content']}\n")
    return "\n".join(lignes)

def formater(texte: str) -> str:
    # Garde les retours à la ligne, sauf dans les lignes de tableau (qui commencent par |)
    return "\n".join(l if l.lstrip().startswith("|") else l + "  "
                     for l in texte.split("\n"))


def separer_source(texte: str):
    """Sépare la dernière ligne « Source » du reste de la réponse."""
    lignes = texte.rstrip().split("\n")
    derniere = lignes[-1].strip()
    if derniere.startswith(("📖", "📅")) and "Source" in derniere:
        return "\n".join(lignes[:-1]).rstrip(), derniere
    return texte, None


def afficher_texte(texte: str, animer: bool = False):
    corps, source = separer_source(texte)
    if re.search(r"[\u0600-\u06ff]", corps):
        html = corps.replace("\n", "<br>")
        st.markdown(f'<div dir="rtl" style="text-align:right">{html}</div>',
                    unsafe_allow_html=True)
    elif animer:
        st.write_stream(flux(corps))
    else:
        st.markdown(formater(corps))
    if source:
        st.info(source)

def flux(texte: str):
    for mot in texte.split(" "):
        yield mot + " "
        time.sleep(0.03)

# --- État de session ---
ss = st.session_state
ss.setdefault("chat_id", uuid.uuid4().hex)
ss.setdefault("historique", [])
ss.setdefault("attente", None)

# Sauvegarde l'état de la conversation courante (avant d'afficher la liste)
if ss.historique:
    save_chat(ss.chat_id, ss.historique)

# --- Barre latérale ---
with st.sidebar:
    if LOGO:
        st.image(str(LOGO), use_container_width=True)
    st.title("🎓 Scolarité")
    if st.button("＋ Nouvelle conversation", use_container_width=True):
        ss.chat_id = uuid.uuid4().hex
        ss.historique = []
        ss.attente = None
        st.rerun()

    st.divider()
    st.caption("Conversations sauvegardées")
    for chat in list_chats()[:30]:
        if st.button(chat["title"], key=f"chat_{chat['id']}", use_container_width=True):
            ss.chat_id = chat["id"]
            ss.historique = load_chat(chat["id"])
            ss.attente = None
            st.rerun()

    if ss.historique and st.button("🗑 Supprimer cette conversation", use_container_width=True):
        (CHAT_DIR / f"{ss.chat_id}.json").unlink(missing_ok=True)
        ss.chat_id = uuid.uuid4().hex
        ss.historique = []
        ss.attente = None
        st.rerun()
    if ss.historique:
        st.download_button("⬇ Télécharger la conversation",
                           data=conversation_en_texte(ss.historique),
                           file_name="conversation.txt", mime="text/plain",
                           use_container_width=True)
# --- Zone principale ---
afficher_banniere()


def afficher_trace(trace: list):
    with st.expander("🔍 Étapes suivies par l'agent"):
        for i, t in enumerate(trace, 1):
            etape = t.get("etape")
            if etape == "classification":
                st.markdown(f"**{i}. Classification** : intention `{t.get('intention')}`, "
                            f"module `{t.get('module')}`")
            elif etape == "appel_outil":
                valide = " ✅ validé par l'étudiant" if t.get("valide_par_humain") else ""
                st.markdown(f"**{i}. Outil MCP** `{t.get('outil')}`{valide}")
                st.code(str(t.get("args", "")), language="json")
                st.text(str(t.get("resultat", ""))[:600])
            elif etape == "accueil":
                st.markdown(f"**{i}. Salutation** : message d'accueil")
            elif etape == "refus_hors_sujet":
                st.markdown(f"**{i}. Question hors sujet** : refus")
            elif etape == "refus_humain":
                st.markdown(f"**{i}. Action `{t.get('outil')}` refusée par l'étudiant**")
            elif etape == "reponse_finale":
                st.markdown(f"**{i}. Réponse finale**")
            else:
                st.markdown(f"**{i}. {etape}**")


def traiter(bilan: dict):
    if bilan["statut"] == "validation":
        ss.attente = bilan
    else:
        ss.attente = None
        ss.historique.append({"role": "assistant", "content": bilan["reponse"],
                              "trace": bilan["trace"]})
        ss.animer = True


for i, m in enumerate(ss.historique):
    with st.chat_message(m["role"]):
        derniere = (i == len(ss.historique) - 1)
        arabe = re.search(r"[\u0600-\u06ff]", m["content"])
        tableau = "|" in m["content"]
        animer = (m["role"] == "assistant" and derniere and ss.get("animer")
                  and not arabe and not tableau)
        afficher_texte(m["content"], animer)
        if derniere:
            ss.animer = False
        if m.get("duree"):
            st.caption(f"⏱ répondu en {m['duree']} s")
        if m.get("trace"):
            afficher_trace(m["trace"])
        if m["role"] == "assistant":
            note = st.feedback("thumbs", key=f"fb_{ss.chat_id}_{i}")
            if note is not None:
                m["feedback"] = note

# --- Validation humaine d'une action sensible ---
if ss.attente:
    action = ss.attente["action"]
    try:
        args = json.loads(action["args"])
    except json.JSONDecodeError:
        args = {"arguments": action["args"]}
    with st.chat_message("assistant"):
        st.warning("Action sensible : l'agent veut préparer une demande administrative avec les "
                   "informations ci-dessous. Vérifiez-les avant de valider.")
        st.json(args)
        col1, col2 = st.columns(2)
        decision = None
        if col1.button("✅ Valider", use_container_width=True):
            decision = True
        if col2.button("❌ Annuler", use_container_width=True):
            decision = False
        if decision is not None:
            try:
                with st.spinner("Traitement…"):
                    traiter(reprendre(ss.attente["thread_id"], decision))
            except Exception as e:
                ss.attente = None
                st.error(f"Erreur : {e}")
            st.rerun()

EXEMPLES = [
    "Quel est le délai du certificat médical ?",
    "When is the networks exam?",
    "chnowa el délai mta3 certificat médical ?",
    "Rédige ma demande de rattrapage",
]
if not ss.historique and not ss.attente:
    st.write("Essayez par exemple :")
    cols = st.columns(2)
    for i, ex in enumerate(EXEMPLES):
        if cols[i % 2].button(ex, key=f"ex_{i}", use_container_width=True):
            ss.question_exemple = ex
            st.rerun()

question = st.chat_input("Posez votre question…", disabled=bool(ss.attente))
if not question:
    question = ss.pop("question_exemple", None)
if question:
    ss.historique.append({"role": "user", "content": question})
    t0 = time.time()
    try:
        with st.spinner("L'agent travaille… (le premier appel est plus long)"):
            traiter(lancer(question))
        if ss.historique and ss.historique[-1]["role"] == "assistant":
            ss.historique[-1]["duree"] = round(time.time() - t0, 1)
    except Exception as e:
        st.error(f"Erreur : {e}")
    st.rerun()