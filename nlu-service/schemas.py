"""
Pydantic models for API request/response validation
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class MessageRequest(BaseModel):
    """Request model for NLU prediction"""
    message: str = Field(..., min_length=1, description="User message in Tunisian dialect")
    threshold: Optional[float] = Field(0.6, ge=0.0, le=1.0, description="Confidence threshold for entity extraction")
    labels: Optional[List[str]] = Field(None, description="Custom entity labels to extract")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "bech nechri t-shirt ahmar size L",
                "threshold": 0.6,
                "labels": ["product", "color", "size"]
            }
        }


class IntentPrediction(BaseModel):
    """Intent classification result"""
    intent: str = Field(..., description="Predicted intent label")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    
    class Config:
        json_schema_extra = {
            "example": {
                "intent": "order_product",
                "confidence": 0.95
            }
        }


class Entity(BaseModel):
    """Extracted entity"""
    text: str = Field(..., description="Entity text")
    label: str = Field(..., description="Entity type/label")
    score: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    start: int = Field(..., ge=0, description="Start position in text")
    end: int = Field(..., ge=0, description="End position in text")
    
    class Config:
        json_schema_extra = {
            "example": {
                "text": "t-shirt",
                "label": "product",
                "score": 0.92,
                "start": 12,
                "end": 19
            }
        }


class NLUResponse(BaseModel):
    """Complete NLU prediction response"""
    intent: IntentPrediction
    entities: List[Entity]
    original_message: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "intent": {
                    "intent": "order_product",
                    "confidence": 0.95
                },
                "entities": [
                    {
                        "text": "t-shirt",
                        "label": "product",
                        "score": 0.92,
                        "start": 12,
                        "end": 19
                    },
                    {
                        "text": "ahmar",
                        "label": "color",
                        "score": 0.88,
                        "start": 20,
                        "end": 25
                    }
                ],
                "original_message": "bech nechri t-shirt ahmar"
            }
        }


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    models_loaded: bool
    tunbert_loaded: bool
    gliner_loaded: bool
