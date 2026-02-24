"""
Configuration settings for NLU Service
"""
import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent
MODELS_DIR = BASE_DIR / "models"

# Model paths
TUNBERT_MODEL_PATH = MODELS_DIR / "tunbert_intent" / "tunbert_v3"
GLINER_MODEL_PATH = MODELS_DIR / "gliner_entity" / "gliner_finetuned_v7"

# Intent labels (from TunBERT model config.json)
INTENT_LABELS = {
    0: "ASK_ADVICE",
    1: "ASK_AVAILABILITY",
    2: "ASK_DELIVERY",
    3: "ASK_DETAILS",
    4: "ASK_DISCOUNT",
    5: "ASK_LOCATION",
    6: "ASK_PRICE",
    7: "CANCEL_ORDER",
    8: "CHECK_PACKAGE",
    9: "COMPLAINT",
    10: "CONFIRM_DENY",
    11: "ECHANGE",
    12: "GREETING",
    13: "INFORM_INFO",
    14: "NOISE",
    15: "ORDER_PRODUCT",
    16: "TRACK_ORDER"
}

# Entity labels for GLiNER
ENTITY_LABELS = [
    "product",
    "color",
    "size",
    "address",
    "quantity",
    "client_name",
    "phone_number"
]

# Confidence thresholds
INTENT_CONFIDENCE_THRESHOLD = 0.5
ENTITY_CONFIDENCE_THRESHOLD = 0.6

# API settings
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8001"))
