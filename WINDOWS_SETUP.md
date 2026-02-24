# 🪟 BioNexus MVP - Windows Setup Guide

## ⚠️ Si vous avez eu l'erreur: `ValueError: Related model 'core.user' cannot be resolved`

✅ **C'EST FIXÉ!** Une nouvelle branche avec les migrations corriges est disponible.

```bash
git pull
```

---

## 🚀 Installation Complète (Windows)

### ÉTAPE 1: Cloner le repo

```bash
cd d:\Projects  (ou votre dossier préféré)
git clone https://github.com/Bayeko/BioNexus-mvp.git
cd BioNexus-mvp
```

### ÉTAPE 2: Setup Backend (Terminal 1)

```bash
cd bionexus-platform\backend

# 2.1 Créer environnement Python
python -m venv venv
venv\Scripts\activate

# 2.2 Installer dépendances
pip install -r requirements.txt

# 2.3 Appliquer migrations
python manage.py migrate

# 2.4 Créer utilisateur test
python manage.py shell
```

**Dans le shell Django:**
```python
from core.models import Tenant, User

tenant = Tenant.objects.create(name="Demo Lab", slug="demo-lab")
user = User.objects.create_user(
    username="demo_user",
    email="demo@lab.local",
    password="DemoPassword123!",
    tenant=tenant
)
print("✓ User créé avec succès!")
exit()
```

### ÉTAPE 3: Lancer Backend

**Rester dans Terminal 1 (avec venv activé):**

```bash
python manage.py runserver
```

**Vous verrez:**
```
Starting development server at http://127.0.0.1:8000/
Quit the server with CTRL-BREAK.
```

✅ Backend lancé sur: `http://localhost:8000`

---

### ÉTAPE 4: Setup Frontend (Terminal 2 NOUVEAU)

```bash
# Ouvrir nouveau terminal (PowerShell ou CMD)
cd d:\Projects\BioNexus-mvp\bionexus-platform\frontend

# 4.1 Installer Node modules
npm install

# 4.2 Lancer React dev server
npm start
```

**Vous verrez:**
```
webpack compiled successfully
Local:      http://localhost:3000
```

✅ Frontend lancé sur: `http://localhost:3000`

---

## 🎯 Premier Test

### 1. Login

Allez sur: `http://localhost:3000/login`

**Entrez:**
- Username: `demo_user`
- Password: `DemoPassword123!`

### 2. Dashboard

Vous verrez le dashboard avec statistiques.

### 3. Upload Test File

Cliquez sur **"Parsing Validation"**

Téléchargez un fichier CSV/PDF de test (voir section ci-dessous)

---

## 📄 Créer un Fichier Test CSV

**Créez un fichier: `test_data.csv`**

```csv
equipment_id,equipment_name,sample_id,date,volume
SPEC-001,Spectrophotometre A,SAMPLE-123,2026-02-17,50mL
SPEC-002,Centrifuge B,SAMPLE-124,2026-02-17,100mL
```

**Upload ce fichier dans l'app** et vous verrez le split-view magic!

---

## 🔧 Troubleshooting Windows

### Erreur: `"venv" n'est pas reconnu`

**Solution:** Faire:
```bash
python -m venv venv
.\venv\Scripts\activate    # Note: backslash, pas forward slash
```

### Erreur: `npm: The term 'npm' is not recognized`

**Solution:** Node.js n'est pas installé. Télécharger depuis: https://nodejs.org/
- Installer la version LTS
- Redémarrer le terminal après installation

### Erreur: `port 8000 already in use`

**Solution:** Utiliser un autre port:
```bash
python manage.py runserver 8001
```

### Erreur: `port 3000 already in use`

**Solution:** Tuer le processus:
```bash
# Windows PowerShell
Get-Process node | Stop-Process -Force

# Ou juste relancer npm sur un autre port:
npm start -- --port 3001
```

### Erreur: `django.db.utils.OperationalError: no such table`

**Solution:** Les migrations ne sont pas appliquées:
```bash
python manage.py migrate
```

---

## 🎮 Commandes Utiles

### Backend Django

```bash
# Voir les tables de la base
python manage.py dbshell

# Créer un superuser pour admin
python manage.py createsuperuser

# Voir les migrations
python manage.py showmigrations

# Régénérer les migrations (si vous modifiez les modèles)
python manage.py makemigrations
python manage.py migrate

# Accéder au shell Django
python manage.py shell

# Lancer les tests
python manage.py test
```

### Frontend React

```bash
# Installer une dépendance supplémentaire
npm install <package-name>

# Build pour production
npm run build

# Tests
npm test
```

---

## 📊 Architecture Rappel

```
┌─────────────────────────────────────────────────────┐
│  Browser (http://localhost:3000)                    │
│  React App + Axios                                  │
└────────────────┬────────────────────────────────────┘
                 │ HTTP REST API
┌────────────────▼────────────────────────────────────┐
│  Django Backend (http://localhost:8000)             │
│  - /api/auth/login/                                 │
│  - /api/parsing/                                    │
│  - /api/executions/                                 │
│  - /api/reports/                                    │
│  - /api/auditlog/                                   │
└────────────────┬────────────────────────────────────┘
                 │ ORM
┌────────────────▼────────────────────────────────────┐
│  SQLite Database (db.sqlite3)                       │
└─────────────────────────────────────────────────────┘
```

---

## ✅ Checklist: Système Prêt?

```
Backend Terminal:
[ ] venv activé
[ ] pip install terminé
[ ] Migrations appliquées
[ ] User test créé
[ ] `python manage.py runserver` lancé
[ ] http://localhost:8000 accessible

Frontend Terminal:
[ ] npm install terminé
[ ] `npm start` lancé
[ ] http://localhost:3000 s'ouvre automatiquement

Test:
[ ] Login fonctionne
[ ] Dashboard visible
[ ] Fichier test peut être uploadé
[ ] Split-view affiche le fichier + formulaire
[ ] Corrections tracées
[ ] Chain badge = ✓ verified
```

**Si tout est ✓ VOUS ÊTES PRÊT!**

---

## 📞 Besoin d'aide?

Si vous avez une erreur:

1. Vérifiez que les 2 terminals tournent (Backend + Frontend)
2. Vérifiez que vous êtes dans le bon dossier
3. Vérifiez que venv est activé (Backend terminal)
4. Regardez les logs d'erreur (ils disent généralement ce qui ne va pas!)
5. Relancez le service qui a l'erreur

---

**Happy coding! 🚀**
