"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from database import Base, engine

# Drop all tables and recreate (useful for development)
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(
    title="Hackathon API",
    description="Backend API for hackathon project",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def read_root():
    """Health check endpoint."""
    return {"message": "Hackathon API is running!"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


# Import and include routers
from routes import users_router
app.include_router(users_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
