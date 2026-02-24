# 🚀 BioNexus MVP - Windows Launcher Guide

## Quick Start (TL;DR)

```
1. Double-click: SETUP.bat        (first time only)
2. Double-click: RUN.bat          (every time you want to work)
3. Open:        http://localhost:3000
4. Login:       demo_user / DemoPassword123!
```

---

## 📁 Three Simple Files

### 1. **SETUP.bat** - First Time Setup Only

**When to use:** First time you download the project

**What it does:**
- ✓ Checks if Python & Node.js are installed
- ✓ Creates Python virtual environment
- ✓ Installs all Python packages (Django, DRF, pytest, etc.)
- ✓ Installs all Node packages (React, Axios, Tailwind, etc.)
- ✓ Creates database tables (SQLite)
- ✓ Creates test user `demo_user`

**How to run:**
```
Double-click SETUP.bat
OR
cmd.exe > SETUP.bat
```

**Expected output:**
```
✓ Python found
✓ Node.js found
✓ Virtual environment created
✓ Packages installed
✓ Migrations applied
✓ Tenant created
✓ User created
✓ Packages installed
✅ SETUP COMPLETE!
```

---

### 2. **RUN.bat** - Start the Application

**When to use:** Every time you want to work on the project

**What it does:**
- ✓ Opens Terminal 1 (Backend Django)
- ✓ Opens Terminal 2 (Frontend React)
- ✓ Automatically opens http://localhost:3000 in your browser

**How to run:**
```
Double-click RUN.bat
```

**What happens:**
```
Terminal 1 opens:
  $ cd bionexus-platform\backend
  $ .\venv\Scripts\activate
  $ python manage.py runserver
  Starting development server at http://127.0.0.1:8000/

Terminal 2 opens:
  $ cd bionexus-platform\frontend
  $ npm start
  webpack compiled successfully
  Local: http://localhost:3000

Browser opens automatically to:
  http://localhost:3000
```

**Keep these terminals open!** ⚠️
- Terminal 1 = Backend API
- Terminal 2 = Frontend UI
- Closing them stops the application

---

### 3. **STOP.bat** - Stop Everything

**When to use:** When you're done and want to close all services

**What it does:**
- ✓ Kills Django process
- ✓ Kills React/Node process
- ✓ Closes both terminals

**How to run:**
```
Double-click STOP.bat
```

---

## 🔄 Typical Workflow

### First Day (Setup)

```
Step 1: Double-click SETUP.bat
        ↓
        (Wait for "SETUP COMPLETE!")
        ↓
Step 2: Double-click RUN.bat
        ↓
        (Two terminals open, browser opens)
        ↓
Step 3: Login with demo_user / DemoPassword123!
        ↓
        ✅ Ready to use!
```

### Every Other Day (Just Run)

```
Step 1: Double-click RUN.bat
        ↓
        (Two terminals open, browser opens)
        ↓
Step 2: Start coding!
        ↓
Step 3: When done: Double-click STOP.bat
```

---

## 👀 Real-Time Changes

### Frontend Changes (React)
```
You edit: bionexus-platform/frontend/src/components/...
          ↓
React dev server detects change
          ↓
Browser auto-reloads
          ↓
You see the change instantly! ✓
```

### Backend Changes (Django)
```
You edit: bionexus-platform/backend/core/models.py
          ↓
Option A: Django auto-reloads (most changes)
          ↓
You see the change instantly! ✓

Option B: Needs restart (migrations, model changes)
          ↓
Close Terminal 1
Double-click RUN.bat
          ↓
Backend restarts ✓
```

---

## 🐛 Troubleshooting

### Terminal 1 (Backend) won't start

**Error:** `python: command not found`
- Python isn't installed or not in PATH
- Solution: https://www.python.org/ (check "Add Python to PATH")

**Error:** `venv not found`
- Run SETUP.bat again
- Or manually: `python -m venv venv`

**Error:** `port 8000 already in use`
- Another Django is running
- Double-click STOP.bat
- Wait 5 seconds
- Double-click RUN.bat

### Terminal 2 (Frontend) won't start

**Error:** `npm: command not found`
- Node.js isn't installed
- Solution: https://nodejs.org/ (download LTS)

**Error:** `port 3000 already in use`
- Another React is running
- Double-click STOP.bat
- Wait 5 seconds
- Double-click RUN.bat

### Browser doesn't open

- Manual: Open http://localhost:3000 in your browser
- Wait 10 seconds (React takes time to compile)

### Login doesn't work

- Make sure you ran SETUP.bat first
- Check username: `demo_user` (exact spelling)
- Check password: `DemoPassword123!` (exact case)

### "Database locked" error

- Close Terminal 1 and Terminal 2
- Wait 5 seconds
- Run SETUP.bat
- Then run RUN.bat

---

## 📊 Architecture Reminder

```
Your Computer:
├── Terminal 1: http://localhost:8000 (Django Backend)
│   └── Handles API requests, database, business logic
│
├── Terminal 2: http://localhost:3000 (React Frontend)
│   └── Shows UI, sends requests to Terminal 1
│
└── Browser: http://localhost:3000 (What you see)
    └── What users interact with
```

---

## 🎮 Advanced: Manual Commands

If the .bat files don't work, here are the manual commands:

### Start Backend Manually

```bash
cd bionexus-platform\backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

### Start Frontend Manually

```bash
cd bionexus-platform\frontend
npm install
npm start
```

### Create User Manually

```bash
cd bionexus-platform\backend
.\venv\Scripts\activate
python manage.py shell
```

Then paste:
```python
from core.models import Tenant, User

tenant = Tenant.objects.create(name="Demo Lab", slug="demo-lab")
User.objects.create_user(
    username='demo_user',
    email='demo@lab.local',
    password='DemoPassword123!',
    tenant=tenant
)
print("User created!")
exit()
```

---

## 📝 Important Files

| File | Purpose |
|------|---------|
| `SETUP.bat` | First-time setup (Python, Node, DB) |
| `RUN.bat` | Start both servers |
| `STOP.bat` | Stop all services |
| `DOCUMENTATION.md` | Complete technical documentation |
| `QUICK_START.md` | Quick reference guide |
| `WINDOWS_SETUP.md` | Windows-specific help |

---

## 🎯 What Happens When You Make Changes

### Code Change → Browser Update

```
You edit frontend code
      ↓
Save file (Ctrl+S)
      ↓
React detects change
      ↓
Webpack recompiles (5 seconds)
      ↓
Browser auto-refreshes
      ↓
You see your change! ✓
```

### Database Change

```
You edit models.py
      ↓
You create migration: python manage.py makemigrations
      ↓
You apply migration: python manage.py migrate
      ↓
Backend automatically reloads
      ↓
Changes are live! ✓
```

---

## ⏰ Time to First Run

| Step | Time |
|------|------|
| SETUP.bat (first time) | 3-5 minutes |
| RUN.bat (every time) | 30 seconds |
| Code change → See in browser | 5-10 seconds |

---

## 🆘 Still Having Issues?

1. **Check the Terminal Output**
   - Read error messages carefully
   - Most errors explain what's wrong

2. **Try restarting**
   - STOP.bat
   - Wait 5 seconds
   - RUN.bat

3. **Check Requirements**
   - Python 3.10+ installed
   - Node.js 16+ installed
   - Both added to PATH

4. **See Documentation**
   - Read WINDOWS_SETUP.md for detailed help
   - Read DOCUMENTATION.md for architecture

---

**Happy Coding! 🚀**

*When you make changes, they appear instantly in http://localhost:3000*
