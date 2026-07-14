package com.minimoney.app.presentation.consent

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.minimoney.app.domain.auth.AuthRepository
import com.minimoney.app.domain.consent.ConsentDocument
import com.minimoney.app.domain.consent.ConsentRepository
import com.minimoney.app.domain.core.AppError
import com.minimoney.app.domain.core.AppResult
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

data class ConsentUiState(
    val isLoading: Boolean = true,
    val document: ConsentDocument? = null,
    val loadError: AppError? = null,
    val ackChecked: Boolean = false,
    val isSubmitting: Boolean = false,
    val submitError: AppError? = null,
) {
    val canAccept: Boolean
        get() = document != null && ackChecked && !isSubmitting
}

/**
 * No navigation effects here: accepting flips the persisted session's
 * consentComplete flag and declining clears the session — the session-driven
 * root (AppViewModel) reacts to both. This screen cannot route anywhere on
 * its own, which is the point: the consent gate is not bypassable from UI code.
 */
@HiltViewModel
class ConsentViewModel @Inject constructor(
    private val consentRepository: ConsentRepository,
    private val authRepository: AuthRepository,
) : ViewModel() {

    private val _uiState = MutableStateFlow(ConsentUiState())
    val uiState: StateFlow<ConsentUiState> = _uiState.asStateFlow()

    init {
        loadDocument()
    }

    fun onRetry() = loadDocument()

    fun onAckToggled(checked: Boolean) {
        _uiState.update { it.copy(ackChecked = checked, submitError = null) }
    }

    fun onAccept() {
        val state = _uiState.value
        val document = state.document ?: return
        if (!state.canAccept) return

        viewModelScope.launch {
            _uiState.update { it.copy(isSubmitting = true, submitError = null) }
            when (val result = consentRepository.acceptConsent(document.version)) {
                is AppResult.Success ->
                    // Session flag now flipped; the root will swap this screen out.
                    _uiState.update { it.copy(isSubmitting = false) }
                is AppResult.Failure -> {
                    _uiState.update { it.copy(isSubmitting = false, submitError = result.error) }
                    // Version changed under us: re-consent against the new text
                    // (BuildSpec §Compliance). Reload so the parent sees what
                    // they are actually agreeing to; the ack resets with it.
                    if (result.error == AppError.Conflict) loadDocument()
                }
            }
        }
    }

    /** Declining consent means the account cannot be used — sign out. */
    fun onDecline() {
        viewModelScope.launch { authRepository.signOut() }
    }

    private fun loadDocument() {
        viewModelScope.launch {
            _uiState.update {
                it.copy(isLoading = true, loadError = null, ackChecked = false)
            }
            when (val result = consentRepository.getCurrentDocument()) {
                is AppResult.Success -> _uiState.update {
                    it.copy(isLoading = false, document = result.value)
                }
                is AppResult.Failure -> _uiState.update {
                    it.copy(isLoading = false, loadError = result.error)
                }
            }
        }
    }
}
