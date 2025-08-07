# BioNexus MVP

Bienvenue dans le projet BioNexus MVP !

Ce dépôt contient la première version minimaliste (Minimum Viable Product) de la plateforme E-lab, visant à fournir les fonctionnalités essentielles pour la gestion d’échantillons, l’automatisation des protocoles et la collaboration en laboratoire.

## Objectif du projet
- Créer une base solide pour la plateforme BioNexus : gestion des échantillons, protocoles de laboratoire, intégration avec les équipements, etc.
- Valider rapidement les concepts clés et obtenir des retours précoces (feedback utilisateurs, équipe métier).
- Poser les fondations pour évoluer ultérieurement (analyses avancées, reporting, automatisation plus poussée, etc.).

## Stack envisagée

### Backend
- Django (Python) – rapidité de développement, fiabilité du framework et ORM robuste.
- Django REST Framework (DRF) – exposition d’API REST et gestion de l’authentification, de la sérialisation et de la pagination.
- PostgreSQL – base de données relationnelle fiable offrant des fonctionnalités avancées (index GIN, etc.).

### Frontend
- React.js – bibliothèque populaire pour des interfaces dynamiques.
- Create React App ou Vite pour simplifier la configuration.
- TypeScript (optionnel) – meilleure maintenabilité et détection des erreurs.
- Redux / React Query (optionnel) – gestion d’état ou mise en cache des requêtes API si l’application grandit rapidement.

### Infra & outils DevOps
- Docker et Docker Compose pour standardiser l’environnement (conteneurs pour Django/PostgreSQL et pour React).
- GitHub Actions pour l’intégration continue (tests, lint, vérification des dépendances).
- Tests unitaires & d’intégration : Pytest pour Python et Jest/React Testing Library pour le frontend.

## Organisation du dépôt
La structure proposée est la suivante :

```
bionexus-mvp/
 ├─ backend/
 │   ├─ bionexus/          # Code Django principal (settings, urls, etc.)
 │   ├─ apps/              # Modules spécifiques (ex : échantillons, protocoles)
 │   ├─ requirements.txt   # Dépendances Python
 │   └─ ...
 ├─ frontend/
 │   ├─ src/
 │   ├─ public/
 │   ├─ package.json
 │   └─ ...
 ├─ docs/
 │   └─ ...               # Documentation fonctionnelle, specs, maquettes
 ├─ docker-compose.yml
 ├─ .github/
 │   └─ workflows/         # Configuration GitHub Actions (CI)
 ├─ .gitignore
 ├─ README.md              # Ce fichier
 └─ ...
```

- `backend/` : code Python (Django), configuration DRF et fichier `requirements.txt`.
- `frontend/` : code source React (ou TypeScript React), configurations Webpack/Vite, etc.
- `docs/` : documentation supplémentaire, cahier des charges, spécifications techniques ou fonctionnelles.
- `docker-compose.yml` : orchestration des conteneurs (backend + base de données + frontend).

## Installation & lancement (local)

### 1. Cloner le dépôt
```bash
git clone https://github.com/<votre-org-ou-utilisateur>/bionexus-mvp.git
cd bionexus-mvp
```

### 2. Configuration par Docker
```bash
# Lancement simultané des conteneurs backend, frontend et base de données
docker-compose up --build
```
- Backend : http://localhost:8000/
- Frontend : http://localhost:3000/ (selon la configuration)

### 3. Configuration manuelle (optionnelle)

#### a) Installation backend (Django)
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```
L’API se lance par défaut sur http://127.0.0.1:8000.

#### b) Installation frontend (React)
```bash
cd frontend
npm install
npm run start
```
L’interface se lance par défaut sur http://localhost:3000.

## Tests & qualité
- **Backend** : depuis `backend/`, exécuter `pytest`.
- **Frontend** : depuis `frontend/`, exécuter `npm test`.

## Contributions & workflow Git
1. Créez une branche `feature/...` pour chaque fonctionnalité ou correctif.
2. Soumettez une Pull Request vers `main` (ou `develop` si utilisée) avec une description concise.
3. Assurez-vous que les tests passent avant de demander une relecture.

## Roadmap & évolution
- **Phase 1 (MVP)** : gestion des échantillons, authentification, premier protocole automatisé.
- **Phase 2** : intégration des équipements, collaboration en temps réel.
- **Phase 3** : analyses avancées, reporting réglementaire, optimisation des performances.

## Support
Pour toute question, suggestion ou rapport de bug :
- Ouvrez une issue sur GitHub.
- Contactez l’équipe par e-mail (ex. : support@bionexus.io).

## Licence
À définir (ex. : MIT, Apache 2.0, etc.).
