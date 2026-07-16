package com.minimoney.app.presentation

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.minimoney.app.data.settings.ThemeStore
import com.minimoney.app.domain.auth.AuthRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import javax.inject.Inject

enum class RootDestination { LOADING, AUTH, CONSENT, HOME }

/**
 * Single navigation authority. The top-level destination is a pure function of
 * the persisted session, so the consent gate (BuildSpec §Compliance: a verified
 * session without completed consent never reaches the app) holds across process
 * death and cannot be skipped by screen-level code.
 */
@HiltViewModel
class AppViewModel @Inject constructor(
    authRepository: AuthRepository,
    private val themeStore: ThemeStore,
) : ViewModel() {

    val destination: StateFlow<RootDestination> = authRepository.session
        .map { session ->
            when {
                session == null -> RootDestination.AUTH
                !session.consentComplete -> RootDestination.CONSENT
                else -> RootDestination.HOME
            }
        }
        .stateIn(
            scope = viewModelScope,
            started = SharingStarted.WhileSubscribed(5_000),
            // LOADING until the first DataStore read lands — avoids flashing
            // the auth screen at an already-signed-in parent on cold start.
            initialValue = RootDestination.LOADING,
        )

    /** Null = no explicit choice yet; the theme falls back to the system setting. */
    val darkMode: StateFlow<Boolean?> = themeStore.darkMode
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), null)

    fun onDarkModeChanged(enabled: Boolean) {
        viewModelScope.launch { themeStore.setDarkMode(enabled) }
    }
}
