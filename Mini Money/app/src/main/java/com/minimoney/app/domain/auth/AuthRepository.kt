package com.minimoney.app.domain.auth

import kotlinx.coroutines.flow.Flow

interface AuthRepository {

    /**
     * The persisted session, or null when signed out. Emits on every change
     * so the UI layer can react to sign-in/sign-out without polling.
     */
    val session: Flow<ParentSession?>

    /** Dispatches an OTP to the given number. Expects E.164 (+27...) input —
     *  validate/normalize with [PhoneNumberValidator] before calling. */
    suspend fun requestOtp(phoneE164: String): AuthResult<OtpChallenge>

    /** Verifies the code against the challenge; persists the session on success. */
    suspend fun verifyOtp(challengeId: String, code: String): AuthResult<ParentSession>

    suspend fun signOut()
}
