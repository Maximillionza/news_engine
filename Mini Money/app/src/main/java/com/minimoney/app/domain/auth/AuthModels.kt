package com.minimoney.app.domain.auth

/**
 * A pending OTP verification, returned when an OTP is dispatched to the
 * parent's phone. `challengeId` ties the later verify call to this dispatch
 * so the code alone is never sufficient server-side.
 */
data class OtpChallenge(
    val challengeId: String,
    val phoneE164: String,
    val expiresInSeconds: Int,
    val resendAllowedInSeconds: Int,
)

/**
 * An authenticated parent session. Registration is complete only once the
 * OTP is verified (BuildSpec §Compliance: registration cannot complete
 * without a verified OTP match).
 *
 * `consentComplete` is carried on the session because the POPIA consent flow
 * is structurally separate from registration — a verified session with
 * consentComplete=false must be routed to the consent flow, not into the app.
 */
data class ParentSession(
    val parentAccountId: String,
    val accessToken: String,
    val consentComplete: Boolean,
)

/** Failures the UI must distinguish; everything else collapses into Unknown. */
sealed interface AuthError {
    data object Network : AuthError
    data object InvalidPhoneNumber : AuthError
    data object OtpMismatch : AuthError
    data object OtpExpired : AuthError
    data object TooManyAttempts : AuthError
    data class Server(val httpCode: Int) : AuthError
    data class Unknown(val cause: Throwable? = null) : AuthError
}

sealed interface AuthResult<out T> {
    data class Success<T>(val value: T) : AuthResult<T>
    data class Failure(val error: AuthError) : AuthResult<Nothing>
}

inline fun <T, R> AuthResult<T>.map(transform: (T) -> R): AuthResult<R> = when (this) {
    is AuthResult.Success -> AuthResult.Success(transform(value))
    is AuthResult.Failure -> this
}
