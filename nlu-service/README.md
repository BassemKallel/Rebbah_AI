# NLU Service

Natural Language Understanding service for Tunisian dialect e-commerce messages.

## Features

- **Intent Classification**: Uses TunBERT to classify user intents (15 intents supported)
  - `ASK_ADVICE` - User asking for advice/recommendations
  - `ASK_AVAILABILITY` - Checking product availability
  - `ASK_DELIVERY` - Questions about delivery
  - `ASK_DETAILS` - Asking for product details
  - `ASK_DISCOUNT` - Inquiring about discounts
  - `ASK_LOCATION` - Asking about store location
  - `ASK_PRICE` - Price inquiries
  - `CANCEL_ORDER` - Order cancellation
  - `COMPLAINT` - Customer complaints
  - `CONFIRM_DENY` - Confirmation or denial
  - `GREETING` - Greetings
  - `INFORM_INFO` - Providing information
  - `NOISE` - Irrelevant/noise messages
  - `ORDER_PRODUCT` - Product ordering
  - `TRACK_ORDER` - Order tracking

- **Entity Extraction**: Uses GLiNER to extract entities
  - `product` - Product names
  - `color` - Colors
  - `size` - Sizes
  - `brand` - Brand names
  - `client_name` - Customer names
  - `phone_number` - Phone numbers
  - `address` - Addresses

## Installation

```bash
pip install -r requirements.txt
```

## Running the Service

```bash
# Development mode with auto-reload
uvicorn main:app --reload --host 0.0.0.0 --port 8001

# Production mode
uvicorn main:app --host 0.0.0.0 --port 8001 --workers 4
```

## API Endpoints

### Health Check
```bash
GET /health
```

### Predict Intent and Entities
```bash
POST /predict
Content-Type: application/json

{
  "message": "bech nechri t-shirt ahmar size L",
  "threshold": 0.6,
  "labels": ["product", "color", "size"]
}
```

**Response:**
```json
{
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
    },
    {
      "text": "L",
      "label": "size",
      "score": 0.85,
      "start": 31,
      "end": 32
    }
  ],
  "original_message": "bech nechri t-shirt ahmar size L"
}
```

## Testing

Run the test script:
```bash
python test_api.py
```

## API Documentation

Interactive API documentation available at:
- Swagger UI: `http://localhost:8001/docs`
- ReDoc: `http://localhost:8001/redoc`
