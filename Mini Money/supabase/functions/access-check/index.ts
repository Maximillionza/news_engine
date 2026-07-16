import { serviceClient } from '../_shared/serviceClient.ts'
import { verifyGoogleIdToken, GoogleTokenVerificationError } from '../_shared/verifyGoogleIdToken.ts'

/**
 * POST /access-check  { id_token: string }
 * Called on every app launch on a device signed into a Google account that
 * is NOT a registered parent. Three outcomes:
 *  - already CLAIMED (google_sub matches a prior claim) -> allowed
 *  - a PENDING row matches this verified email -> claim it now, allowed
 *  - neither -> not allowed ("Request access from a parent to use the app")
 *
 * The claim step uses a single conditional UPDATE so two simultaneous first
 * sign-ins on the same pending row can't both "win" — Postgres serializes
 * concurrent UPDATEs to the same row, so only one succeeds.
 */
Deno.serve(async (req) => {
    if (req.method !== 'POST') return new Response('Method not allowed', { status: 405 })

    let body: { id_token?: string }
    try {
        body = await req.json()
    } catch {
        return Response.json({ error: 'invalid_json' }, { status: 400 })
    }
    if (!body.id_token) return Response.json({ error: 'missing id_token' }, { status: 400 })

    let claims
    try {
        claims = await verifyGoogleIdToken(body.id_token)
    } catch (e) {
        if (e instanceof GoogleTokenVerificationError) {
            return Response.json({ error: e.message }, { status: 401 })
        }
        throw e
    }

    const client = serviceClient()

    const existing = await client
        .from('child_links')
        .select('id, parent_account_id, display_name, age_band')
        .eq('google_sub', claims.sub)
        .maybeSingle()

    if (existing.error) {
        console.error('access-check lookup failed', existing.error)
        return Response.json({ error: 'internal_error' }, { status: 500 })
    }
    if (existing.data) {
        return Response.json({
            allowed: true,
            status: 'linked',
            parent_account_id: existing.data.parent_account_id,
            display_name: existing.data.display_name,
            age_band: existing.data.age_band,
        })
    }

    const claim = await client
        .from('child_links')
        .update({ google_sub: claims.sub, claimed_at: new Date().toISOString() })
        .eq('email', claims.email.toLowerCase())
        .is('google_sub', null)
        .select('id, parent_account_id, display_name, age_band')
        .maybeSingle()

    if (claim.error) {
        console.error('access-check claim failed', claim.error)
        return Response.json({ error: 'internal_error' }, { status: 500 })
    }
    if (claim.data) {
        return Response.json({
            allowed: true,
            status: 'linked',
            parent_account_id: claim.data.parent_account_id,
            display_name: claim.data.display_name,
            age_band: claim.data.age_band,
        })
    }

    return Response.json({ allowed: false, status: 'not_linked' })
})
