package com.minimoney.app.presentation.auth

import com.minimoney.app.domain.auth.AuthError

enum class AuthStage { PHONE, OTP }

/**
 * Single immutable snapshot of the auth screen. One state object (rather than
 * separate flows per field) so the UI can never observe a torn combination,
 * e.g. stage=OTP with a stale phone error.
 */
data class AuthUiState(
    val stage: AuthStage = AuthStage.PHONE,
    val phoneInput: String = "",
    val phoneInvalid: Boolean = false,
    val otpInput: String = "",
    val maskedPhone: String? = null,
    val isSubmitting: Boolean = false,
    val resendSecondsRemaining: Int = 0,
    val error: AuthError? = null,
) {
    val canSubmitOtp: Boolean
        get() = otpInput.length == AuthViewModel.OTP_LENGTH && !isSubmitting

    val canResend: Boolean
        get() = resendSecondsRemaining == 0 && !isSubmitting
}
