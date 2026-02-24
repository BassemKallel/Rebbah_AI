"""
Test script for NLU Service API
Tests intent classification and entity extraction endpoints
"""
import requests
import json
from typing import Dict, Any


# API base URL
BASE_URL = "http://localhost:8001"


def print_response(title: str, response: Dict[Any, Any]):
    """Pretty print API response"""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")
    print(json.dumps(response, indent=2, ensure_ascii=False))
    print(f"{'='*60}\n")


def test_health():
    """Test health check endpoint"""
    print("\n🏥 Testing Health Check Endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        response.raise_for_status()
        print_response("Health Check Response", response.json())
        return True
    except Exception as e:
        print(f"❌ Health check failed: {str(e)}")
        return False


def test_predict(message: str, threshold: float = 0.6, labels: list = None):
    """Test prediction endpoint"""
    print(f"\n🔮 Testing Prediction for: '{message}'")
    
    payload = {
        "message": message,
        "threshold": threshold
    }
    
    if labels:
        payload["labels"] = labels
    
    try:
        response = requests.post(
            f"{BASE_URL}/predict",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        print_response(f"Prediction Response", response.json())
        return True
    except Exception as e:
        print(f"❌ Prediction failed: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}")
        return False


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("🚀 Starting NLU Service API Tests")
    print("="*60)
    
    # Test 1: Health check
    if not test_health():
        print("\n❌ Service is not healthy. Make sure the API is running.")
        print("Start the API with: uvicorn main:app --reload --host 0.0.0.0 --port 8001")
        return
    
    print("\n✅ Service is healthy!")
    
    # Test 2: ORDER_PRODUCT intent
    test_predict(
        message="bech nechri t-shirt ahmar size L",
        labels=["product", "color", "size"]
    )
    
    # Test 3: ASK_PRICE intent
    test_predict(
        message="b9adech el pantalon?",
        labels=["product"]
    )
    
    # Test 4: ASK_AVAILABILITY intent
    test_predict(
        message="3andkom size M fel jeans?",
        labels=["size", "product"]
    )
    
    # Test 5: INFORM_INFO - Customer information
    test_predict(
        message="maryem slama 50152515 sidi ameur, sahline",
        threshold=0.6,
        labels=["client_name", "phone_number", "address"]
    )
    
    # Test 6: ORDER_PRODUCT with brand
    test_predict(
        message="nheb nechri Nike shoes size 42",
        labels=["brand", "product", "size"]
    )
    
    # Test 7: GREETING
    test_predict(
        message="salam, kifech?",
        labels=[]
    )
    
    # Test 8: ASK_DELIVERY
    test_predict(
        message="wakt el livraison 9adech?",
        labels=[]
    )
    
    # Test 9: ASK_DISCOUNT
    test_predict(
        message="3andkom promo 3al jeans?",
        labels=["product"]
    )

    
    print("\n" + "="*60)
    print("✅ All tests completed!")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
