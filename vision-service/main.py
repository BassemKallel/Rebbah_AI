"""
TikTak Vision Service — CLIP-based Image-to-Image search with pgvector

Architecture:
- Pure Image-to-Image similarity search (Visual RAG)
- Text search has been removed: catalogue is injected directly in the LLM prompt
- _embed_image() shared across all endpoints (no code duplication)
- _search_similar_db() shared SQL helper with configurable threshold
- Connection pool with context manager (no connection leaks)
- DB initialized at startup: CREATE TABLE crm_itemvector + HNSW index
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
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.75"))


# ── Database ──────────────────────────────────────────────────────────────────

def _create_db_pool() -> SimpleConnectionPool:
    """Create a connection pool at startup."""
    return SimpleConnectionPool(
        minconn=2,
        maxconn=10,
        host=os.getenv("VECTOR_DB_HOST", "vector-db"),
        port=os.getenv("VECTOR_DB_PORT", "5432"),
        dbname=os.getenv("VECTOR_DB_NAME", "tiktak_vectors"),
        user=os.getenv("VECTOR_DB_USER", "tiktak_vector"),
        password=os.getenv("VECTOR_DB_PASSWORD", "vector_pass"),
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
            CREATE TABLE IF NOT EXISTS crm_itemvector (
                id SERIAL PRIMARY KEY,
                item_id      VARCHAR(255) NOT NULL,
                shop_id      VARCHAR(255) NOT NULL,
                image_url    TEXT,
                metadata     JSONB,
                embedding    vector(512),
                created_at   TIMESTAMP DEFAULT NOW(),
                UNIQUE(item_id, image_url, shop_id)
            );
        """)
        # HNSW index for fast cosine similarity search (O(log n) instead of O(n))
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_crm_itemvector_embedding
                ON crm_itemvector
                USING hnsw (embedding vector_cosine_ops)
                WITH (m = 16, ef_construction = 64);
        """)
        conn.commit()
        cur.close()
    logger.info("[DB] Table crm_itemvector and HNSW index initialized.")


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



async def _download_and_embed(image_url: str) -> tuple[list, Image.Image]:
    """Download image async + compute embedding."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(image_url)
        response.raise_for_status()
    image = Image.open(io.BytesIO(response.content)).convert("RGB")
    return _embed_image(image), image


# ── Database Search ───────────────────────────────────────────────────────────

def _search_similar_db(embedding: list, shop_id: str = None, limit: int = 5, threshold: float = SIMILARITY_THRESHOLD) -> list:
    """Search pgvector for similar item embeddings."""
    with get_db_connection() as conn:
        cur = conn.cursor()
        if shop_id:
            cur.execute(
                """
                SELECT item_id, shop_id, image_url, metadata,
                       1 - (embedding <=> %s::vector) AS similarity
                FROM crm_itemvector
                WHERE shop_id = %s
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (embedding, shop_id, embedding, limit),
            )
        else:
            cur.execute(
                """
                SELECT item_id, shop_id, image_url, metadata,
                       1 - (embedding <=> %s::vector) AS similarity
                FROM crm_itemvector
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (embedding, embedding, limit),
            )

        results = []
        all_scores = []
        for row in cur.fetchall():
            score = float(row[4])
            item_id = row[0]
            passed = score >= threshold

            all_scores.append({
                "item_id": item_id,
                "score": score,
                "passed": passed,
            })

            results.append({
                "item_id":          item_id,
                "shop_id":          row[1],
                "image_url":        row[2],
                "metadata":         row[3] if row[3] else {},
                "similarity_score": score,
                "is_exact_match":   passed,
            })

        # ── Detailed similarity logs for threshold tuning ─────────────────
        logger.info(
            f"[VISION-SEARCH] shop_id={shop_id} | threshold={threshold} | "
            f"candidates={len(all_scores)} | matches={len(results)}"
        )
        for i, s in enumerate(all_scores):
            marker = "✅ MATCH" if s["passed"] else "❌ BELOW"
            logger.info(
                f"[VISION-SEARCH]   #{i+1} {marker} | "
                f"score={s['score']:.4f} | "
                f"item_id={s['item_id']}"
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
    item_id: Optional[str] = None
    shop_id: Optional[str] = None
    metadata: Optional[dict] = None
    store_image_url: Optional[str] = None

class VectorizeTextRequest(BaseModel):
    text_to_embed: str
    item_id: str
    shop_id: str
    metadata: Optional[dict] = None
    image_url: Optional[str] = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "vision-service", "device": device}


@app.post("/vectorize")
async def predict_embedding(request: ImageRequest):
    """Extract CLIP embedding from image URL (and text if provided), fuse them, and save to DB."""
    try:
        embedding_img, _ = await _download_and_embed(request.image_url)
        
        if request.text_to_embed:
            embedding_txt = _embed_text(request.text_to_embed)
            # FUSION MULTIMODALE : Moyenne des vecteurs (Texte + Image) pour une recherche parfaite
            import torch
            fused = torch.tensor(embedding_img) + torch.tensor(embedding_txt)
            fused = fused / fused.norm(p=2, dim=-1, keepdim=True)
            embedding = fused.tolist()
        else:
            embedding = embedding_img
            
        status_msg = "success"

        # Save to database if item details provided
        if request.item_id and request.shop_id:
            import json
            final_url = request.store_image_url or request.image_url
            try:
                with get_db_connection() as conn:
                    cur = conn.cursor()
                    cur.execute(
                        """
                        INSERT INTO crm_itemvector (item_id, shop_id, image_url, metadata, embedding, created_at)
                        VALUES (%s, %s, %s, %s::jsonb, %s::vector, NOW())
                        ON CONFLICT (item_id, image_url, shop_id)
                        DO UPDATE SET
                            metadata     = EXCLUDED.metadata,
                            embedding    = EXCLUDED.embedding,
                            created_at   = NOW();
                        """,
                        (request.item_id, request.shop_id, final_url, json.dumps(request.metadata or {}), embedding),
                    )
                    conn.commit()
                    cur.close()
                status_msg = "success (saved to db)"
            except psycopg2.Error as db_e:
                status_msg = f"success but failed to save to db: {str(db_e)}"

        return {
            "status": status_msg,
            "dimensions": len(embedding),
            "payload": {
                "item_id": request.item_id,
                "shop_id": request.shop_id,
                "image_url": final_url if request.item_id else request.image_url,
                "metadata": request.metadata
            }
        }

    except psycopg2.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except httpx.HTTPError as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch image: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@app.post("/vectorize-text")
async def vectorize_text(request: VectorizeTextRequest):
    """Extract CLIP embedding from a text description and save to DB."""
    try:
        embedding = _embed_text(request.text_to_embed)
        import json
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO crm_itemvector (item_id, shop_id, image_url, metadata, embedding, created_at)
                VALUES (%s, %s, %s, %s::jsonb, %s::vector, NOW())
                ON CONFLICT (item_id, image_url, shop_id)
                DO UPDATE SET
                    metadata     = EXCLUDED.metadata,
                    embedding    = EXCLUDED.embedding,
                    created_at   = NOW();
                """,
                (request.item_id, request.shop_id, "text_only", json.dumps(request.metadata or {}), embedding),
            )
            conn.commit()
            cur.close()
            
        return {
            "status": "success",
            "dimensions": len(embedding),
            "payload": {
                "item_id": request.item_id,
                "shop_id": request.shop_id,
                "image_url": "text_only",
                "metadata": request.metadata
            }
        }
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
            "total_matches": len(results),
        }

    except psycopg2.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except httpx.HTTPError as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch image: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.post("/vectorize-upload")
async def vectorize_upload(
    image: UploadFile = File(...),
    item_id: str = Form(...),
    shop_id: str = Form(...),
    metadata: str = Form("{}"),  # JSON passé sous forme de string
    image_url: str = Form("uploaded_file"), # URL de l'image (Optionnel)
):
    """Extract CLIP embedding from uploaded image file and save to DB."""
    import json
    try:
        contents = await image.read()
        pil_image = Image.open(io.BytesIO(contents)).convert("RGB")
        embedding = _embed_image(pil_image)
        
        try:
            metadata_dict = json.loads(metadata)
        except json.JSONDecodeError:
            metadata_dict = {}

        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO crm_itemvector (item_id, shop_id, image_url, metadata, embedding, created_at)
                VALUES (%s, %s, %s, %s::jsonb, %s::vector, NOW())
                ON CONFLICT (item_id, image_url, shop_id)
                DO UPDATE SET
                    metadata     = EXCLUDED.metadata,
                    embedding    = EXCLUDED.embedding,
                    created_at   = NOW();
                """,
                (item_id, shop_id, image_url, json.dumps(metadata_dict), embedding),
            )
            conn.commit()
            cur.close()

        return {
            "status": "success", 
            "dimensions": len(embedding),
            "product": {
                "item_id": item_id,
                "shop_id": shop_id,
                "image_url": image_url,
                "metadata": metadata_dict
            }
        }

    except psycopg2.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}") 
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
                    "DELETE FROM crm_itemvector WHERE shop_id = %s RETURNING id;",
                    (shop_id,),
                )
            else:
                cur.execute("DELETE FROM crm_itemvector RETURNING id;")
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
                    "SELECT COUNT(*) FROM crm_itemvector WHERE shop_id = %s;",
                    (shop_id,),
                )
            else:
                cur.execute(
                    "SELECT shop_id, COUNT(*) FROM crm_itemvector GROUP BY shop_id ORDER BY shop_id;"
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
