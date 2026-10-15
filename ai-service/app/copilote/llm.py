"""
LLM local optionnel via Ollama (aucune donnée ne quitte ta machine).

Le LLM ne calcule jamais rien : il reçoit les faits déjà calculés à partir du grand livre
et les reformule. Si Ollama n'est pas lancé, Maliya répond avec ses propres phrases.
"""
import json
import os

import httpx

OLLAMA_URL = os.getenv("OLLAMA_URL", "")
OLLAMA_MODELE = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")

SYSTEME = (
    "Tu es Maliya, l'assistante financière d'un entrepreneur marocain qui gère une agence, une société, "
    "des projets et ses finances perso. Tu le tutoies, tu es chaleureuse et directe, sans jargon. "
    "Règle absolue : tu n'inventes aucun chiffre. Tu utilises uniquement les faits fournis, "
    "en gardant les montants exactement tels qu'ils sont écrits. Si les faits ne permettent pas de répondre, "
    "dis-le simplement. Réponds en 2 à 5 phrases, dans la langue de la question "
    "(français, darija en lettres latines ou anglais)."
)


def disponible() -> bool:
    if not OLLAMA_URL:
        return False
    try:
        return httpx.get(f"{OLLAMA_URL}/api/tags", timeout=1.5).status_code == 200
    except httpx.HTTPError:
        return False


def reformuler(question: str, faits: dict, brouillon: str) -> str | None:
    if not OLLAMA_URL:
        return None
    try:
        r = httpx.post(f"{OLLAMA_URL}/api/chat", timeout=45, json={
            "model": OLLAMA_MODELE,
            "stream": False,
            "options": {"temperature": 0.3},
            "messages": [
                {"role": "system", "content": SYSTEME},
                {"role": "user", "content": (
                    f"Question : {question}\n\nFaits calculés (JSON) :\n{json.dumps(faits, ensure_ascii=False, default=str)}\n\n"
                    f"Brouillon de réponse :\n{brouillon}\n\nRéécris le brouillon plus naturellement.")},
            ],
        })
        r.raise_for_status()
        texte = r.json().get("message", {}).get("content", "").strip()
        return texte or None
    except (httpx.HTTPError, ValueError, KeyError):
        return None
