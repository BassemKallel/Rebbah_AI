# 🛒 TikTak-AI.

TikTak-AI est une plateforme intelligente d'e-commerce et d'interaction client basée sur l'intelligence artificielle. Elle expose un **webhook Meta Messenger** qui orchestre NLU (TunBERT + GLiNER + Gemini Fallback), Vision (CLIP), Hot Memory (Redis), Cold Memory (PostgreSQL) et l'API TikTak (catalogue et commandes).

## 🏗️ Architecture du Projet

```text
Meta Messenger (Webhook)
       │
       ▼
Cloudflare Tunnel  ──►  backend-orchestrator :8000   (Django — Orchestrateur)
                                │
                                ├──► nlu-service       (FastAPI — TunBERT intent + GLiNER NER)
                                ├──► gemini-api        (Google Gemini — Fallback NLU si TunBERT < seuil)
                                ├──► vision-service    (FastAPI — CLIP embeddings + vectorisation)
                                ├──► redis :6379       (Hot Memory + Cache Produits)
                                ├──► postgres-db :5432 (PostgreSQL + pgvector — BDD + embeddings)
                                └──► TikTak API        (Catalogue en ligne + Commandes)

[sync-worker]  ──►  vision-service + postgres-db   (tâche ponctuelle — docker compose run)
```

### Services

| Service | Port | Description |
| --- | --- | --- |
| `backend-orchestrator` | 8000 | Cœur du système — NLU, dialog manager, TikTak API. |
| `nlu-service` | 8001 | TunBERT (intention) + GLiNER (entités). Limite : 2 Go RAM. |
| `vision-service` | 8002 | CLIP (similarité image). Limite : 4 Go RAM, GPU optionnel. |
| `postgres-db` | 5432 | PostgreSQL + **pgvector** — BDD principale ET embeddings images. |
| `redis` | 6379 | Contexte de conversation + cache produits. |
| `sync-worker` | — | Tâche ponctuelle (`docker compose run --rm sync-worker`). Sync catalogue → embeddings. |

## 🚀 Fonctionnalités Clés

- **Webhook Meta Messenger** : Réception et réponse automatique aux messages Messenger.
- **NLU Multilingue** : Détection d'intentions et extraction d'entités en dialecte tunisien (arabizi, arabe, français).
- **Gemini NLU Fallback** : Si TunBERT retourne un score < seuil, Google Gemini prend le relais pour classifier l'intention.
- **Active Learning** : Les corrections Gemini sont loggées (`NLUFallbackLog`) dans l'admin Django pour future rétro-alimentation de TunBERT.
- **Recherche Visuelle** : Envoi d'une photo de produit → identification automatique + pré-remplissage du panier.
- **Machine à États** : Gestion du flux de commande complet (taille, couleur, adresse, téléphone).
- **Multi-Shop Sync** : Le sync-worker récupère dynamiquement toutes les boutiques actives en base et synchronise chaque catalogue.
- **Vérification de stock** : Contrôle en temps réel avant confirmation de la commande.
- **Score de confiance NLU** : Affiché dans l'admin Django (badge coloré vert/orange/rouge).
- **Gestion des ambiguïtés** : Le bot propose le choix si plusieurs produits correspondent.
- **Setup automatique au démarrage** : Superuser et Company créés automatiquement depuis les variables d'environnement.

## 💻 Installation et Démarrage Local

### Prérequis

- Docker Desktop avec Docker Compose
- Accès à l'API TikTak (Token JWT requis)
- Compte Meta Developer (pour le webhook Messenger)

### 1. Cloner le dépôt et configurer l'environnement

```bash
git clone https://github.com/BassemKallel/tiktak-ai.git
cd tiktak-ai
cp .env.example .env
```

Ouvrir `.env` et renseigner les variables nécessaires (voir section [Variables d'Environnement](#-variables-denvironnement)).

### 2. Build et démarrage des services Docker

**Premier lancement (build + démarrage) :**

```bash
docker compose up --build -d
```

Au premier démarrage, la commande `setup_initial_data` s'exécute automatiquement et crée :

- Le **superutilisateur** Django (depuis `DJANGO_SUPERUSER_*`)
- La **Company / Shop** initiale (depuis `SHOP_ID`, `TIKTAK_API_TOKEN`)

**Démarrage sans rebuild (après `git pull` de code Python uniquement) :**

```bash
docker compose restart backend-orchestrator
```

**Rebuild complet si `Dockerfile` ou `requirements.txt` ont changé :**

```bash
docker compose build backend-orchestrator
docker compose up -d --no-deps backend-orchestrator
```

**Arrêter tous les services :**

```bash
docker compose down
```

**Arrêter ET supprimer les volumes (reset complet BDD) :**

```bash
docker compose down -v
```

**Voir les logs en temps réel :**

```bash
docker compose logs -f backend-orchestrator
```

### 3. Accès Admin Django

Admin disponible sur : `http://localhost:8000/admin/`

> Le superuser est créé automatiquement au premier `docker compose up` si `DJANGO_SUPERUSER_PASSWORD` est défini dans `.env`.

### 4. Configurer le webhook Meta Messenger

1. Lancer le tunnel Cloudflare pour exposer le backend localement :

   ```bash
   cloudflared tunnel --url http://localhost:8000
   ```

2. Copier l'URL générée (ex: `https://xyz.trycloudflare.com`)
3. Dans [Meta Developer Portal](https://developers.facebook.com) → App → Webhooks → **Modifier** :
   - **URL de rappel** : `https://xyz.trycloudflare.com/api/v1/gateway/meta/webhook`
   - **Token de vérification** : valeur de `META_VERIFY_TOKEN` dans `.env`
   - Cocher **`messages`** → Enregistrer

> ⚠️ L'URL Cloudflare change à chaque relancement du tunnel. Mettre à jour le webhook Meta à chaque fois.

### 5. Synchroniser les produits (sync-worker)

```bash
docker compose run --rm sync-worker
```

> À relancer après chaque ajout/modification de produits dans le catalogue TikTak.

### 6. Vérification des services

| Service | URL |
| --- | --- |
| Django Admin | `http://localhost:8000/admin/` |
| Backend (test POC) | `http://localhost:8000/api/v1/gateway/messenger/poc` |
| nlu-service | `http://localhost:8001` (interne) |
| vision-service | `http://localhost:8002` (interne) |

## 🔧 Variables d'Environnement

Copier `.env.example` en `.env` et renseigner les valeurs :

| Variable | Description | Requis |
| --- | --- | :---: |
| `POSTGRES_USER` | Utilisateur PostgreSQL | ✅ |
| `POSTGRES_PASSWORD` | Mot de passe PostgreSQL | ✅ |
| `POSTGRES_DB` | Nom de la base de données | ✅ |
| `DJANGO_SECRET_KEY` | Clé secrète Django (générer avec [djecrety.ir](https://djecrety.ir)) | ✅ |
| `GEMINI_API_KEY` | Clé API Google Gemini (fallback NLU) | ✅ |
| `GEMINI_MODEL` | Modèle Gemini (défaut: `gemini-2.0-flash`) | |
| `GEMINI_FALLBACK_ENABLED` | Activer/désactiver le fallback (`True`/`False`) | |
| `GEMINI_FALLBACK_CONFIDENCE_THRESHOLD` | Seuil de déclenchement (défaut: `0.65`) | |
| `META_VERIFY_TOKEN` | Token de vérification webhook Meta | ✅ |
| `TIKTAK_API_BASE_URL` | URL de base de l'API TikTak | ✅ |
| `DJANGO_SUPERUSER_USERNAME` | Username du superuser (défaut: `admin`) | |
| `DJANGO_SUPERUSER_PASSWORD` | Mot de passe du superuser | ✅ |
| `SHOP_ID` | ID du shop TikTak (slug) | ✅ |
| `SHOP_NAME` | Nom du shop | |
| `TIKTAK_API_TOKEN` | Token JWT de l'API TikTak | ✅ |
| `AZURE_ACCOUNT_NAME` | Compte Azure Blob Storage | |
| `AZURE_ACCOUNT_KEY` | Clé Azure Blob Storage | |

## 🔄 Procédure de mise à jour (après `git pull`)

```bash
git pull origin dev
docker compose restart backend-orchestrator
docker compose exec backend-orchestrator python manage.py migrate
```

> **Rebuild nécessaire uniquement** si `Dockerfile` ou `requirements.txt` ont été modifiés.

## 🧠 Architecture Interne — Dialog Manager

### Machine à États

| État | Description |
| --- | --- |
| `NEW_CONVERSATION` | Début de conversation |
| `WAITING_USER_REPLY` | En attente d'une info (taille, couleur, adresse, téléphone) |
| `WAITING_DISAMBIGUATION` | Plusieurs produits trouvés → demande de choix |
| `AWAITING_CORRECTION` | Déclinaison hors stock — attente d'une correction |
| `COMPLETED` | Commande passée ou conversation terminée |

### Pipeline de traitement

```text
Message reçu → NLU (intent + confiance) → [Gemini Fallback si confiance < seuil]
    → Entity Guards → Accumulate Context
    → State Machine (Dialog Manager) → TikTak API (stock, prix, commande)
    → Réponse Messenger
```

## 🤝 Travailler en Binôme

Les deux membres ont besoin de :

1. **Accès Meta Developer App** (pour modifier le webhook)
2. **Accès Page Facebook** (pour tester les messages)

**Règle de rotation** : Meta n'autorise qu'**une seule URL webhook** à la fois. Chaque membre met à jour l'URL quand c'est son tour de tester.

## 🤝 Contribuer

**Les push directs sur `main` et `dev` sont interdits.**

👉 Lire **[CONTRIBUTING.md](CONTRIBUTING.md)** avant de commencer.

1. Créer une branche depuis `dev` (ex: `feat/nouvelle-fonctionnalite`).
2. Faire ses commits.
3. Pousser la branche et ouvrir une Pull Request vers `dev`.

## 📄 Licence et Propriété

Ce projet est la propriété de l'équipe TikTak-AI dans le cadre de leur PFE.

**Auteurs :**

- Bassem Kallel
- Aziz Belgaied
