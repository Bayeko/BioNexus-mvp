# BioNexus MVP

Bienvenue dans le projet BioNexus MVP !

Ce dépôt contient la première version minimaliste de la plateforme E‑lab. Le but est de fournir les fonctionnalités essentielles pour la gestion d'échantillons, l'automatisation des protocoles et la collaboration en laboratoire.

## Objectif du projet

- Créer une base solide pour la plateforme BioNexus.
- Valider rapidement les concepts clés et obtenir des retours précoces.
- Poser les fondations pour évoluer ultérieurement.

## Stack envisagée

### Backend
- Django & Django REST Framework
- PostgreSQL

### Frontend
- React.js
- Vite ou Create React App
- TypeScript (optionnel)

### Infra & outils DevOps
- Docker & Docker Compose
- GitHub Actions
- Pytest & Jest/React Testing Library

## Organisation du dépôt

```
bionexus-mvp/
├── bionexus-platform/
│   ├── backend/   # Code Django principal
│   └── frontend/  # Code React
├── .github/       # Workflows CI
├── conftest.py    # Configuration tests backend
└── README.md
```

## Installation & lancement (local)

### 1. Via Docker

```
cd bionexus-platform
docker compose up --build
```

- Backend : <http://localhost:8000/>
- Frontend : <http://localhost:3000/>

### 2. Installation manuelle (optionnelle)

#### Backend

```
cd bionexus-platform/backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

L’API se lance sur <http://127.0.0.1:8000/>.

#### Frontend

```
cd bionexus-platform/frontend
npm install
npm run start
```

L’interface se lance sur <http://localhost:3000/>.

## Tests & qualité

- Backend : depuis `bionexus-platform/backend`, exécuter `pytest`.
- Frontend : depuis `bionexus-platform/frontend`, exécuter `npm test`.

## Contributions & workflow Git

1. Créez une branche `feature/...` pour chaque fonctionnalité ou correctif.
2. Soumettez une Pull Request vers `main` avec une description concise.
3. Assurez-vous que les tests passent avant de demander une relecture.

## Licence

À définir (ex. : MIT, Apache 2.0, etc.).

