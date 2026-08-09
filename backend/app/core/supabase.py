from supabase import create_client, Client
from app.core.config import settings

# Initialize the Supabase admin client with service role key
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
supabase_admin: Client = supabase

def get_supabase_client() -> Client:
    """Returns a fresh client instance for standard user auth operations."""
    key = settings.SUPABASE_ANON_KEY or settings.SUPABASE_SERVICE_ROLE_KEY
    return create_client(settings.SUPABASE_URL, key)

