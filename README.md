# 🛒 TikTak-AI

TikTak-AI est une plateforme intelligente d'e-commerce et d'interaction client basée sur l'intelligence artificielle. Elle expose un **webhook Meta Messenger** qui orchestre NLU (TunBERT + GLiNER), Vision (CLIP), Hot Memory (Redis), Cold Memory (PostgreSQL) et l'API TikTak (catalogue et commandes).

## 🏗️ Architecture du Projet

```
Meta Messenger (Webhook)
       │
       ▼
Cloudflare Tunnel  ──►  backend-orchestrator :8000   (Django — Orchestrateur)
                                │
                                ├──► nlu-service       (FastAPI — TunBERT intent + GLiNER NER)
                                ├──► vision-service    (FastAPI — CLIP embeddings + vectorisation)
                                ├──► redis :6379       (Hot Memory + Cache Produits)
                                ├──► postgres-db :5432 (PostgreSQL + pgvector — BDD + embeddings)
                                └──► TikTak API        (Catalogue en ligne + Commandes)

[sync-worker]  ──►  vision-service + postgres-db   (tâche ponctuelle — docker compose run)
```

### Services

| Service | Port | Description |
|---|---|---|
| `api-gateway` | 80 | Point d'entrée unique. Reverse proxy Nginx. |
| `backend-orchestrator` | 8000 | Cœur du système — NLU, dialog manager, TikTak API. |
| `nlu-service` | interne | TunBERT (intention) + GLiNER (entités). Limite : 2 Go RAM. |
| `vision-service` | interne | CLIP (similarité image). Limite : 4 Go RAM, GPU optionnel. |
| `postgres-db` | 5432 | PostgreSQL + **pgvector** — BDD principale ET embeddings images. |
| `redis` | 6379 | Contexte de conversation + cache produits. |
| `sync-worker` | — | Tâche ponctuelle (`docker compose run --rm sync-worker`). Sync catalogue → embeddings. |

## 🚀 Fonctionnalités Clés

- **Webhook Meta Messenger** : Réception et réponse automatique aux messages Messenger.
- **NLU Multilingue** : Détection d'intentions et extraction d'entités en dialecte tunisien (arabizi, arabe, français).
- **Recherche Visuelle** : Envoi d'une photo de produit → identification automatique + pré-remplissage du panier.
- **Machine à États** : Gestion du flux de commande complet (taille, couleur, adresse, téléphone).
- **Vérification de stock** : Contrôle en temps réel avant confirmation de la commande.
- **Score de confiance NLU** : Affiché dans l'admin Django (badge coloré vert/orange/rouge).
- **Gestion des ambiguïtés** : Le bot propose le choix si plusieurs produits correspondent.
- **Observabilité** : Django Admin enrichi — conversations, messages, score d'intention.

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

Ouvrir `.env` et renseigner les variables nécessaires (voir `.env.example`).

### 2. Build et démarrage des services Docker

**Premier lancement (build + démarrage) :**

```bash
docker compose up --build -d
```

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

### 3. Appliquer les migrations Django

À faire **obligatoirement** au premier lancement et après chaque `git pull` qui touche les modèles :

```bash
docker compose exec backend-orchestrator python manage.py migrate
```

### 4. Créer un superutilisateur (accès Admin Django)

```bash
docker compose exec backend-orchestrator python manage.py createsuperuser
```

Admin disponible sur : `http://localhost/admin/`

### 5. Configurer le webhook Meta Messenger

1. Lancer le tunnel Cloudflare pour exposer le backend localement :

   ```bash
   cloudflared tunnel --url http://localhost:8000
   ```

2. Copier l'URL générée (ex: `https://xyz.trycloudflare.com`)
3. Dans [Meta Developer Portal](https://developers.facebook.com) → App → Webhooks → **Modifier** :
   - **URL de rappel** : `https://xyz.trycloudflare.com/api/v1/gateway/meta/webhook`
   - **Token de vérification** : `tiktak_verify_token`
   - Cocher **`messages`** → Enregistrer

> ⚠️ L'URL Cloudflare change à chaque relancement du tunnel. Mettre à jour le webhook Meta à chaque fois.

### 6. Synchroniser les produits (sync-worker)

```bash
docker compose run --rm sync-worker
```

> À relancer après chaque ajout/modification de produits dans le catalogue TikTak.

### 7. Vérification des services

| Service | URL |
|---|---|
| Django Admin | `http://localhost/admin/` |
| Backend (santé) | `http://localhost/api/v1/gateway/messenger/poc` |
| nlu-service | Interne uniquement |
| vision-service | Interne uniquement |

## 🔄 Procédure de mise à jour (après `git pull`)

```bash
git pull origin feat/meta-webhook
docker compose restart backend-orchestrator
docker compose exec backend-orchestrator python manage.py migrate
```

> **Rebuild nécessaire uniquement** si `Dockerfile` ou `requirements.txt` ont été modifiés.

## 🧠 Architecture Interne — Dialog Manager

### Machine à États

| État | Description |
|---|---|
| `NEW_CONVERSATION` | Début de conversation |
| `WAITING_USER_REPLY` | En attente d'une info (taille, couleur, adresse, téléphone) |
| `WAITING_DISAMBIGUATION` | Plusieurs produits trouvés → demande de choix |
| `AWAITING_CORRECTION` | Déclinaison hors stock — attente d'une correction |
| `COMPLETED` | Commande passée ou conversation terminée |

### Pipeline de traitement

```
Message reçu → NLU (intent + confiance) → Entity Guards → Accumulate Context
    → State Machine (Dialog Manager) → TikTak API (stock, prix, commande)
    → Réponse Messenger
```

## 🤝 Travailler en Binôme

Les deux membres ont besoin de :

1. **Accès Meta Developer App** (pour modifier le webhook)
2. **Accès Page Facebook** (pour tester les messages)

👉 Consulter **[guide_binome.md](.gemini/antigravity/brain/6b6c35cc-2284-4e8e-b4bc-2c8a62f61676/guide_binome.md)** pour la configuration complète.

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
