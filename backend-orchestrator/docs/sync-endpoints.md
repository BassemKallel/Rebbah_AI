# Product Sync Endpoints

## Overview

Les endpoints de synchronisation permettent de déclencher la vectorisation des produits pour la recherche visuelle (Vision Service).

---

## Endpoints

### 1. **Sync All Companies**

Déclenche la synchronisation pour toutes les companies actives.

```http
POST /api/v1/gateway/sync/trigger
Authorization: Bearer <JWT_TOKEN>
```

**Réponse:**
```json
{
  "status": "success",
  "companies_synced": 2,
  "total_vectorized": 150,
  "total_failed": 2,
  "total_skipped": 10,
  "details": [
    {
      "shop_id": "1LXybpj",
      "shop_name": "My Shop",
      "success": 75,
      "failed": 1,
      "skipped": 5
    },
    {
      "shop_id": "2ABcdef",
      "shop_name": "Another Shop",
      "success": 75,
      "failed": 1,
      "skipped": 5
    }
  ]
}
```

---

### 2. **Sync Specific Shop**

Déclenche la synchronisation pour un shop spécifique.

```http
POST /api/v1/gateway/sync/trigger/{shop_id}
Authorization: Bearer <JWT_TOKEN>
```

**Exemple:**
```bash
curl -X POST https://ai.tiktakpro.com/api/v1/gateway/sync/trigger/1LXybpj \
  -H "Authorization: Bearer your-jwt-token"
```

**Réponse:**
```json
{
  "status": "success",
  "shop_id": "1LXybpj",
  "shop_name": "My Shop",
  "success": 75,
  "failed": 1,
  "skipped": 5
}
```

---

### 3. **Sync Status**

Récupère les informations de configuration du sync.

```http
GET /api/v1/gateway/sync/status
Authorization: Bearer <JWT_TOKEN>
```

**Réponse:**
```json
{
  "status": "ok",
  "vision_service": "http://vision-service:8002",
  "tiktak_api": "https://api.tiktakpro.com",
  "active_companies": 3
}
```

---

## Authentification

Tous les endpoints nécessitent une authentification :
- **JWT Token** (recommandé)
- **Static Token** via header `X-Dashboard-Token`

---

## Workflow

```
1. POST /sync/trigger
   ↓
2. Pour chaque company active:
   a. Fetch produits depuis TikTak API
   b. Extraire images (produits + variations)
   c. POST vers Vision Service /vectorize
   ↓
3. Retourne statistiques (success/failed/skipped)
```

---

## Configuration Requise

### Dans Django Admin → Companies:

1. **is_active** = True
2. **shop_id** = UUID du shop

**Note:** L'API TikTak est publique, aucun token n'est requis.

---

## Exemples d'utilisation

### Avec JWT (dashboard)

```bash
# 1. Login
curl -X POST https://ai.tiktakpro.com/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'

# Réponse: {"access": "eyJ0eXAi...", "refresh": "..."}

# 2. Trigger sync
curl -X POST https://ai.tiktakpro.com/api/v1/gateway/sync/trigger \
  -H "Authorization: Bearer eyJ0eXAi..."
```

### Avec Static Token

```bash
curl -X POST https://ai.tiktakpro.com/api/v1/gateway/sync/trigger \
  -H "X-Dashboard-Token: your-static-token"
```

---

## Erreurs Possibles

| Code | Message | Solution |
|------|---------|----------|
| 404 | No active companies found | Activer company dans Django Admin |
| 401 | Authentication failed | Vérifier JWT/Static Token |
| 500 | Vision service unavailable | Vérifier que vision-service est démarré |
| 500 | TikTak API unavailable | Vérifier connectivité réseau |

---

## Différence avec sync-worker container

| Aspect | Endpoint REST | Sync-worker container |
|--------|---------------|----------------------|
| Déclenchement | À la demande (API call) | Automatique (cron 24h) |
| Authentification | JWT/Token requis | Aucune (interne) |
| Use case | Sync manuel après ajout produit | Sync nocturne automatique |
| Monitoring | Réponse HTTP immédiate | Logs Docker uniquement |

---

## Notes

- Rate limiting: 0.5s entre chaque image (éviter surcharge Vision)
- Max 10 pages de produits par shop (safety)
- Images dupliquées sont skippées (déduplication par product_id + URL)
