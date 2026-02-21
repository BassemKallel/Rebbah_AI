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
from schemas import MessageRequest, NLUResponse, IntentPrediction, Entity, HealthResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global model instances
tunbert_model = None
tunbert_tokenizer = None
gliner_model = None
device = None


def load_models():
    """Load TunBERT and GLiNER models at startup"""
    global tunbert_model, tunbert_tokenizer, gliner_model, device
    
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
    """Manage application lifespan - load models on startup, cleanup on shutdown"""
    load_models()
    yield
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
        text: Input message
        
    Returns:
        IntentPrediction with intent label and confidence
    """
    try:
        # Tokenize input
        inputs = tunbert_tokenizer(
            text,
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
        intent_label = INTENT_LABELS.get(predicted_class, "unknown")
        
        return IntentPrediction(
            intent=intent_label,
            confidence=confidence
        )
        
    except Exception as e:
        logger.error(f"Error in intent prediction: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Intent prediction failed: {str(e)}")


def extract_entities(text: str, labels: Optional[list] = None, threshold: float = ENTITY_CONFIDENCE_THRESHOLD) -> list[Entity]:
    """
    Extract entities using GLiNER model
    
    Args:
        text: Input message
        labels: Entity labels to extract (uses default if None)
        threshold: Confidence threshold for entity extraction
        
    Returns:
        List of extracted entities
    """
    try:
        # Use provided labels or default
        entity_labels = labels if labels else ENTITY_LABELS
        
        # Predict entities
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
    2. Entity extraction using GLiNER
    
    Args:
        request: MessageRequest with message text and optional parameters
        
    Returns:
        NLUResponse with intent and entities
    """
    try:
        # Validate models are loaded
        if tunbert_model is None or gliner_model is None:
            raise HTTPException(status_code=503, detail="Models not loaded")
        
        # Get intent prediction
        intent = predict_intent(request.message)
        
        # Determine if we should extract entities based on the intent
        # Extract entities ONLY IF the intent is ORDER_PRODUCT or INFORM_INFO
        allowed_intents_for_extraction = ["ORDER_PRODUCT", "INFORM_INFO"]
        entities = []
        
        if intent.intent in allowed_intents_for_extraction:
            entities = extract_entities(
                request.message,
                labels=request.labels,
                threshold=request.threshold
            )
        
        # Return combined response
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
