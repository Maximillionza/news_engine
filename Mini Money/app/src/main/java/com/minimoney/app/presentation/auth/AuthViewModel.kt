package com.minimoney.app.presentation.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.minimoney.app.domain.auth.AuthRepository
import com.minimoney.app.domain.auth.AuthResult
import com.minimoney.app.domain.auth.OtpChallenge
import com.minimoney.app.domain.auth.PhoneNumberValidator
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class AuthViewModel @Inject constructor(
    private val authRepository: AuthRepository,
) : ViewModel() {

    private val _uiState = MutableStateFlow(AuthUiState())
    val uiState: StateFlow<AuthUiState> = _uiState.asStateFlow()

    // Held outside UI state: the challenge id is a server credential the
    // composable has no business reading.
    private var challenge: OtpChallenge? = null
    private var countdownJob: Job? = null

    fun onPhoneChanged(value: String) {
        _uiState.update { it.copy(phoneInput = value, phoneInvalid = false, error = null) }
    }

    fun onSubmitPhone() {
        if (_uiState.value.isSubmitting) return
        // Validate/normalize before any network call — invalid input never
        // leaves the device.
        val validated = PhoneNumberValidator.validate(_uiState.value.phoneInput)
        if (validated !is PhoneNumberValidator.Result.Valid) {
            _uiState.update { it.copy(phoneInvalid = true) }
            return
        }
        requestOtp(validated.phoneE164)
    }

    fun onOtpChanged(value: String) {
        val digits = value.filter(Char::isDigit).take(OTP_LENGTH)
        _uiState.update { it.copy(otpInput = digits, error = null) }
    }

    fun onSubmitOtp() {
        val current = _uiState.value
        val activeChallenge = challenge ?: return
        if (!current.canSubmitOtp) return

        viewModelScope.launch {
            _uiState.update { it.copy(isSubmitting = true, error = null) }
            when (val result = authRepository.verifyOtp(activeChallenge.challengeId, current.otpInput)) {
                is AuthResult.Success ->
                    // Session is now persisted; the session-driven root
                    // (AppViewModel) routes to consent or home from there.
                    _uiState.update { it.copy(isSubmitting = false) }
                is AuthResult.Failure -> _uiState.update {
                    it.copy(isSubmitting = false, error = result.error)
                }
            }
        }
    }

    fun onResendOtp() {
        val activeChallenge = challenge ?: return
        if (!_uiState.value.canResend) return
        requestOtp(activeChallenge.phoneE164)
    }

    /** Back from OTP entry to phone entry; abandons the active challenge. */
    fun onEditPhone() {
        countdownJob?.cancel()
        challenge = null
        _uiState.update {
            it.copy(stage = AuthStage.PHONE, otpInput = "", error = null, resendSecondsRemaining = 0)
        }
    }

    private fun requestOtp(phoneE164: String) {
        viewModelScope.launch {
            _uiState.update { it.copy(isSubmitting = true, error = null) }
            when (val result = authRepository.requestOtp(phoneE164)) {
                is AuthResult.Success -> {
                    challenge = result.value
                    startResendCountdown(result.value.resendAllowedInSeconds)
                    _uiState.update {
                        it.copy(
                            isSubmitting = false,
                            stage = AuthStage.OTP,
                            maskedPhone = mask(phoneE164),
                            otpInput = "",
                        )
                    }
                }
                is AuthResult.Failure -> _uiState.update {
                    it.copy(isSubmitting = false, error = result.error)
                }
            }
        }
    }

    private fun startResendCountdown(seconds: Int) {
        countdownJob?.cancel()
        countdownJob = viewModelScope.launch {
            var remaining = seconds
            while (remaining > 0) {
                _uiState.update { it.copy(resendSecondsRemaining = remaining) }
                delay(1_000)
                remaining--
            }
            _uiState.update { it.copy(resendSecondsRemaining = 0) }
        }
    }

    /** +27821234567 -> +27••••••567 — enough for the parent to recognize the number. */
    private fun mask(phoneE164: String): String {
        if (phoneE164.length < 7) return phoneE164
        return phoneE164.take(3) + "•".repeat(phoneE164.length - 6) + phoneE164.takeLast(3)
    }

    companion object {
        const val OTP_LENGTH = 6
    }
}
