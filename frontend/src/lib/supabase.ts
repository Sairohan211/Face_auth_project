import { createClient, type SupabaseClient } from '@supabase/supabase-js'

const rawUrl = import.meta.env.VITE_SUPABASE_URL || ''
const rawKey =
  import.meta.env.VITE_SUPABASE_ANON_KEY ||
  import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY ||
  ''

const isValidUrl = Boolean(rawUrl && rawUrl.startsWith('http') && rawUrl !== 'YOUR_SUPABASE_PROJECT_URL')
const isValidKey = Boolean(rawKey && rawKey !== 'YOUR_SUPABASE_PUBLISHABLE_KEY')

// Fallback to project defaults if env variables are missing or placeholders
const supabaseUrl = isValidUrl ? rawUrl : 'https://obbgczntnnwitcmogdig.supabase.co'
const supabaseAnonKey = isValidKey ? rawKey : 'sb_publishable_AugMDSx73ONyahKZmLS2Tw_6363-rzn'

export const supabase: SupabaseClient = createClient(supabaseUrl, supabaseAnonKey)
