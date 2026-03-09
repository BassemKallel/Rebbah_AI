"""
dialog_manager.py — Layer 3: State Machine & Contextual Logic

Responsibilities:
- Filter & guard entities extracted by GLiNER
- Accumulate entities into conversation context
- Run contextual mapping (Strategy 1 + Strategy 2)
- Execute the main state machine (ORDER_PRODUCT, INFORM_INFO, etc.)
"""
import re
import logging
from django.conf import settings
from apps.gateway.response_templates import (
    TEMPLATES, MISSING_ENTITY_TEMPLATES, REQUIRED_ORDER_ENTITIES,
    OUT_OF_STOCK_TEMPLATE, ORDER_CONFIRMED_TEMPLATE, ORDER_CONFIRMED_NO_REF_TEMPLATE,
)

logger = logging.getLogger(__name__)

# Map intent → entity labels that GLiNER results are filtered to
INTENT_ENTITY_FILTER = {
    "ORDER_PRODUCT":   {"product", "color", "size", "address", "phone_number", "quantity"},
    "ASK_PRICE":       {"product"},
    "ASK_AVAILABILITY": {"product", "color", "size"},
    "INFORM_INFO":     {"address", "phone_number", "color", "size"},
    "ASK_DELIVERY":    set(),
    "GREETING":        set(),
    "UNKNOWN":         set(),
    "NOISE":           set(),
    "ASK_DETAILS":     {"product"},
    "ASK_DISCOUNT":    set(),
    "ASK_LOCATION":    set(),
    "CANCEL_ORDER":    set(),
    "CHECK_PACKAGE":   set(),
    "COMPLAINT":       set(),
    "CONFIRM_DENY":    set(),
    "TRACK_ORDER":     {"phone_number"},
    "ASK_ADVICE":      {"product"},
    "ECHANGE":         {"product"},
}

_VALID_SIZES = {"S", "M", "L", "XL", "2XL", "3XL", "4XL", "ONE SIZE", "XS", "XXL", "XXXL"}


# ─── Entity Guards ───────────────────────────────────────────────────────────

def apply_entity_guards(nlu_raw_entities: list, intent: str, conversation) -> dict:
    """
    Filter GLiNER entities:
    - Only keep labels relevant to the current intent / missing_entities
    - Reject address entries that are too short, look like a size, or were also
      labelled as phone_number by GLiNER
    - Color correction bypass: even when color is not in relevant_entities,
      allow it if a color is already in context (explicit user correction)

    Returns extracted_entities dict.
    """
    if (intent == "INFORM_INFO"
            and conversation.missing_entities
            and conversation.state == "WAITING_USER_REPLY"):
        relevant = set(conversation.missing_entities)
    else:
        relevant = INTENT_ENTITY_FILTER.get(intent, set())

    phone_texts = {e["text"].strip() for e in nlu_raw_entities if e["label"] == "phone_number"}

    extracted: dict = {}
    for ent in nlu_raw_entities:
        if ent["label"] in relevant:
            if ent["label"] == "address":
                val = ent["text"].strip()
                if len(val) < 3 or val.upper() in _VALID_SIZES or val in phone_texts:
                    continue
            extracted[ent["label"]] = ent["text"]

    # Color correction bypass
    if "color" in conversation.context_data:
        for ent in nlu_raw_entities:
            if ent["label"] == "color":
                extracted["color"] = ent["text"]
                logger.debug(f"[COLOR CORRECTION] {conversation.context_data['color']} → {ent['text']}")
                break

    return extracted


# ─── Context Accumulation ────────────────────────────────────────────────────

def accumulate_context(current_context: dict, extracted_entities: dict) -> dict:
    """
    Merge extracted_entities into the conversation context with priority rules:

    - product: locked once set, EXCEPT when the new product comes from the
      vision service (Article_From_Image_xxx) — image always wins.
    - color: locked, EXCEPT when the ONLY entity in this message is "color"
      (explicit correction like "Non, Bleu").
    - address: rejected if product/color/size are not yet known (either in
      the existing context or in the current message entities).
      Prevents free-text noise from being mistakenly captured as an address.

    Returns the updated current_context.
    """
    # ── Address Guard ────────────────────────────────────────────────────────
    # Merge current context with freshly extracted entities so that a full
    # sentence like "t-shirt rouge M à Tunis" doesn't lose the address.
    if "address" in extracted_entities:
        context_plus_new = {**current_context, **extracted_entities}
        prerequisite_entities = {"product", "color", "size"}
        if not prerequisite_entities.issubset(context_plus_new.keys()):
            extracted_entities.pop("address")
            logger.info("[ADDRESS GUARD] Address rejected: product/color/size not yet collected")

    new_product      = extracted_entities.get("product", "")
    is_image_product = new_product.startswith("Article_From_Image_")

    if "product" in current_context:
        if is_image_product:
            current_context.pop("color", None)
            extracted_entities.pop("color", None)
            logger.info(f"[VISION PRIORITY] '{current_context['product']}' → '{new_product}'")
        else:
            extracted_entities.pop("product", None)

    if "color" in current_context:
        is_explicit_correction = list(extracted_entities.keys()) == ["color"]
        if not is_explicit_correction:
            extracted_entities.pop("color", None)

    current_context.update(extracted_entities)
    current_context.pop("_vision_variation_id", None)
    return current_context


# ─── Contextual Mapping ──────────────────────────────────────────────────────

def run_contextual_mapping(conversation, text: str, extracted_entities: dict,
                            nlu_raw_entities: list, current_context: dict) -> tuple:
    """
    When the bot is WAITING_USER_REPLY, try to extract the expected entity from
    the user's free-text response using two strategies:

    Strategy 1 — direct GLiNER label match against missing fields.
    Strategy 2 — pattern-based validation (size, phone number, address/color).

    Returns (updated_extracted_entities, contextual_match: bool).
    """
    _contextual_intents = {"INFORM_INFO", "NOISE", "ORDER_PRODUCT", "UNKNOWN"}
    previous_state = conversation.state

    if not (previous_state == "WAITING_USER_REPLY"
            and conversation.missing_entities):
        return extracted_entities, False

    # Import here to avoid circular check — intent passed in from views
    contextual_match = False
    text_clean = text.strip().upper()

    # Strategy 1
    for ent in nlu_raw_entities:
        label = ent["label"]
        if label not in extracted_entities and label in conversation.missing_entities:
            extracted_entities[label] = ent["text"]
            current_context[label]    = ent["text"]
            contextual_match = True
            break

    # Strategy 2
    if not contextual_match:
        for missing_field in conversation.missing_entities:
            if missing_field in extracted_entities:
                continue

            if missing_field == "size":
                valid_sizes = ["S", "M", "L", "XL", "2XL", "3XL", "4XL", "ONE SIZE"]
                if text_clean in valid_sizes:
                    extracted_entities[missing_field] = text_clean
                    current_context[missing_field]    = text_clean
                    contextual_match = True
                    break

            elif missing_field == "quantity":
                try:
                    qty = int(text_clean)
                    if 1 <= qty <= 999:
                        extracted_entities[missing_field] = str(qty)
                        current_context[missing_field]    = str(qty)
                        contextual_match = True
                        break
                except ValueError:
                    pass

            elif missing_field == "phone_number":
                phone_pattern = r'^(\+216|00216|216)?[\s.-]?[0-9\s.-]{7,}$'
                if re.match(phone_pattern, text_clean):
                    extracted_entities[missing_field] = text
                    current_context[missing_field]    = text
                    contextual_match = True
                    break

            elif missing_field in ["address", "color"]:
                val            = text.strip()
                already_labelled        = val in extracted_entities.values()
                gliner_labels  = {e["label"] for e in nlu_raw_entities if e["text"].strip() == val}
                gliner_not_addr = bool(gliner_labels) and gliner_labels != {"address"}

                if missing_field == "address":
                    valid_sizes = ["S", "M", "L", "XL", "2XL", "3XL", "4XL", "ONE SIZE"]
                    if (val and len(val) >= 3 and val.upper() not in valid_sizes
                            and not already_labelled and not gliner_not_addr):
                        extracted_entities[missing_field] = val
                        current_context[missing_field]    = val
                        contextual_match = True
                        break
                elif missing_field == "color":
                    # Only accept color if GLiNER explicitly labeled it as such.
                    # Prevents generic text (e.g. "nheb naadi commande") from being
                    # captured as a color entity when the bot is waiting for one.
                    color_match = next(
                        (e["text"] for e in nlu_raw_entities if e["label"] == "color"),
                        None
                    )
                    if color_match:
                        extracted_entities[missing_field] = color_match
                        current_context[missing_field]    = color_match
                        contextual_match = True
                        break

    return extracted_entities, contextual_match


# ─── Stock Check Helper ──────────────────────────────────────────────────────

def _check_stock(matched_product: dict, color: str, size: str) -> tuple:
    """
    Check stock for a given color/size combination.

    Returns (stock_ok: bool, available_str: str).

    - Si matched_product est None, on ne peut pas vérifier → on passe (True).
    - Sinon, on filtre les variations selon les champs non-vides (color et/ou size).
    - Un produit avec stock_quantity == 0 est détecté même si color est vide.
    """
    if not matched_product:
        return True, ""

    # Filtre dynamique selon les champs fournis
    def _matches(v: dict) -> bool:
        color_match = (not color) or (v.get("color", "").lower() == color.lower())
        size_match  = (not size)  or (v.get("size",  "").lower() == size.lower())
        return color_match and size_match

    # Si aucun critère, vérifier le stock global du produit
    if not color and not size:
        total_stock = sum(v.get("stock_quantity", 0) for v in matched_product.get("variations", []))
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


# ─── State Machine ───────────────────────────────────────────────────────────

def run_state_machine(intent: str, previous_state: str, current_context: dict,
                      matched_product, lead, conversation,
                      vision_variation_id: str = None) -> dict:
    """
    Execute the main intent→state machine.

    Returns:
    {
        "bot_response": str,
        "new_state":    str,
        "missing_list": list,
    }
    """
    bot_response = TEMPLATES.get("UNKNOWN", "Je n'ai pas compris.")
    missing_list = []
    new_state    = previous_state

    # ── ORDER_PRODUCT ──────────────────────────────────────────────────────
    if intent == "ORDER_PRODUCT":
        for req in REQUIRED_ORDER_ENTITIES:
            if req not in current_context:
                missing_list.append(req)

        if missing_list:
            new_state = "WAITING_USER_REPLY"
            color = current_context.get("color", "")
            size  = current_context.get("size",  "")
            stock_ok, avail = _check_stock(matched_product, color, size)

            if not stock_ok:
                display = matched_product["name"]
                bot_response = (
                    OUT_OF_STOCK_TEMPLATE
                    .replace("{product}", display)
                    .replace("{color}",   color)
                    .replace("{size}",    size)
                )
                if avail:
                    bot_response += f"\nDisponible en : {avail}"
                current_context.pop("color", None)
                current_context.pop("size",  None)
                missing_list = [r for r in REQUIRED_ORDER_ENTITIES if r not in current_context]
            else:
                first_missing = missing_list[0]
                display       = matched_product["name"] if matched_product else "cet article"
                bot_response  = (
                    MISSING_ENTITY_TEMPLATES
                    .get(first_missing, f"Pouvez-vous me dire {first_missing} ?")
                    .replace("{product}", display)
                    .replace("{color}",   color)
                )
                if matched_product and first_missing in ("size", "color"):
                    variations = matched_product.get("variations", [])
                    if first_missing == "size":
                        avail = ", ".join(list(set(v["size"] for v in variations if v.get("stock_quantity", 0) > 0)))
                        bot_response += f"\nTailles disponibles : {avail}" if avail else ""
                    else:
                        avail = ", ".join(list(set(v["color"] for v in variations if v.get("stock_quantity", 0) > 0)))
                        bot_response += f"\nCouleurs disponibles : {avail}" if avail else ""
        else:
            # All entities collected — create pre-order
            chosen_color = current_context.get("color", "")
            chosen_size  = current_context.get("size",  "")
            display      = matched_product["name"] if matched_product else current_context.get("product", "votre article")
            stock_ok, avail = _check_stock(matched_product, chosen_color, chosen_size)

            if not stock_ok:
                bot_response = (
                    OUT_OF_STOCK_TEMPLATE
                    .replace("{product}", display)
                    .replace("{color}",   chosen_color)
                    .replace("{size}",    chosen_size)
                )
                if avail:
                    bot_response += f"\nDisponible en : {avail}"
                current_context.pop("color", None)
                current_context.pop("size",  None)
                missing_list = [r for r in REQUIRED_ORDER_ENTITIES if r not in current_context]
                new_state    = "WAITING_USER_REPLY"
            else:
                new_state = "COMPLETED"
                bot_response = _create_preorder_and_confirm(
                    lead, matched_product, vision_variation_id,
                    chosen_color, chosen_size, current_context, display
                )

    # ── INFORM_INFO ────────────────────────────────────────────────────────
    elif intent == "INFORM_INFO":
        if previous_state == "WAITING_USER_REPLY" and conversation.missing_entities:
            for req in REQUIRED_ORDER_ENTITIES:
                if req not in current_context:
                    missing_list.append(req)

            if missing_list:
                new_state = "WAITING_USER_REPLY"
                color = current_context.get("color", "")
                size  = current_context.get("size",  "")
                stock_ok, avail = _check_stock(matched_product, color, size)

                if not stock_ok:
                    display = matched_product["name"]
                    bot_response = (
                        OUT_OF_STOCK_TEMPLATE
                        .replace("{product}", display)
                        .replace("{color}",   color)
                        .replace("{size}",    size)
                    )
                    if avail:
                        bot_response += f"\nDisponible en : {avail}"
                    current_context.pop("color", None)
                    current_context.pop("size",  None)
                    missing_list = [r for r in REQUIRED_ORDER_ENTITIES if r not in current_context]
                else:
                    first_missing = missing_list[0]
                    bot_response  = (
                        MISSING_ENTITY_TEMPLATES
                        .get(first_missing, f"Et pour la {first_missing} ?")
                        .replace("{product}", current_context.get("product", "cet article"))
                        .replace("{color}",   color)
                    )
            else:
                # All entities collected
                chosen_color = current_context.get("color", "")
                chosen_size  = current_context.get("size",  "")
                display      = matched_product["name"] if matched_product else current_context.get("product", "votre article")

                if not matched_product and current_context.get("product", "").startswith("Article_From_Image_"):
                    bot_response = "Désolé, impossible de vérifier le stock pour le moment. Veuillez réessayer."
                    new_state    = "WAITING_USER_REPLY"
                    missing_list = [r for r in REQUIRED_ORDER_ENTITIES if r not in current_context]
                else:
                    stock_ok, avail = _check_stock(matched_product, chosen_color, chosen_size)
                    if not stock_ok:
                        bot_response = (
                            OUT_OF_STOCK_TEMPLATE
                            .replace("{product}", display)
                            .replace("{color}",   chosen_color)
                            .replace("{size}",    chosen_size)
                        )
                        if avail:
                            bot_response += f"\nDisponible en : {avail}"
                        current_context.pop("color", None)
                        current_context.pop("size",  None)
                        missing_list = [r for r in REQUIRED_ORDER_ENTITIES if r not in current_context]
                        new_state    = "WAITING_USER_REPLY"
                    else:
                        logger.debug(f"[STOCK CHECK] color='{chosen_color}' size='{chosen_size}'")
                        new_state    = "COMPLETED"
                        bot_response = _create_preorder_and_confirm(
                            lead, matched_product, vision_variation_id,
                            chosen_color, chosen_size, current_context, display
                        )
        else:
            # INFORM_INFO outside an active flow
            if "product" not in current_context:
                bot_response = "Merci pour ces informations ! Quel article souhaitez-vous commander ?"
                new_state    = "WAITING_USER_REPLY"
                missing_list = ["product"]
            else:
                bot_response = TEMPLATES.get("INFORM_INFO")

    # ── ASK_PRICE / ASK_AVAILABILITY / ASK_DELIVERY ────────────────────────
    elif intent in ("ASK_PRICE", "ASK_AVAILABILITY", "ASK_DELIVERY"):
        if previous_state == "WAITING_USER_REPLY" and conversation.missing_entities:
            if intent == "ASK_PRICE" and matched_product:
                bot_response = f"Le {matched_product['name']} est au prix de {matched_product.get('base_price', '0')} TND. "
            elif intent == "ASK_AVAILABILITY" and matched_product:
                variations = matched_product.get("variations", [])
                sizes  = ", ".join(list(set(v["size"]  for v in variations if v.get("stock_quantity", 0) > 0)))
                colors = ", ".join(list(set(v["color"] for v in variations if v.get("stock_quantity", 0) > 0)))
                bot_response = f"Oui, le {matched_product['name']} est en stock. Tailles : {sizes or 'aucune'}. Couleurs : {colors or 'aucune'}. "
            else:
                bot_response = TEMPLATES.get(intent, "Je n'ai pas compris.")

            for req in REQUIRED_ORDER_ENTITIES:
                if req not in current_context:
                    missing_list.append(req)
            if missing_list:
                new_state    = "WAITING_USER_REPLY"
                first_missing = missing_list[0]
                bot_response += (
                    MISSING_ENTITY_TEMPLATES
                    .get(first_missing, f"Pouvez-vous me dire {first_missing} ?")
                    .replace("{product}", matched_product["name"] if matched_product else current_context.get("product", "cet article"))
                    .replace("{color}",   current_context.get("color", ""))
                )
        else:
            if not matched_product:
                if intent == "ASK_AVAILABILITY":
                    bot_response = "Sur quel article souhaitez-vous vérifier la disponibilité ?"
                elif intent == "ASK_PRICE":
                    bot_response = "Sur quel article souhaitez-vous connaître le prix ?"
                else:
                    bot_response = TEMPLATES.get(intent, "Je n'ai pas compris.")
            else:
                bot_response = TEMPLATES.get(intent, "Je n'ai pas compris.")
                price = matched_product.get("base_price", "0")
                variations = matched_product.get("variations", [])
                sizes  = ", ".join(list(set(v["size"]  for v in variations if v.get("stock_quantity", 0) > 0)))
                colors = ", ".join(list(set(v["color"] for v in variations if v.get("stock_quantity", 0) > 0)))
                bot_response = (
                    bot_response
                    .replace("{product}", matched_product["name"])
                    .replace("{price}",   str(price))
                    .replace("{sizes}",   sizes  or "rupture de stock")
                    .replace("{colors}",  colors or "rupture de couleur")
                )

    # ── ALL OTHER INTENTS ──────────────────────────────────────────────────
    else:
        if intent == "NOISE" and previous_state == "WAITING_USER_REPLY" and conversation.missing_entities:
            new_state    = "WAITING_USER_REPLY"
            missing_list = conversation.missing_entities
            first_missing = missing_list[0] if missing_list else None
            bot_response  = "Parlez plus clairement s'il vous plaît. "
            if first_missing:
                bot_response += (
                    MISSING_ENTITY_TEMPLATES
                    .get(first_missing, f"Pouvez-vous me dire {first_missing} ?")
                    .replace("{product}", current_context.get("product", "cet article"))
                    .replace("{color}",   current_context.get("color", ""))
                )
        else:
            bot_response = TEMPLATES.get(intent, TEMPLATES.get("UNKNOWN"))

    # Safety net: remove unresolved {placeholders}
    bot_response = re.sub(r'\{[a-z_]+\}', '', bot_response).strip()

    return {
        "bot_response": bot_response,
        "new_state":    new_state,
        "missing_list": missing_list,
    }


# ─── Pre-order helper ────────────────────────────────────────────────────────

def _create_preorder_and_confirm(lead, matched_product, vision_variation_id,
                                  chosen_color, chosen_size, context, display_name) -> str:
    """Create a pre-order in Lead and return the confirmation message."""
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
        return ORDER_CONFIRMED_TEMPLATE.replace("{product}", display_name).replace("{ref}", str(pre_order_ref))
    return ORDER_CONFIRMED_NO_REF_TEMPLATE.replace("{product}", display_name)
