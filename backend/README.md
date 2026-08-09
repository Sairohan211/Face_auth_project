# Backend (FaceAuthSystem)

This is the FastAPI backend API for the Face Authentication System.

## Project Structure
```text
backend/
├── app/
│   ├── __init__.py
│   └── main.py       # FastAPI application entrypoint
├── .env              # Environment variables (ignored by Git)
├── .gitignore        # Git ignores for Python/venv
├── requirements.txt  # Python package dependencies
└── README.md         # This documentation
```

## Setup Instructions

### 1. Prerequisites
Make sure Python 3.10 is installed on your system.

### 2. Virtual Environment Setup
Inside the `backend/` directory, create and activate a virtual environment:

**On Windows (PowerShell):**
```powershell
py -3.10 -m venv .venv
.venv\Scripts\Activate.ps1
```

**On macOS/Linux:**
```bash
python3.10 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Running the API Server
Start the local server with Uvicorn:
```bash
uvicorn app.main:app --reload
```
The server will run on [http://127.0.0.1:8000](http://127.0.0.1:8000).

### 5. API Endpoints
- **Health Check**: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)
- **Interactive Documentation (Swagger)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
