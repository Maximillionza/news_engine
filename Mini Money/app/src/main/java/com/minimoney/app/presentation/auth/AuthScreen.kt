package com.minimoney.app.presentation.auth

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.minimoney.app.R
import com.minimoney.app.domain.auth.AuthError

/**
 * Stateful entry point. Parent-facing surface — all strings resolve from
 * strings_parent.xml. No navigation here: a successful verify persists the
 * session and the session-driven root (AppViewModel) swaps this screen out.
 */
@Composable
fun AuthRoute(viewModel: AuthViewModel = hiltViewModel()) {
    // Lifecycle-aware collection: no state updates (or recompositions) while backgrounded.
    val state by viewModel.uiState.collectAsStateWithLifecycle()

    // Method references are stable across recompositions, keeping AuthScreen
    // and its children skippable — no lambda reallocation per frame.
    AuthScreen(
        state = state,
        onPhoneChanged = viewModel::onPhoneChanged,
        onSubmitPhone = viewModel::onSubmitPhone,
        onOtpChanged = viewModel::onOtpChanged,
        onSubmitOtp = viewModel::onSubmitOtp,
        onResendOtp = viewModel::onResendOtp,
        onEditPhone = viewModel::onEditPhone,
    )
}

/** Stateless and previewable; all state hoisted to the ViewModel. */
@Composable
fun AuthScreen(
    state: AuthUiState,
    onPhoneChanged: (String) -> Unit,
    onSubmitPhone: () -> Unit,
    onOtpChanged: (String) -> Unit,
    onSubmitOtp: () -> Unit,
    onResendOtp: () -> Unit,
    onEditPhone: () -> Unit,
) {
    Scaffold { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(horizontal = 24.dp),
            verticalArrangement = Arrangement.Center,
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            when (state.stage) {
                AuthStage.PHONE -> PhoneStage(
                    phoneInput = state.phoneInput,
                    phoneInvalid = state.phoneInvalid,
                    isSubmitting = state.isSubmitting,
                    error = state.error,
                    onPhoneChanged = onPhoneChanged,
                    onSubmitPhone = onSubmitPhone,
                )
                AuthStage.OTP -> OtpStage(
                    otpInput = state.otpInput,
                    maskedPhone = state.maskedPhone,
                    canSubmit = state.canSubmitOtp,
                    canResend = state.canResend,
                    resendSecondsRemaining = state.resendSecondsRemaining,
                    isSubmitting = state.isSubmitting,
                    error = state.error,
                    onOtpChanged = onOtpChanged,
                    onSubmitOtp = onSubmitOtp,
                    onResendOtp = onResendOtp,
                    onEditPhone = onEditPhone,
                )
            }
        }
    }
}

// Each stage takes only the fields it renders — a countdown tick recomposes
// OtpStage alone, never the whole screen tree.

@Composable
private fun PhoneStage(
    phoneInput: String,
    phoneInvalid: Boolean,
    isSubmitting: Boolean,
    error: AuthError?,
    onPhoneChanged: (String) -> Unit,
    onSubmitPhone: () -> Unit,
) {
    Text(
        text = stringResource(R.string.parent_auth_title),
        style = MaterialTheme.typography.headlineMedium,
    )
    Text(
        text = stringResource(R.string.parent_auth_subtitle),
        style = MaterialTheme.typography.bodyMedium,
        modifier = Modifier.padding(top = 8.dp, bottom = 24.dp),
    )
    OutlinedTextField(
        value = phoneInput,
        onValueChange = onPhoneChanged,
        label = { Text(stringResource(R.string.parent_auth_phone_label)) },
        placeholder = { Text(stringResource(R.string.parent_auth_phone_placeholder)) },
        isError = phoneInvalid,
        supportingText = if (phoneInvalid) {
            { Text(stringResource(R.string.parent_auth_phone_invalid)) }
        } else null,
        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Phone),
        singleLine = true,
        enabled = !isSubmitting,
        modifier = Modifier.fillMaxWidth(),
    )
    ErrorText(error)
    SubmitButton(
        textRes = R.string.parent_auth_continue,
        enabled = !isSubmitting && phoneInput.isNotBlank(),
        isSubmitting = isSubmitting,
        onClick = onSubmitPhone,
    )
}

@Composable
private fun OtpStage(
    otpInput: String,
    maskedPhone: String?,
    canSubmit: Boolean,
    canResend: Boolean,
    resendSecondsRemaining: Int,
    isSubmitting: Boolean,
    error: AuthError?,
    onOtpChanged: (String) -> Unit,
    onSubmitOtp: () -> Unit,
    onResendOtp: () -> Unit,
    onEditPhone: () -> Unit,
) {
    Text(
        text = stringResource(R.string.parent_auth_otp_title),
        style = MaterialTheme.typography.headlineMedium,
    )
    if (maskedPhone != null) {
        Text(
            text = stringResource(R.string.parent_auth_otp_sent_to, maskedPhone),
            style = MaterialTheme.typography.bodyMedium,
            modifier = Modifier.padding(top = 8.dp),
        )
    }
    OutlinedTextField(
        value = otpInput,
        onValueChange = onOtpChanged,
        label = { Text(stringResource(R.string.parent_auth_otp_label)) },
        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.NumberPassword),
        singleLine = true,
        enabled = !isSubmitting,
        modifier = Modifier
            .fillMaxWidth()
            .padding(top = 24.dp),
    )
    ErrorText(error)
    SubmitButton(
        textRes = R.string.parent_auth_verify,
        enabled = canSubmit,
        isSubmitting = isSubmitting,
        onClick = onSubmitOtp,
    )
    TextButton(onClick = onResendOtp, enabled = canResend) {
        Text(
            text = if (resendSecondsRemaining > 0) {
                stringResource(R.string.parent_auth_resend_in, resendSecondsRemaining)
            } else {
                stringResource(R.string.parent_auth_resend)
            },
        )
    }
    TextButton(onClick = onEditPhone, enabled = !isSubmitting) {
        Text(stringResource(R.string.parent_auth_edit_number))
    }
}

@Composable
private fun ErrorText(error: AuthError?) {
    if (error == null) return
    Text(
        text = stringResource(error.messageRes()),
        color = MaterialTheme.colorScheme.error,
        style = MaterialTheme.typography.bodySmall,
        modifier = Modifier.padding(top = 12.dp),
    )
}

@Composable
private fun SubmitButton(
    textRes: Int,
    enabled: Boolean,
    isSubmitting: Boolean,
    onClick: () -> Unit,
) {
    Button(
        onClick = onClick,
        enabled = enabled,
        modifier = Modifier
            .fillMaxWidth()
            .padding(top = 16.dp),
    ) {
        if (isSubmitting) {
            CircularProgressIndicator(
                modifier = Modifier.padding(vertical = 2.dp),
                strokeWidth = 2.dp,
            )
        } else {
            Text(stringResource(textRes))
        }
    }
}

/** Error → parent-facing copy. Lives at the UI edge so the ViewModel stays Android-free. */
private fun AuthError.messageRes(): Int = when (this) {
    AuthError.Network -> R.string.parent_auth_error_network
    AuthError.InvalidPhoneNumber -> R.string.parent_auth_error_invalid_phone
    AuthError.OtpMismatch -> R.string.parent_auth_error_otp_mismatch
    AuthError.OtpExpired -> R.string.parent_auth_error_otp_expired
    AuthError.TooManyAttempts -> R.string.parent_auth_error_too_many
    is AuthError.Server -> R.string.parent_auth_error_server
    is AuthError.Unknown -> R.string.parent_auth_error_unknown
}
