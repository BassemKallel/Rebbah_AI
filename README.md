# 🛒 TikTak-AI

TikTak-AI est une plateforme intelligente d'e-commerce et d'interaction client basée sur l'intelligence artificielle. Elle expose un webhook Messenger/WhatsApp qui orchestre NLU (TunBERT + GLiNER), Vision (CLIP), Hot Memory (Redis), Cold Memory (PostgreSQL) et l'API TikTak (catalogue et commandes).

## 🏗️ Architecture du Projet

```
Messenger/WhatsApp
       │
       ▼
backend-orchestrator :8000   (Django — API Gateway Clean Architecture)
       │
       ├──► nlu-service :8001       (FastAPI — TunBERT intent + GLiNER NER)
       ├──► vision-service :8002    (FastAPI — CLIP embeddings + pgvector)
       ├──► Redis :6379             (Hot Memory + Cache Produits)
       ├──► PostgreSQL :5432        (Cold Memory — leads, conversations, messages)
       ├──► pgvector DB :5433       (Vector DB — embeddings images)
       └──► TikTak API externes     (Catalogue en ligne + Commandes)
```

### Services
| Service | Port | Description |
|---|---|---|
| `backend-orchestrator` | 8000 | Cœur du système. Séparé en 3 couches : AI Service, TikTak Service, Dialog Manager. |
| `nlu-service` | 8001 | TunBERT (classification intention) + GLiNER (extraction entités) |
| `vision-service` | 8002 | CLIP (similarité image) + pgvector |
| `postgres-db` | 5432 | Base principale (leads, conversations, pré-commandes) |
| `vector-db` | 5433 | pgvector — embeddings images liés au `backend-orchestrator` |
| `tiktak-redis` | 6379 | Contexte conversation court terme + Cache du catalogue (10 min) |

## 🚀 Fonctionnalités Clés

- **Clean Architecture** : Séparation stricte des préoccupations (appels externes, BDD, machine à états).
- **Compréhension du Langage Naturel (NLU)** : Détection d'intentions en dialecte tunisien (arabizi, arabe, français).
- **Extraction d'Entités (NER)** : Produits, tailles, couleurs, adresses, numéros avec système hybride de correction.
- **Recherche Visuelle** : Priorité à l'image envoyée sur le texte de l'utilisateur pour pré-remplir le panier.
- **Gestion des ambiguïtés** : Le bot gère le multi-choix si plusieurs produits correspondent.
- **Flux commande intelligent** : Vérification immédiate du stock des déclinaisons via API distante.

## 💻 Installation et Démarrage Local

### Prérequis
- Docker Desktop avec Docker Compose
- GPU NVIDIA + pilotes CUDA (optionnel, pour accélérer la vision)
- Accès à l'API TikTak (Token JWT requis)

### 1. Cloner le dépôt et configurer l'environnement

```bash
git clone https://github.com/BassemKallel/tiktak-ai.git
cd tiktak-ai
cp .env.example .env
```
👉 Ouvrez `.env` et assurez-vous d'avoir inséré un `TIKTAK_API_TOKEN` valide.

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
