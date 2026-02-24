# 🛒 TikTak-AI

TikTak-AI est une plateforme intelligente d'e-commerce et d'interaction client basée sur l'intelligence artificielle. Elle expose un webhook Messenger/WhatsApp qui orchestre NLU (TunBERT + GLiNER), Vision (CLIP), Hot Memory (Redis), Cold Memory (PostgreSQL) et une Mock API produits.

## 🏗️ Architecture du Projet

```
Messenger/WhatsApp
       │
       ▼
backend-orchestrator :8000   (Django — API Gateway + State Machine)
       │
       ├──► nlu-service :8001       (FastAPI — TunBERT intent + GLiNER NER)
       ├──► vision-service :8002    (FastAPI — CLIP embeddings + pgvector)
       ├──► Redis :6379             (Hot Memory — contexte conversation)
       ├──► PostgreSQL :5432        (Cold Memory — leads, conversations, messages)
       ├──► pgvector DB :5433       (Vector DB — embeddings produits)
       └──► Mock API :8003          (Django externe — catalogue produits + commandes)
```

### Services
| Service | Port | Description |
|---|---|---|
| `backend-orchestrator` | 8000 | Cœur du système, Django, state machine conversation |
| `nlu-service` | 8001 | TunBERT (classification intention) + GLiNER (extraction entités) |
| `vision-service` | 8002 | CLIP (similarité image) + pgvector |
| `postgres-db` | 5432 | Base principale (leads, conversations, messages) |
| `vector-db` | 5433 | pgvector — embeddings images produits |
| `tiktak-redis` | 6379 | Contexte conversation court terme |
| **Mock API** | 8003 | API externe Django — catalogue produits + création commandes |

## 🚀 Fonctionnalités Clés

- **Compréhension du Langage Naturel (NLU)** : Détection d'intentions en français/arabe/arabizi tunisien.
- **Extraction d'Entités (NER)** : Produits, tailles, couleurs, adresses, numéros de téléphone.
- **Recherche Visuelle** : L'utilisateur envoie une photo → le bot identifie la variation exacte (couleur) et pré-remplit la commande.
- **Gestion des ambiguïtés** : Plusieurs produits correspondants → le bot liste et demande lequel.
- **Flux commande complet** : Vérification stock → collecte taille/adresse/téléphone → POST commande → référence de commande.
- **Architecture Multi-Tenant** : Chaque boutique identifiée par `shop_id` (UUID).

## 💻 Installation et Démarrage Local

### Prérequis
- Docker Desktop avec Docker Compose
- GPU NVIDIA + pilotes CUDA (optionnel, pour accélérer la vision)
- Git

### 1. Cloner le dépôt

```bash
git clone https://github.com/BassemKallel/tiktak-ai.git
cd tiktak-ai
```

### 2. Démarrer la Mock API (service externe)

La Mock API est un projet Django séparé qui expose le catalogue produits et l'API de création de commandes. Elle **doit être accessible depuis les conteneurs Docker** donc lancée sur `0.0.0.0` (pas `127.0.0.1`).

```bash
# Dans le répertoire du projet Mock API
cd /chemin/vers/mock-api
python manage.py runserver 0.0.0.0:8003
```

> L'adresse à configurer dans `backend-orchestrator/core/settings.py` (ou `views.py`) pour atteindre la Mock API depuis les conteneurs est l'IP locale de la machine hôte, par exemple `http://192.168.100.10:8003`.

Endpoints utilisés :
| Méthode | URL | Header | Description |
|---|---|---|---|
| `GET` | `/api/v1/products/` | `X-Store-ID: <shop_id>` | Liste tous les produits |
| `GET` | `/api/v1/products/<id>/` | `X-Store-ID: <shop_id>` | Détail d'un produit |
| `POST` | `/api/v1/orders/` | `X-Store-ID: <shop_id>` | Créer une commande |

Voir [API_MOCK_DOCS.json](API_MOCK_DOCS.json) pour la documentation complète (importable dans Postman).

### 3. Build et démarrage des services Docker

**Premier lancement (build + démarrage) :**
```bash
docker-compose up --build
```

**Démarrage sans rebuild (si aucun changement de code) :**
```bash
docker-compose up
```

**En arrière-plan (mode détaché) :**
```bash
docker-compose up --build -d
```

**Rebuild d'un seul service (ex: après modification de `views.py`) :**
```bash
docker-compose build backend-orchestrator
docker-compose up -d --no-deps backend-orchestrator
```

**Arrêter tous les services :**
```bash
docker-compose down
```

**Arrêter ET supprimer les volumes (reset complet BDD) :**
```bash
docker-compose down -v
```

**Voir les logs d'un service en temps réel :**
```bash
docker-compose logs -f backend-orchestrator
docker-compose logs -f vision-service
```

**Services démarrés dans l'ordre :** `postgres-db` → `vector-db` → `tiktak-redis` → `nlu-service` → `vision-service` → `backend-orchestrator`

> **GPU (optionnel)** : Si vous avez un GPU NVIDIA, il sera détecté automatiquement par `vision-service`. Vérifiez que le driver NVIDIA et CUDA 11.8+ sont installés sur l'hôte.

### 4. Appliquer les migrations Django

```bash
docker exec -it backend-orchestrator python manage.py migrate
```

### 5. Synchroniser les produits vers le Vector DB (sync-worker)

Le sync-worker récupère les produits depuis la Mock API, génère les embeddings CLIP et les stocke dans pgvector. À lancer après chaque ajout/modification de produits.

```bash
# Avec Docker
docker-compose run --rm sync-worker

# Ou directement (si environnement Python local configuré)
cd sync-worker
pip install -r requirements.txt
python sync.py
```

> Si c'est le premier lancement ou si le schéma a changé, supprimez d'abord l'ancienne table :
> ```sql
> -- Se connecter au vector-db (port 5433, user: tiktak_vector, db: tiktak_vectors)
> DROP TABLE IF EXISTS products_vector;
> ```
> Puis relancer le sync-worker.

### 6. Vérification des services

| Service | URL de santé |
|---|---|
| backend-orchestrator | `http://localhost:8000/api/v1/gateway/messenger/poc` |
| nlu-service | `http://localhost:8001/docs` |
| vision-service | `http://localhost:8002/docs` |

### 7. Tester avec Postman

Importer [TikTak_AI_Tests.postman_collection.json](TikTak_AI_Tests.postman_collection.json) dans Postman.

Configurer les variables d'environnement :
| Variable | Valeur |
|---|---|
| `BASE_URL` | `http://localhost:8000` |
| `SHOP_ID` | UUID de votre boutique (ex: `b632373b-398a-4e21-9b17-a99b511f8c47`) |

**Endpoint principal :**
```
POST http://localhost:8000/api/v1/gateway/messenger/poc
Content-Type: multipart/form-data

user_id  = whatsapp:+216XXXXXXXX
shop_id  = <UUID boutique>
text     = "Je veux commander un pull noir"     (optionnel)
image_url= "https://..."                         (optionnel)
```

## 🔄 État de la Conversation (State Machine)

| État | Description |
|---|---|
| `NEW_CONVERSATION` | Nouveau fil |
| `WAITING_USER_REPLY` | En attente d'une info manquante (taille, adresse, téléphone) |
| `WAITING_DISAMBIGUATION` | Plusieurs produits trouvés → demande à l'utilisateur de choisir |
| `COMPLETED` | Commande passée ou conversation terminée |

## 🤝 Contribuer

**Les push directs sur `main` et `dev` sont strictement interdits.**

👉 Lire **[CONTRIBUTING.md](CONTRIBUTING.md)** avant de commencer.

1. Créer une branche depuis `dev` (ex: `feat/nouvelle-fonctionnalite`).
2. Faire ses commits.
3. Pousser la branche et ouvrir une Pull Request vers `dev`.
4. Attendre l'approbation d'un Codeowner.

## 📄 Licence et Propriété

Ce projet est la propriété de l'équipe TikTak-AI dans le cadre de leur PFE.

**Auteurs :**
- Bassem Kallel
- Aziz Belgaied
