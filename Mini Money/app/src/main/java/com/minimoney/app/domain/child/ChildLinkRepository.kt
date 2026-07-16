package com.minimoney.app.domain.child

import com.minimoney.app.domain.core.AppResult

/**
 * Registers a child's Google account email as a PENDING link (server-side —
 * see supabase/functions/link-child). The link is CLAIMED automatically the
 * first time a device signs in with that email; until then the child's
 * device shows "Request access from a parent to use the app". This is
 * separate from ChildRepository: that creates the LOCAL ChildProfile row
 * used by the core mechanic (tasks, Mbucks); this is the identity-linking
 * layer only (see supabase/README.md's scope boundary note).
 */
interface ChildLinkRepository {
    /** Fails with AppError.Conflict if this email is already linked/pending elsewhere. */
    suspend fun linkChild(email: String, displayName: String?, ageBand: AgeBand): AppResult<Unit>
}
