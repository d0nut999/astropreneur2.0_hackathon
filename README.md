# Hackathon Project

A full-stack web application built with FastAPI (Python), PostgreSQL, and React for a hackathon.

## Project Structure

```
hackathon/
├── backend/                    # FastAPI backend
│   ├── controllers/           # Business logic layer
│   ├── models/               # SQLAlchemy database models
│   ├── repositories/         # Data access layer
│   ├── routes/              # API endpoint definitions
│   ├── schemas/             # Pydantic validation schemas
│   ├── config.py            # Configuration settings
│   ├── database.py          # Database connection and session
│   ├── main.py              # FastAPI app entry point
│   ├── requirements.txt      # Python dependencies
│   ├── Dockerfile           # Docker container for backend
│   └── .env.example         # Environment variables template
│
├── frontend/                 # React + Vite frontend
│   ├── src/
│   │   ├── App.jsx          # Main app component
│   │   ├── App.css          # App styles
│   │   ├── main.jsx         # React entry point
│   │   └── index.css        # Global styles
│   ├── package.json         # Node dependencies
│   ├── vite.config.js       # Vite build configuration
│   ├── index.html           # HTML template
│   └── .gitignore          # Git ignore rules
│
├── docker-compose.yml       # Docker services orchestration
├── .gitignore              # Git ignore rules
└── README.md               # This file
```

## Architecture Overview

### Backend (FastAPI)

The backend uses a layered architecture:

1. **Routes** (`routes/`) - HTTP endpoints
2. **Controllers** (`controllers/`) - Business logic
3. **Repositories** (`repositories/`) - Database operations
4. **Models** (`models/`) - SQLAlchemy ORM models
5. **Schemas** (`schemas/`) - Request/response validation (Pydantic)

### Frontend (React + Vite)

- **Vite**: Fast build tool for modern web dev
- **React**: Component-based UI library
- **Axios**: HTTP client for API calls
- **React Router**: (Optional) for navigation

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- Git

### 1. Clone and Setup Repository

```bash
cd /path/to/hackathon
git init
git add .
git commit -m "Initial commit: project structure"
```

### 2. Start PostgreSQL Database

```bash
docker-compose up -d postgres
```

The database will be available at `localhost:5432` with:
- Username: `hackathon_user`
- Password: `hackathon_password`
- Database: `hackathon_db`

### 3. Setup Backend

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file from example
copy .env.example .env
# Or on Mac/Linux: cp .env.example .env
```

### 4. Run Backend

```bash
# Make sure you're in backend/ directory with venv activated
python main.py
```

Backend will run at `http://localhost:8000`

Check the API docs at `http://localhost:8000/docs` (Swagger UI)

### 5. Setup Frontend

```bash
# In a new terminal, navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend will run at `http://localhost:5173`

## API Endpoints

### Users

- `POST /api/users` - Create a new user
  ```json
  {
    "email": "user@example.com",
    "username": "john_doe",
    "full_name": "John Doe",
    "password": "securepassword"
  }
  ```

- `GET /api/users` - Get all users (with pagination)
  - Query params: `skip=0&limit=10`

- `GET /api/users/{user_id}` - Get specific user

- `PUT /api/users/{user_id}` - Update user

- `DELETE /api/users/{user_id}` - Delete user

## How to Add New Features

### Adding a New Database Model

1. **Create Model** (`backend/models/example.py`):
```python
from sqlalchemy import Column, Integer, String
from database import Base

class Example(Base):
    __tablename__ = "examples"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
```

2. **Create Schema** (`backend/schemas/example.py`):
```python
from pydantic import BaseModel

class ExampleCreate(BaseModel):
    name: str

class ExampleResponse(BaseModel):
    id: int
    name: str
    
    class Config:
        from_attributes = True
```

3. **Create Repository** (`backend/repositories/example_repository.py`):
```python
from sqlalchemy.orm import Session
from models.example import Example

class ExampleRepository:
    @staticmethod
    def create(db: Session, example: ExampleCreate) -> Example:
        db_example = Example(**example.model_dump())
        db.add(db_example)
        db.commit()
        db.refresh(db_example)
        return db_example
```

4. **Create Controller** (`backend/controllers/example_controller.py`):
```python
from controllers.example_controller import ExampleController

class ExampleController:
    @staticmethod
    def create_example(db: Session, example: ExampleCreate):
        return ExampleRepository.create(db, example)
```

5. **Create Routes** (`backend/routes/examples.py`):
```python
from fastapi import APIRouter, Depends
from controllers.example_controller import ExampleController

router = APIRouter(prefix="/api/examples", tags=["examples"])

@router.post("/")
async def create_example(example: ExampleCreate, db: Session = Depends(get_db)):
    return ExampleController.create_example(db, example)
```

6. **Register Route** in `backend/main.py`:
```python
from routes import examples_router
app.include_router(examples_router)
```

## Environment Variables

Create a `.env` file in the `backend/` directory:

```
DATABASE_URL=postgresql://hackathon_user:hackathon_password@localhost:5432/hackathon_db
DEBUG=True
SECRET_KEY=your-secret-key-here
FRONTEND_URL=http://localhost:5173
```

## Development Tips

### Frontend Proxy

Vite is configured to proxy API requests to the backend. Any request to `/api/*` is forwarded to `http://localhost:8000`.

### Database

The database is automatically created on first connection. SQLAlchemy will create tables from models.

### Debugging Backend

Set `DEBUG=True` in `.env` to see SQL queries in the console.

### Frontend Hot Reload

Vite automatically reloads when you save files.

## Deployment

### Backend (Docker)

```bash
docker build -t hackathon-backend ./backend
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql://... \
  hackathon-backend
```

### Frontend

```bash
cd frontend
npm run build
# Serve dist/ folder with your hosting provider
```

## Troubleshooting

### Port Already in Use

- Backend (8000): `lsof -i :8000` (Mac/Linux) or check Windows Task Manager
- Frontend (5173): Change port in `frontend/vite.config.js`

### Database Connection Error

- Ensure PostgreSQL is running: `docker ps | grep postgres`
- Verify DATABASE_URL in `.env`
- Check database credentials match docker-compose.yml

### CORS Errors

- Ensure `FRONTEND_URL` in backend `.env` matches your frontend URL
- Restart backend after changing `.env`

## Next Steps for Hackathon

1. ✅ Database & Backend structure setup
2. ✅ Frontend structure setup
3. **Add your features**: Expand models, controllers, routes, and UI
4. **Authentication**: Add JWT tokens for secure API access
5. **Validation**: Add input validation in Pydantic schemas
6. **Testing**: Write unit and integration tests
7. **Deployment**: Push to GitHub and deploy to Heroku, Render, or similar

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev)
- [SQLAlchemy ORM](https://docs.sqlalchemy.org/en/20/)
- [Vite Documentation](https://vitejs.dev/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

## License

MIT
