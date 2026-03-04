# Migration Mock API → TikTak Real API

**Branche:** `feat/tiktak-real-api`  
**Date:** 4 mars 2026  
**Objectif:** Remplacer l'API Mock locale par l'API TikTak réelle de production

---

## Contexte

### Problème actuel
- Backend utilise une Mock API locale (`http://192.168.100.10:8003`) pour simuler le catalogue produits
- Format de données Mock ≠ format TikTak réel
- Pas d'authentification Bearer
- Pas de pagination
- sync-worker ne fonctionne pas avec l'API réelle

### Solution
- Migrer vers `https://api.tiktakpro.com/api/v1/products-read/`
- Ajouter cache Redis (10 min) pour réduire latence et appels API
- Normaliser les données TikTak → format interne unifié
- Optimiser sync-worker avec déduplication d'images

---

## Différences API Mock vs TikTak Réelle

| Aspect | Mock API | TikTak réelle |
|---|---|---|
| **URL** | `http://192.168.100.10:8003/api/v1/products/` | `https://api.tiktakpro.com/api/v1/products-read/` |
| **Auth** | Header `X-Store-ID: <uuid>` | Query `?company=1LXybpj` + Header `Authorization: Bearer <token>` |
| **Response** | `[{...}, ...]` liste directe | `{"results": [...], "next": ..., "count": ...}` |
| **Pagination** | Non | Oui (`next` URL) |
| **Produit enfant** | N/A | `parent: <id>` présent dans results |
| **Variations** | `p["variations"]` | `p["declinaisons"]` |
| **Couleur/Taille** | `v["color"]`, `v["size"]` | `v["_attributs"]` → parser `is_color true/false` |
| **Stock** | `v["stock_quantity"]` | `v["stock"]` |
| **Prix** | `p["base_price"]` | `p["price"]` |
| **Image** | `v["image"]` | `v["photo"]` |
| **ID produit** | UUID string | Integer |

---

## Plan d'Implémentation — 6 Tâches

### ✅ Tâche 1 — `settings.py` : Variables TikTak

**Fichier:** `backend-orchestrator/core/settings.py`  
**Lignes:** 94–97

**SUPPRIMER:**
```python
# Mock API (External product catalog)
MOCK_API_BASE_URL           = os.getenv('MOCK_API_BASE_URL',           'http://192.168.100.10:8003')
MOCK_API_PRODUCTS_PATH      = os.getenv('MOCK_API_PRODUCTS_PATH',      '/api/v1/products/')
MOCK_API_SHOP_ID_HEADER     = os.getenv('MOCK_API_SHOP_ID_HEADER',     'X-Store-ID')
```

**AJOUTER:**
```python
# TikTak Real API (External product catalog)
TIKTAK_API_BASE_URL      = os.getenv('TIKTAK_API_BASE_URL',     'https://api.tiktakpro.com')
TIKTAK_API_PRODUCTS_PATH = os.getenv('TIKTAK_API_PRODUCTS_PATH', '/api/v1/products-read/')
TIKTAK_API_TOKEN         = os.getenv('TIKTAK_API_TOKEN',         '')
PRODUCTS_CACHE_TTL       = int(os.getenv('PRODUCTS_CACHE_TTL',   '600'))  # 10 min
```

---

### ✅ Tâche 2 — `views.py` : Imports + Variables globales

**Fichier:** `backend-orchestrator/apps/gateway/views.py`

**2a — Ajouter imports (après ligne 3):**
```python
import logging
from django.core.cache import cache

logger = logging.getLogger(__name__)
```

**2b — Remplacer variables globales (lignes 22–23):**
```python
# AVANT
MOCK_API_PRODUCTS_URL = settings.MOCK_API_BASE_URL.rstrip('/') + settings.MOCK_API_PRODUCTS_PATH
MOCK_API_SHOP_HEADER  = settings.MOCK_API_SHOP_ID_HEADER

# APRÈS
TIKTAK_API_PRODUCTS_URL = settings.TIKTAK_API_BASE_URL.rstrip('/') + settings.TIKTAK_API_PRODUCTS_PATH
```

---

### ✅ Tâche 3 — `views.py` : Fonction normalize_tiktak_products()

**Fichier:** `backend-orchestrator/apps/gateway/views.py`  
**Position:** Juste avant `context_manager = ContextManager()`

```python
def normalize_tiktak_products(results: list) -> list:
    """
    Convertit la réponse brute de l'API TikTak réelle en format interne standard.

    Format interne :
    {
        "id":         <int>,
        "name":       <str>,
        "base_price": <str>,
        "variations": [
            {
                "id":             <int>,
                "color":          <str>,   # extrait de _attributs où is_color==True
                "size":           <str>,   # extrait de _attributs où is_color==False
                "image":          <str>,   # renommé depuis "photo"
                "stock_quantity": <int>,   # renommé depuis "stock"
            }
        ]
    }
    """
    normalized = []
    for p in results:
        if p.get("parent") is not None:
            continue

        variations = []
        for decl in p.get("declinaisons", []):
            color = ""
            size  = ""
            for attr in decl.get("_attributs", []):
                if attr.get("is_color"):
                    color = attr.get("value", "")
                else:
                    size = attr.get("value", "")
            variations.append({
                "id":             decl["id"],
                "color":          color,
                "size":           size,
                "image":          decl.get("photo", ""),
                "stock_quantity": decl.get("stock", 0),
            })

        if not variations:
            variations.append({
                "id":             p["id"],
                "color":          "",
                "size":           "",
                "image":          p.get("photo", ""),
                "stock_quantity": p.get("stock", 0),
            })

        normalized.append({
            "id":         p["id"],
            "name":       p["name"],
            "base_price": str(p.get("price", "0")),
            "variations": variations,
        })

    return normalized
```

---

### ✅ Tâche 4 — `views.py` : Fetch API avec cache + pagination

**Fichier:** `backend-orchestrator/apps/gateway/views.py`  
**Lignes:** 294–352 (bloc `if prod_name:`)

**REMPLACER:**
```python
if prod_name:
    try:
        mock_api_url = MOCK_API_PRODUCTS_URL
        headers = {MOCK_API_SHOP_HEADER: shop_id}
        resp = requests.get(mock_api_url, headers=headers, timeout=REQUEST_TIMEOUT)
        if resp.status_code == 200:
            products = resp.json()
```

**PAR:**
```python
if prod_name:
    try:
        # Cache Redis
        cache_key = f"tiktak_products:{shop_id}"
        products = cache.get(cache_key)

        if products is None:
            logger.info(f"[TIKTAK API] cache miss shop_id={shop_id}")
            api_headers = {"Authorization": f"Bearer {settings.TIKTAK_API_TOKEN}"}
            all_results = []
            next_url = TIKTAK_API_PRODUCTS_URL
            params = {"company": shop_id}
            page_count = 0

            while next_url and page_count < 10:
                if page_count == 0:
                    resp = requests.get(next_url, headers=api_headers, params=params, timeout=REQUEST_TIMEOUT)
                else:
                    resp = requests.get(next_url, headers=api_headers, timeout=REQUEST_TIMEOUT)

                if resp.status_code == 200:
                    data = resp.json()
                    all_results.extend(data.get("results", []))
                    next_url = data.get("next")
                    page_count += 1
                else:
                    logger.error(f"[TIKTAK API] error {resp.status_code}")
                    break

            products = normalize_tiktak_products(all_results)
            cache.set(cache_key, products, settings.PRODUCTS_CACHE_TTL)
            logger.info(f"[TIKTAK API] {len(products)} produits cachés")
        else:
            logger.debug(f"[TIKTAK API] cache hit shop_id={shop_id}")
```

**GARDER:** Toute la logique de matching après (prod_name.startswith("Article_From_Image_"), keyword_candidates, etc.) → **INCHANGÉE**

---

### ✅ Tâche 5 — `sync-worker/sync.py` : API réelle + déduplication

**Fichier:** `sync-worker/sync.py`

**Remplacer entièrement le contenu:**
```python
import os
import time
import requests
import logging

# Configuration
TIKTAK_API_BASE_URL = os.getenv("TIKTAK_API_BASE_URL",  "https://api.tiktakpro.com")
TIKTAK_API_TOKEN    = os.getenv("TIKTAK_API_TOKEN",      "")
COMPANY_SLUG        = os.getenv("COMPANY_SLUG",          "1LXybpj")
VISION_SERVICE_URL  = os.getenv("VISION_SERVICE_URL",    "http://vision-service:8002/vectorize")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fetch_products():
    """Fetch tous les produits avec pagination."""
    url = f"{TIKTAK_API_BASE_URL}/api/v1/products-read/"
    headers = {"Authorization": f"Bearer {TIKTAK_API_TOKEN}"}
    all_results = []
    params = {"company": COMPANY_SLUG}
    page_count = 0

    logger.info(f"Fetching products pour company={COMPANY_SLUG}")

    while url and page_count < 10:
        try:
            if page_count == 0:
                resp = requests.get(url, headers=headers, params=params, timeout=10)
            else:
                resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            all_results.extend(data.get("results", []))
            url = data.get("next")
            page_count += 1
            logger.info(f"Page {page_count}: {len(data.get('results', []))} produits")
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur page {page_count}: {e}")
            break

    logger.info(f"Total brut: {len(all_results)} entrées")
    return all_results

def vectorize_image(image_url, product_id, shop_id, variation_id):
    """Envoie l'image au vision-service pour vectorisation."""
    payload = {
        "image_url":       image_url,
        "product_id":      str(product_id),
        "variation_id":    str(variation_id),
        "shop_id":         str(shop_id),
        "store_image_url": image_url
    }
    
    try:
        logger.info(f"Vectorizing {variation_id} pour produit {product_id}")
        response = requests.post(VISION_SERVICE_URL, json=payload, timeout=30)
        response.raise_for_status()
        logger.info(f"Success: {response.json().get('status')}")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed: {e}")
        return False

def sync_catalog():
    """
    Sync avec déduplication d'images.
    
    Logique: une même image (sweatshirt_bleu.webp) peut être partagée
    par plusieurs tailles (S/M/L/XL). CLIP ne voit pas la taille
    → vectoriser 1 fois par (product_id, image_url) unique.
    """
    logger.info(f"Démarrage sync company={COMPANY_SLUG}")

    raw_results = fetch_products()
    if not raw_results:
        logger.warning("Aucun produit récupéré")
        return

    success_count = 0
    failure_count = 0
    skipped_count = 0
    seen_images   = set()  # déduplication

    for product in raw_results:
        if product.get("parent") is not None:
            continue

        product_id = product.get("id")

        # Produits avec déclinaisons
        for decl in product.get("declinaisons", []):
            image_url    = decl.get("photo")
            variation_id = decl.get("id")

            if not image_url:
                skipped_count += 1
                continue

            dedup_key = (str(product_id), image_url)
            if dedup_key in seen_images:
                logger.debug(f"Image déjà vectorisée: {image_url}")
                skipped_count += 1
                continue

            seen_images.add(dedup_key)
            success = vectorize_image(image_url, product_id, COMPANY_SLUG, variation_id)
            if success:
                success_count += 1
            else:
                failure_count += 1
            time.sleep(0.5)

        # Produit simple
        if not product.get("declinaisons") and product.get("photo"):
            image_url = product["photo"]
            dedup_key = (str(product_id), image_url)
            if dedup_key not in seen_images:
                seen_images.add(dedup_key)
                success = vectorize_image(image_url, product_id, COMPANY_SLUG, product_id)
                if success:
                    success_count += 1
                else:
                    failure_count += 1
                time.sleep(0.5)

    logger.info(
        f"Sync terminé. "
        f"Vectorisés: {success_count} | "
        f"Échoués: {failure_count} | "
        f"Skippés: {skipped_count}"
    )

if __name__ == "__main__":
    logger.info("Initializing Sync Worker...")
    sync_catalog()
```

---

### ✅ Tâche 6 — Variables env + docker-compose

**6a — `docker-compose.yml` (lignes 50–56):**
```yaml
sync-worker:
  build: ./sync-worker
  container_name: sync-worker
  env_file:
    - .env
  environment:
    TIKTAK_API_BASE_URL: ${TIKTAK_API_BASE_URL}
    TIKTAK_API_TOKEN:    ${TIKTAK_API_TOKEN}
    COMPANY_SLUG:        ${COMPANY_SLUG}
    VISION_SERVICE_URL:  http://vision-service:8002/vectorize
  depends_on:
    - vision-service
  deploy:
    resources:
      limits:
        memory: 256m
```

**6b — `.env.example` (lignes 27–30):**
```dotenv
# SUPPRIMER
MOCK_API_BASE_URL=http://<MOCK_API_HOST>:8003
MOCK_API_PRODUCTS_PATH=/api/v1/products/
MOCK_API_SHOP_ID_HEADER=X-Store-ID

# AJOUTER
TIKTAK_API_BASE_URL=https://api.tiktakpro.com
TIKTAK_API_PRODUCTS_PATH=/api/v1/products-read/
TIKTAK_API_TOKEN=<bearer_token_ici>
PRODUCTS_CACHE_TTL=600
COMPANY_SLUG=<company_slug_ici>
```

**6c — `.env` (fichier réel):**
```dotenv
TIKTAK_API_BASE_URL=https://api.tiktakpro.com
TIKTAK_API_PRODUCTS_PATH=/api/v1/products-read/
TIKTAK_API_TOKEN=<TON_VRAI_TOKEN>
PRODUCTS_CACHE_TTL=600
COMPANY_SLUG=1LXybpj
```

---

## Tests Après Implémentation

### 1. Test backend — requête produits
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "shop_id": "1LXybpj",
    "message": {"text": "Je veux commander un pull"}
  }'
```

**Attendu:** Logs `[TIKTAK API] cache miss` + produits retournés

### 2. Test cache
Même requête 2× → deuxième fois doit afficher `[TIKTAK API] cache hit`

### 3. Test sync-worker
```bash
docker-compose up sync-worker
```

**Attendu:** Logs montrant déduplication + nombre d'images vectorisées

### 4. Vérifier pgvector
```sql
SELECT product_id, variation_id, COUNT(*) 
FROM product_embeddings 
GROUP BY product_id, variation_id;
```

---

## Commandes Git

### Commit après implémentation
```bash
git add .
git commit -m "feat: migrate from Mock API to TikTak real API

- Replace Mock API with https://api.tiktakpro.com
- Add Redis cache (10 min TTL) for products
- Add Bearer token authentication
- Handle pagination (max 10 pages)
- Normalize TikTak format to internal format
- Optimize sync-worker with image deduplication
- Update docker-compose for sync-worker env vars"
```

### Push la branche
```bash
git push origin feat/tiktak-real-api
```

### Retour à feat/smart-order-flow (si besoin)
```bash
git checkout feat/smart-order-flow
```

---

## Rollback Plan

Si problème en prod:

```bash
git checkout feat/smart-order-flow
git push origin feat/smart-order-flow --force
```

Ou revenir au commit avant migration:
```bash
git revert <commit_hash_migration>
```

---

## Notes Importantes

1. **Token Bearer** → Ne jamais commit dans git, seulement dans `.env`
2. **Cache 10 min** → Ajustable via `PRODUCTS_CACHE_TTL` dans `.env`
3. **Pagination limitée 10 pages** → ~500 produits max, sécurité anti-boucle infinie
4. **Déduplication sync** → 1 vecteur par (product_id, image_url) unique (ex: 1 vecteur pour Bleu/S/M/L/XL au lieu de 4)
5. **Format interne** → Aucun changement dans la logique métier de views.py grâce à normalize_tiktak_products()

---

**Statut:** ⏳ Prêt à implémenter  
**Branche:** `feat/tiktak-real-api` (créée, aucune modification pour l'instant)
