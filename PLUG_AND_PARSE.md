# 🔌 Plug-and-Parse Architecture Guide

## Aperçu

**Plug-and-Parse** est le système qui transforme BioNexus d'un service à un **produit scalable**. Au lieu de coder une nouvelle machine à chaque fois, vous déposez simplement un fichier de configuration JSON.

```
┌─────────────────────────────────────────────────────────┐
│  Admin dépose hamilton_microlab_star.json dans          │
│  /backend/connectors/                                   │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
          python manage.py load_connectors
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│  Base de données enregistre:                            │
│  - Connector (interface standard SiLA 2)                │
│  - ConnectorMapping (schéma FDL)                        │
│  - API endpoints actifs                                 │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
        Utilisateur upload un fichier CSV
                      │
                      ▼
    AI reconnaît: "Temp" → "temperature",
    "Vol" → "volume", "Sample_ID" → "sample_id"
                      │
                      ▼
      Utilisateur confirme les mappings
                      │
                      ▼
   TenantConnectorProfile sauvegarde la décision
                      │
                      ▼
  Prochains uploads du même labo utilisent
  automatiquement les mappings sauvegardés (✓ Plug-and-Play!)
```

---

## 🏗️ 3 Couches d'Architecture

### 1. **Hub de Drivers Abstraits (SiLA 2 Standard)**

#### Qu'est-ce que SiLA 2 ?
**SiLA 2** = "Standardization in Lab Automation" = **le Bluetooth des labos**

Au lieu que chaque machine ait son propre protocole propriétaire, SiLA 2 définit une interface commune.

#### Modèle: `Connector`
```python
from core.models import Connector

# Créer un connector
hamilton = Connector.objects.create(
    connector_id="hamilton-microlab-star",
    connector_name="Hamilton Microlab STAR",
    connector_type=Connector.LIQUID_HANDLER,
    version="1.0.0",
    status=Connector.ACTIVE,
    fdl_descriptor={
        "standard": "SiLA 2.0",
        "manufacturer": "Hamilton Company",
        "capabilities": ["aspirate", "dispense", "mix"],
        "output_format": "CSV"
    },
    pivot_model_mapping={
        "Sample ID": "sample_id",
        "Aspirated Volume": "aspirated_volume",
        "Timestamp": "timestamp"
    }
)
```

#### Types de Connecteurs Supportés
```
✓ liquid_handler     - Hamilton, Tecan, Eppendorf
✓ plate_reader       - BioTek, Tecan, Infinite
✓ incubator          - Température & humidité
✓ centrifuge         - Vitesse, durée
✓ spectrophotometer  - Absorbance (OD600, OD405)
✓ pcr_machine        - Ct values, amplification
✓ microscope         - Images, analyses
✓ storage            - Freezers, incubateurs
✓ other              - Équipement custom
```

#### Modèle: `ConnectorMapping` (FDL - Feature Definition Language)
```python
from core.models import ConnectorMapping

# Définir ce que cette machine peut envoyer
ConnectorMapping.objects.create(
    connector=hamilton,
    field_name="Aspirated Volume",
    data_type="float",
    unit="μL",
    is_required=True,
    min_value=0.0,
    max_value=1000.0,
    pivot_field="aspirated_volume",
    confidence_default=0.95  # Haute confiance (presque certain)
)

ConnectorMapping.objects.create(
    connector=hamilton,
    field_name="Status",
    data_type="string",
    is_required=True,
    validation_regex="^(success|error|warning)$",
    pivot_field="status",
    confidence_default=1.0  # Certitude absolue
)
```

---

### 2. **Mapping Dynamique par IA (AI-Powered Recognition)**

#### Le Problème
```
Même machine → Deux labos différents → Noms de colonnes différents

Labo A: "Temp", "Sample_ID", "Vol"
Labo B: "Temperature_Celsius", "Sample", "Volume_uL"

Sans AI: il faudrait recoder pour chaque labo.
Avec AI: une fois reconnu, c'est sauvegardé pour toujours.
```

#### Pivot Model (Golden Standard)
Le **Pivot Model** définit tous les champs connus dans BioNexus:

```python
from core.ai_mapping_engine import get_mapping_engine

engine = get_mapping_engine()

# Voir tous les champs du Pivot Model
for field_name, field_info in engine.pivot_model.items():
    print(f"{field_name}: {field_info['description']}")
```

**Champs disponibles (~20+):**
```
SAMPLES:
  - sample_id          → Unique identifier
  - sample_name        → Human name
  - plate_id           → Container ID
  - well_position      → A1, H12, etc.

ENVIRONMENT:
  - temperature        → °C
  - humidity           → %

LIQUID HANDLING:
  - volume             → μL
  - dispensed_volume   → μL
  - aspirated_volume   → μL

OPTICAL:
  - absorbance         → OD values
  - fluorescence       → Intensity
  - luminescence       → Signal

MOLECULAR:
  - dna_concentration  → ng/μL
  - ct_value           → qPCR threshold
  - amplification_status → yes/no

TIME:
  - timestamp          → ISO 8601
  - duration           → seconds

STATUS:
  - status             → success/error/warning
  - quality_flag       → ok/warning/fail
```

#### AI Recognition Engine
```python
from core.ai_mapping_engine import get_mapping_engine

engine = get_mapping_engine(threshold=0.7)

# Machine envoie: ["Temp", "Sample_ID", "Vol", "UnknownField"]
incoming = ["Temp", "Sample_ID", "Vol", "UnknownField"]

result = engine.suggest_mappings(incoming)

# Résultat:
# {
#     "Temp": "temperature" (confidence: 0.90),
#     "Sample_ID": "sample_id" (confidence: 0.80),
#     "Vol": "volume" (confidence: 0.90),
#     "UnknownField": None (confidence: 0.00)  ← pas confiant
# }
```

#### Strategies de Reconnaissance
```
1. Exact Match (100% confiance)
   "temperature" == "temperature" → 1.0

2. Substring Match (90% confiance)
   "temperature_celsius" contient "temperature" → 0.9

3. Word Overlap (jusqu'à 80% confiance)
   "temp_celsius" et "temperature"
   shared word: "temp" → 0.6-0.8

4. No Match (0% confiance)
   "weirdcolumn" → None
```

#### Modèle: `TenantConnectorProfile`
```python
from core.models import TenantConnectorProfile

# Après que l'utilisateur confirme les mappings
profile = TenantConnectorProfile.objects.create(
    tenant=request.user.tenant,
    connector=hamilton,
    machine_instance_name="Hamilton-Lab1",
    column_mapping={
        "Temp": "temperature",
        "Sample_ID": "sample_id",
        "Vol": "volume"
    },
    mapping_confidence_scores={
        "Temp": 0.98,
        "Sample_ID": 0.95,
        "Vol": 0.87
    },
    confirmed_by=request.user,
    confirmed_at=timezone.now(),
    is_active=True
)

# Prochains uploads → utilise automatiquement ce mapping ✓
```

---

### 3. **Architecture Hot-Plug (Runtime Loading)**

#### Directory Structure
```
backend/
├── connectors/                          ← Hot-Plug Directory
│   ├── __init__.py
│   ├── loader.py                        ← Dynamic loader
│   ├── hamilton_microlab_star.json      ← Config 1
│   ├── tecan_freedom_evo.json           ← Config 2
│   ├── biotek_plate_reader.json         ← Config 3
│   └── ... (add more without touching core code)
├── core/
│   ├── models.py                        ← Connector, ConnectorMapping, etc.
│   ├── ai_mapping_engine.py             ← AI recognition
│   ├── connector_views.py                ← API endpoints
│   ├── management/commands/
│   │   └── load_connectors.py           ← Management command
│   └── ...
```

#### Ajouter une Nouvelle Machine (Sans Coder!)

**Étape 1:** Créer le JSON config
```bash
# File: /connectors/tecan_freedom_evo.json
{
  "connector_id": "tecan-freedom-evo",
  "connector_name": "Tecan Freedom EVO",
  "description": "Tecan Freedom EVO liquid handler",
  "connector_type": "liquid_handler",
  "version": "1.0.0",
  "status": "active",
  "fdl_descriptor": {
    "standard": "SiLA 2.0",
    "manufacturer": "Tecan",
    "capabilities": ["aspirate", "dispense", "incubate"]
  },
  "pivot_model_mapping": {
    "Sample ID": "sample_id",
    "Aspirated mL": "aspirated_volume",
    "Status Code": "status"
  }
}
```

**Étape 2:** Charger la config
```bash
python manage.py load_connectors
# Found 1 connector config(s)
# ✓ Loaded tecan_freedom_evo.json
# 1/1 connectors loaded successfully
```

**Étape 3:** C'est tout! Les API endpoints sont maintenant disponibles ✓

#### Loader (Dynamic Loading)
```python
from connectors.loader import ConnectorLoader

loader = ConnectorLoader(connectors_dir="./connectors")
loaded = loader.load_all()

# Résultat:
# {
#     "hamilton-microlab-star": {...},
#     "tecan-freedom-evo": {...}
# }

# Sync vers database
loader.sync_to_database()
```

---

## 📡 API Endpoints

### 1. List All Connectors
```bash
GET /api/connectors/

Response:
[
  {
    "connector_id": "hamilton-microlab-star",
    "connector_name": "Hamilton Microlab STAR",
    "connector_type": "liquid_handler",
    "version": "1.0.0",
    "status": "active",
    "description": "...",
    "output_fields": [
      {
        "field_name": "Aspirated Volume",
        "data_type": "float",
        "unit": "μL",
        "is_required": true,
        "pivot_field": "aspirated_volume"
      },
      ...
    ]
  }
]
```

### 2. Get Connector Details
```bash
GET /api/connectors/hamilton-microlab-star/

Response:
{
  "connector_id": "hamilton-microlab-star",
  "connector_name": "Hamilton Microlab STAR",
  "description": "Hamilton Microlab STAR liquid handling robot",
  "connector_type": "liquid_handler",
  "version": "1.0.0",
  "status": "active",
  "fdl_descriptor": {
    "standard": "SiLA 2.0",
    "manufacturer": "Hamilton Company",
    "capabilities": ["aspirate", "dispense", "mix"]
  },
  "pivot_model_mapping": {
    "Sample ID": "sample_id",
    "Aspirated Volume": "aspirated_volume"
  },
  "output_fields": [...]
}
```

### 3. AI Suggests Column Mappings
```bash
POST /api/mappings/suggest/

Request:
{
  "incoming_columns": ["Temp", "Sample_ID", "Vol"],
  "connector_id": "hamilton-microlab-star"
}

Response:
{
  "incoming_columns": ["Temp", "Sample_ID", "Vol"],
  "suggestions": {
    "Temp": {
      "pivot_field": "temperature",
      "confidence": 0.98,
      "description": "Temperature in Celsius",
      "unit": "°C"
    },
    "Sample_ID": {
      "pivot_field": "sample_id",
      "confidence": 0.95,
      "description": "Unique identifier for the sample",
      "unit": ""
    },
    "Vol": {
      "pivot_field": "volume",
      "confidence": 0.87,
      "description": "Volume in microliters",
      "unit": "μL"
    }
  },
  "summary": "AI suggested 3/3 mappings with high confidence"
}
```

### 4. User Confirms & Saves Mappings
```bash
POST /api/mappings/confirm/

Request:
{
  "connector_id": "hamilton-microlab-star",
  "machine_instance_name": "Hamilton-Lab1",
  "column_mapping": {
    "Temp": "temperature",
    "Sample_ID": "sample_id",
    "Vol": "volume"
  },
  "mapping_confidence_scores": {
    "Temp": 0.98,
    "Sample_ID": 0.95,
    "Vol": 0.87
  }
}

Response:
{
  "success": true,
  "tenant_profile_id": 123,
  "message": "Mapping saved for Hamilton-Lab1",
  "profile": {
    "id": 123,
    "machine_instance_name": "Hamilton-Lab1",
    "connector": "Hamilton Microlab STAR",
    "column_mapping": {...},
    "mapping_confidence_scores": {...},
    "confirmed_at": "2024-01-15T10:30:00Z",
    "confirmed_by": "john.doe",
    "is_active": true
  }
}
```

### 5. List Tenant's Saved Profiles
```bash
GET /api/tenant-profiles/

Response:
[
  {
    "id": 123,
    "machine_instance_name": "Hamilton-Lab1",
    "connector": "Hamilton Microlab STAR",
    "connector_id": "hamilton-microlab-star",
    "column_mapping": {
      "Temp": "temperature",
      "Sample_ID": "sample_id",
      "Vol": "volume"
    },
    "mapping_confidence_scores": {...},
    "confirmed_at": "2024-01-15T10:30:00Z",
    "confirmed_by": "john.doe",
    "is_active": true
  }
]
```

### 6. Deactivate a Profile
```bash
DELETE /api/tenant-profiles/123/deactivate/

Response:
{
  "success": true,
  "message": "Profile deactivated"
}
```

---

## 🔄 Workflow Complet: Du Fichier CSV à la Base de Données

### Utilisateur Final Perspective

```
1️⃣  Admin dépose hamilton_microlab_star.json dans /connectors/
    python manage.py load_connectors
    ✓ Connector enregistré

2️⃣  Technician upload un fichier CSV
    Colonnes: "Temp", "Sample_ID", "Vol", "Status"

3️⃣  Frontend appelle /api/mappings/suggest/
    AI répond:
    - "Temp" → "temperature" (98% confiance)
    - "Sample_ID" → "sample_id" (95% confiance)
    - "Vol" → "volume" (87% confiance)
    - "Status" → "status" (100% confiance)

4️⃣  Technician voit l'interface:
    ┌─────────────────────────────────────────┐
    │ AI a reconnu les colonnes:              │
    │                                         │
    │ [✓] Temp → temperature                  │
    │ [✓] Sample_ID → sample_id               │
    │ [✓] Vol → volume                        │
    │ [✓] Status → status                     │
    │                                         │
    │ Cliquez pour confirmer si correct       │
    │                                         │
    │      [ Confirm ]    [ Edit ]            │
    └─────────────────────────────────────────┘

5️⃣  Technician clique "Confirm"
    POST /api/mappings/confirm/
    TenantConnectorProfile créé ✓

6️⃣  Prochains uploads de Hamilton-Lab1:
    ✓ Mappings appliqués automatiquement
    ✓ Zéro re-configuration
    ✓ Vitesse 10x plus rapide
```

---

## 🧪 Test & Development

### Charger Connectors (Development)
```bash
cd /home/user/BioNexus-mvp/bionexus-platform/backend

# Charger tous les connectors depuis /connectors directory
python manage.py load_connectors

# Avec rebuild (supprimer & recréer les mappings)
python manage.py load_connectors --rebuild

# Avec chemin custom
python manage.py load_connectors --connectors-dir /path/to/connectors
```

### Tester AI Engine (Python Shell)
```python
python manage.py shell

from core.ai_mapping_engine import get_mapping_engine

engine = get_mapping_engine()

# Test 1: Exact matches
result = engine.suggest_mappings(["temperature", "volume", "sample_id"])
# Output: All 3 with 1.0 confidence

# Test 2: Variations
result = engine.suggest_mappings(["Temp", "Vol", "Sample ID"])
# Output: temperature (0.9), volume (0.9), sample_id (0.8)

# Test 3: Mixed
result = engine.suggest_mappings(["Temp", "WeirdColumn", "Status"])
# Output: Temp→temperature, WeirdColumn→None, Status→status

# Test 4: Word overlap
result = engine.suggest_mappings(["temperature_celsius"])
# Output: temperature (0.9 substring match)
```

### Tester via cURL
```bash
# List connectors
curl http://localhost:8000/api/connectors/

# Get one connector
curl http://localhost:8000/api/connectors/hamilton-microlab-star/

# Suggest mappings
curl -X POST http://localhost:8000/api/mappings/suggest/ \
  -H "Content-Type: application/json" \
  -d '{
    "incoming_columns": ["Temp", "Sample_ID", "Vol"],
    "connector_id": "hamilton-microlab-star"
  }'
```

---

## 📋 Fichier JSON Connector (Template)

```json
{
  "connector_id": "machine-name-slug",
  "connector_name": "Human-Readable Machine Name",
  "description": "What this machine does, manufacturer, use case",
  "connector_type": "liquid_handler",
  "version": "1.0.0",
  "status": "active",
  "fdl_descriptor": {
    "standard": "SiLA 2.0",
    "manufacturer": "Manufacturer Name",
    "model": "Model Number",
    "capabilities": ["aspirate", "dispense", "incubate"],
    "output_format": "CSV"
  },
  "pivot_model_mapping": {
    "Machine Column Name 1": "pivot_field_1",
    "Machine Column Name 2": "pivot_field_2",
    "Machine Column Name 3": "pivot_field_3"
  }
}
```

---

## 🎯 Avantages du Plug-and-Parse

| Avant | Après (Plug-and-Parse) |
|-------|------------------------|
| Ajouter machine = modifier code | Ajouter machine = déposer JSON |
| Recoder pour chaque labo | AI reconnaît automatiquement |
| Déploiement = arrêter l'app | Déploiement = `python manage.py load_connectors` |
| Maintenance = difficult | Maintenance = facile (JSON) |
| Support machines = limité | Support machines = extensible |
| Time-to-market = lent | Time-to-market = rapide |

---

## 🚀 Prochaines Étapes

- [ ] Ajouter plus de connecteurs (Tecan, BioTek, Eppendorf, etc.)
- [ ] UI React pour visualiser & confirmer les mappings
- [ ] Validation de schéma JSON au upload
- [ ] Historique des mappings (audit trail)
- [ ] Machine learning avancé (apprendre des patterns)
- [ ] Support pour machine settings (température, vitesse, etc.)

---

## 📚 Références

- **SiLA 2 Standard**: https://www.sila-standard.org/
- **Feature Definition Language (FDL)**: SiLA 2 specification document
- **Django Models**: `core/models.py` (Connector, ConnectorMapping, TenantConnectorProfile)
- **AI Engine**: `core/ai_mapping_engine.py`
- **Loader**: `connectors/loader.py`
- **API Views**: `core/connector_views.py`

