package com.minimoney.app.presentation.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.minimoney.app.domain.auth.AuthError
import com.minimoney.app.domain.auth.AuthRepository
import com.minimoney.app.domain.auth.AuthResult
import dagger.hilt.android.lifecycle.HiltViewModel
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

    /** Credential Manager needs a Context, so the UI layer launches the sign-in flow and hands back just the outcome. */
    fun onSignInStarted() = _uiState.update { it.copy(isSubmitting = true, error = null) }

    fun onGoogleIdToken(idToken: String) {
        viewModelScope.launch {
            when (val result = authRepository.signInWithGoogle(idToken)) {
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

    fun onSignInFailed(error: AuthError) = _uiState.update { it.copy(isSubmitting = false, error = error) }
}
