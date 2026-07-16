package com.minimoney.app.presentation.auth

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.minimoney.app.BuildConfig
import com.minimoney.app.R
import com.minimoney.app.domain.auth.AuthError
import kotlinx.coroutines.launch

/**
 * Stateful entry point. Parent-facing surface — all strings resolve from
 * strings_parent.xml. No navigation here: a successful verify persists the
 * session and the session-driven root (AppViewModel) swaps this screen out.
 */
@Composable
fun AuthRoute(viewModel: AuthViewModel = hiltViewModel()) {
    val state by viewModel.uiState.collectAsStateWithLifecycle()
    val context = LocalContext.current
    val scope = rememberCoroutineScope()

    // Splash is purely presentational — no session state involved — so plain
    // local state is enough to gate it (handoff §Screens 1).
    var splashDismissed by rememberSaveable { mutableStateOf(false) }
    if (!splashDismissed) {
        SplashScreen(onGetStarted = { splashDismissed = true })
        return
    }

    AuthScreen(
        state = state,
        onSignInClick = {
            viewModel.onSignInStarted()
            scope.launch {
                when (val outcome = launchGoogleSignIn(context, BuildConfig.GOOGLE_WEB_CLIENT_ID)) {
                    is GoogleSignInOutcome.Success -> viewModel.onGoogleIdToken(outcome.idToken)
                    is GoogleSignInOutcome.Failure -> viewModel.onSignInFailed(outcome.error)
                }
            }
        },
    )
}

/** Stateless and previewable; all state hoisted to the ViewModel (the sign-in launch itself needs a Context, hence AuthRoute owns it). */
@Composable
fun AuthScreen(
    state: AuthUiState,
    onSignInClick: () -> Unit,
) {
    val colors = com.minimoney.app.ui.theme.MiniMoneyTheme.colors
    Scaffold(containerColor = colors.background) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(horizontal = 24.dp),
            verticalArrangement = Arrangement.Center,
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Text(
                text = stringResource(R.string.parent_auth_title),
                style = MaterialTheme.typography.headlineMedium,
                color = colors.text,
            )
            Text(
                text = stringResource(R.string.parent_auth_subtitle),
                style = MaterialTheme.typography.bodyMedium,
                color = colors.textMuted,
                modifier = Modifier.padding(top = 8.dp, bottom = 24.dp),
            )
            Button(
                onClick = onSignInClick,
                enabled = !state.isSubmitting,
                shape = com.minimoney.app.ui.theme.PillShape,
                contentPadding = androidx.compose.foundation.layout.PaddingValues(vertical = 16.dp),
                modifier = Modifier.fillMaxWidth(),
            ) {
                if (state.isSubmitting) {
                    CircularProgressIndicator(
                        modifier = Modifier.padding(vertical = 2.dp),
                        strokeWidth = 2.dp,
                    )
                } else {
                    Text(stringResource(R.string.parent_auth_google_button))
                }
            }
            if (state.error != null) {
                Text(
                    text = stringResource(state.error.messageRes()),
                    color = MaterialTheme.colorScheme.error,
                    style = MaterialTheme.typography.bodySmall,
                    modifier = Modifier.padding(top = 12.dp),
                )
            }
        }
    }
}

/** Error → parent-facing copy. Lives at the UI edge so the ViewModel stays Android-free. */
private fun AuthError.messageRes(): Int = when (this) {
    AuthError.Network -> R.string.parent_auth_error_network
    AuthError.SignInCancelled -> R.string.parent_auth_error_cancelled
    AuthError.NoGoogleAccount -> R.string.parent_auth_error_no_account
    is AuthError.Server -> R.string.parent_auth_error_server
    is AuthError.Unknown -> R.string.parent_auth_error_unknown
}
