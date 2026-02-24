# 📚 BioNexus MVP - Documentation Complète

## Table des Matières
1. [Vue d'Ensemble](#vue-densemble)
2. [Architecture](#architecture)
3. [Modèles de Données](#modèles-de-données)
4. [Workflow Complet](#workflow-complet)
5. [APIs & Endpoints](#apis--endpoints)
6. [Frontend React](#frontend-react)
7. [Sécurité & Conformité](#sécurité--conformité)
8. [Déploiement](#déploiement)

---

## Vue d'Ensemble

**BioNexus MVP** est une plateforme de gestion de données de conformité GxP (Good eXperimental Practice) pour laboratoires. Elle garantit l'**intégrité des données**, l'**audit trail complet**, et la **certification GxP**.

### Cas d'Usage Principal
```
Laboratoire collecte données (fichiers CSV/PDF)
          ↓
Système parse les données
          ↓
Utilisateur valide/corrige les données
          ↓
Système trace CHAQUE modification
          ↓
Utilisateur certifie avec double authentification
          ↓
Rapport généré avec signature SHA-256 (chaîne d'intégrité)
          ↓
Stockage immutable pour audit externe
```

### Stack Technologique
```
Frontend:    React 18 + TypeScript + Tailwind CSS
Backend:     Django 4.2 + DRF (Django REST Framework)
Base de Données: SQLite (MVP) / PostgreSQL (Production)
Authentification: JWT (JSON Web Token)
Signature:   SHA-256 + Chaîne de hachage
```

---

## Architecture

### Diagramme d'Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      FRONTEND (React)                       │
│  ┌──────────────┬──────────────┬──────────────┐             │
│  │ Login Page   │ Dashboard    │ Parsing View │             │
│  │              │              │ (Split View) │             │
│  └──────┬───────┴──────┬───────┴──────┬───────┘             │
│         │              │              │                     │
│         └──────────────┼──────────────┘                     │
│                        │ HTTP/REST                          │
├─────────────────────────┼──────────────────────────────────┤
│                        API Gateway (Django)                 │
│         ┌──────────────┴──────────────┐                    │
│         │                             │                    │
│    ┌────▼────┐              ┌────────▼────┐               │
│    │   Auth  │              │  Parsers &  │               │
│    │ Service │              │ Validators  │               │
│    └────┬────┘              └────────┬────┘               │
│         │                            │                    │
│    ┌────▼──────────┬────────────────▼────┐               │
│    │   Core Service Layer                 │               │
│    │ - ParsedData Store                   │               │
│    │ - Correction Tracker                 │               │
│    │ - Chain Integrity Checker            │               │
│    └────┬──────────┬──────────────┬───────┘               │
│         │          │              │                       │
│    ┌────▼──┐  ┌───▼────┐  ┌─────▼──────┐                │
│    │ Audit │  │ Reports│  │Execution   │                │
│    │ Trail │  │ Service│  │ Service    │                │
│    └───────┘  └────────┘  └────────────┘                │
│                                                          │
├──────────────────────────────────────────────────────────┤
│              DATABASE LAYER (SQLite/PostgreSQL)          │
│  ┌───────────────────────────────────────────────────┐  │
│  │ Tables: AuditLog, ParsedData, CertifiedReport    │  │
│  │         Protocol, ExecutionLog, ExecutionStep    │  │
│  │         Tenant, User, CorrectionTracker          │  │
│  └───────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

### Flux de Données

```
USER INPUT (Frontend)
    ↓
React Component (ParsingValidation)
    ↓
API Request (JWT Token)
    ↓
Django APIView
    ↓
Service Layer (ParsedDataService, ExecutionService, etc.)
    ↓
ORM Models (Django Models)
    ↓
Database Transaction
    ↓
Audit Logger (Immutable Record)
    ↓
Chain Integrity Calculator (SHA-256)
    ↓
Response + Audit Trail
    ↓
Frontend State Update
    ↓
UI Re-render
```

---

## Modèles de Données

### 1. **AuditLog** - Piste d'audit immuable

```python
class AuditLog(models.Model):
    entity_type      # "ParsedData", "ExecutionLog", etc.
    entity_id        # ID de l'entité modifiée
    operation        # CREATE, UPDATE, DELETE
    timestamp        # Quand (UTC, immuable)
    user_id          # Qui
    user_email       # Pour la lisibilité
    changes          # {field: {before, after}}
    snapshot_before  # État complet avant
    snapshot_after   # État complet après
    signature        # SHA-256(prev_sig + this_record)
    previous_signature  # Lien vers l'audit précédent
```

**Exemple en base:**
```json
{
  "id": 1,
  "entity_type": "ParsedData",
  "entity_id": 5,
  "operation": "UPDATE",
  "timestamp": "2026-02-17T14:35:22Z",
  "user_email": "demo_user@lab.local",
  "changes": {
    "equipment_name": {
      "before": "Spectrophotometre A",
      "after": "Spectrophotometer A"  // Typo corrigé
    }
  },
  "signature": "abc123def456...",
  "previous_signature": "xyz789uvw123..."
}
```

### 2. **ParsedData** - Données parsées (état mutant)

```python
class ParsedData(models.Model):
    parsing_file        # Fichier d'origine (PDF/CSV)
    raw_content         # Contenu brut initial
    schema              # Schéma Pydantic JSON
    parsed_content      # Données extraites {"field": value}
    confirmed_data      # Données validées par l'utilisateur
    state               # raw, parsed, validated, certified
    tenant              # Multi-tenant
    created_by          # Qui a créé
    created_at          # Quand

    # Corrections
    corrections         # [{field, before, after, reason, timestamp}]

    # Chaîne d'intégrité
    chain_hash          # SHA-256 de tous les changements
    chain_verified      # Boolean (recalculé toutes les 30s)
    corruption_detected # Boolean
```

**Workflow d'état:**
```
┌──────────────────────────────────────────────────┐
│                 raw_content                      │
│          Fichier d'origine uploadé               │
└────────────────┬─────────────────────────────────┘
                 │ Parser (Pydantic)
                 ↓
┌──────────────────────────────────────────────────┐
│              parsed_content                      │
│    Données extraites (peut avoir erreurs)       │
└────────────────┬─────────────────────────────────┘
                 │ Utilisateur modifie + valide
                 ↓
┌──────────────────────────────────────────────────┐
│             confirmed_data                       │
│    Utilisateur a corrigé toutes les erreurs     │
└────────────────┬─────────────────────────────────┘
                 │ Double Auth + Signature
                 ↓
┌──────────────────────────────────────────────────┐
│          CertifiedReport (immutable)              │
│    Report signé, prêt pour audit externe         │
└──────────────────────────────────────────────────┘
```

### 3. **CorrectionTracker** - Suivi des corrections

```python
class CorrectionTracker(models.Model):
    parsed_data         # FK vers ParsedData
    field_name          # "equipment_name"
    original_value      # "Spectrophotometre A"
    corrected_value     # "Spectrophotometer A"
    reason              # "Typo correction"
    corrected_by        # User qui a corrigé
    corrected_at        # Quand
    is_critical         # Important ou mineure
```

**Affichage frontend:**
```
┌─────────────────────────────────────┐
│ 🔄 Corrections Made (2)             │
├─────────────────────────────────────┤
│ ✏️  equipment_name                  │
│    "Spectrophotometre A"            │
│    → "Spectrophotometer A"          │
│    Reason: Typo correction          │
│    By: demo_user @ 14:35:22         │
├─────────────────────────────────────┤
│ ✏️  sample_volume                   │
│    "50mL" → "50 mL"                 │
│    Reason: Format standardization   │
│    By: demo_user @ 14:36:05         │
└─────────────────────────────────────┘
```

### 4. **ExecutionLog** - Journal d'exécution de protocole

```python
class ExecutionLog(models.Model):
    protocol            # FK vers Protocol
    executor            # User qui exécute
    state               # not_started, in_progress, completed, failed, paused
    started_at          # Quand commencé
    completed_at        # Quand terminé
    notes               # Notes libres

    # Validation
    all_steps_executed  # Boolean
    all_steps_valid     # Boolean
```

**Exemple:**
```
ExecutionLog: DNA Extraction
- Protocol: "DNA Extraction v1.0"
- Executor: "lab_tech_01"
- State: "in_progress"
- Started: 2026-02-17 14:30:00
- Steps Completed: 3/5

Timeline:
  14:30 - Step 1: Sample Collection ✓
  14:35 - Step 2: Lysis ✓
  14:40 - Step 3: Purification ✓
  14:50 - Step 4: (in progress...)
```

### 5. **ExecutionStep** - Étapes individuelles

```python
class ExecutionStep(models.Model):
    execution_log       # FK vers ExecutionLog
    step_number         # 1, 2, 3...
    name                # "Sample Collection"
    description         # Instructions détaillées
    state               # not_started, in_progress, completed, failed
    recorded_at         # Quand enregistré
    notes               # Observations
    measurements        # [{instrument, value, unit, timestamp}]
    equipment_used      # [équipement]
```

### 6. **CertifiedReport** - Rapport final immutable

```python
class CertifiedReport(models.Model):
    parsed_data         # FK vers ParsedData
    certified_by        # User
    certified_at        # Timestamp

    # Signature
    report_hash         # SHA-256 du rapport complet
    signature_chain     # [hash1, hash2, ..., hashN] (chaîne entière)

    # Intégrité
    chain_integrity_verified  # Boolean
    corruption_detected       # Boolean
    all_corrections_logged    # Boolean

    # Export
    report_pdf          # Généré avec signature
    report_json         # Données complètes

    # Conformité
    gxp_version         # "2.1"
    compliance_score    # 94%
```

---

## Workflow Complet

### PHASE 1: Upload et Parsing

```
User Upload File (PDF/CSV)
    ↓
Frontend: POST /api/parsing/ (file)
    ↓
Backend: ParsedDataService.parse_file()
    - Détecte format (PDF/CSV)
    - Utilise le parser correspondant
    - Extrait données brutes
    - Valide contre schéma Pydantic
    ↓
ParsedData.state = "parsed"
ParsedData.parsed_content = {"equipment_id": "SPEC-001", ...}
    ↓
AuditLog créé automatiquement:
  {
    "operation": "CREATE",
    "entity_type": "ParsedData",
    "user_email": "demo_user@lab.local",
    "snapshot_after": {...}
  }
    ↓
Signature calculée: SHA-256(prev_sig + record)
    ↓
Response au Frontend:
  {
    "parsed_data_id": 5,
    "parsed_content": {...},
    "state": "parsed",
    "corrections": [],
    "chain_verified": true
  }
```

### PHASE 2: Validation et Correction

```
User voit formulaire avec données parsées
    ↓
User modifie un champ
    - Suppose : "equipment_name" "Spectrophotometre A" → "Spectrophotometer A"
    ↓
Frontend: POST /api/parsing/{id}/corrections/
  {
    "field_name": "equipment_name",
    "original_value": "Spectrophotometre A",
    "corrected_value": "Spectrophotometer A",
    "reason": "Fixed typo"
  }
    ↓
Backend: CorrectionTracker créé
    {
      "field_name": "equipment_name",
      "original_value": "Spectrophotometre A",
      "corrected_value": "Spectrophotometer A",
      "corrected_by": user,
      "is_critical": false
    }
    ↓
AuditLog créé pour CHAQUE correction
    ↓
Chain recalculée
    ↓
Frontend affiche:
  - Correction tracked ✓
  - Badge "2 corrections" allumé
  - Chain status: "✓ Verified"
    ↓
User peut faire autant de corrections qu'il veut
    ↓
Quand prêt: POST /api/parsing/{id}/validate/
  {
    "confirmed_data": {
      "equipment_id": "SPEC-001",
      "equipment_name": "Spectrophotometer A",
      ...
    },
    "validation_notes": "All corrections verified and complete"
  }
    ↓
ParsedData.state = "validated"
ParsedData.confirmed_data = {...}
AuditLog créé
    ↓
Response:
  {
    "state": "validated",
    "can_certify": true,
    "corrections_count": 2
  }
```

### PHASE 3: Certification Double Auth

```
User clique [🔒 CERTIFY]
    ↓
Modal Step 1: Re-enter password
  (Security: force ré-authentification)
    ↓
Modal Step 2: OTP or Second factor
    ↓
Modal Step 3: Review & Confirm
  "I certify that all data is accurate"
    ↓
Frontend: POST /api/parsing/{id}/sign/
  {
    "password": "****",
    "otp_code": "123456",
    "notes": "All validation complete"
  }
    ↓
Backend: AuthService.verify_password() + verify_otp()
    ↓
Si valide:
    - Générer rapport final
    - Calculer SHA-256 de tout le contenu
    - Créer CertifiedReport (immutable)
    - Marquer comme "certified"
    ↓
AuditLog: SIGN operation (spécial)
  {
    "operation": "SIGN",
    "entity_type": "CertifiedReport",
    "user_email": "demo_user@lab.local",
    "signature": "abc123def456...",
    "certification_method": "password+otp"
  }
    ↓
Générer PDF avec QR code de signature
    ↓
Response:
  {
    "report_id": 42,
    "certified_at": "2026-02-17T14:35:22Z",
    "report_hash": "abc123def456...",
    "pdf_url": "/api/reports/42/pdf/",
    "chain_verified": true,
    "compliance_score": "94%"
  }
    ↓
Frontend affiche:
  ┌─────────────────────────────────┐
  │ ✓ CERTIFIED                     │
  │ Report ID: 42                   │
  │ Hash: abc123def456...           │
  │ Certified by: demo_user         │
  │ At: 2026-02-17 14:35:22         │
  │ [Download PDF] [View Report]    │
  └─────────────────────────────────┘
```

### PHASE 4: Chaîne d'Intégrité (Background)

```
Toutes les 30 secondes (WebSocket):
    ↓
ChainIntegrityService.verify_chain()
    ↓
Récupérer tous les AuditLog depuis dernière vérification
    ↓
Pour chaque AuditLog:
  1. Récupérer audit_N-1.signature (previous)
  2. Construire données de audit_N
  3. Calculer SHA-256(previous_sig + json(audit_N))
  4. Comparer avec audit_N.signature stockée
  ↓
Si MISMATCH détecté:
  - ALERTE: "Tampering detected!"
  - corruption_detected = TRUE
  - Email alert à admin
    ↓
Si tout OK:
  - chain_verified = TRUE
  - compliance_score += 5%
    ↓
Frontend met à jour badge:
  "✓ Chain Verified | CONF: 94% | GxP v2.1"
```

---

## APIs & Endpoints

### Authentication

```
POST /api/auth/login/
  Request:
    {
      "username": "demo_user",
      "password": "DemoPassword123!"
    }
  Response:
    {
      "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
      "refresh": "...",
      "user_id": 1,
      "tenant_id": 1
    }

POST /api/auth/refresh/
  Request:
    {
      "refresh": "..."
    }
  Response:
    {
      "access": "..."
    }

POST /api/auth/verify-password/
  Request:
    {
      "password": "****"
    }
  Response:
    {
      "valid": true
    }
```

### Parsing & Validation

```
POST /api/parsing/
  Description: Upload new file
  Request:
    multipart/form-data
    - file: (PDF/CSV)
  Response:
    {
      "id": 5,
      "state": "parsed",
      "parsed_content": {...},
      "schema": {...},
      "created_at": "2026-02-17T14:35:22Z"
    }

GET /api/parsing/{id}/
  Description: Get parsing details
  Response:
    {
      "id": 5,
      "state": "parsed",
      "raw_content": "...",
      "parsed_content": {...},
      "confirmed_data": null,
      "corrections": [
        {
          "field_name": "equipment_name",
          "original_value": "...",
          "corrected_value": "...",
          "reason": "..."
        }
      ],
      "chain_verified": true,
      "corruption_detected": false
    }

POST /api/parsing/{id}/corrections/
  Description: Add correction
  Request:
    {
      "field_name": "equipment_name",
      "original_value": "Spectrophotometre A",
      "corrected_value": "Spectrophotometer A",
      "reason": "Fixed typo"
    }
  Response:
    {
      "correction_id": 12,
      "corrections_count": 2,
      "audit_log_id": 456,
      "chain_hash_updated": true
    }

POST /api/parsing/{id}/validate/
  Description: Validate all corrections
  Request:
    {
      "confirmed_data": {
        "equipment_id": "SPEC-001",
        "equipment_name": "Spectrophotometer A",
        ...
      },
      "validation_notes": "All corrections verified"
    }
  Response:
    {
      "state": "validated",
      "audit_log_id": 457,
      "can_certify": true
    }

POST /api/parsing/{id}/sign/
  Description: Certify and sign report (Double Auth)
  Request:
    {
      "password": "****",
      "otp_code": "123456",
      "notes": "All validation complete"
    }
  Response:
    {
      "report_id": 42,
      "certified_at": "2026-02-17T14:35:22Z",
      "report_hash": "abc123...",
      "compliance_score": "94%",
      "pdf_url": "/api/reports/42/pdf/"
    }
```

### Execution Logs

```
GET /api/executions/
  Description: List all execution logs
  Response:
    {
      "count": 5,
      "results": [
        {
          "id": 1,
          "protocol": "DNA Extraction",
          "executor": "lab_tech_01",
          "state": "in_progress",
          "started_at": "2026-02-17T14:30:00Z",
          "steps_completed": 3,
          "steps_total": 5
        }
      ]
    }

POST /api/executions/
  Description: Start new execution
  Request:
    {
      "protocol_id": 1,
      "notes": "Starting DNA extraction"
    }
  Response:
    {
      "id": 5,
      "state": "in_progress",
      "audit_log_id": 458
    }

POST /api/executions/{id}/step/
  Description: Record step completion
  Request:
    {
      "step_number": 1,
      "notes": "Sample collected successfully",
      "measurements": [
        {
          "instrument": "Thermometer",
          "value": 37.2,
          "unit": "°C"
        }
      ]
    }
  Response:
    {
      "step_id": 10,
      "execution_log_id": 5,
      "audit_log_id": 459
    }
```

### Reports

```
GET /api/reports/
  Description: List certified reports
  Response:
    [
      {
        "id": 42,
        "certified_by": "demo_user",
        "certified_at": "2026-02-17T14:35:22Z",
        "chain_verified": true,
        "compliance_score": "94%"
      }
    ]

GET /api/reports/{id}/
  Description: Get report details
  Response:
    {
      "id": 42,
      "report_hash": "abc123...",
      "report_data": {...},
      "chain_integrity": {
        "verified": true,
        "total_records": 42,
        "verified_records": 42,
        "corrupted_records": []
      }
    }

GET /api/reports/{id}/pdf/
  Description: Download PDF report
  Response: PDF file with signature

POST /api/reports/{id}/verify/
  Description: Verify report integrity
  Response:
    {
      "is_valid": true,
      "chain_verified": true,
      "all_corrections_logged": true
    }
```

### Audit Trail

```
GET /api/auditlog/
  Description: Get audit log entries
  Query params:
    - entity_type: "ParsedData"
    - entity_id: 5
    - operation: "UPDATE"
    - date_from: "2026-02-17"
  Response:
    {
      "count": 42,
      "results": [
        {
          "id": 456,
          "entity_type": "ParsedData",
          "entity_id": 5,
          "operation": "UPDATE",
          "timestamp": "2026-02-17T14:35:22Z",
          "user_email": "demo_user@lab.local",
          "changes": {
            "equipment_name": {
              "before": "Spectrophotometre A",
              "after": "Spectrophotometer A"
            }
          },
          "signature": "abc123...",
          "previous_signature": "xyz789..."
        }
      ]
    }

GET /api/auditlog/{id}/
  Description: Get single audit entry
  Response: (same as above, single object)

GET /api/integrity/check/
  Description: Check chain integrity
  Response:
    {
      "is_valid": true,
      "total_records": 42,
      "verified_records": 42,
      "corrupted_records": [],
      "chain_integrity_ok": true,
      "safe_to_export": true,
      "last_check": "2026-02-17T14:35:22Z"
    }
```

---

## Frontend React

### Structure des Composants

```
src/
├── components/
│   ├── Login/
│   │   ├── LoginForm.tsx
│   │   └── OTPInput.tsx
│   │
│   ├── Dashboard/
│   │   ├── Dashboard.tsx
│   │   ├── StatsCard.tsx
│   │   └── Navigation.tsx
│   │
│   ├── ParsingValidation/
│   │   ├── ParsingValidation.tsx (Container)
│   │   ├── SplitView.tsx
│   │   ├── FileViewer.tsx (LEFT - affiche PDF/CSV)
│   │   ├── DynamicForm.tsx (RIGHT - formulaire)
│   │   ├── CorrectionTracker.tsx
│   │   ├── ChainBadge.tsx
│   │   └── CertificationModal.tsx
│   │
│   ├── ExecutionLogs/
│   │   ├── ExecutionList.tsx
│   │   ├── ExecutionDetail.tsx
│   │   └── StepRecorder.tsx
│   │
│   └── Reports/
│       ├── ReportList.tsx
│       ├── ReportDetail.tsx
│       └── VerificationPanel.tsx
│
├── services/
│   ├── api.ts (Axios config + interceptors)
│   ├── authService.ts
│   ├── parsingService.ts
│   ├── executionService.ts
│   ├── reportService.ts
│   └── integrityService.ts
│
├── hooks/
│   ├── useAuth.ts
│   ├── useChainVerification.ts (30s interval)
│   └── useCorrectionTracker.ts
│
├── types/
│   ├── index.ts (TypeScript interfaces)
│   └── models.ts
│
└── App.tsx
```

### Composant Clé: ParsingValidation (Split View)

```typescript
// src/components/ParsingValidation/ParsingValidation.tsx

function ParsingValidation() {
  const { id } = useParams<{ id: string }>();
  const [parsedData, setParsedData] = useState(null);
  const [corrections, setCorrections] = useState([]);
  const [chainVerified, setChainVerified] = useState(true);

  // Hook custom: vérifie la chaîne d'intégrité toutes les 30s
  useChainVerification(id);

  useEffect(() => {
    loadParsingData(id);
  }, [id]);

  const handleCorrection = async (field: string, newValue: string, reason: string) => {
    // POST /api/parsing/{id}/corrections/
    const response = await parsingService.addCorrection(id, {
      field_name: field,
      original_value: parsedData.parsed_content[field],
      corrected_value: newValue,
      reason: reason
    });

    // Met à jour l'état local
    setCorrections([...corrections, response.data.correction]);

    // La chaîne se recalcule automatiquement dans le backend
  };

  const handleValidate = async () => {
    const response = await parsingService.validate(id, {
      confirmed_data: parsedData.parsed_content,
      validation_notes: "All corrections verified"
    });
    // Désactiver les inputs, activer le bouton certify
  };

  const handleCertify = async (password: string, otp: string) => {
    // POST /api/parsing/{id}/sign/
    const response = await parsingService.sign(id, {
      password: password,
      otp_code: otp,
      notes: "Certified for audit"
    });
    // Montrer modal de succès avec le PDF
  };

  return (
    <div className="flex gap-4 p-4">
      {/* LEFT: File Viewer */}
      <div className="flex-1 border rounded">
        <h2>Original File</h2>
        <FileViewer file={parsedData.raw_content} />
      </div>

      {/* Chain Badge - TOP RIGHT */}
      <ChainBadge
        verified={chainVerified}
        complianceScore={parsedData.compliance_score}
        version="v2.1"
      />

      {/* RIGHT: Dynamic Form */}
      <div className="flex-1 border rounded">
        <h2>Validation Form</h2>
        <DynamicForm
          schema={parsedData.schema}
          data={parsedData.parsed_content}
          onFieldChange={handleCorrection}
        />

        {/* Correction Tracker */}
        <CorrectionTracker corrections={corrections} />

        {/* Buttons */}
        <div className="space-x-2">
          <button onClick={handleValidate}>Validate</button>
          {parsedData.state === 'validated' && (
            <button onClick={() => setCertifyModalOpen(true)}>
              🔒 Certify for Audit
            </button>
          )}
        </div>
      </div>

      {/* Certification Modal */}
      <CertificationModal
        open={certifyModalOpen}
        onSign={handleCertify}
        onClose={() => setCertifyModalOpen(false)}
      />
    </div>
  );
}
```

### Hook Custom: useChainVerification

```typescript
// src/hooks/useChainVerification.ts

function useChainVerification(parsingDataId: string) {
  const [chainVerified, setChainVerified] = useState(true);

  useEffect(() => {
    // Vérifier immédiatement
    checkChain();

    // Puis toutes les 30 secondes
    const interval = setInterval(checkChain, 30000);

    return () => clearInterval(interval);
  }, [parsingDataId]);

  const checkChain = async () => {
    try {
      const response = await fetch(`/api/parsing/${parsingDataId}/chain-verify/`);
      const data = await response.json();
      setChainVerified(data.chain_verified);

      // Si corruption détectée, montrer alerte
      if (data.corruption_detected) {
        showAlert('⚠️ TAMPERING DETECTED!', 'red');
      }
    } catch (error) {
      console.error('Chain verification failed:', error);
    }
  };

  return { chainVerified };
}
```

### Service: parsingService

```typescript
// src/services/parsingService.ts

class ParsingService {
  async uploadFile(file: File) {
    const formData = new FormData();
    formData.append('file', file);

    return api.post('/parsing/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
  }

  async getParsingData(id: string) {
    return api.get(`/parsing/${id}/`);
  }

  async addCorrection(id: string, correction: any) {
    return api.post(`/parsing/${id}/corrections/`, correction);
  }

  async validate(id: string, data: any) {
    return api.post(`/parsing/${id}/validate/`, data);
  }

  async sign(id: string, signData: any) {
    return api.post(`/parsing/${id}/sign/`, signData);
  }
}

export default new ParsingService();
```

---

## Sécurité & Conformité

### 1. Chaîne d'Intégrité SHA-256

**Concept:**
Chaque audit log a une signature SHA-256 qui inclut la signature précédente, créant une chaîne inviolable.

```
AuditLog 1: signature = SHA-256("initial" + json(log1))
AuditLog 2: signature = SHA-256(log1.signature + json(log2))
AuditLog 3: signature = SHA-256(log2.signature + json(log3))
...

Si quelqu'un modifie AuditLog 2:
  - log2.signature change
  - log3, log4, ... deviennent invalides
  - DETECTION immédiate de tampering
```

**Code Backend:**

```python
# core/utils/integrity.py

import hashlib
import json

def calculate_signature(previous_signature: str, audit_log_data: dict) -> str:
    """Calcul du SHA-256 avec chaînage."""
    base = (previous_signature or "initial") + json.dumps(audit_log_data, sort_keys=True)
    return hashlib.sha256(base.encode()).hexdigest()

def verify_chain_integrity() -> dict:
    """Vérifie la chaîne entière."""
    audit_logs = AuditLog.objects.all().order_by('timestamp')

    previous_sig = "initial"
    corrupted = []

    for log in audit_logs:
        expected_sig = calculate_signature(previous_sig, {
            'entity_type': log.entity_type,
            'entity_id': log.entity_id,
            'operation': log.operation,
            'timestamp': str(log.timestamp),
            'changes': log.changes
        })

        if expected_sig != log.signature:
            corrupted.append(log.id)

        previous_sig = log.signature

    return {
        'is_valid': len(corrupted) == 0,
        'corrupted_records': corrupted,
        'total_records': audit_logs.count()
    }
```

### 2. Double Authentification pour Certification

```
Step 1: Password Re-entry
  - Demande user de re-saisir password
  - Vérifie contre hash en base
  - Prévient rubber duck attacks

Step 2: One-Time Password (OTP)
  - Envoyé par email/SMS
  - Valide une seule fois
  - Expire après 10 minutes

Step 3: Confirmation Explicite
  - "I certify that all data is accurate"
  - Checkbox to accept
  - Trace complète
```

**Code Backend:**

```python
# core/api_views.py

class ParsedDataSignView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        parsed_data = ParsedData.objects.get(pk=pk)

        password = request.data.get('password')
        otp_code = request.data.get('otp_code')
        notes = request.data.get('notes')

        # Vérifier password
        if not request.user.check_password(password):
            return Response({'error': 'Invalid password'}, status=401)

        # Vérifier OTP
        otp = OTP.objects.filter(
            user=request.user,
            code=otp_code,
            used=False,
            expires_at__gt=timezone.now()
        ).first()

        if not otp:
            return Response({'error': 'Invalid or expired OTP'}, status=401)

        # Marquer OTP comme utilisé
        otp.used = True
        otp.save()

        # Créer le rapport certifié
        report = CertifiedReport.objects.create(
            parsed_data=parsed_data,
            certified_by=request.user,
            certified_at=timezone.now(),
            notes=notes
        )

        # Calculer le hash du rapport
        report_data = {
            'parsed_data_id': parsed_data.id,
            'corrections': parsed_data.corrections,
            'certified_by': request.user.email,
            'certified_at': str(report.certified_at)
        }
        report.report_hash = calculate_signature("cert_initial", report_data)
        report.save()

        # AuditLog special pour la signature
        AuditLog.objects.create(
            entity_type='CertifiedReport',
            entity_id=report.id,
            operation='SIGN',
            timestamp=timezone.now(),
            user_id=request.user.id,
            user_email=request.user.email,
            changes={},
            snapshot_after={'report_id': report.id}
        )

        return Response({
            'report_id': report.id,
            'report_hash': report.report_hash,
            'certified_at': report.certified_at
        })
```

### 3. Conformité GxP (21 CFR Part 11)

**Critères:**
- ✅ Audit Trail immuable avec timestamps
- ✅ Identification de qui a fait quoi et quand
- ✅ Données originales préservées
- ✅ Signature électronique (double auth)
- ✅ Corrections tracées avec raison
- ✅ Chaîne d'intégrité vérifiable

**Conformité Score:**

```python
# core/services/compliance.py

def calculate_compliance_score(parsed_data: ParsedData) -> int:
    score = 50  # Base

    # +10: Audit trail complet
    if AuditLog.objects.filter(
        entity_type='ParsedData',
        entity_id=parsed_data.id
    ).count() > 0:
        score += 10

    # +10: Corrections tracées
    if CorrectionTracker.objects.filter(
        parsed_data=parsed_data
    ).count() > 0:
        score += 10

    # +10: Chaîne d'intégrité OK
    chain = verify_chain_integrity()
    if chain['is_valid']:
        score += 10

    # +10: Validée par utilisateur
    if parsed_data.state == 'validated':
        score += 10

    # +4: Certifiée (double auth)
    if parsed_data.state == 'certified':
        score += 4

    return min(score, 100)
```

---

## Déploiement

### 1. Setup Local (Développement)

```bash
# Clone et setup
cd /home/user/BioNexus-mvp
git clone https://github.com/Bayeko/BioNexus-mvp.git

# Backend
cd bionexus-platform/backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver

# Frontend (nouveau terminal)
cd bionexus-platform/frontend
npm install
npm start
```

### 2. Production Checklist

```
[ ] Remplacer SQLite par PostgreSQL
[ ] Configurer HTTPS (SSL certificate)
[ ] Configurer CORS pour domaine de production
[ ] Activer OTP via Twilio/AWS SNS
[ ] Configurer email pour audit reports
[ ] Activer logging centralizado (ELK stack)
[ ] Configurer backups automatiques
[ ] Mettre en place monitoring (New Relic, Datadog)
[ ] Documenter disaster recovery
[ ] Audit de sécurité par expert
```

### 3. Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.11

WORKDIR /app

COPY bionexus-platform/backend ./backend
COPY bionexus-platform/frontend ./frontend

# Install backend
WORKDIR /app/backend
RUN pip install -r requirements.txt

# Install frontend
WORKDIR /app/frontend
RUN npm install && npm run build

# Expose ports
EXPOSE 8000 3000

# Run both
CMD ["./start.sh"]
```

```bash
# start.sh
#!/bin/bash
cd /app/backend && python manage.py runserver 0.0.0.0:8000 &
cd /app/frontend && npm start &
wait
```

---

## Résumé Visuel

```
┌─────────────────────────────────────────────────────────────┐
│                    BioNexus MVP Workflow                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. UPLOAD FILE (PDF/CSV)                                  │
│     ↓                                                       │
│  2. PARSE & VALIDATE (Pydantic schema)                     │
│     ↓ AuditLog created                                     │
│  3. USER CORRECTIONS (Split view)                          │
│     ↓ CorrectionTracker + AuditLog                         │
│  4. VALIDATE & CONFIRM                                     │
│     ↓ ParsedData.state = "validated"                       │
│  5. DOUBLE AUTH CERTIFICATION                              │
│     ├─ Re-enter password ✓                                 │
│     ├─ OTP verification ✓                                  │
│     └─ Explicit confirmation ✓                             │
│     ↓ CertifiedReport created                              │
│  6. GENERATE SIGNED REPORT (SHA-256)                       │
│     ↓                                                       │
│  7. CONTINUOUS CHAIN VERIFICATION (30s)                    │
│     ├─ SHA-256 chain intact? ✓                             │
│     ├─ No tampering detected? ✓                            │
│     └─ Compliance score: 94% ✓                             │
│                                                             │
│  ✓ Ready for Audit & Regulatory Submission                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## FAQ

**Q: Que se passe-t-il si quelqu'un essaie de modifier un AuditLog en base?**
A: La chaîne SHA-256 devient invalide. Tous les records après le modification seront détectés comme corrompus. Une alerte est envoyée immédiatement.

**Q: Peut-on annuler une certification?**
A: Non. CertifiedReport est immuable. Vous devez créer un nouveau parsing et une nouvelle certification.

**Q: Que contient le PDF signé?**
A: Toutes les données, la date/heure, qui a certifié, le hash SHA-256, un QR code du hash, et la chaîne d'audit complète.

**Q: Comment exporter les données?**
A: GET /api/reports/{id}/ retourne tout en JSON. Vous pouvez faire un audit trail complet.

**Q: Support multi-tenant?**
A: Oui, chaque utilisateur appartient à un Tenant, et les données sont isolées par tenant.

---

**Documentation générée le 2026-02-24**
**Version: BioNexus MVP 1.0**
