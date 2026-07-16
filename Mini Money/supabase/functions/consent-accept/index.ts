import { serviceClient } from '../_shared/serviceClient.ts'
import { requireParentAuth } from '../_shared/requireParentAuth.ts'
import { CURRENT_CONSENT_VERSION } from '../_shared/consentDocument.ts'

/**
 * POST /consent-accept  { document_version: string }
 * 409 if the submitted version isn't the one currently in force (the
 * document changed underneath the parent mid-flow — they must re-read).
 */
Deno.serve(async (req) => {
    if (req.method !== 'POST') return new Response('Method not allowed', { status: 405 })

    const client = serviceClient()
    const parent = await requireParentAuth(req, client)
    if (!parent) return Response.json({ error: 'unauthorized' }, { status: 401 })

    let body: { document_version?: string }
    try {
        body = await req.json()
    } catch {
        return Response.json({ error: 'invalid_json' }, { status: 400 })
    }
    if (body.document_version !== CURRENT_CONSENT_VERSION) {
        return Response.json({ error: 'stale_version' }, { status: 409 })
    }

    const acceptedAt = new Date().toISOString()
    const { error } = await client
        .from('parent_accounts')
        .update({ consent_version: CURRENT_CONSENT_VERSION, consent_accepted_at: acceptedAt })
        .eq('id', parent.id)

    if (error) {
        console.error('consent-accept update failed', error)
        return Response.json({ error: 'internal_error' }, { status: 500 })
    }

    return Response.json({
        document_version: CURRENT_CONSENT_VERSION,
        accepted_at_epoch_millis: Date.parse(acceptedAt),
    })
})
