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
    allow_origins=["*"],  # Adjust for security in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(auth_router)
app.include_router(face_router)


@app.get("/api/health")
async def health_check():
    return {
        "status": "ok",
        "service": "FaceAuthSystem backend"
    }

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
