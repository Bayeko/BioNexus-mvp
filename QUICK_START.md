# 🚀 BioNexus MVP - Quick Start Guide

## 📋 En 5 Minutes: Comment Ça Marche

### Architecture Visuelle

```
┌──────────────────────────────────────────────────────────┐
│                   UTILISATEUR                            │
│         (Navigateur Web - http://localhost:3000)         │
└────────────────────┬─────────────────────────────────────┘
                     │ Frontend React
                     ├─ Login Page
                     ├─ Dashboard
                     ├─ Parsing Validation (SPLIT VIEW)
                     ├─ Execution Logs
                     └─ Reports
                     │
┌────────────────────▼─────────────────────────────────────┐
│              BACKEND DJANGO API                          │
│        (http://localhost:8000/api/)                      │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │ AuthService    → Verify password + OTP             │ │
│  │ ParsingService → Parse file + Validate data        │ │
│  │ ExecutionService → Track protocol execution        │ │
│  │ ReportService  → Generate certified reports       │ │
│  │ ChainService   → Verify SHA-256 integrity         │ │
│  └────────────────────────────────────────────────────┘ │
│                     ↓ ORM Django                         │
└────────────────────┬─────────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────────┐
│          DATABASE (SQLite / PostgreSQL)                  │
│                                                          │
│  Tables:                                                │
│  - AuditLog (Immuable, SHA-256 chaîne)                │
│  - ParsedData (Données parsées, état)                 │
│  - CorrectionTracker (Qui a corrigé quoi)            │
│  - CertifiedReport (Rapport final signé)             │
│  - ExecutionLog (Journal d'exécution)                │
│  - ExecutionStep (Étapes individuelles)              │
│  - User, Tenant (Authentification)                   │
└──────────────────────────────────────────────────────────┘
```

---

## ⚡ Lancer le Système

### Terminal 1: Backend Django

```bash
cd /home/user/BioNexus-mvp/bionexus-platform/backend

# 1. Créer base de données et migrations
python manage.py migrate --run-syncdb

# 2. Créer utilisateur test (optionnel)
python manage.py shell
>>> from core.models import Tenant, User
>>> tenant = Tenant.objects.create(name="Lab Test", slug="lab-test")
>>> user = User.objects.create_user(
...     username="demo_user",
...     email="demo@lab.local",
...     password="DemoPassword123!",
...     tenant=tenant
... )
>>> exit()

# 3. Lancer serveur Django
python manage.py runserver 0.0.0.0:8000

# ✓ Vous verrez:
# Starting development server at http://0.0.0.0:8000/
# Quit the server with CONTROL-C.
```

### Terminal 2: Frontend React

```bash
cd /home/user/BioNexus-mvp/bionexus-platform/frontend

# 1. Installer dépendances
npm install

# 2. Lancer serveur de développement
npm start

# ✓ Le navigateur s'ouvre automatiquement sur:
# http://localhost:3000
```

---

## 🎬 Workflow Complet - Étape par Étape

### ÉTAPE 1️⃣: Login

```
URL: http://localhost:3000/login

Écran:
┌─────────────────────────────────┐
│     BioNexus Login              │
├─────────────────────────────────┤
│ Username [demo_user          ]  │
│ Password [••••••••••        ]   │
│                                 │
│        [LOGIN]                  │
└─────────────────────────────────┘

Entrez:
- Username: demo_user
- Password: DemoPassword123!
```

### ÉTAPE 2️⃣: Dashboard

```
URL: http://localhost:3000/dashboard

Écran:
┌──────────────────────────────────────────┐
│ 🏠 BioNexus Dashboard                    │
├──────────────────────────────────────────┤
│                                          │
│  📊 Statistics                           │
│  ├─ Total Executions: 0                  │
│  ├─ Certified Reports: 0                 │
│  ├─ Audit Records: 0                     │
│  └─ Chain Status: ✓ Valid                │
│                                          │
│  🔗 Navigation                           │
│  ├─ [Parsing Validation] ← CLICK HERE   │
│  ├─ [Execution Logs]                    │
│  ├─ [Reports]                           │
│  └─ [Audit Trail]                       │
│                                          │
└──────────────────────────────────────────┘
```

### ÉTAPE 3️⃣: Upload File

```
URL: http://localhost:3000/parsing

Écran:
┌──────────────────────────────────────────┐
│ 📄 Parsing Validation - Upload           │
├──────────────────────────────────────────┤
│                                          │
│  [📁 Choose File (CSV/PDF)]              │
│                                          │
│  File: sample_data.csv                   │
│  [Upload]                                │
│                                          │
└──────────────────────────────────────────┘

Résultat:
✓ File uploaded
✓ Parsing started
✓ Auto-redirect to validation view
```

### ÉTAPE 4️⃣: SPLIT VIEW MAGIC 🎨

```
URL: http://localhost:3000/parsing/5/

Écran (après upload):

┌─────────────────────────────────────────────────────────────┐
│ 🛡️ CHAIN VERIFIED │ CONF: 73% │ GxP v2.1 │ ⏱️ 30s verify   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌────────────────────────┬──────────────────────────────┐ │
│  │                        │                              │ │
│  │    LEFT SIDE:          │   RIGHT SIDE:               │ │
│  │  Original File (PDF)   │   Validation Form           │ │
│  │                        │                              │ │
│  │  ┌──────────────────┐  │  Equipment ID:              │ │
│  │  │                  │  │  [SPEC-001]                 │ │
│  │  │   CSV/PDF Data   │  │  Equipment Name:            │ │
│  │  │                  │  │  [Spectrophotometer A]      │ │
│  │  │   Scroll to view │  │  Sample ID:                 │ │
│  │  │   all content    │  │  [SAMPLE-123]               │ │
│  │  │                  │  │  Date:                      │ │
│  │  │                  │  │  [2026-02-17]               │ │
│  │  └──────────────────┘  │                              │ │
│  │                        │  🔄 Corrections Made (1)    │ │
│  │                        │  ├─ equipment_name          │ │
│  │                        │  │  "Spectrophotometre A"   │ │
│  │                        │  │  → "Spectrophotometer A"  │ │
│  │                        │  │  Reason: "Fixed typo"     │ │
│  │                        │  └─ By: demo_user @ 14:35   │ │
│  │                        │                              │ │
│  │                        │  [Validate] [🔒 Certify]    │ │
│  └────────────────────┬──────────────────────────────────┘ │
│                       │                                    │
└───────────────────────┴────────────────────────────────────┘
```

**Qu'est-ce qui se passe?**
- LEFT: Affiche le fichier original (PDF/CSV) qu'on a uploadé
- RIGHT: Formulaire dynamique basé sur Pydantic schema
- Chaque modification = AuditLog + CorrectionTracker
- Chain badge = vérifié toutes les 30 secondes
- Compliance score = augmente au fur et à mesure

### ÉTAPE 5️⃣: Faire des Corrections

```
User modifie un champ dans le formulaire RIGHT:

"Spectrophotometre A" → "Spectrophotometer A" (fix typo)

Backend:
1. CorrectionTracker créé
   {
     "field": "equipment_name",
     "original": "Spectrophotometre A",
     "corrected": "Spectrophotometer A",
     "reason": "Fixed typo"
   }

2. AuditLog créé
   {
     "operation": "UPDATE",
     "entity_type": "ParsedData",
     "user_email": "demo_user@lab.local",
     "changes": { "equipment_name": {...} },
     "signature": "abc123def456..."
   }

3. Chain recalculée
   - Vérify tous les audit logs
   - Calc SHA-256(prev_sig + current)
   - Vérifié? chain_verified = TRUE
   - Sinon? corruption_detected = TRUE

Frontend:
- UI met à jour
- Correction counter = 1
- Chain badge reste ✓ VERIFIED
- Compliance score += 10%
```

### ÉTAPE 6️⃣: Valider

```
User clique [Validate]

Request:
POST /api/parsing/5/validate/
{
  "confirmed_data": {
    "equipment_id": "SPEC-001",
    "equipment_name": "Spectrophotometer A",
    "sample_id": "SAMPLE-123",
    "date": "2026-02-17"
  },
  "validation_notes": "All corrections verified and complete"
}

Response:
{
  "state": "validated",
  "corrections_count": 1,
  "can_certify": true,
  "audit_log_id": 123
}

Frontend:
- State changes to "validated"
- Buttons update:
  - [Validate] ✓ (disabled)
  - [🔒 Certify] ← NOW ENABLED
- Can't edit fields anymore
```

### ÉTAPE 7️⃣: CERTIFICATION - Double Auth 🔐

```
User clique [🔒 CERTIFY]

Modal Pops Up:

┌──────────────────────────────────────────┐
│ 🔒 CERTIFY REPORT                        │
├──────────────────────────────────────────┤
│                                          │
│  STEP 1/3: RE-AUTHENTICATE               │
│                                          │
│  Password: [••••••••••]  👁️            │
│  OTP:      [____]                       │
│                                          │
│  [CANCEL]              [NEXT →]         │
│                                          │
└──────────────────────────────────────────┘

User enters:
- Password: DemoPassword123!
- OTP: (reçu par email/SMS)
```

**Pourquoi Double Auth?**
1. **Password** = re-authentification (empêche rubber duck attacks)
2. **OTP** = second facteur (prévient credential stuffing)
3. **Confirmation explicite** = "I certify" acceptance

```
Après validation OTP:

┌──────────────────────────────────────────┐
│ 🔒 CERTIFY REPORT                        │
├──────────────────────────────────────────┤
│                                          │
│  STEP 2/3: REVIEW & CONFIRM              │
│                                          │
│  Report Summary:                         │
│  - Equipment: Spectrophotometer A        │
│  - Corrections: 1 (all logged)           │
│  - Chain Status: ✓ Verified              │
│  - Compliance: 94%                       │
│                                          │
│  Certification Notes:                    │
│  [All validation complete. Ready for] │
│  [audit submission.               ]  │
│                                          │
│  [ ] I certify that all data is accurate │
│                                          │
│  [CANCEL]          [🔒 CERTIFY REPORT]  │
│                                          │
└──────────────────────────────────────────┘
```

### ÉTAPE 8️⃣: FINAL - Report Généré

```
Backend: POST /api/parsing/5/sign/
{
  "password": "****",
  "otp_code": "123456",
  "notes": "All validation complete"
}

Processus:
1. Verify password + OTP ✓
2. Générer CertifiedReport ✓
3. Calc report_hash (SHA-256) ✓
4. Create AuditLog (SIGN operation) ✓
5. Générer PDF avec signature ✓

Response:
{
  "report_id": 42,
  "certified_at": "2026-02-17T14:35:22Z",
  "report_hash": "abc123def456...",
  "compliance_score": "94%",
  "pdf_url": "/api/reports/42/pdf/"
}

Frontend:
┌──────────────────────────────────────────┐
│ ✅ CERTIFIED!                            │
├──────────────────────────────────────────┤
│                                          │
│ Report ID: 42                            │
│ Hash: abc123def456...                    │
│ Certified by: demo_user                  │
│ At: 2026-02-17 14:35:22                  │
│ Compliance: 94%                          │
│ Status: ✓ Chain Verified                 │
│                                          │
│ [📥 Download PDF] [📊 View Report]      │
│                                          │
└──────────────────────────────────────────┘
```

---

## 🔍 Vérifier les Données en Base

### Terminal 3: Django Shell

```bash
cd /home/user/BioNexus-mvp/bionexus-platform/backend
python manage.py shell
```

**Voir les corrections:**
```python
from core.models import CorrectionTracker

for corr in CorrectionTracker.objects.all():
    print(f"Field: {corr.field_name}")
    print(f"  {corr.original_value} → {corr.corrected_value}")
    print(f"  Reason: {corr.reason}")
    print()
```

**Voir l'audit trail:**
```python
from core.models import AuditLog

for log in AuditLog.objects.all().order_by('timestamp'):
    print(f"{log.timestamp}: {log.operation} {log.entity_type}#{log.entity_id}")
    print(f"  By: {log.user_email}")
    print(f"  Signature: {log.signature[:16]}...")
    print()
```

**Vérifier la chaîne d'intégrité:**
```python
from core.utils.integrity import verify_chain_integrity

result = verify_chain_integrity()
print(f"Chain Valid: {result['is_valid']}")
print(f"Total Records: {result['total_records']}")
print(f"Corrupted: {result['corrupted_records']}")
```

**Voir les rapports certifiés:**
```python
from core.models import CertifiedReport

for report in CertifiedReport.objects.all():
    print(f"Report #{report.id}")
    print(f"  Certified by: {report.certified_by.email}")
    print(f"  At: {report.certified_at}")
    print(f"  Hash: {report.report_hash}")
    print(f"  Chain Verified: {report.chain_integrity_verified}")
    print()
```

---

## 📊 Visualiser le Flow Complet

### Timeline Visuelle

```
TIMELINE DE L'APPLICATION
═══════════════════════════════════════════════════════════════

14:30 - User logs in
├─ Auth endpoint called
└─ JWT token created
   AuditLog: 1 (CREATE User session)

14:31 - User uploads CSV file
├─ File parsed by Pydantic
└─ ParsedData.state = "parsed"
   AuditLog: 2 (CREATE ParsedData)
   Compliance: 50%

14:32 - User corrects "equipment_name" typo
├─ CorrectionTracker created
└─ ParsedData NOT updated yet
   AuditLog: 3 (UPDATE CorrectionTracker)
   Chain recalculated (✓ verified)
   Compliance: 60%

14:33 - User corrects "sample_volume" format
├─ Another CorrectionTracker
└─ Total corrections: 2
   AuditLog: 4 (UPDATE CorrectionTracker)
   Chain recalculated (✓ verified)
   Compliance: 70%

14:34 - User clicks [Validate]
├─ All corrections applied to confirmed_data
└─ ParsedData.state = "validated"
   AuditLog: 5 (UPDATE ParsedData state)
   Compliance: 80%
   [🔒 Certify] button enabled

14:35 - User clicks [🔒 Certify]
├─ Modal: Re-enter password + OTP
├─ Modal: Review & confirm
└─ POST /api/parsing/5/sign/
   ├─ Password verified ✓
   ├─ OTP verified ✓
   └─ CertifiedReport created
      ├─ report_hash calculated
      ├─ AuditLog: 6 (SIGN CertifiedReport)
      ├─ Chain fully verified
      ├─ PDF generated with signature
      ├─ Compliance: 94%
      └─ ✅ REPORT READY FOR AUDIT

Every 30s - Background chain verification
├─ Fetch all AuditLogs
├─ Recalculate signatures
├─ Detect tampering if any
└─ Update chain_verified status
   (Chain stays ✓ verified every 30s)
```

---

## 🎯 Key Concepts

### 1. AuditLog = Immuable Record

```
┌──────────────────────────────────┐
│  AuditLog #2                     │
├──────────────────────────────────┤
│ operation: UPDATE                │
│ entity_type: ParsedData          │
│ entity_id: 5                     │
│ timestamp: 2026-02-17T14:32:00Z  │
│ user_email: demo_user@lab.local  │
│ changes: {...}                   │
│ signature: abc123def456...       │ ← SHA-256
│ previous_signature: xyz789uvw... │ ← Link to prev
└──────────────────────────────────┘
```

**Chain Integrity Check:**
```
SHA-256(xyz789uvw + json(log_data)) = abc123def456
  ↓
If someone changes log_data:
  SHA-256(xyz789uvw + modified_data) ≠ abc123def456
  ↓
TAMPERING DETECTED ⚠️
```

### 2. ParsedData State Machine

```
raw_content (upload)
    ↓ Parse
parsed_content (with potential errors)
    ↓ User corrects
confirmed_data (all errors fixed)
    ↓ Validate
state = "validated"
    ↓ Double Auth + Certify
CertifiedReport (immutable, signed)
    ↓
state = "certified"
    ↓
Ready for audit submission
```

### 3. Compliance Score

```
Base: 50%
+ 10% = Audit trail exists
+ 10% = Corrections tracked
+ 10% = Chain integrity OK
+ 10% = Validated by user
+ 4% = Certified (double auth)
─────
= 94% (or higher)
```

---

## 🐛 Troubleshooting

**Q: "ModuleNotFoundError: No module named 'core'"**
A: Assurez-vous d'être dans le bon dossier:
```bash
cd /home/user/BioNexus-mvp/bionexus-platform/backend
```

**Q: "CORS error" au frontend**
A: Vérifiez que les serveurs tournent:
- Backend: http://localhost:8000 (terminal 1)
- Frontend: http://localhost:3000 (terminal 2)

**Q: "Database not found"**
A: Lancez les migrations:
```bash
python manage.py migrate --run-syncdb
```

**Q: "User not found" quand je login**
A: Créez un utilisateur test:
```bash
python manage.py shell
>>> from core.models import Tenant, User
>>> tenant = Tenant.objects.create(name="Lab", slug="lab")
>>> User.objects.create_user(
...     username="demo_user",
...     password="DemoPassword123!",
...     tenant=tenant
... )
```

---

## ✅ Checklist: Système Prêt?

```
[ ] Backend Django lancé sur 0.0.0.0:8000
[ ] Frontend React lancé sur localhost:3000
[ ] Base de données initialisée (migrate)
[ ] Utilisateur test créé
[ ] Login fonctionne
[ ] Dashboard visible
[ ] Fichier test peut être uploadé
[ ] Split-view fonctionne (LEFT + RIGHT)
[ ] Corrections tracées correctement
[ ] Chain verification toutes les 30s
[ ] Certification double auth fonctionne
[ ] PDF généré avec signature
[ ] Compliance score = 94%
```

**Si tout est ✓ VOUS ÊTES PRÊT!**

---

**Happy Testing! 🚀**
