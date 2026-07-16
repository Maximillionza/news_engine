/**
 * Verifies a Google ID token server-side via Google's tokeninfo endpoint —
 * this validates the signature, issuer, and expiry for us (avoids pulling in
 * a JWKS/JWT library for a Deno Edge Function). CRITICAL: `aud` must be
 * checked against our own OAuth client ID(s) — without that check, a token
 * minted for a completely different app would be accepted here too.
 *
 * Two client IDs are expected (both from the same Google Cloud project):
 * one for the Android app itself (audience on tokens obtained via Credential
 * Manager) and, optionally, a web client ID if a companion web flow is ever
 * added. Set MINIMONEY_GOOGLE_CLIENT_IDS as a comma-separated list.
 */
export interface GoogleIdTokenClaims {
    sub: string
    email: string
    email_verified: boolean
    name?: string
    aud: string
    exp: number
}

export class GoogleTokenVerificationError extends Error {}

export async function verifyGoogleIdToken(idToken: string): Promise<GoogleIdTokenClaims> {
    const allowedAudiences = (Deno.env.get('MINIMONEY_GOOGLE_CLIENT_IDS') ?? '')
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean)
    if (allowedAudiences.length === 0) {
        throw new GoogleTokenVerificationError('MINIMONEY_GOOGLE_CLIENT_IDS is not configured')
    }

    const res = await fetch(
        `https://oauth2.googleapis.com/tokeninfo?id_token=${encodeURIComponent(idToken)}`,
    )
    if (!res.ok) {
        throw new GoogleTokenVerificationError('Google rejected the ID token (invalid signature, expired, or malformed)')
    }
    const claims = await res.json() as GoogleIdTokenClaims & { email_verified: string | boolean }

    if (!allowedAudiences.includes(claims.aud)) {
        throw new GoogleTokenVerificationError('Token audience does not match this app\'s OAuth client ID')
    }
    // Google's tokeninfo endpoint returns email_verified as a string ("true"/"false"), not a boolean.
    const emailVerified = claims.email_verified === true || claims.email_verified === 'true'
    if (!emailVerified) {
        throw new GoogleTokenVerificationError('Google account email is not verified')
    }

    return { ...claims, email_verified: emailVerified }
}
