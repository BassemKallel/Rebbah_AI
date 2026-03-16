"""
stock_checker.py — Vérification de stock & création de pré-commande

Responsabilités :
- Vérifier la disponibilité d'un produit (couleur + taille)
- Créer une pré-commande et retourner le message de confirmation
"""
import logging
from apps.gateway.response_templates import (
    ORDER_CONFIRMED_TEMPLATE,
    ORDER_CONFIRMED_NO_REF_TEMPLATE,
)

logger = logging.getLogger(__name__)


def check_stock(matched_product: dict, color: str, size: str) -> tuple[bool, str]:
    """
    Vérifie si un produit est en stock pour une couleur/taille donnée.

    Returns:
        (is_in_stock, available_alternatives_str)
    """
    if not matched_product:
        return True, ""

    def _matches(v: dict) -> bool:
        color_match = (not color) or (v.get("color", "").lower() == color.lower())
        size_match = (not size) or (v.get("size", "").lower() == size.lower())
        return color_match and size_match

    if not color and not size:
        total_stock = sum(
            v.get("stock_quantity", 0)
            for v in matched_product.get("variations", [])
        )
        return (total_stock > 0), ""

    valid = next(
        (v for v in matched_product.get("variations", [])
         if _matches(v) and v.get("stock_quantity", 0) > 0),
        None,
    )
    if valid:
        return True, ""

    avail = ", ".join(list(set(
        f"{v['color']} / {v['size']}"
        for v in matched_product.get("variations", [])
        if v.get("stock_quantity", 0) > 0
    )))
    return False, avail


def create_preorder_and_confirm(
    lead, matched_product, vision_variation_id,
    chosen_color, chosen_size, context, display_name, lang="FR"
) -> str:
    """
    Crée une pré-commande dans le Lead et retourne le message de confirmation.

    Returns:
        Le texte de confirmation de commande (avec ou sans référence).
    """
    pre_order_ref = None
    try:
        lead.create_pending_order(
            shop_id=context.get("shop_id", ""),
            product_id=matched_product["id"] if matched_product else None,
            variation_id=vision_variation_id,
            color=chosen_color,
            size=chosen_size,
            address=context.get("address"),
            phone_number=context.get("phone_number"),
            quantity=int(context.get("quantity", 1)),
        )
        pre_order_ref = lead.pending_order_reference
    except Exception as e:
        logger.error(f"[PRE-ORDER] creation error: {e}")

    if pre_order_ref:
        return (
            ORDER_CONFIRMED_TEMPLATE.get(lang, "")
            .replace("{product}", display_name)
            .replace("{ref}", str(pre_order_ref))
        )
    return (
        ORDER_CONFIRMED_NO_REF_TEMPLATE.get(lang, "")
        .replace("{product}", display_name)
    )
