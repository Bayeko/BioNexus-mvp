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

## 🔌 Plug-and-Parse Architecture

BioNexus intègre une architecture **hot-plug** qui permet d'ajouter de nouvelles machines sans coder.

### Quick Start
```bash
# 1. Déposer un fichier JSON dans /backend/connectors/
# 2. Charger les connecteurs
python manage.py load_connectors

# 3. L'API est prête!
curl http://localhost:8000/api/connectors/
```

### Features
- **SiLA 2 Standard**: Interface standardisée pour toutes les machines
- **AI Column Recognition**: L'IA reconnaît automatiquement les colonnes entrantes
- **Tenant Profiles**: Chaque labo peut configurer ses machines indépendamment
- **Hot-Plug**: Ajouter une machine = déposer un JSON (zéro redéploiement)

👉 **Voir la documentation complète**: [PLUG_AND_PARSE.md](./PLUG_AND_PARSE.md)

### Exemple
```bash
# Ajouter une nouvelle machine (Hamilton Microlab STAR)
# File: /backend/connectors/hamilton_microlab_star.json
{
  "connector_id": "hamilton-microlab-star",
  "connector_name": "Hamilton Microlab STAR",
  "connector_type": "liquid_handler",
  "version": "1.0.0",
  "status": "active",
  "pivot_model_mapping": {
    "Sample ID": "sample_id",
    "Aspirated Volume": "aspirated_volume",
    "Timestamp": "timestamp"
  }
}

# Recharger
python manage.py load_connectors

# C'est tout! Endpoints disponibles:
# GET  /api/connectors/
# GET  /api/connectors/hamilton-microlab-star/
# POST /api/mappings/suggest/
# POST /api/mappings/confirm/
# GET  /api/tenant-profiles/
```

## Tests
- Backend : depuis `bionexus-platform/backend`, exécuter `pytest`.
- Frontend : depuis `bionexus-platform/frontend`, exécuter `npm test`.

## Contributions
1. Créez une branche `feature/...` pour chaque fonctionnalité ou correctif.
2. Soumettez une Pull Request vers `main` avec une description concise.
3. Assurez-vous que les tests passent avant de demander une relecture.

## Licence
À définir (ex. : MIT, Apache 2.0, etc.).
