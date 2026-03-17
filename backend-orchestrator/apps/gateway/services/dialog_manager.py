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
from typing import Optional, Set
from django.conf import settings  # pyre-ignore[21]
from apps.gateway.response_templates import (  # pyre-ignore[21]
    TEMPLATES, MISSING_ENTITY_TEMPLATES, REQUIRED_ORDER_ENTITIES,
    OUT_OF_STOCK_TEMPLATE, ORDER_CONFIRMED_TEMPLATE, ORDER_CONFIRMED_NO_REF_TEMPLATE,
    OUT_OF_STOCK_AVAILABLE, OUT_OF_STOCK_SIZES, OUT_OF_STOCK_COLORS,
    MISSING_ENTITY_DEFAULT, INFORM_INFO_DEFAULT, INFORM_PRODUCT_DEFAULT,
    ASK_AVAILABILITY_DEFAULT, ASK_PRICE_DEFAULT, NOISE_DEFAULT, STOCK_CHECK_ERROR,
    DISAMBIGUATION_TEMPLATE
)

logger = logging.getLogger(__name__)

def detect_language(text: str) -> str:
    """Detect language: Arabic characters → AR, everything else → FR."""
    if not text:
        return "FR"
    if re.search(r'[\u0600-\u06FF]', text):
        return "AR"
    return "FR"

def _format_bot_response(response: str, variables: dict) -> str:
    """Replaces {{variable}} or {variable} with its corresponding value."""
    if not response:
        return ""
    
    for key, value in variables.items():
        if value is not None:
            # Replace {{var}}
            response = response.replace(f"{{{{{key}}}}}", str(value))
            # Replace {var} for older templates compatibility
            response = response.replace(f"{{{key}}}", str(value))
    
    # Clean up any remaining unresolved placeholders
    response = re.sub(r'\{\{?[a-z_]+\}?\}', '', response).strip()
    return response

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
    "ASK_DISCOUNT":    {"product", "color", "size"},
    "ASK_LOCATION":    {"address", "phone_number"},
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
    relevant: Set[str] = set()
    if (conversation.missing_entities
            and conversation.state in ("WAITING_USER_REPLY", "NEW_CONVERSATION")
            and intent in ("INFORM_INFO", "ASK_LOCATION", "CONFIRM_DENY")):
        relevant = set(conversation.missing_entities)
    else:
        relevant = set(INTENT_ENTITY_FILTER.get(intent, set()))

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
    # ── Address Guard ────────────────────────────────────────────────────────
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
    _contextual_intents = {"INFORM_INFO", "NOISE", "ORDER_PRODUCT", "UNKNOWN"}
    previous_state = conversation.state

    if not (previous_state == "WAITING_USER_REPLY"
            and conversation.missing_entities):
        return extracted_entities, False

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
    if not matched_product:
        return True, ""

    def _matches(v: dict) -> bool:
        color_match = (not color) or (v.get("color", "").lower() == color.lower())
        size_match  = (not size)  or (v.get("size",  "").lower() == size.lower())
        return color_match and size_match

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


def _auto_fill_single_color(matched_product: dict, current_context: dict) -> None:
    """If only one in-stock color exists for the product, pre-fill it in context."""
    if not matched_product:
        return
    in_stock_colors = list({
        v["color"] for v in matched_product.get("variations", [])
        if v.get("stock_quantity", 0) > 0 and v.get("color")
    })
    if len(in_stock_colors) == 1:
        current_context["color"] = in_stock_colors[0]
        logger.info(f"[AUTO COLOR] Single color available: '{in_stock_colors[0]}' — pre-filled in context")


# ─── State Machine ───────────────────────────────────────────────────────────

def run_state_machine(intent: str, previous_state: str, current_context: dict,
                      matched_product, lead, conversation,
                      vision_variation_id: Optional[str] = None, bot_config = None, text: str = "") -> dict:
    
    lang = "FR"
    if bot_config:
        if bot_config.language == "AUTO":
            lang = detect_language(text)
        else:
            lang = bot_config.language

    # Build substitution variables
    shop_name = bot_config.shop_name if bot_config and bot_config.shop_name else "notre boutique"
    ai_agent_name = bot_config.ai_agent_name if bot_config and bot_config.ai_agent_name else "TikTak AI"
    variables = {
        "shop_name": shop_name,
        "ai_agent_name": ai_agent_name,
        "product": matched_product["name"] if matched_product else current_context.get("product", "cet article"),
        "color": current_context.get("color", ""),
        "size": current_context.get("size", ""),
        "price": str(matched_product.get("base_price", "0")) if matched_product else "0",
    }

    # Custom intents override
    custom_intents = bot_config.custom_intents if bot_config and isinstance(bot_config.custom_intents, dict) else {}
    if intent in custom_intents and custom_intents[intent].strip():
        # But wait, ORDER_PRODUCT and INFORM_INFO have complex state logic for missing entities.
        # So we only override single turn intents directly if it's purely informational or if it's already fulfilled.
        # For simplicity, we only fully return custom directly for informational intents:
        if intent in ("ASK_PRICE", "ASK_AVAILABILITY", "ASK_DELIVERY", "GREETING") or (intent not in ["ORDER_PRODUCT", "INFORM_INFO", "NOISE", "UNKNOWN"]):
            return {
                "bot_response": _format_bot_response(custom_intents[intent], variables),
                "new_state": previous_state,
                "missing_list": []
            }

    bot_response = TEMPLATES.get(lang, {}).get("UNKNOWN", "Je n'ai pas compris.")
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
                    OUT_OF_STOCK_TEMPLATE.get(lang, "")
                    .replace("{product}", display)
                    .replace("{color}",   color)
                    .replace("{size}",    size)
                )
                if avail:
                    bot_response += OUT_OF_STOCK_AVAILABLE.get(lang, "").replace("{avail}", avail)
                current_context.pop("color", None)
                current_context.pop("size",  None)
                _auto_fill_single_color(matched_product, current_context)
                missing_list = [r for r in REQUIRED_ORDER_ENTITIES if r not in current_context]
            else:
                first_missing = missing_list[0]
                display       = matched_product["name"] if matched_product else "cet article"
                bot_response  = (
                    MISSING_ENTITY_TEMPLATES.get(lang, {})
                    .get(first_missing, MISSING_ENTITY_DEFAULT.get(lang, "").replace("{first_missing}", first_missing))
                    .replace("{product}", display)
                    .replace("{color}",   color)
                )
                if matched_product and first_missing in ("size", "color"):
                    variations = matched_product.get("variations", [])
                    if first_missing == "size":
                        avail = ", ".join(list(set(v["size"] for v in variations if v.get("stock_quantity", 0) > 0)))
                        if avail: bot_response += OUT_OF_STOCK_SIZES.get(lang, "").replace("{avail}", avail)
                    else:
                        avail = ", ".join(list(set(v["color"] for v in variations if v.get("stock_quantity", 0) > 0)))
                        if avail: bot_response += OUT_OF_STOCK_COLORS.get(lang, "").replace("{avail}", avail)
        else:
            # All entities collected — create pre-order
            chosen_color = current_context.get("color", "")
            chosen_size  = current_context.get("size",  "")
            display      = matched_product["name"] if matched_product else current_context.get("product", "votre article")
            stock_ok, avail = _check_stock(matched_product, chosen_color, chosen_size)

            if not stock_ok:
                bot_response = (
                    OUT_OF_STOCK_TEMPLATE.get(lang, "")
                    .replace("{product}", display)
                    .replace("{color}",   chosen_color)
                    .replace("{size}",    chosen_size)
                )
                if avail:
                    bot_response += OUT_OF_STOCK_AVAILABLE.get(lang, "").replace("{avail}", avail)
                current_context.pop("color", None)
                current_context.pop("size",  None)
                _auto_fill_single_color(matched_product, current_context)
                missing_list = [r for r in REQUIRED_ORDER_ENTITIES if r not in current_context]
                new_state    = "WAITING_USER_REPLY"
            else:
                new_state = "COMPLETED"
                bot_response = _create_preorder_and_confirm(
                    lead, matched_product, vision_variation_id,
                    chosen_color, chosen_size, current_context, display, lang=lang
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
                        OUT_OF_STOCK_TEMPLATE.get(lang, "")
                        .replace("{product}", display)
                        .replace("{color}",   color)
                        .replace("{size}",    size)
                    )
                    if avail:
                        bot_response += OUT_OF_STOCK_AVAILABLE.get(lang, "").replace("{avail}", avail)
                    current_context.pop("color", None)
                    current_context.pop("size",  None)
                    _auto_fill_single_color(matched_product, current_context)
                    missing_list = [r for r in REQUIRED_ORDER_ENTITIES if r not in current_context]
                else:
                    first_missing = missing_list[0]
                    bot_response  = (
                        MISSING_ENTITY_TEMPLATES.get(lang, {})
                        .get(first_missing, INFORM_INFO_DEFAULT.get(lang, "").replace("{first_missing}", first_missing))
                        .replace("{product}", matched_product["name"] if matched_product else current_context.get("product", "cet article"))
                        .replace("{color}",   color)
                    )
            else:
                # All entities collected
                chosen_color = current_context.get("color", "")
                chosen_size  = current_context.get("size",  "")
                display      = matched_product["name"] if matched_product else current_context.get("product", "votre article")

                if not matched_product and current_context.get("product", "").startswith("Article_From_Image_"):
                    bot_response = STOCK_CHECK_ERROR.get(lang, "")
                    new_state    = "WAITING_USER_REPLY"
                    missing_list = [r for r in REQUIRED_ORDER_ENTITIES if r not in current_context]
                else:
                    stock_ok, avail = _check_stock(matched_product, chosen_color, chosen_size)
                    if not stock_ok:
                        bot_response = (
                            OUT_OF_STOCK_TEMPLATE.get(lang, "")
                            .replace("{product}", display)
                            .replace("{color}",   chosen_color)
                            .replace("{size}",    chosen_size)
                        )
                        if avail:
                            bot_response += OUT_OF_STOCK_AVAILABLE.get(lang, "").replace("{avail}", avail)
                        current_context.pop("color", None)
                        current_context.pop("size",  None)
                        _auto_fill_single_color(matched_product, current_context)
                        missing_list = [r for r in REQUIRED_ORDER_ENTITIES if r not in current_context]
                        new_state    = "WAITING_USER_REPLY"
                    else:
                        logger.debug(f"[STOCK CHECK] color='{chosen_color}' size='{chosen_size}'")
                        new_state    = "COMPLETED"
                        bot_response = _create_preorder_and_confirm(
                            lead, matched_product, vision_variation_id,
                            chosen_color, chosen_size, current_context, display, lang=lang
                        )
        else:
            # INFORM_INFO outside an active flow
            if "product" not in current_context:
                bot_response = INFORM_PRODUCT_DEFAULT.get(lang, "")
                new_state    = "WAITING_USER_REPLY"
                missing_list = ["product"]
            else:
                bot_response = TEMPLATES.get(lang, {}).get("INFORM_INFO", "")

    # ── ASK_PRICE / ASK_AVAILABILITY / ASK_DELIVERY ────────────────────────
    elif intent in ("ASK_PRICE", "ASK_AVAILABILITY", "ASK_DELIVERY"):
        if previous_state == "WAITING_USER_REPLY" and conversation.missing_entities:
            skip_missing_flow = False

            if intent == "ASK_PRICE" and matched_product:
                price = matched_product.get('base_price', '0')
                bot_response = TEMPLATES.get(lang, {}).get("ASK_PRICE", "").replace("{product}", matched_product['name']).replace("{price}", str(price)) + " "
            elif intent == "ASK_AVAILABILITY" and matched_product:
                size  = current_context.get("size", "")
                color = current_context.get("color", "")
                if size:
                    # User asked about a specific size — validate stock first
                    stock_ok, avail = _check_stock(matched_product, color, size)
                    if not stock_ok:
                        display = matched_product["name"]
                        bot_response = (
                            OUT_OF_STOCK_TEMPLATE.get(lang, "")
                            .replace("{product}", display)
                            .replace("{color}", color)
                            .replace("{size}", size)
                        )
                        if avail:
                            bot_response += OUT_OF_STOCK_AVAILABLE.get(lang, "").replace("{avail}", avail)
                        current_context.pop("size", None)
                        _auto_fill_single_color(matched_product, current_context)
                        missing_list = [r for r in REQUIRED_ORDER_ENTITIES if r not in current_context]
                        new_state = "WAITING_USER_REPLY"
                        skip_missing_flow = True  # Don't re-append missing list below
                    else:
                        # Size IS in stock — confirm and continue flow
                        variations = matched_product.get("variations", [])
                        sizes  = ", ".join(sorted(set(v["size"]  for v in variations if v.get("stock_quantity", 0) > 0)))
                        colors = ", ".join(sorted(set(v["color"] for v in variations if v.get("stock_quantity", 0) > 0)))
                        bot_response = TEMPLATES.get(lang, {}).get("ASK_AVAILABILITY", "").replace("{product}", matched_product['name']).replace("{sizes}", sizes or "-").replace("{colors}", colors or "-") + " "
                else:
                    # No specific size — show all available
                    variations = matched_product.get("variations", [])
                    sizes  = ", ".join(sorted(set(v["size"]  for v in variations if v.get("stock_quantity", 0) > 0)))
                    colors = ", ".join(sorted(set(v["color"] for v in variations if v.get("stock_quantity", 0) > 0)))
                    bot_response = TEMPLATES.get(lang, {}).get("ASK_AVAILABILITY", "").replace("{product}", matched_product['name']).replace("{sizes}", sizes or "-").replace("{colors}", colors or "-") + " "
            else:
                bot_response = TEMPLATES.get(lang, {}).get(intent, "")

            if not skip_missing_flow:
                for req in REQUIRED_ORDER_ENTITIES:
                    if req not in current_context:
                        missing_list.append(req)
                if missing_list:
                    new_state    = "WAITING_USER_REPLY"
                    first_missing = missing_list[0]
                    bot_response += (
                        MISSING_ENTITY_TEMPLATES.get(lang, {})
                        .get(first_missing, MISSING_ENTITY_DEFAULT.get(lang, "").replace("{first_missing}", first_missing))
                        .replace("{product}", matched_product["name"] if matched_product else current_context.get("product", "cet article"))
                        .replace("{color}",   current_context.get("color", ""))
                    )

        else:
            if not matched_product:
                if intent == "ASK_AVAILABILITY":
                    bot_response = ASK_AVAILABILITY_DEFAULT.get(lang, "")
                elif intent == "ASK_PRICE":
                    bot_response = ASK_PRICE_DEFAULT.get(lang, "")
                else:
                    bot_response = TEMPLATES.get(lang, {}).get(intent, "")
            else:
                bot_response = TEMPLATES.get(lang, {}).get(intent, "")
                price = matched_product.get("base_price", "0")
                variations = matched_product.get("variations", [])
                sizes  = ", ".join(list(set(v["size"]  for v in variations if v.get("stock_quantity", 0) > 0)))
                colors = ", ".join(list(set(v["color"] for v in variations if v.get("stock_quantity", 0) > 0)))
                bot_response = (
                    bot_response
                    .replace("{product}", matched_product["name"])
                    .replace("{price}",   str(price))
                    .replace("{sizes}",   sizes  or "-")
                    .replace("{colors}",  colors or "-")
                )

    # ── ALL OTHER INTENTS ──────────────────────────────────────────────────
    else:
        # Preserve context for vague/confirmatory intents when entities are still missing
        if intent in ("NOISE", "CONFIRM_DENY", "ASK_LOCATION") and conversation.missing_entities:
            new_state    = "WAITING_USER_REPLY"
            missing_list = conversation.missing_entities
            first_missing = missing_list[0] if missing_list else None
            if intent == "ASK_LOCATION":
                bot_response = TEMPLATES.get(lang, {}).get("ASK_LOCATION", "") + " "
            else:
                bot_response = NOISE_DEFAULT.get(lang, "")
            if first_missing:
                bot_response += (
                    MISSING_ENTITY_TEMPLATES.get(lang, {})
                    .get(first_missing, MISSING_ENTITY_DEFAULT.get(lang, "").replace("{first_missing}", first_missing))
                    .replace("{product}", matched_product["name"] if matched_product else current_context.get("product", "cet article"))
                    .replace("{color}",   current_context.get("color", ""))
                )
        else:
            bot_response = TEMPLATES.get(lang, {}).get(intent, TEMPLATES.get(lang, {}).get("UNKNOWN", ""))

    # If it's a custom intent that wasn't eagerly bypassed (e.g., custom ORDER_PRODUCT response after completion)
    # Note: Complex interactions like order flow still use the built-in OUT_OF_STOCK and MISSING_ENTITY templates for flow logic.
    if intent in custom_intents and custom_intents[intent] and new_state == "COMPLETED" and not missing_list:
         # Optionally override the final completion message
         pass

    # Standardize output by running through format mapper
    bot_response = _format_bot_response(bot_response, variables)

    return {
        "bot_response": bot_response,
        "new_state":    new_state,
        "missing_list": missing_list,
    }


# ─── Pre-order helper ────────────────────────────────────────────────────────

def _create_preorder_and_confirm(lead, matched_product, vision_variation_id,
                                  chosen_color, chosen_size, context, display_name, lang="FR") -> str:
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
        return ORDER_CONFIRMED_TEMPLATE.get(lang, "").replace("{product}", display_name).replace("{ref}", str(pre_order_ref))
    return ORDER_CONFIRMED_NO_REF_TEMPLATE.get(lang, "").replace("{product}", display_name)
