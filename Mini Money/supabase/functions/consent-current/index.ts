import { CURRENT_CONSENT_DOCUMENT } from '../_shared/consentDocument.ts'

/** GET /consent-current — public, not account-specific. */
Deno.serve((req) => {
    if (req.method !== 'GET') return new Response('Method not allowed', { status: 405 })
    return Response.json(CURRENT_CONSENT_DOCUMENT)
})
