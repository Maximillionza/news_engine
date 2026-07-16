import { serviceClient, randomToken } from '../_shared/serviceClient.ts'
import { verifyGoogleIdToken, GoogleTokenVerificationError } from '../_shared/verifyGoogleIdToken.ts'
import { CURRENT_CONSENT_VERSION } from '../_shared/consentDocument.ts'

/**
 * POST /auth-google  { id_token: string }
 * Replaces the old phone+OTP flow entirely (decision: Google Sign-In only,
 * no dual auth paths to reconcile). Verifies the Google ID token, upserts a
 * parent_accounts row keyed on the token's stable `sub`, issues a fresh
 * app session token (invalidating any prior one — single active session),
 * and reports whether the CURRENT consent version is already accepted.
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
    const accessToken = randomToken()

    const { data, error } = await client
        .from('parent_accounts')
        .upsert(
            {
                google_sub: claims.sub,
                email: claims.email,
                display_name: claims.name ?? null,
                access_token: accessToken,
            },
            { onConflict: 'google_sub' },
        )
        .select('id, consent_version, consent_accepted_at')
        .single()

    if (error) {
        console.error('auth-google upsert failed', error)
        return Response.json({ error: 'internal_error' }, { status: 500 })
    }

    return Response.json({
        parent_account_id: data.id,
        access_token: accessToken,
        consent_complete: data.consent_version === CURRENT_CONSENT_VERSION,
    })
})
