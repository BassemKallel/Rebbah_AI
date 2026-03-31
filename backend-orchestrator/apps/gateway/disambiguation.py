"""
disambiguation.py — Résolution d'ambiguïté produit

Quand plusieurs produits correspondent à la recherche de l'utilisateur,
ce module gère la sélection via 3 stratégies :
1. Sélection par numéro ("1", "2", ...)
2. Correspondance par nom de produit
3. Correspondance par couleur de variation
"""
import logging
from .response_templates import DISAMBIGUATION_TEMPLATE

logger = logging.getLogger(__name__)


def resolve(text: str, candidates: list) -> dict | None:
    """
    Tente de résoudre l'ambiguïté entre plusieurs produits candidats.

    Args:
        text: Texte de l'utilisateur (ex: "1", "le pull bleu", "rouge")
        candidates: Liste de produits candidats [{name, base_price, variations}, ...]

    Returns:
        Le produit résolu ou None si aucun match.
    """
    if not text or not candidates:
        return None

    text_lower = text.lower()

    # Stratégie 1 : Sélection par numéro
    for i, c in enumerate(candidates):
        if str(i + 1) in text:
            logger.debug(f"[DISAMBIGUATION] Résolu par numéro: #{i+1} → {c['name']}")
            return c

    # Stratégie 2 : Correspondance par nom
    for c in candidates:
        if c["name"].lower() in text_lower or text_lower in c["name"].lower():
            logger.debug(f"[DISAMBIGUATION] Résolu par nom: {c['name']}")
            return c

    # Stratégie 3 : Correspondance par couleur de variation
    for c in candidates:
        for v in c.get("variations", []):
            if v.get("color", "").lower() in text_lower:
                logger.debug(f"[DISAMBIGUATION] Résolu par couleur: {v['color']} → {c['name']}")
                return c

    return None


def build_response(candidates: list, lang: str = "FR") -> str:
    """
    Construit le message bot demandant à l'utilisateur de choisir parmi les candidats.

    Args:
        candidates: Liste de produits [{name, base_price}, ...]
        lang: Langue du template (FR, AR, EN)

    Returns:
        Le texte formaté du message de désambiguïsation.
    """
    template = DISAMBIGUATION_TEMPLATE.get(lang, DISAMBIGUATION_TEMPLATE.get("FR", ""))
    items_list = "\n".join(
        f"{i+1}. {c['name']} ({c['base_price']} TND)"
        for i, c in enumerate(candidates)
    )
    return template.replace("{count}", str(len(candidates))).replace("{list}", items_list)
