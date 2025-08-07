# BioNexus MVP

## Aperçu
BioNexus MVP est une version minimaliste de la plateforme E-lab offrant les fonctionnalités essentielles pour la gestion d'échantillons, l'automatisation des protocoles et la collaboration en laboratoire.

## Stack
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

## Installation

### Via Docker
```bash
cd bionexus-platform
docker compose up --build
```
Backend : http://localhost:8000/
Frontend : http://localhost:3000/

### Installation manuelle

#### Backend (Django)
```bash
cd bionexus-platform/backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```
API disponible sur http://127.0.0.1:8000/

#### Frontend (React)
```bash
cd bionexus-platform/frontend
npm install
npm run start
```
Interface disponible sur http://localhost:3000/

## Tests
- Backend : depuis `bionexus-platform/backend`, exécuter `pytest`.
- Frontend : depuis `bionexus-platform/frontend`, exécuter `npm test`.

## Contributions
1. Créez une branche `feature/...` pour chaque fonctionnalité ou correctif.
2. Soumettez une Pull Request vers `main` avec une description concise.
3. Assurez-vous que les tests passent avant de demander une relecture.

## Licence
À définir (ex. : MIT, Apache 2.0, etc.).
