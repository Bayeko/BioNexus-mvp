# 📚 BioNexus MVP - Complete Files Guide

## 🎯 Quick Navigation

**Je veux...**

| Objectif | Fichier | Temps |
|----------|---------|-------|
| Lancer l'app rapidement | `SETUP.bat` + `RUN.bat` | 5 min |
| Comprendre comment l'app fonctionne | `DOCUMENTATION.md` | 20 min |
| Setup pas à pas (Windows) | `WINDOWS_SETUP.md` | 10 min |
| Reference rapide | `QUICK_START.md` | 5 min |
| Comment utiliser les .bat files | `LAUNCH_GUIDE.md` ou `README_BATCH.md` | 5 min |
| Voir les changements en temps réel | `RUN.bat` | 30 sec |

---

## 📂 Fichiers par Catégorie

### 🚀 Pour Lancer l'App (Batch Files)

| Fichier | Quand | Qu'est-ce ça fait |
|---------|-------|------------------|
| `SETUP.bat` | 1ère fois seulement | Crée venv, installe packages, init DB, crée user |
| `RUN.bat` | À chaque fois | Lance backend + frontend + ouvre browser |
| `STOP.bat` | Quand tu termines | Arrête tous les services |
| `README_BATCH.md` | Pour comprendre les .bat | Explique comment utiliser les fichiers batch |

### 📖 Pour Apprendre (Documentation)

| Fichier | Contenu | Durée de lecture |
|---------|---------|-----------------|
| `DOCUMENTATION.md` | Architecture complète, APIs, modèles, workflows | 30 min |
| `QUICK_START.md` | Vue d'ensemble visuelle, 8 étapes du workflow | 10 min |
| `WINDOWS_SETUP.md` | Installation Windows détaillée, troubleshooting | 15 min |
| `LAUNCH_GUIDE.md` | Guide détaillé des .bat files | 10 min |
| `FILES_GUIDE.md` | Ce fichier! Navigation complète | 5 min |

### 💻 Fichiers de Code

#### Backend (Django)
```
bionexus-platform/backend/
├── core/
│   ├── models.py              ← Modèles (AuditLog, ParsedData, etc.)
│   ├── settings.py            ← Configuration Django (fixed!)
│   ├── api_views.py           ← API endpoints
│   ├── services.py            ← Business logic
│   ├── migrations/0001_...    ← Database migrations (regenerated!)
│   └── ...
├── manage.py                  ← Django manager
├── requirements.txt           ← Python packages
└── db.sqlite3                 ← Database (created by SETUP.bat)
```

#### Frontend (React)
```
bionexus-platform/frontend/
├── src/
│   ├── components/
│   │   ├── Login/             ← Login page
│   │   ├── Dashboard/         ← Dashboard
│   │   ├── ParsingValidation/ ← Split-view magic!
│   │   ├── ExecutionLogs/     ← Execution logs
│   │   └── Reports/           ← Certified reports
│   ├── services/
│   │   ├── api.ts             ← API requests (Axios)
│   │   ├── authService.ts     ← Authentication
│   │   ├── parsingService.ts  ← Parsing logic
│   │   └── ...
│   ├── App.tsx                ← Main app
│   └── index.tsx              ← Entry point
├── package.json               ← Node.js packages
└── node_modules/              ← Installed packages
```

### 🔧 Fichiers de Configuration

```
Root Directory:
├── SETUP.bat                  ← Batch file: First-time setup
├── RUN.bat                    ← Batch file: Start everything
├── STOP.bat                   ← Batch file: Stop everything
├── README.md                  ← Original project README
├── DOCUMENTATION.md           ← Full technical docs (1400+ lines)
├── QUICK_START.md            ← Quick reference (700+ lines)
├── WINDOWS_SETUP.md          ← Windows-specific guide (280+ lines)
├── LAUNCH_GUIDE.md           ← .bat files guide (400+ lines)
├── README_BATCH.md           ← .bat files recap (200+ lines)
├── FILES_GUIDE.md            ← This file!
├── .gitignore                ← Git configuration
└── .git/                     ← Git repository
```

---

## 🎓 Learning Path

### Beginner: Just Want It Running?
```
1. Read: README_BATCH.md (5 min)
2. Run: SETUP.bat (5 min)
3. Run: RUN.bat (1 min)
4. Login: demo_user / DemoPassword123!
5. Start modifying code and see changes live!
```

### Intermediate: Want to Understand?
```
1. Read: QUICK_START.md (10 min)
   - Understand the 8-step workflow
   - See architecture diagrams
2. Read: LAUNCH_GUIDE.md (10 min)
   - Understand how .bat files work
3. Run: RUN.bat
4. Start making changes and watch them update!
```

### Advanced: Want Full Details?
```
1. Read: DOCUMENTATION.md (30 min)
   - Architecture
   - Data models
   - API endpoints
   - Frontend structure
   - Security & compliance
2. Explore the code:
   - bionexus-platform/backend/core/models.py
   - bionexus-platform/backend/core/services.py
   - bionexus-platform/frontend/src/components/
3. Run: RUN.bat
4. Modify code, see real-time changes
5. Read the audit logs and understand the system
```

---

## 🔍 Find What You Need

### "How do I start the app?"
→ `README_BATCH.md` or `LAUNCH_GUIDE.md`

### "I'm getting an error on Windows"
→ `WINDOWS_SETUP.md` (Troubleshooting section)

### "How does the system work?"
→ `DOCUMENTATION.md` (Architecture section)

### "I want to see the workflow"
→ `QUICK_START.md` (Workflow section with visuals)

### "I want to understand the code"
→ `DOCUMENTATION.md` (Data Models & APIs sections)

### "How do I modify the code and see changes?"
→ `README_BATCH.md` (Real-Time Changes section)

### "What are all the files?"
→ You're reading it! (This file)

---

## 📊 What Each Documentation File Covers

### DOCUMENTATION.md (1400+ lines)
**Best for:** Understanding the system completely

Sections:
- Vue d'ensemble
- Architecture (avec diagrammes)
- Modèles de données (avec exemples)
- Workflow complet (4 phases détaillées)
- APIs & endpoints (tous les endpoints)
- Frontend React (structure complète)
- Sécurité & conformité GxP
- Déploiement

### QUICK_START.md (700+ lines)
**Best for:** Getting started quickly

Sections:
- Architecture visuelle ASCII
- Lancer le système (Terminal 1, 2, 3)
- Workflow complet (8 étapes avec mockups UI)
- Vérifier les données en base
- Key concepts (AuditLog, State Machine, Compliance Score)
- Troubleshooting
- Checklist

### WINDOWS_SETUP.md (280+ lines)
**Best for:** Windows users, step-by-step

Sections:
- Lancer le système
- Première utilisation
- Commandes utiles
- Troubleshooting Windows
- Architecture

### LAUNCH_GUIDE.md (400+ lines)
**Best for:** Understanding the .bat files

Sections:
- Quick Start
- Three Simple Files (SETUP, RUN, STOP)
- Typical Workflow
- Real-Time Changes
- Troubleshooting
- Architecture Reminder

### README_BATCH.md (200+ lines)
**Best for:** Quick overview of .bat files

Sections:
- TL;DR (just 2 commands)
- The 3 Files
- Typical Workflow
- See Changes in Real-Time
- How It Works
- What to Do With It
- Common Problems

---

## 🎯 First 5 Minutes Checklist

```
☐ Read README_BATCH.md (2 min)
☐ Double-click SETUP.bat (3 min)
```

Done! Now you can:

```
☐ Double-click RUN.bat (every time)
☐ See http://localhost:3000 open
☐ Login with demo_user
☐ Start coding!
```

---

## 🔄 What Changed (Recent Fixes)

### Migration Errors (FIXED ✅)
- **Problem:** `ValueError: Related model 'core.user' cannot be resolved`
- **Cause:** ForeignKey to "User" instead of settings.AUTH_USER_MODEL
- **Solution:** Fixed all references + regenerated migrations
- **Files changed:** `core/models.py`, `core/settings.py`, all migrations

### Added These Files
- `SETUP.bat` - Automated first-time setup
- `RUN.bat` - Start everything with one click
- `STOP.bat` - Clean shutdown
- `DOCUMENTATION.md` - Complete guide (1400+ lines)
- `QUICK_START.md` - Quick reference (700+ lines)
- `WINDOWS_SETUP.md` - Windows help (280+ lines)
- `LAUNCH_GUIDE.md` - .bat files guide (400+ lines)
- `README_BATCH.md` - .bat recap (200+ lines)
- `FILES_GUIDE.md` - This navigation file

---

## ✨ What You Can Do Now

### See Changes in Real-Time ✅
```
Edit frontend code
         ↓
Save (Ctrl+S)
         ↓
Browser auto-refreshes (5 sec)
         ↓
You see the change! ✓
```

### Start App with One Click ✅
```
Double-click RUN.bat
         ↓
Backend + Frontend start
         ↓
Browser opens automatically
         ↓
Ready to use! ✓
```

### Understand the System ✅
```
Read DOCUMENTATION.md
         ↓
Understand architecture
         ↓
Know what each component does
         ↓
Make informed changes! ✓
```

---

## 🎓 File Selection Tree

```
START
 │
 ├─ "I just want it running"
 │  └─→ SETUP.bat + RUN.bat
 │      └─→ README_BATCH.md for help
 │
 ├─ "I want to understand it"
 │  └─→ QUICK_START.md (10 min)
 │      └─→ DOCUMENTATION.md (30 min)
 │
 ├─ "I'm on Windows and confused"
 │  └─→ WINDOWS_SETUP.md
 │      └─→ LAUNCH_GUIDE.md
 │
 ├─ "I want to make changes"
 │  └─→ README_BATCH.md ("Real-Time Changes" section)
 │      └─→ Edit code → Save → See changes in browser!
 │
 └─ "I'm stuck or getting errors"
    └─→ WINDOWS_SETUP.md (Troubleshooting)
       └─→ Or LAUNCH_GUIDE.md (Troubleshooting)
```

---

## 📞 Still Lost?

1. **What file should I read?**
   → Check the table at the top of this file!

2. **Where do I find the code?**
   → `bionexus-platform/backend/` and `bionexus-platform/frontend/`

3. **How do I see my changes?**
   → Run `RUN.bat` and edit any file (changes appear in 5 seconds)

4. **Something is broken**
   → Read `WINDOWS_SETUP.md` (Troubleshooting section)

5. **I want to understand the system**
   → Read `DOCUMENTATION.md` (Architecture section)

---

**That's it! You now have a complete guide to BioNexus MVP!** 🚀

*Go ahead, double-click SETUP.bat and start coding!* 🎉
