"""
Configuration for the NLU Service.
Defines model paths, labels, and thresholds used by main.py.
"""
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent

TUNBERT_MODEL_PATH = BASE_DIR / "models" / "tunbert_intent" / "tunbert_v3"
GLINER_MODEL_PATH  = BASE_DIR / "models" / "gliner_entity"  / "gliner_finetuned_v7"

# ── Intent label mapping (index → label) ───────────────────────────────────
# MUST match the model's own id2label in models/tunbert_intent/tunbert_v3/config.json
INTENT_LABELS = {
    0:  "ASK_ADVICE",
    1:  "ASK_AVAILABILITY",
    2:  "ASK_DELIVERY",
    3:  "ASK_DETAILS",
    4:  "ASK_DISCOUNT",
    5:  "ASK_LOCATION",
    6:  "ASK_PRICE",
    7:  "CANCEL_ORDER",
    8:  "CHECK_PACKAGE",
    9:  "COMPLAINT",
    10: "CONFIRM_DENY",
    11: "ECHANGE",
    12: "GREETING",
    13: "INFORM_INFO",
    14: "NOISE",
    15: "ORDER_PRODUCT",
    16: "TRACK_ORDER",
}

# ── Entity labels (GLiNER) ─────────────────────────────────────────────────
ENTITY_LABELS = [
    "product",
    "color",
    "size",
    "address",
    "phone_number",
    "quantity",
    "client_name",
]

# ── Thresholds ─────────────────────────────────────────────────────────────
INTENT_CONFIDENCE_THRESHOLD = 0.5
ENTITY_CONFIDENCE_THRESHOLD = 0.6

# ── API server settings ────────────────────────────────────────────────────
API_HOST = "0.0.0.0"
API_PORT = 8001
