import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from app.core.supabase import supabase
from app.api.auth import router as auth_router
from app.api.face import router as face_router

# Load environment variables
load_dotenv()

app = FastAPI(title="FaceAuthSystem Backend API")

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_origin_regex=r"https?://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(auth_router)
app.include_router(face_router)


@app.get("/")
async def root():
    return {
        "status": "ok",
        "service": "FaceAuthSystem Backend API",
        "docs_url": "/docs",
        "health_url": "/api/health"
    }


@app.get("/api/health")
async def health_check():
    return {
        "status": "ok",
        "service": "FaceAuthSystem backend"
    }


@app.get("/api/warmup")
async def warmup():
    """
    Pre-warms the Render instance and Supabase connection.
    Call this from the frontend when the registration/login page loads
    to avoid ReadTimeout errors on the first real request.
    """
    try:
        # Lightweight ping — just checks Supabase reachability
        supabase.table("profiles").select("id").limit(1).execute()
        return {"status": "warm", "supabase": "connected"}
    except Exception:
        return {"status": "warm", "supabase": "pending"}


@app.get("/api/supabase-health")
async def supabase_health_check():
    try:
        # Verify connection using a lightweight API call
        supabase.storage.list_buckets()
        return {
            "status": "ok",
            "service": "supabase",
            "connected": True
        }
    except Exception as e:
        # Safe warning output, hiding raw connection credentials
        return {
            "status": "error",
            "service": "supabase",
            "connected": False,
            "details": "Could not establish database connection or verify credentials."
        }
