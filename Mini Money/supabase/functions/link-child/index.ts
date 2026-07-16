import { serviceClient } from '../_shared/serviceClient.ts'
import { requireParentAuth } from '../_shared/requireParentAuth.ts'

const VALID_AGE_BANDS = ['SIX_TO_NINE', 'TEN_TO_FOURTEEN', 'FIFTEEN_TO_EIGHTEEN']
const MAX_CHILDREN_PER_PARENT = 4 // mirrors app.domain.child.MAX_CHILDREN_PER_PARENT

/**
 * POST /link-child  { email: string, display_name?: string, age_band: string }
 * Parent-authenticated. Creates a PENDING child_links row — google_sub is
 * filled in later, the first time a device actually signs in with this
 * email (see access-check). Until then the child sees "request access".
 */
Deno.serve(async (req) => {
    if (req.method !== 'POST') return new Response('Method not allowed', { status: 405 })

    const client = serviceClient()
    const parent = await requireParentAuth(req, client)
    if (!parent) return Response.json({ error: 'unauthorized' }, { status: 401 })

    let body: { email?: string; display_name?: string; age_band?: string }
    try {
        body = await req.json()
    } catch {
        return Response.json({ error: 'invalid_json' }, { status: 400 })
    }
    const email = body.email?.trim().toLowerCase()
    if (!email || !email.includes('@')) {
        return Response.json({ error: 'invalid_email' }, { status: 400 })
    }
    if (!body.age_band || !VALID_AGE_BANDS.includes(body.age_band)) {
        return Response.json({ error: 'invalid_age_band' }, { status: 400 })
    }

    const { count, error: countError } = await client
        .from('child_links')
        .select('id', { count: 'exact', head: true })
        .eq('parent_account_id', parent.id)
    if (countError) {
        console.error('link-child count failed', countError)
        return Response.json({ error: 'internal_error' }, { status: 500 })
    }
    if ((count ?? 0) >= MAX_CHILDREN_PER_PARENT) {
        return Response.json({ error: 'child_limit_reached' }, { status: 409 })
    }

    const { data, error } = await client
        .from('child_links')
        .insert({
            parent_account_id: parent.id,
            email,
            display_name: body.display_name ?? null,
            age_band: body.age_band,
        })
        .select('id, email, display_name, age_band, created_at')
        .single()

    if (error) {
        // Most likely: this email is already claimed/pending under a DIFFERENT parent
        // (google_sub uniqueness doesn't catch this pre-claim, but a parent shouldn't
        // silently steal another family's pending link either) — surface as a conflict.
        if (error.code === '23505') {
            return Response.json({ error: 'already_linked' }, { status: 409 })
        }
        console.error('link-child insert failed', error)
        return Response.json({ error: 'internal_error' }, { status: 500 })
    }

    return Response.json({
        child_link_id: data.id,
        email: data.email,
        display_name: data.display_name,
        age_band: data.age_band,
        status: 'pending',
    })
})
