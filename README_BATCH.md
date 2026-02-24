# 🪟 BioNexus MVP - Windows Batch Launchers

## 📌 TL;DR - Juste 2 commandes

```
1. Double-click SETUP.bat   (first time only)
2. Double-click RUN.bat      (every time after)
```

Voilà! L'app démarre automatiquement et tu vois les changements en temps réel! ✨

---

## 📂 Les 3 Fichiers .bat

### 🟦 **SETUP.bat**
**À utiliser:** La première fois seulement

Fait:
- ✅ Crée environnement Python (venv)
- ✅ Installe packages backend (Django, DRF, etc.)
- ✅ Installe packages frontend (React, Axios, etc.)
- ✅ Crée base de données SQLite
- ✅ Crée utilisateur test `demo_user`

```bash
Double-click SETUP.bat
```

Attends que tu voies: `✅ SETUP COMPLETE!`

---

### 🟦 **RUN.bat**
**À utiliser:** À chaque fois que tu veux travailler

Fait:
- ✅ Ouvre Terminal 1 = Backend Django (port 8000)
- ✅ Ouvre Terminal 2 = Frontend React (port 3000)
- ✅ Ouvre le navigateur automatiquement

```bash
Double-click RUN.bat
```

**Après 10 secondes:**
- ✅ http://localhost:3000 s'ouvre dans le navigateur
- ✅ Tu peux login avec `demo_user` / `DemoPassword123!`

---

### 🟦 **STOP.bat**
**À utiliser:** Quand tu veux arrêter complètement

Fait:
- ✅ Tue les processus Django et React
- ✅ Ferme les 2 terminals

```bash
Double-click STOP.bat
```

---

## 🔄 Workflow Typique

### 🌅 Premier jour (Setup)
```
1. Double-click SETUP.bat
   ↓ (attends ~3-5 min)
2. Double-click RUN.bat
   ↓ (attends ~30 sec)
3. Login avec demo_user
   ↓
✅ Prêt à coder!
```

### 📅 Jours suivants (Just Run)
```
1. Double-click RUN.bat
   ↓
2. Commence à coder
   ↓
3. Les changements s'affichent automatiquement!
```

---

## 👀 Voir les Changements en Temps Réel

### Frontend (React)
```
Tu modifies: bionexus-platform/frontend/src/components/Dashboard.tsx
             ↓
             Tu appuies sur Ctrl+S (save)
             ↓
React détecte le changement
             ↓
Webpack recompile (5 sec)
             ↓
Le navigateur se rafraîchit automatiquement
             ↓
✅ Tu vois ton changement au http://localhost:3000!
```

### Backend (Django)
```
Tu modifies: bionexus-platform/backend/core/models.py
             ↓
             Tu appuies sur Ctrl+S
             ↓
Django détecte le changement (la plupart des cas)
             ↓
✅ L'API se rafraîchit automatiquement!

(Si tu changes les migrations, tu dois redémarrer manuellement)
```

---

## 🎯 Comment Ça Marche

```
Ton Ordinateur:

┌─────────────────────────────────────────┐
│ Terminal 1: Django Backend              │
│ http://localhost:8000/api/...          │
│ (Gère API, Database, Logic)            │
└────────────┬────────────────────────────┘
             │ HTTP Requests
┌────────────▼────────────────────────────┐
│ Terminal 2: React Frontend              │
│ http://localhost:3000                  │
│ (Affiche l'interface)                  │
└────────────┬────────────────────────────┘
             │ Ce que tu vois
┌────────────▼────────────────────────────┐
│ Navigateur (Browser)                   │
│ http://localhost:3000                  │
│ (Ce qu'il voit l'utilisateur)          │
└─────────────────────────────────────────┘
```

---

## 📝 Que Faire Avec Ça?

### 🎨 Modifier l'UI
```
Fichier: bionexus-platform/frontend/src/components/...
Action: Double-click RUN.bat
Result: Changements visibles au http://localhost:3000 en 5 sec!
```

### 🔌 Modifier l'API
```
Fichier: bionexus-platform/backend/core/...
Action: Double-click RUN.bat
Result: API reloade automatiquement (ou redémarre si besoin)
```

### 💾 Modifier la Base de Données
```
Fichier: bionexus-platform/backend/core/models.py
Action:
  1. python manage.py makemigrations
  2. python manage.py migrate
  3. Redémarre RUN.bat
Result: Base de données mise à jour!
```

---

## 🐛 Problèmes Courants

### "Python not found"
- Python n'est pas installé
- Solution: https://www.python.org/
- **Important:** Cocher "Add Python to PATH"

### "Node not found"
- Node.js n'est pas installé
- Solution: https://nodejs.org/ (version LTS)

### Port 8000 ou 3000 déjà utilisé
```
1. Double-click STOP.bat
2. Attends 5 sec
3. Double-click RUN.bat
```

### Ça ne marche toujours pas?
- Lis les **terminal logs** (fenêtres qui s'ouvrent)
- Lis `WINDOWS_SETUP.md` pour l'aide détaillée
- Lis `DOCUMENTATION.md` pour comprendre l'architecture

---

## 📚 Documentation Complète

| Fichier | Contenu |
|---------|---------|
| `LAUNCH_GUIDE.md` | Guide détaillé des .bat files |
| `WINDOWS_SETUP.md` | Setup Windows complet |
| `QUICK_START.md` | Quick reference |
| `DOCUMENTATION.md` | Architecture & APIs |

---

## ✅ Résumé

**Avant:** Setup manuel, 20 commandes, très compliqué
```bash
cd backend && python -m venv venv && .\venv\Scripts\activate && ...
```

**Maintenant:** Juste double-click sur un fichier! 🎉
```
Double-click SETUP.bat
Double-click RUN.bat
✅ Done!
```

**Les changements sont visibles en temps réel** dans le navigateur! 🔥

---

## 🚀 Ready to Go?

```
cd d:\Projects\BioNexus-mvp
Double-click SETUP.bat
(attends que ça finisse)
Double-click RUN.bat
(attends 10 secondes)
Login: demo_user / DemoPassword123!
```

**Voilà! BioNexus MVP est prêt à l'emploi!** 🎉
