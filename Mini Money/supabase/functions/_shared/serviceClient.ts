import { createClient } from 'jsr:@supabase/supabase-js@2'

/**
 * Service-role client — bypasses RLS entirely. Only ever used inside Edge
 * Functions (server-side); the key backing this must NEVER reach the
 * Android app or any client-side code. Both tables have RLS enabled with
 * no policies, so this is the only way anything reads or writes them.
 */
export function serviceClient() {
    return createClient(
        Deno.env.get('SUPABASE_URL')!,
        Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!,
    )
}

export function randomToken(): string {
    return crypto.randomUUID() + crypto.randomUUID()
}
