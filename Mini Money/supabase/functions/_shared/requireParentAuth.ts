import type { SupabaseClient } from 'jsr:@supabase/supabase-js@2'

export interface ParentAccountRow {
    id: string
    google_sub: string
    email: string
    display_name: string | null
    access_token: string | null
    consent_version: string | null
    consent_accepted_at: string | null
}

/** Looks up the parent account owning this Bearer token, or null if missing/invalid. */
export async function requireParentAuth(
    req: Request,
    client: SupabaseClient,
): Promise<ParentAccountRow | null> {
    const header = req.headers.get('Authorization') ?? ''
    const token = header.startsWith('Bearer ') ? header.slice('Bearer '.length) : null
    if (!token) return null

    const { data, error } = await client
        .from('parent_accounts')
        .select('id, google_sub, email, display_name, access_token, consent_version, consent_accepted_at')
        .eq('access_token', token)
        .maybeSingle()

    if (error || !data) return null
    return data as ParentAccountRow
}
