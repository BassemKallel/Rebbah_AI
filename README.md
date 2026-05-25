# 🛒 TikTak-AI

TikTak-AI est une plateforme intelligente d'e-commerce et d'interaction client basée sur l'intelligence artificielle. Elle utilise le SDK officiel **Google GenAI** (modèle *Gemini*) et le framework **Google ADK (Agent Development Kit)** pour orchestrer une architecture multi-agents dynamique et réactive.

La plateforme expose un **webhook Meta Messenger** officiel et un point d'entrée de test (POC) qui intègrent la recherche visuelle multimodale (CLIP + pgvector), la Hot Memory (Redis), la Cold Memory (PostgreSQL) et la gestion de dialogue de vente intelligente avec collecte CRM automatique.

---

## 🏗️ Architecture Globale & Services

```text
Meta Messenger (Webhook)
       │
       ▼
Production: https://ai2.tiktakpro.com/  /  Local: ngrok tunnel (port 8010)
       │
       ▼
backend-orchestrator :8010   (Django — Dialog Manager & Multi-Agents ADK)
       │
       ├──► vision-service    :8020 (FastAPI — CLIP Vector Search)
       ├──► redis             :6380 (Hot Memory & Sliding Window Debouncer)
       └──► postgres-db (db)  :5434 (PostgreSQL + pgvector)
```

### Services

| Service | Port (Externe) | Port (Interne) | Description |
| --- | --- | --- | --- |
| `backend-orchestrator` | `8010` | `8000` | Cœur du système — Dialog Manager, Multi-Agents ADK, APIs CRM, validation de quotas et synchronisation de catalogue. Limite : 512 Mo RAM. |
| `frontend` | `3010` | `3000` | Dashboard client de gestion TikTak Pro. Limite : 256 Mo RAM. |
| `vision-service` | `8020` | `8002` | CLIP embeddings & similarité visuelle (Vector RAG). Limite : 4 Go RAM, GPU Nvidia optionnel. |
| `db` | `5434` | `5432` | PostgreSQL + **pgvector** — Stockage des données CRM et des embeddings vectoriels des images produits. Limite : 768 Mo RAM. |
| `redis` | `6380` | `6379` | Hot Memory (historique de conversation) + Queue de debouncing et coalescence temporelle. Limite : 256 Mo RAM. |

---

## 🤖 Architecture Multi-Agents & Google ADK

Le traitement NLU et la gestion du dialogue reposent sur une architecture multi-agents développée à l'aide de **Google ADK (Agent Development Kit)**. 

### Le Routeur Intelligent
Lorsqu'un message utilisateur arrive, un routeur basé sur l'API Gemini analyse le message et l'historique de conversation récent pour l'orienter dynamiquement vers l'agent ayant la responsabilité adéquate.

### Les 4 Agents Spécialisés
Chaque agent est défini comme un `google.adk.agents.Agent` autonome, possède des instructions de rôle strictes, des prompts en dialecte tunisien (Derja) ou français, et des outils dédiés coordonnés via un `InMemoryRunner` :

* **Agent `FAQ`** : Gère toutes les questions générales, les horaires d'ouverture, les coordonnées de la boutique, les politiques de livraison et les modalités d'achat génériques.
* **Agent `SALES`** : S'occupe de l'exploration du catalogue de produits. Il utilise un outil de recherche sémantique (`search_products`) connecté à la base vectorielle pour recommander des produits adaptés.
* **Agent `CHECKOUT`** : Orchestre le flux de commande. Il collecte dynamiquement et séquentiellement les informations obligatoires du CRM (`full_name`, `phone_number`, `shop_name`, `daily_volume`), présente un récapitulatif structuré et attend la confirmation finale du client.
* **Agent `POST_SALES`** : Gère le support après-vente et le suivi de colis grâce à l'outil `check_order_status` connecté à l'historique d'achat du client.

---

## 🚀 Fonctionnalités Clés

- **Webhook Meta Messenger & POC** : Réception des messages de production sur Messenger/Instagram et point d'entrée POC simplifié sécurisé par token (`X-Shop-Token`) pour l'intégration continue.
- **Sliding Window Message Debouncer** : File d'attente Redis qui regroupe automatiquement les messages successifs rapides d'un client (ex: *"nheb t-shirt"* puis *"bleu"* une seconde plus tard) sous une fenêtre glissante de 3 secondes en un seul message consolidé (*"nheb t-shirt bleu"*). Prévient les exécutions concurrentes de l'IA et évite les réponses fragmentées ou multiples.
- **Circuit Breaker par Client** : Compteur glissant d'erreurs d'API Gemini sur 5 minutes pour chaque client. Si un client rencontre 3 erreurs successives, le bot bascule automatiquement la conversation en mode manuel (`is_human_controlled = True`) pour ne pas bloquer l'utilisateur.
- **Contrôle de Quota Financier (Billing Wallet)** : Contrôle en temps réel du budget mensuel alloué à la boutique (`BillingWallet`). L'IA est désactivée automatiquement au profit d'un opérateur humain si le quota de la boutique est dépassé.
- **Préchargement du Contexte CRM** : Injection automatique du profil CRM (nom, numéro de téléphone, historique) au premier contact pour les clients récurrents afin d'éviter de reposer les mêmes questions.
- **Recherche Visuelle Multimodale (Visual RAG)** : Envoi d'une photo de produit ➔ identification automatique par le Vision Service et pré-remplissage du panier.

---

## 💻 Installation et Démarrage Local

### Prérequis
- Docker Desktop avec Docker Compose
- Clé API Google Gemini

### 1. Cloner le dépôt et configurer l'environnement
```bash
git clone https://github.com/BassemKallel/tiktak-ai-v2.git
cd tiktak-ai-v2
cp .env.example .env
```
Ouvrir le fichier `.env` et renseigner les variables d'environnement nécessaires (les variables sont auto-documentées dans le fichier `.env.example`).

### 2. Build et démarrage des services Docker
```bash
docker compose up --build -d
```
Au premier démarrage, la commande `setup_initial_data` s'exécute automatiquement pour initialiser le superutilisateur Django et la boutique par défaut.

**Restart après modification de code Python :**
```bash
docker compose restart backend-orchestrator
```

**Arrêter les services et libérer les ressources :**
```bash
docker compose down
```

### 3. Tester localement avec `ngrok`
Puisque le webhook Meta requiert une URL HTTPS publique pour envoyer les événements :
1. Démarrez un tunnel ngrok vers le port externe du backend :
   ```bash
   ngrok http 8010
   ```
2. Copiez l'URL HTTPS générée par ngrok (ex: `https://abcd-1234.ngrok-free.app`).
3. Configurez cette URL comme **URL de rappel** dans votre portail Meta Developer : `https://abcd-1234.ngrok-free.app/api/v1/gateway/meta/webhook`.
4. Renseignez la clé de vérification configurée dans votre fichier `.env` (`META_VERIFY_TOKEN`).

---

## 🧪 Suite de Tests & Validation

La plateforme intègre trois scripts de tests automatisés autonomes pour valider le comportement du système à l'intérieur du conteneur Django (regroupés dans le dossier `tests/`) :

1. **`tests/test_run.py`** : Valide le flux conversationnel complet en simulant une conversation interactive de bout en bout (salutations ➔ collecte de nom ➔ téléphone ➔ boutique ➔ volume ➔ confirmation finale et clôture de commande).
2. **`tests/test_debounce.py`** : Valide la file d'attente temporelle glissante (debouncer). Il simule deux requêtes webhooks concurrentes envoyées par le même client à 1 seconde d'intervalle et vérifie que la première est annulée avec le statut `queued_and_skipped` et que la seconde fusionne le texte et s'exécute avec succès.
3. **`tests/test_raw_output.py`** : Valide le format JSON brut retourné par le pipeline de messages.

**Commandes pour exécuter les tests :**
```bash
# Lancer le test complet du flux conversationnel
docker exec tiktak-ai-v2-backend python tests/test_run.py

# Lancer le test de concurrence et de debouncing Redis
docker exec tiktak-ai-v2-backend python tests/test_debounce.py

# Lancer le test de structure des sorties
docker exec tiktak-ai-v2-backend python tests/test_raw_output.py
```

---

## 🧠 Dialog Manager — Machine à États

La conversation avec chaque client progresse à travers 4 états distincts enregistrés en base de données :

| État | Description |
| --- | --- |
| `NEW_CONVERSATION` | Session de conversation initialement ouverte. |
| `LLM_ACTIVE` | Phase active de dialogue (vente ou FAQ) gérée dynamiquement par l'orchestrateur multi-agents Google ADK. |
| `LLM_CONFIRMING` | Toutes les informations CRM requises ont été collectées. Le récapitulatif est présenté au client et le système attend sa confirmation finale (Oui/Non). |
| `COMPLETED` | Le client a validé son récapitulatif. La commande est définitivement enregistrée dans le CRM. |

---

## 🤝 Travailler en Binôme

Meta n'autorisant qu'**une seule URL de webhook** active à la fois par page Facebook de test :
* **Règle de rotation** : Chaque membre de l'équipe met à jour l'URL de rappel dans le portail Meta Developer avec son adresse publique `ngrok` active lorsqu'il teste ses modifications locales.
* En production, l'URL pointe vers l'adresse stable hébergée : **`https://ai2.tiktakpro.com/api/v1/gateway/meta/webhook`**.

---

## 🤝 Contribuer

Les push directs sur les branches principales (`main`, `dev`) sont bloqués par les règles du dépôt.
1. Créez une branche de fonctionnalité depuis `dev` (ex : `feat/ma-fonctionnalite` ou `fix/mon-correctif`).
2. Faites vos commits et poussez votre branche.
3. Ouvrez une Pull Request (PR) vers `dev` pour examen.

---

## 📄 Licence et Propriété

Ce projet est la propriété de l'équipe TikTak-AI dans le cadre de leur Projet de Fin d'Études (PFE).

**Auteurs :**
- Bassem Kallel
- Aziz Belgaied
