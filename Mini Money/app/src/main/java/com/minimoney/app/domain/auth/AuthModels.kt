package com.minimoney.app.domain.auth

/**
 * An authenticated parent session. `consentComplete` is carried on the
 * session because the POPIA consent flow is structurally separate from
 * registration — a verified session with consentComplete=false must be
 * routed to the consent flow, not into the app.
 */
data class ParentSession(
    val parentAccountId: String,
    val accessToken: String,
    val consentComplete: Boolean,
)

/** Failures the UI must distinguish; everything else collapses into Unknown. */
sealed interface AuthError {
    data object Network : AuthError
    /** The user dismissed the Google account picker or cancelled the flow. */
    data object SignInCancelled : AuthError
    /** No Google account is available/selectable on this device. */
    data object NoGoogleAccount : AuthError
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
