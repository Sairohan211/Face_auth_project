from supabase import create_client, Client
from app.core.config import settings
import httpx

# Longer timeout to handle Render free-tier cold-start delays (default is ~5s, set to 30s)
_TIMEOUT = httpx.Timeout(30.0, connect=10.0)

def _make_client(key: str) -> Client:
    """Create a Supabase client with an extended HTTP timeout."""
    client = create_client(settings.SUPABASE_URL, key)
    # Patch the underlying httpx clients used by postgrest and auth
    try:
        client.postgrest.session.timeout = _TIMEOUT
    except Exception:
        pass
    try:
        client.auth._http_client.timeout = _TIMEOUT
    except Exception:
        pass
    return client

# Initialize the Supabase admin client with service role key
supabase: Client = _make_client(settings.SUPABASE_SERVICE_ROLE_KEY)
supabase_admin: Client = supabase

def get_supabase_client() -> Client:
    """Returns a fresh client instance for standard user auth operations."""
    key = settings.SUPABASE_ANON_KEY or settings.SUPABASE_SERVICE_ROLE_KEY
    return _make_client(key)

