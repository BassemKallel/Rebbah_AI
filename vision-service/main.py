import io
import requests
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from PIL import Image
import torch
import psycopg2
from pgvector.psycopg2 import register_vector
import os
from transformers import CLIPProcessor, CLIPModel

# Global model instances
processor = None
model = None
model_name = "openai/clip-vit-base-patch32"
device = "cuda" if torch.cuda.is_available() else "cpu"

@asynccontextmanager
async def lifespan(app: FastAPI):
    global processor, model
    print(f"Loading CLIP model: {model_name} on {device}")
    processor = CLIPProcessor.from_pretrained(model_name)
    model = CLIPModel.from_pretrained(model_name, torch_dtype=torch.float32).to(device)
    model.eval()
    print("CLIP model loaded successfully!")
    yield
    print("Shutting down vision service...")

app = FastAPI(title="TikTak Vision Service", lifespan=lifespan)

from typing import Optional

class ImageRequest(BaseModel):
    image_url: str
    limit: int = 5
    product_id: Optional[str] = None
    variation_id: Optional[str] = None   # ID de la déclinaison exacte (couleur/taille)
    shop_id: Optional[str] = None
    store_image_url: Optional[str] = None  # URL Azure Blob à stocker en DB

# Database connection helper
def get_db_connection():
    conn = psycopg2.connect(
        host=os.getenv("VECTOR_DB_HOST", "vector-db"),
        port=os.getenv("VECTOR_DB_PORT", "5432"),
        dbname=os.getenv("VECTOR_DB_NAME", "tiktak_vectors"),
        user=os.getenv("VECTOR_DB_USER", "tiktak_vector"),
        password=os.getenv("VECTOR_DB_PASSWORD", "vector_pass")
    )
    register_vector(conn)
    return conn

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "vision-service"}

@app.post("/vectorize")
async def predict_embedding(request: ImageRequest):
    try:
        # 1. Download image
        response = requests.get(request.image_url, stream=True)
        response.raise_for_status()
        image = Image.open(io.BytesIO(response.content)).convert("RGB")

        # 2. Extract embedding
        inputs = processor(images=image, return_tensors="pt").to(device)
        with torch.no_grad():
            # Use vision_model directly for transformers 5.x compatibility
            pixel_values = inputs.get("pixel_values")
            vision_outputs = model.vision_model(pixel_values=pixel_values)
            image_features = vision_outputs.pooler_output
            # Project through the visual projection layer
            image_features = model.visual_projection(image_features)
        
        # 3. Normalize & convert to list
        image_features = image_features / image_features.norm(p=2, dim=-1, keepdim=True)
        embedding = image_features.squeeze().cpu().tolist()

        status_msg = "success"

        # 4. Optional: Save to database if product details are provided
        if request.product_id and request.shop_id:
            try:
                conn = get_db_connection()
                cur = conn.cursor()
                
                # Check if table exists, if not, create it (basic setup logic for POC)
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS products_vector (
                        id SERIAL PRIMARY KEY,
                        product_id   VARCHAR(255) NOT NULL,
                        variation_id VARCHAR(255) NOT NULL,
                        shop_id      VARCHAR(255) NOT NULL,
                        image_url    TEXT,
                        embedding    vector(512),
                        UNIQUE(variation_id, shop_id)
                    );
                """)

                # Upsert the embedding — one row per variation
                cur.execute("""
                    INSERT INTO products_vector (product_id, variation_id, shop_id, image_url, embedding)
                    VALUES (%s, %s, %s, %s, %s::vector)
                    ON CONFLICT (variation_id, shop_id)
                    DO UPDATE SET
                        embedding  = EXCLUDED.embedding,
                        image_url  = EXCLUDED.image_url;
                """, (request.product_id, request.variation_id, request.shop_id, request.store_image_url, embedding))
                
                conn.commit()
                cur.close()
                conn.close()
                status_msg = "success (saved to db)"
                
            except psycopg2.Error as db_e:
                status_msg = f"success but failed to save to db: {str(db_e)}"

        return {
            "status": status_msg,
            "embedding": embedding,
            "dimensions": len(embedding)
        }
        
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch image: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@app.post("/search-similar")
async def search_similar_products(request: ImageRequest):
    try:
        # 1. Download image
        response = requests.get(request.image_url, stream=True)
        response.raise_for_status()
        image = Image.open(io.BytesIO(response.content)).convert("RGB")

        # 2. Extract embedding
        inputs = processor(images=image, return_tensors="pt").to(device)
        with torch.no_grad():
            pixel_values = inputs.get("pixel_values")
            vision_outputs = model.vision_model(pixel_values=pixel_values)
            image_features = vision_outputs.pooler_output
            image_features = model.visual_projection(image_features)
        
        # 3. Normalize & convert to list
        image_features = image_features / image_features.norm(p=2, dim=-1, keepdim=True)
        embedding = image_features.squeeze().cpu().tolist()

        # 4. Search in pgvector database
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Uses cosine distance (<=>) for similarity
        # Filter by shop_id if provided (multi-tenant isolation)
        if request.shop_id:
            cur.execute(
                """
                SELECT product_id, variation_id, shop_id, image_url,
                       1 - (embedding <=> %s::vector) AS similarity
                FROM products_vector
                WHERE shop_id = %s
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (embedding, request.shop_id, embedding, request.limit)
            )
        else:
            cur.execute(
                """
                SELECT product_id, variation_id, shop_id, image_url,
                       1 - (embedding <=> %s::vector) AS similarity
                FROM products_vector
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (embedding, embedding, request.limit)
            )

        results = []
        for row in cur.fetchall():
            results.append({
                "product_id":    row[0],
                "variation_id":  row[1],
                "shop_id":       row[2],
                "image_url":     row[3],
                "similarity_score": float(row[4])
            })
            
        cur.close()
        conn.close()

        return {
            "status": "success",
            "results": results
        }
        
    except psycopg2.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch image: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
