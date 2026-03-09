"""
NLU Service - FastAPI application for intent classification and entity extraction
Uses TunBERT for intent classification and GLiNER for entity extraction
"""
import logging
from contextlib import asynccontextmanager
from typing import Optional

import torch
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from gliner import GLiNER

from config import (
    TUNBERT_MODEL_PATH,
    GLINER_MODEL_PATH,
    INTENT_LABELS,
    ENTITY_LABELS,
    INTENT_CONFIDENCE_THRESHOLD,
    ENTITY_CONFIDENCE_THRESHOLD,
)
from anonymization import anonymize_message
from schemas import MessageRequest, NLUResponse, IntentPrediction, Entity, HealthResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Intents that require entity extraction
INTENTS_REQUIRING_ENTITIES = {
    "ORDER_PRODUCT",
    "ASK_AVAILABILITY",
    "ASK_PRICE",
    "INFORM_INFO"
}

# Global model instances
tunbert_model = None
tunbert_tokenizer = None
gliner_model = None
device = None
models_loaded = False


def load_models():
    """Load TunBERT and GLiNER models on first request (lazy loading)"""
    global tunbert_model, tunbert_tokenizer, gliner_model, device, models_loaded
    
    if models_loaded:
        return  # Already loaded, skip
    
    try:
        # Determine device
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"Using device: {device}")
        
        # Load TunBERT for intent classification
        logger.info(f"Loading TunBERT model from {TUNBERT_MODEL_PATH}")
        tunbert_tokenizer = AutoTokenizer.from_pretrained(str(TUNBERT_MODEL_PATH))
        tunbert_model = AutoModelForSequenceClassification.from_pretrained(
            str(TUNBERT_MODEL_PATH)
        )
        tunbert_model.to(device)
        tunbert_model.eval()
        logger.info("TunBERT model loaded successfully")
        
        # Load GLiNER for entity extraction
        logger.info(f"Loading GLiNER model from {GLINER_MODEL_PATH}")
        gliner_model = GLiNER.from_pretrained(str(GLINER_MODEL_PATH))
        gliner_model.to(device)
        gliner_model.eval()
        logger.info("GLiNER model loaded successfully")
        
        models_loaded = True
        logger.info("All models loaded successfully!")
        
    except Exception as e:
        logger.error(f"Error loading models: {str(e)}")
        raise


def unload_models():
    """Cleanup models on shutdown"""
    global tunbert_model, tunbert_tokenizer, gliner_model
    
    logger.info("Unloading models...")
    tunbert_model = None
    tunbert_tokenizer = None
    gliner_model = None
    
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    
    logger.info("Models unloaded")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - models loaded on first request (lazy loading)"""
    logger.info("NLU Service starting... Models will be loaded on first request")
    yield
    logger.info("Unloading models...")
    unload_models()


# Initialize FastAPI app
app = FastAPI(
    title="TikTak NLU Service",
    description="Natural Language Understanding service for Tunisian dialect e-commerce",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def predict_intent(text: str) -> IntentPrediction:
    """
    Predict intent using TunBERT model
    
    Args:
        text: Input message (will be anonymized before TunBERT)
        
    Returns:
        IntentPrediction with intent label and confidence
    """
    try:
        # Anonymize text before TunBERT (model was trained with __phone__ and __address__ tokens)
        anonymized_text = anonymize_message(text)
        
        # Tokenize anonymized input
        inputs = tunbert_tokenizer(
            anonymized_text,
            return_tensors="pt",
            truncation=True,
            max_length=128,
            padding=True
        )
        inputs = {k: v.to(device) for k, v in inputs.items()}
        
        # Get prediction
        with torch.no_grad():
            outputs = tunbert_model(**inputs)
            logits = outputs.logits
            probabilities = torch.softmax(logits, dim=-1)
            predicted_class = torch.argmax(probabilities, dim=-1).item()
            confidence = probabilities[0][predicted_class].item()
        
        # Map to intent label
        intent_label = INTENT_LABELS.get(predicted_class, f"unknown_class_{predicted_class}")
        
        return IntentPrediction(
            intent=intent_label,
            confidence=confidence
        )
        
    except Exception as e:
        logger.error(f"Error in intent prediction: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Intent prediction failed: {str(e)}")


def extract_entities(text: str, labels: Optional[list] = None, threshold: float = ENTITY_CONFIDENCE_THRESHOLD) -> list[Entity]:
    """
    Extract entities using GLiNER model.
    
    NOTE: GLiNER was trained on anonymized data (__phone__, __address__ tokens).
    To maintain extraction accuracy:
    1. Anonymize the text before GLiNER
    2. GLiNER extracts from anonymized text
    3. Map results back to original text where needed
    
    Args:
        text: Input message (original, non-anonymized)
        labels: Entity labels to extract (uses default if None)
        threshold: Confidence threshold for entity extraction
        
    Returns:
        List of extracted entities with original (non-anonymized) values
    """
    try:
        # Use provided labels or default
        entity_labels = labels if labels else ENTITY_LABELS
        
        # GLiNER was trained on REAL data (real addresses like "Mourouj", "Manzah", real phone numbers)
        # So we pass the ORIGINAL text directly — no anonymization needed here
        entities_raw = gliner_model.predict_entities(
            text,
            entity_labels,
            threshold=threshold
        )
        
        # Convert to Entity schema
        entities = []
        for ent in entities_raw:
            entities.append(Entity(
                text=ent["text"],
                label=ent["label"],
                score=ent["score"],
                start=ent["start"],
                end=ent["end"]
            ))
        
        return entities
        
    except Exception as e:
        logger.error(f"Error in entity extraction: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Entity extraction failed: {str(e)}")


@app.get("/", tags=["Info"])
async def root():
    """Service information endpoint"""
    return {
        "service": "TikTak NLU Service",
        "version": "1.0.0",
        "description": "Intent classification and entity extraction for Tunisian dialect",
        "endpoints": {
            "predict": "/predict",
            "health": "/health",
            "docs": "/docs"
        }
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint"""
    tunbert_loaded = tunbert_model is not None and tunbert_tokenizer is not None
    gliner_loaded = gliner_model is not None
    models_loaded = tunbert_loaded and gliner_loaded
    
    return HealthResponse(
        status="healthy" if models_loaded else "unhealthy",
        models_loaded=models_loaded,
        tunbert_loaded=tunbert_loaded,
        gliner_loaded=gliner_loaded
    )


@app.post("/predict", response_model=NLUResponse, tags=["NLU"])
async def predict(request: MessageRequest):
    """
    Main NLU prediction endpoint
    
    Performs:
    1. Intent classification using TunBERT
    2. Entity extraction using GLiNER (only for intents that require it)
    
    Args:
        request: MessageRequest with message text and optional parameters
        
    Returns:
        NLUResponse with intent and entities
    """
    try:
        # Lazy load models on first request
        load_models()
        
        # Get intent prediction (with anonymized text for TunBERT)
        intent = predict_intent(request.message)
        
        # Extract entities only for intents that require them
        # GLiNER receives the ORIGINAL message (not anonymized) to extract real phone/address values
        entities = []
        if intent.intent in INTENTS_REQUIRING_ENTITIES:
            entities = extract_entities(
                request.message,  # Original message, NOT anonymized
                labels=request.labels,
                threshold=request.threshold
            )
        
        # Return combined response with original message
        return NLUResponse(
            intent=intent,
            entities=entities,
            original_message=request.message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in prediction: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    from config import API_HOST, API_PORT
    
    uvicorn.run(
        "main:app",
        host=API_HOST,
        port=API_PORT,
        reload=True
    )
