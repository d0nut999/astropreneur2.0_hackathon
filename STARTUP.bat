@echo off
REM This script helps you remember the startup commands
REM Read QUICKSTART.md for detailed instructions

echo.
echo ============================================
echo   HACKATHON PROJECT - STARTUP COMMANDS
echo ============================================
echo.

echo Step 1: Start PostgreSQL Database
echo   Command: docker-compose up -d postgres
echo   Check with: docker ps
echo.

echo Step 2: Start Backend (Open NEW Terminal)
echo   Commands:
echo   cd backend
echo   python -m venv venv
echo   venv\Scripts\activate
echo   pip install -r requirements.txt
echo   copy .env.example .env
echo   python main.py
echo   Test: http://localhost:8000/docs
echo.

echo Step 3: Start Frontend (Open NEW Terminal)
echo   Commands:
echo   cd frontend
echo   npm install
echo   npm run dev
echo   Test: http://localhost:5173
echo.

echo ============================================
echo   QUICK REFERENCE
echo ============================================
echo.
echo Backend (Python):
echo   - Main file: backend\main.py
echo   - API docs: http://localhost:8000/docs
echo   - Port: 8000
echo.
echo Frontend (React):
echo   - Main file: frontend\src\App.jsx
echo   - App runs at: http://localhost:5173
echo   - Port: 5173
echo.
echo Database:
echo   - Type: PostgreSQL
echo   - Username: hackathon_user
echo   - Password: hackathon_password
echo   - Database: hackathon_db
echo   - Port: 5432
echo.
echo ============================================
echo   IMPORTANT: Read QUICKSTART.md first!
echo ============================================
echo.
pause
