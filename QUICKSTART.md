# Quick Start Guide (5 minutes)

## Step 1: Start Database (30 seconds)

```bash
docker-compose up -d postgres
```

Wait for it to be ready. Check with:
```bash
docker ps
```

Should see `hackathon_db` running.

## Step 2: Start Backend (1 minute)

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Create .env file
copy .env.example .env

# Run
python main.py
```

You should see:
```
Uvicorn running on http://127.0.0.1:8000
```

**Test it**: Open http://localhost:8000/docs in browser → should see Swagger UI

## Step 3: Start Frontend (2 minutes)

In a **new terminal**:

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

You should see:
```
VITE v5.0.8  ready in 200 ms
Local: http://localhost:5173/
```

## Step 4: Test It (1 minute)

Open http://localhost:5173 in browser:

1. Fill in the form (email, username, password, name)
2. Click "Create User"
3. See user appear in the list below

**If it works** ✅ → Start building your features!

**If it doesn't** ❌ → See troubleshooting below

## Keeping Servers Running

Terminal 1: Backend stays running
Terminal 2: Frontend stays running
Terminal 3: Use for git commands

## Quick Commands Reference

### Backend
```bash
cd backend
venv\Scripts\activate  # Activate venv
python main.py         # Start server
pip install package    # Add dependency
```

### Frontend
```bash
cd frontend
npm run dev           # Start dev server
npm install package   # Add dependency
npm run build         # Build for production
```

### Database
```bash
docker-compose up -d postgres      # Start
docker-compose down                # Stop
docker-compose logs postgres       # View logs
```

## Troubleshooting

### "Port 5432 already in use"
```bash
docker-compose down
docker-compose up -d postgres
```

### "ModuleNotFoundError" in backend
```bash
cd backend
venv\Scripts\activate
pip install -r requirements.txt
```

### "npm ERR! code ERESOLVE" in frontend
```bash
cd frontend
npm install --legacy-peer-deps
```

### "Cannot connect to database"
```bash
# Check if postgres is running
docker ps | grep postgres

# If not, restart
docker-compose down
docker-compose up -d postgres
```

### Frontend shows "Cannot GET /" 
Make sure you're running `npm run dev` in the frontend folder, not `npm start`

## Next: Build Your Feature

Now that everything works:

1. **Plan your data**: What information do you need? (users, posts, products, etc.)
2. **Create models**: Add to `backend/models/`
3. **Create schemas**: Add to `backend/schemas/`
4. **Create repository**: Add to `backend/repositories/`
5. **Create controller**: Add to `backend/controllers/`
6. **Create routes**: Add to `backend/routes/`
7. **Update main.py**: Register the routes
8. **Build frontend**: Update components in `frontend/src/`

See `README.md` for detailed examples of each step.

## Push to GitHub

```bash
git add .
git commit -m "Initial hackathon setup with FastAPI + React + PostgreSQL"
git remote add origin https://github.com/YOUR_USERNAME/your-repo.git
git branch -M main
git push -u origin main
```

Good luck with your hackathon! 🚀
