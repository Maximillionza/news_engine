package com.minimoney.app.domain.auth

import kotlinx.coroutines.flow.Flow

interface AuthRepository {

    /**
     * The persisted session, or null when signed out. Emits on every change
     * so the UI layer can react to sign-in/sign-out without polling.
     */
    val session: Flow<ParentSession?>

    /**
     * Verifies a Google ID token (obtained via Credential Manager at the UI
     * layer — token acquisition needs an Activity context, so it never
     * belongs in this Android-free domain layer) against the backend, which
     * re-verifies it server-side before trusting anything in it. Persists
     * the session only after a fully successful verify.
     */
    suspend fun signInWithGoogle(googleIdToken: String): AuthResult<ParentSession>

    suspend fun signOut()
}
