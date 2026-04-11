"""
TikTak Vision Service — CLIP-based image search with pgvector

Optimizations applied:
- _embed_image() reused across all endpoints (no code duplication)
- _search_similar_db() shared SQL helper
- Connection pool with context manager (no connection leaks)
- DB initialization at startup (CREATE TABLE + HNSW index)
- httpx async for non-blocking image downloads
"""
import io
from contextlib import asynccontextmanager, contextmanager

import httpx
import psycopg2
from psycopg2.pool import SimpleConnectionPool
from pgvector.psycopg2 import register_vector
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from PIL import Image
import torch
from transformers import CLIPProcessor, CLIPModel
import os
import logging
from typing import Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# Ensure logs reach stdout even when uvicorn overrides root logger
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)

# Global instances
processor = None
model = None
db_pool = None
model_name = "openai/clip-vit-base-patch32"
device = "cuda" if torch.cuda.is_available() else "cpu"

# Minimum cosine similarity score to consider a result as a valid match.
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.7"))


# ── Database ──────────────────────────────────────────────────────────────────

_REQUIRED_DB_ENV_VARS = [
    "VECTOR_DB_HOST",
    "VECTOR_DB_NAME",
    "VECTOR_DB_USER",
    "VECTOR_DB_PASSWORD",
]


def _validate_db_env() -> None:
    """Fail fast at startup if any required DB env vars are missing."""
    missing = [var for var in _REQUIRED_DB_ENV_VARS if not os.getenv(var)]
    if missing:
        raise EnvironmentError(
            f"[vision-service] Missing required environment variables: {', '.join(missing)}. "
            "Set them in your .env file before starting the service."
        )


def _create_db_pool() -> SimpleConnectionPool:
    """Create a connection pool at startup.

    All connection parameters MUST be provided via environment variables.
    No credential defaults — the service will refuse to start if they are missing.
    """
    _validate_db_env()
    return SimpleConnectionPool(
        minconn=2,
        maxconn=10,
        host=os.getenv("VECTOR_DB_HOST"),
        port=os.getenv("VECTOR_DB_PORT", "5432"),
        dbname=os.getenv("VECTOR_DB_NAME"),
        user=os.getenv("VECTOR_DB_USER"),
        password=os.getenv("VECTOR_DB_PASSWORD"),
    )


@contextmanager
def get_db_connection():
    """Context manager — always returns connection to pool, even on error."""
    conn = db_pool.getconn()
    register_vector(conn)
    try:
        yield conn
    finally:
        db_pool.putconn(conn)


def _init_database():
    """Create table + HNSW index at startup (runs once)."""
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS products_vector (
                id SERIAL PRIMARY KEY,
                product_id   VARCHAR(255) NOT NULL,
                variation_id VARCHAR(255) NOT NULL,
                shop_id      VARCHAR(255) NOT NULL,
                image_url    TEXT,
                embedding    vector(512),
                created_at   TIMESTAMP DEFAULT NOW(),
                UNIQUE(variation_id, shop_id)
            );
        """)
        # Add created_at column if table already exists without it
        cur.execute("""
            DO $$ BEGIN
                ALTER TABLE products_vector ADD COLUMN created_at TIMESTAMP DEFAULT NOW();
            EXCEPTION WHEN duplicate_column THEN NULL;
            END $$;
        """)
        # HNSW index for fast cosine similarity search (O(log n) instead of O(n))
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_products_vector_embedding
                ON products_vector
                USING hnsw (embedding vector_cosine_ops)
                WITH (m = 16, ef_construction = 64);
        """)
        conn.commit()
        cur.close()
    logger.info("[DB] Table and HNSW index initialized.")


# ── CLIP Embedding ────────────────────────────────────────────────────────────

def _embed_image(image: Image.Image) -> list:
    """Compute normalized CLIP embedding for a PIL image."""
    inputs = processor(images=image, return_tensors="pt").to(device)
    with torch.no_grad():
        pixel_values = inputs.get("pixel_values")
        vision_outputs = model.vision_model(pixel_values=pixel_values)
        image_features = vision_outputs.pooler_output
        image_features = model.visual_projection(image_features)
    image_features = image_features / image_features.norm(p=2, dim=-1, keepdim=True)
    return image_features.squeeze().cpu().tolist()


async def _download_and_embed(image_url: str) -> list:
    """Download image async + compute embedding."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(image_url)
        response.raise_for_status()
    image = Image.open(io.BytesIO(response.content)).convert("RGB")
    return _embed_image(image), image


# ── Database Search ───────────────────────────────────────────────────────────

def _search_similar_db(embedding: list, shop_id: str = None, limit: int = 5) -> list:
    """Search pgvector for similar product embeddings."""
    with get_db_connection() as conn:
        cur = conn.cursor()
        if shop_id:
            cur.execute(
                """
                SELECT product_id, variation_id, shop_id, image_url,
                       1 - (embedding <=> %s::vector) AS similarity
                FROM products_vector
                WHERE shop_id = %s
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (embedding, shop_id, embedding, limit),
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
                (embedding, embedding, limit),
            )

        results = []
        all_scores = []
        for row in cur.fetchall():
            score = float(row[4])
            product_id = row[0]
            variation_id = row[1]
            passed = score >= SIMILARITY_THRESHOLD

            all_scores.append({
                "product_id": product_id,
                "variation_id": variation_id,
                "score": score,
                "passed": passed,
            })

            if passed:
                results.append({
                    "product_id":       product_id,
                    "variation_id":     variation_id,
                    "shop_id":          row[2],
                    "image_url":        row[3],
                    "similarity_score": score,
                })

        # ── Detailed similarity logs for threshold tuning ─────────────────
        logger.info(
            f"[VISION-SEARCH] shop_id={shop_id} | threshold={SIMILARITY_THRESHOLD} | "
            f"candidates={len(all_scores)} | matches={len(results)}"
        )
        for i, s in enumerate(all_scores):
            marker = "✅ MATCH" if s["passed"] else "❌ BELOW"
            logger.info(
                f"[VISION-SEARCH]   #{i+1} {marker} | "
                f"score={s['score']:.4f} | "
                f"product_id={s['product_id']} | "
                f"variation_id={s['variation_id']}"
            )
        if not all_scores:
            logger.warning(f"[VISION-SEARCH] No embeddings found in DB for shop_id={shop_id}")

        cur.close()
    return results


# ── App Lifespan ──────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    global processor, model, db_pool
    # Load CLIP model
    logger.info(f"Loading CLIP model: {model_name} on {device}")
    processor = CLIPProcessor.from_pretrained(model_name)
    model = CLIPModel.from_pretrained(model_name, torch_dtype=torch.float32).to(device)
    model.eval()
    logger.info("CLIP model loaded successfully!")

    # Initialize DB pool + schema
    db_pool = _create_db_pool()
    _init_database()

    yield

    # Cleanup
    logger.info("Shutting down vision service...")
    if db_pool:
        db_pool.closeall()


app = FastAPI(title="TikTak Vision Service", lifespan=lifespan)


# ── Schemas ───────────────────────────────────────────────────────────────────

class ImageRequest(BaseModel):
    image_url: str
    limit: int = 5
    product_id: Optional[str] = None
    variation_id: Optional[str] = None
    shop_id: Optional[str] = None
    store_image_url: Optional[str] = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "vision-service", "device": device}


@app.post("/vectorize")
async def predict_embedding(request: ImageRequest):
    """Extract CLIP embedding from image URL and optionally save to DB."""
    try:
        embedding, _ = await _download_and_embed(request.image_url)
        status_msg = "success"

        # Save to database if product details provided
        if request.product_id and request.shop_id:
            try:
                with get_db_connection() as conn:
                    cur = conn.cursor()
                    cur.execute(
                        """
                        INSERT INTO products_vector (product_id, variation_id, shop_id, image_url, embedding, created_at)
                        VALUES (%s, %s, %s, %s, %s::vector, NOW())
                        ON CONFLICT (variation_id, shop_id)
                        DO UPDATE SET embedding = EXCLUDED.embedding, image_url = EXCLUDED.image_url, created_at = NOW();
                        """,
                        (request.product_id, request.variation_id, request.shop_id,
                         request.store_image_url, embedding),
                    )
                    conn.commit()
                    cur.close()
                status_msg = "success (saved to db)"
            except psycopg2.Error as db_e:
                status_msg = f"success but failed to save to db: {str(db_e)}"

        return {"status": status_msg, "embedding": embedding, "dimensions": len(embedding)}

    except httpx.HTTPError as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch image: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.post("/search-similar")
async def search_similar_products(request: ImageRequest):
    """Search for similar products by image URL."""
    try:
        embedding, _ = await _download_and_embed(request.image_url)
        results = _search_similar_db(embedding, request.shop_id, request.limit)

        return {
            "status": "success",
            "results": results,
            "threshold": SIMILARITY_THRESHOLD,
            "total_matches": len(results),
        }

    except psycopg2.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except httpx.HTTPError as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch image: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.post("/search-similar-upload")
async def search_similar_upload(
    image: UploadFile = File(...),
    shop_id: str = Form(None),
    limit: int = Form(5),
):
    """Search for similar products by uploaded image file."""
    try:
        contents = await image.read()
        pil_image = Image.open(io.BytesIO(contents)).convert("RGB")
        embedding = _embed_image(pil_image)
        results = _search_similar_db(embedding, shop_id, limit)

        return {
            "status": "success",
            "results": results,
            "threshold": SIMILARITY_THRESHOLD,
            "total_matches": len(results),
        }

    except psycopg2.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}") 
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.delete("/vectors/")
def clear_vectors(shop_id: Optional[str] = None):
    """
    Delete vectors from the DB.
    - shop_id provided → delete only that shop's vectors
    - no shop_id       → delete ALL vectors (full reset)
    """
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            if shop_id:
                cur.execute(
                    "DELETE FROM products_vector WHERE shop_id = %s RETURNING id;",
                    (shop_id,),
                )
            else:
                cur.execute("DELETE FROM products_vector RETURNING id;")
            deleted = cur.rowcount
            conn.commit()
            cur.close()

        scope = f"shop_id={shop_id}" if shop_id else "ALL shops"
        logger.info(f"[VECTORS] Cleared {deleted} vectors ({scope})")
        return {"status": "success", "deleted": deleted, "scope": scope}

    except psycopg2.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.get("/vectors/stats/")
def vectors_stats(shop_id: Optional[str] = None):
    """
    Return count of vectors in DB, optionally filtered by shop_id.
    Used by Django admin to display current state.
    """
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            if shop_id:
                cur.execute(
                    "SELECT COUNT(*) FROM products_vector WHERE shop_id = %s;",
                    (shop_id,),
                )
            else:
                cur.execute(
                    "SELECT shop_id, COUNT(*) FROM products_vector GROUP BY shop_id ORDER BY shop_id;"
                )
                rows = cur.fetchall()
                cur.close()
                return {
                    "status": "success",
                    "shops": [{"shop_id": r[0], "count": r[1]} for r in rows],
                    "total": sum(r[1] for r in rows),
                }
            count = cur.fetchone()[0]
            cur.close()
        return {"status": "success", "shop_id": shop_id, "count": count}

    except psycopg2.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
