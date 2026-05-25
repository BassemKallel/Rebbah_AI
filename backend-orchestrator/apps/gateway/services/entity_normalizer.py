import ast
import json
import re
import unicodedata
from typing import Any, Dict, List, Optional

# Clés canoniques B2C & E-Commerce
_ENTITY_KEY_ALIASES: Dict[str, str] = {
    "phone": "phone_number",
    "phone_number": "phone_number",
    "telephone": "phone_number",
    "tel": "phone_number",
    "num_tel": "phone_number",
    "numero": "phone_number",
    "numero_telephone": "phone_number",
    "numero_de_telephone": "phone_number",
    "address": "address",
    "adresse": "address",
    "adresse_livraison": "address",
    "adresse_de_livraison": "address",
    "delivery_address": "address",
    "name": "name",
    "nom": "name",
    "nom_client": "name",
    "full_name": "name",
    "items": "items",
    "cart": "items",
    "panier": "items",
    "order_items": "items",
    "produit_souhaite": "product",
    "jeu_souhaite": "product",
    "product": "product",
    "produit": "product"
}

_ITEM_STANDARD_KEYS: set = {
    "product_id",
    "product_name",
    "name",
    "product",
    "quantity",
    "qty",
    "price",
    "attributes",
    "color",
    "size",
    "variant"
}

def _to_snake_case(value: str) -> str:
    normalized: str = unicodedata.normalize("NFKD", value or "")
    ascii_value: str = normalized.encode("ascii", "ignore").decode("ascii")
    underscored: str = re.sub(r"[^a-z0-9]+", "_", ascii_value.lower().strip())
    return re.sub(r"_+", "_", underscored).strip("_")

def normalize_entity_key(key: str) -> str:
    snake_key: str = _to_snake_case(key)
    return _ENTITY_KEY_ALIASES.get(snake_key, snake_key)

def _safe_int(value: Any, default: int = 1) -> int:
    try:
        parsed: int = int(str(value).strip())
        return parsed if parsed > 0 else default
    except (TypeError, ValueError):
        return default

def _parse_item_string(value: str) -> Optional[Dict[str, Any]]:
    """
    Parse les chaînes de produits en extrayant proprement les quantités
    tout en protégeant les versions de produits (ex: "FIFA 24", "GTA 5").
    """
    text: str = str(value or "").strip()
    if not text:
        return None

    # 1. Quantité en début de ligne (ex: "2 FIFA 24", "3x T-shirt")
    leading = re.match(r"^(?P<quantity>\d+)\s*(?:[xX*]\s*|\s+)(?P<name>.+)$", text)
    if leading:
        return {
            "product_name": leading.group("name").strip(),
            "quantity": _safe_int(leading.group("quantity")),
            "attributes": {}
        }

    # 2. Quantité en fin de ligne avec multiplicateur explicite (ex: "T-shirt x2", "Jeu * 3")
    trailing_explicit = re.match(r"^(?P<name>.+?)\s*(?:[:xX*]\s+|(?:[:xX*])\s*)(?P<quantity>\d+)\s*$", text)
    if trailing_explicit:
        return {
            "product_name": trailing_explicit.group("name").strip(),
            "quantity": _safe_int(trailing_explicit.group("quantity")),
            "attributes": {}
        }

    # 3. Quantité en fin de ligne avec simple espace (ex: "T-shirt 2")
    # Sécurité : Uniquement si la quantité est un chiffre < 10 ET que le mot précédent n'est pas un jeu/produit à version.
    trailing_space = re.match(r"^(?P<name>.+?)\s+(?P<quantity>\d+)\s*$", text)
    if trailing_space:
        qty: int = _safe_int(trailing_space.group("quantity"))
        name: str = trailing_space.group("name").strip()
        last_word: str = name.lower().split()[-1] if name.split() else ""
        
        version_words: set = {
            "fifa", "gta", "ps", "playstation", "xbox", "iphone", "galaxy", 
            "pes", "cod", "windows", "unravel", "mario", "zelda", "far cry"
        }
        if 0 < qty < 10 and last_word not in version_words:
            return {
                "product_name": name,
                "quantity": qty,
                "attributes": {}
            }

    # Fallback par défaut
    return {
        "product_name": text,
        "quantity": 1,
        "attributes": {}
    }

def _parse_serialized_items(value: str) -> Any:
    text: str = str(value or "").strip()
    if not (text.startswith("[") or text.startswith("{")):
        return None
    for parser in (json.loads, ast.literal_eval):
        try:
            return parser(text)
        except Exception:
            continue
    return None

def _normalize_item_dict(value: Dict[str, Any]) -> Dict[str, Any]:
    normalized: Dict[str, Any] = {normalize_entity_key(str(k)): v for k, v in value.items()}
    product_name: str = str(
        normalized.get("product_name") or 
        normalized.get("name") or 
        normalized.get("product") or 
        ""
    )
    
    # Élimine les débris JSON invalides
    if any(m in product_name for m in ("[{", "{'", "'product_name'", '"product_name"')):
        return {}

    item: Dict[str, Any] = {
        "product_name": product_name.strip(),
        "quantity": _safe_int(normalized.get("quantity", normalized.get("qty", 1))),
        "attributes": {}
    }

    if normalized.get("product_id"):
        item["product_id"] = str(normalized["product_id"]).strip()
    if normalized.get("price") not in (None, ""):
        item["price"] = normalized["price"]

    # Extraction des attributs (tailles, couleurs...)
    attributes: Any = normalized.get("attributes")
    if isinstance(attributes, dict):
        item["attributes"].update(attributes)

    for k, v in normalized.items():
        if k not in _ITEM_STANDARD_KEYS and v not in (None, ""):
            item["attributes"][k] = v
        if k in ("color", "size", "variant") and v:
            item["attributes"][k] = v

    return item

def normalize_order_items(value: Any) -> List[Dict[str, Any]]:
    if not value:
        return []
    if isinstance(value, dict):
        value = [value]
    elif isinstance(value, str):
        parsed: Any = _parse_serialized_items(value)
        if parsed is not None:
            return normalize_order_items(parsed)
        value = [part.strip() for part in re.split(r"[;\n]+", value) if part.strip()]

    if not isinstance(value, list):
        return []

    items: List[Dict[str, Any]] = []
    for raw_item in value:
        item: Optional[Dict[str, Any]] = None
        if isinstance(raw_item, dict):
            item = _normalize_item_dict(raw_item)
        elif isinstance(raw_item, str):
            parsed = _parse_serialized_items(raw_item)
            if parsed is not None:
                items.extend(normalize_order_items(parsed))
                continue
            item = _parse_item_string(raw_item)
        else:
            continue

        if item and item.get("product_name"):
            items.append(item)
    return items

def normalize_entities(entities: Dict[str, Any]) -> Dict[str, Any]:
    normalized: Dict[str, Any] = {}
    for raw_key, value in (entities or {}).items():
        key: str = normalize_entity_key(str(raw_key))
        normalized_value: Any = normalize_order_items(value) if key == "items" else value
        if normalized_value in (None, "", [], {}):
            continue
        if key in normalized:
            if key == "items":
                normalized[key] = normalize_order_items(normalized[key]) + normalize_order_items(normalized_value)
            else:
                normalized[key] = normalized_value
        else:
            normalized[key] = normalized_value
    return normalized

def normalize_context_data(context_data: Dict[str, Any]) -> Dict[str, Any]:
    public_data: Dict[str, Any] = {k: v for k, v in (context_data or {}).items() if not str(k).startswith("_")}
    internal_data: Dict[str, Any] = {k: v for k, v in (context_data or {}).items() if str(k).startswith("_")}
    return {**normalize_entities(public_data), **internal_data}
