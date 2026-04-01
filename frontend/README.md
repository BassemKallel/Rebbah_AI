# TikTak AI — Frontend

Interface d'administration pour la plateforme **TikTak AI**, un assistant e-commerce basé sur l'IA conversationnelle. Elle permet de gérer les conversations clients, les leads, et de piloter les messages envoyés via les canaux Meta (WhatsApp / Messenger / Instagram).

---

## Stack technique

| Outil | Version |
|---|---|
| React | 19 |
| React Router | 7 |
| TanStack Query | 5 |
| Axios | 1 |
| Tailwind CSS | 3 |
| Recharts | 3 |
| Lucide React | 0.577 |

---

## Prérequis

- **Node.js** ≥ 18
- **npm** ≥ 9
- Backend TikTak AI en cours d'exécution sur `http://localhost`

---

## Installation

```bash
# 1. Cloner le dépôt
git clone <url-du-repo>
cd tiktak-ai-frontend

# 2. Installer les dépendances
npm install

# 3. Configurer les variables d'environnement
cp .env .env.local
# Éditer .env.local si nécessaire (voir section Variables d'environnement)

# 4. Lancer en développement
npm start
```

L'application est disponible sur [http://localhost:3000](http://localhost:3000).

---

## Variables d'environnement

Le fichier `.env` contient les valeurs par défaut pour un environnement local :

| Variable | Description |
|---|---|
| `REACT_APP_CRM_API_URL` | URL de base de l'API CRM |
| `REACT_APP_META_API_URL` | URL du gateway Messenger POC |
| `REACT_APP_SHOP_ID` | Identifiant de la boutique |
| `REACT_APP_NAME` | Nom affiché de l'application |

> Pour des surcharges locales, créer un fichier `.env.local` (ignoré par git).

---

## Scripts disponibles

| Commande | Description |
|---|---|
| `npm start` | Lance le serveur de développement (port 3000) |
| `npm run build` | Build de production dans `build/` |
| `npm test` | Lance les tests unitaires |

---

## Structure du projet

```
src/
├── api/               # Clients HTTP Axios
│   ├── crmApi.js      # Conversations, messages (CRM)
│   ├── leadsApi.js    # CRUD Leads
│   └── metaApi.js     # Envoi de messages via gateway Messenger
│
├── components/
│   ├── admin/         # Composants spécifiques à l'administration
│   └── layout/        # Sidebar + Navbar (layout global)
│
├── context/           # Contextes React globaux
├── hooks/             # Hooks métier (chat, vision, interventions)
│
├── pages/
│   ├── Dashboard/         # Tableau de bord principal
│   ├── Messages/          # AdminMessages — liste des conversations + bulles
│   ├── Leads/             # Gestion CRM des leads (tableau CRUD)
│   ├── Inbox/             # Boîte de réception (filtres par canal)
│   ├── ClientChat/        # Interface chat côté client (sans sidebar)
│   └── TestMetaSender/    # Outil de test Messenger (thème Messenger)
│
└── utils/             # Utilitaires (formatters, etc.)
```

---

## Routes

| URL | Page | Description |
|---|---|---|
| `/` | Dashboard | Vue d'ensemble & métriques |
| `/messages` | AdminMessages | Gestion des conversations IA |
| `/leads` | Leads | CRM — tableau des leads |
| `/inbox` | Inbox | Boîte de réception multi-canal |
| `/chat` | ClientChat | Interface client (sans layout admin) |
| `/test-sender` | TestMetaSender | Outil de test — envoi de messages Messenger |

---

## Fonctionnalités principales

### AdminMessages
- Liste des conversations filtrées par `shop_id`
- Bulles de messages avec **pills d'intent** (colorées par type d'intention IA)
- Affichage des images (URL blob) ou icône placeholder si image absente
- Déduplication des messages (même expéditeur, même texte consécutif)

### Leads
- Tableau paginé des leads issus des conversations
- Modales de création, édition et suppression

### TestMetaSender
- Interface de type **Messenger** (thème clair Facebook)
- Envoi de messages texte ou avec image
- Debug panel avec état de la requête API

---

## Git

Branche de travail : `feature/admin-messages-ui`

```
feat: add AdminMessages page, Leads CRUD, APIs
feat: restructure layout (sidebar z-30, navbar z-20)
chore: remove unused files
```

---

## Licence

Projet privé — © TikTak AI 2025


### `npm run eject`

**Note: this is a one-way operation. Once you `eject`, you can't go back!**

If you aren't satisfied with the build tool and configuration choices, you can `eject` at any time. This command will remove the single build dependency from your project.

Instead, it will copy all the configuration files and the transitive dependencies (webpack, Babel, ESLint, etc) right into your project so you have full control over them. All of the commands except `eject` will still work, but they will point to the copied scripts so you can tweak them. At this point you're on your own.

You don't have to ever use `eject`. The curated feature set is suitable for small and middle deployments, and you shouldn't feel obligated to use this feature. However we understand that this tool wouldn't be useful if you couldn't customize it when you are ready for it.

## Learn More

You can learn more in the [Create React App documentation](https://facebook.github.io/create-react-app/docs/getting-started).

To learn React, check out the [React documentation](https://reactjs.org/).

### Code Splitting

This section has moved here: [https://facebook.github.io/create-react-app/docs/code-splitting](https://facebook.github.io/create-react-app/docs/code-splitting)

### Analyzing the Bundle Size

This section has moved here: [https://facebook.github.io/create-react-app/docs/analyzing-the-bundle-size](https://facebook.github.io/create-react-app/docs/analyzing-the-bundle-size)

### Making a Progressive Web App

This section has moved here: [https://facebook.github.io/create-react-app/docs/making-a-progressive-web-app](https://facebook.github.io/create-react-app/docs/making-a-progressive-web-app)

### Advanced Configuration

This section has moved here: [https://facebook.github.io/create-react-app/docs/advanced-configuration](https://facebook.github.io/create-react-app/docs/advanced-configuration)

### Deployment

This section has moved here: [https://facebook.github.io/create-react-app/docs/deployment](https://facebook.github.io/create-react-app/docs/deployment)

### `npm run build` fails to minify

This section has moved here: [https://facebook.github.io/create-react-app/docs/troubleshooting#npm-run-build-fails-to-minify](https://facebook.github.io/create-react-app/docs/troubleshooting#npm-run-build-fails-to-minify)
