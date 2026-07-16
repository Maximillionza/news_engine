package com.minimoney.app.presentation.auth

import com.minimoney.app.domain.auth.AuthError

/** Single immutable snapshot of the auth screen — just a Google Sign-In button and its outcome. */
data class AuthUiState(
    val isSubmitting: Boolean = false,
    val error: AuthError? = null,
)
