# 🛒 TikTak-AI

TikTak-AI est une plateforme intelligente d'e-commerce et d'interaction client basée sur l'intelligence artificielle. Le projet se compose de plusieurs microservices visant à comprendre les intentions des utilisateurs (NLU) et à analyser des contenus visuels.

## 🏗️ Architecture du Projet

Le backend est structuré autour d'une architecture orientée microservices, orchestrée par Docker :

- **`backend-orchestrator/`** : Le cœur du système (Django). Il gère la logique métier principale, l'API Gateway, l'authentification multilocataire (multi-tenant) et la base de données PostgreSQL.
- **`nlu-service/`** : Un microservice FastAPI dédié à la compréhension du langage naturel (NLU). Il utilise un modèle TunBERT affiné pour la classification des intentions clients et un modèle GLiNER pour l'extraction d'entités nommées (NER), spécifiquement adaptés au contexte tunisien (français/arabe/arabizi).
- **`vision-service/`** : Un service chargé du traitement, de l'analyse des images et de la génération d'embeddings vectoriels (stockés dans pgvector) pour la recherche visuelle de produits.

## 🚀 Fonctionnalités Clés

- **Compréhension du Langage Naturel (NLU)** : Détection précise des intentions d'achat ou de support client, même dans des dialectes locaux.
- **Extraction d'Entités (NER)** : Identification des produits, tailles, couleurs et adresses dans les requêtes textuelles.
- **Recherche Visuelle** : Analyse des images de produits et recherche par similarité vectorielle.
- **Architecture Multi-Tenant** : Isolation des données pour prendre en charge plusieurs boutiques ou clients de manière sécurisée.
- **Infrastructure Scalable** : Services conteneurisés prêts pour le déploiement cloud (ex: Azure).

## 💻 Installation et Démarrage Local

### Prérequis
- Docker et Docker Compose
- Python 3.10+ (pour le développement local hors conteneurs)
- Git

### Étapes de lancement

1. **Cloner le dépôt :**
   ```bash
   git clone https://github.com/BassemKallel/tiktak-ai.git
   cd tiktak-ai
   ```

2. **Démarrer les services avec Docker Compose :**
   ```bash
   docker-compose up --build
   ```

   Cela va construire et démarrer :
   - La base de données PostgreSQL (avec l'extension pgvector)
   - Redis (pour le cache ou les files d'attente)
   - Le `nlu-service` (accessible généralement sur le port 8001)
   - Le `vision-service`
   - Le `backend-orchestrator` (Django)

3. **Vérifier l'état :**
   Rendez-vous sur les URLs fournies par chaque service (par exemple `http://localhost:8001/docs` pour le NLU).

## 🤝 Contribuer

Nous utilisons un processus de développement rigoureux basé sur les Pull Requests.
**Les push directs sur les branches `main` et `dev` sont strictement interdits.**

👉 Veuillez lire le **[Guide de Contribution complet (CONTRIBUTING.md)](CONTRIBUTING.md)** avant de commencer à travailler.

1. Créez une branche à partir de `dev` (ex: `feat/nouvelle-fonctionnalite`).
2. Faites vos modifications et vos commits.
3. Poussez votre branche sur GitHub.
4. Ouvrez une Pull Request vers la branche `dev`.
5. Attendez la relecture et la validation (*Approve*) par un Codeowner.

## 📄 Licence et Propriété

Ce projet est la propriété de Bassem Kallel et de l'équipe TikTak-AI dans le cadre de leur PFE.
