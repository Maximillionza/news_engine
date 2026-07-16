package com.minimoney.app.presentation.profile

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.minimoney.app.R
import com.minimoney.app.data.settings.ThemeStore
import com.minimoney.app.domain.auth.AuthRepository
import com.minimoney.app.domain.child.ChildRepository
import com.minimoney.app.ui.theme.CardShape
import com.minimoney.app.ui.theme.MiniMoneyTheme
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class ProfileViewModel @Inject constructor(
    private val authRepository: AuthRepository,
    private val themeStore: ThemeStore,
    childRepository: ChildRepository,
) : ViewModel() {

    val childCount: StateFlow<Int> = childRepository.children()
        .map { it.size }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), 0)

    val darkMode: StateFlow<Boolean?> = themeStore.darkMode
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), null)

    fun onDarkModeToggled(enabled: Boolean) {
        viewModelScope.launch { themeStore.setDarkMode(enabled) }
    }

    /** Session clear routes the whole app back to AUTH via AppViewModel — no nav call needed. */
    fun onSignOut() {
        viewModelScope.launch { authRepository.signOut() }
    }
}

/** Profile (handoff §Screens 9) — settings-level surface: theme toggle, sign out. */
@Composable
fun ProfileRoute(viewModel: ProfileViewModel = hiltViewModel()) {
    val colors = MiniMoneyTheme.colors
    val childCount by viewModel.childCount.collectAsStateWithLifecycle()
    val darkMode by viewModel.darkMode.collectAsStateWithLifecycle()

    Scaffold(containerColor = colors.background) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(horizontal = 20.dp),
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.padding(vertical = 20.dp),
            ) {
                Box(
                    modifier = Modifier
                        .size(56.dp)
                        .background(colors.accentGradient, CircleShape),
                    contentAlignment = Alignment.Center,
                ) {
                    Text("M", color = Color.White, fontWeight = FontWeight.ExtraBold, fontSize = 22.sp)
                }
                Column(Modifier.padding(start = 12.dp)) {
                    Text(
                        text = stringResource(R.string.parent_profile_greeting),
                        color = colors.text,
                        fontSize = 17.sp,
                        fontWeight = FontWeight.ExtraBold,
                    )
                    Text(
                        text = stringResource(R.string.parent_profile_signed_in_google),
                        color = colors.textMuted,
                        fontSize = 13.sp,
                    )
                }
            }
            Row(
                horizontalArrangement = Arrangement.SpaceBetween,
                modifier = Modifier
                    .fillMaxWidth()
                    .background(colors.surface, CardShape)
                    .padding(18.dp),
            ) {
                Column {
                    Text(
                        text = stringResource(R.string.parent_profile_children_linked),
                        color = colors.textMuted,
                        fontSize = 12.sp,
                    )
                    Text(
                        text = childCount.toString(),
                        color = colors.text,
                        fontSize = 22.sp,
                        fontWeight = FontWeight.ExtraBold,
                    )
                }
            }
            Column(Modifier.padding(top = 20.dp)) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(vertical = 6.dp),
                ) {
                    Text(
                        text = stringResource(R.string.parent_profile_dark_mode),
                        color = colors.text,
                        modifier = Modifier.weight(1f),
                    )
                    Switch(
                        checked = darkMode ?: true, // dark-first default
                        onCheckedChange = viewModel::onDarkModeToggled,
                    )
                }
                HorizontalDivider(color = colors.divider)
                TextButton(
                    onClick = viewModel::onSignOut,
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = 8.dp),
                ) {
                    Text(
                        text = stringResource(R.string.parent_profile_sign_out),
                        color = MaterialTheme.colorScheme.error,
                        fontWeight = FontWeight.Bold,
                    )
                }
            }
        }
    }
}
