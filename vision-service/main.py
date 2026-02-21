import io
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from PIL import Image
import torch
import psycopg2
from pgvector.psycopg2 import register_vector
import os
from transformers import CLIPProcessor, CLIPModel

app = FastAPI(title="TikTak Vision Service")

# Load model (using CLIP as a solid default for image embeddings / similarity)
model_name = "openai/clip-vit-base-patch32"
processor = CLIPProcessor.from_pretrained(model_name)
model = CLIPModel.from_pretrained(model_name)

from typing import Optional

class ImageRequest(BaseModel):
    image_url: str
    limit: int = 5
    product_id: Optional[str] = None
    shop_id: Optional[str] = None

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
        inputs = processor(images=image, return_tensors="pt")
        with torch.no_grad():
            image_features = model.get_image_features(**inputs)
        
        # 3. Normalize & convert to list
        image_features = image_features / image_features.norm(p=2, dim=-1, keepdim=True)
        embedding = image_features.squeeze().tolist()

        status_msg = "success"

        # 4. Optional: Save to database if product details are provided
        if request.product_id and request.shop_id:
            try:
                conn = get_db_connection()
                cur = conn.cursor()
                
                # Check if table exists, if not, create it (basic setup logic for POC)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS products_vector (
                        id SERIAL PRIMARY KEY,
                        product_id VARCHAR(255) NOT NULL,
                        shop_id VARCHAR(255) NOT NULL,
                        embedding vector(512),
                        UNIQUE(product_id, shop_id)
                    );
                """)
                
                # Upsert the embedding
                cur.execute("""
                    INSERT INTO products_vector (product_id, shop_id, embedding)
                    VALUES (%s, %s, %s::vector)
                    ON CONFLICT (product_id, shop_id) 
                    DO UPDATE SET 
                        embedding = EXCLUDED.embedding;
                """, (request.product_id, request.shop_id, embedding))
                
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
        inputs = processor(images=image, return_tensors="pt")
        with torch.no_grad():
            image_features = model.get_image_features(**inputs)
        
        # 3. Normalize & convert to list
        image_features = image_features / image_features.norm(p=2, dim=-1, keepdim=True)
        embedding = image_features.squeeze().tolist()

        # 4. Search in pgvector database
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Uses cosine distance (<=>) for similarity
        cur.execute(
            """
            SELECT product_id, shop_id, 1 - (embedding <=> %s::vector) AS similarity
            FROM products_vector
            ORDER BY embedding <=> %s::vector
            LIMIT %s
            """,
            (embedding, embedding, request.limit)
        )
        
        results = []
        for row in cur.fetchall():
            results.append({
                "product_id": row[0],
                "shop_id": row[1],
                "similarity_score": float(row[2])
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
