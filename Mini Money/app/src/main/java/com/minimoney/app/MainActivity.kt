package com.minimoney.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.minimoney.app.presentation.AppViewModel
import com.minimoney.app.presentation.ParentNavGraph
import com.minimoney.app.presentation.RootDestination
import com.minimoney.app.presentation.auth.AuthRoute
import com.minimoney.app.presentation.consent.ConsentRoute
import com.minimoney.app.ui.theme.MiniMoneyTheme
import dagger.hilt.android.AndroidEntryPoint

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MiniMoneyRoot()
        }
    }
}

/** Top-level routing is a pure function of session state — see AppViewModel. */
@Composable
private fun MiniMoneyRoot(appViewModel: AppViewModel = hiltViewModel()) {
    val destination by appViewModel.destination.collectAsStateWithLifecycle()
    val darkModeChoice by appViewModel.darkMode.collectAsStateWithLifecycle()

    // Dark-first design: the Profile toggle's persisted choice wins; before
    // any choice is made we follow the system (handoff §Visual Direction).
    MiniMoneyTheme(darkTheme = darkModeChoice ?: isSystemInDarkTheme()) {
        when (destination) {
            RootDestination.LOADING -> Box(Modifier.fillMaxSize())
            RootDestination.AUTH -> AuthRoute()
            RootDestination.CONSENT -> ConsentRoute()
            RootDestination.HOME -> ParentNavGraph()
        }
    }
}
